import logging
from datetime import datetime, timezone
from urllib.parse import urlparse

import httpx
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from core.celery_client import celery_client
from core.constants import CampaignStatus, SubmissionStatus
from core.database import get_db
from core.security import get_current_hacker
from models import Campaign, Submission
from models.hacker import Hacker
from schemas import SubmissionCreate, SubmissionResponse

logger = logging.getLogger(__name__)

router = APIRouter(tags=["submissions"])


async def _verify_repo_access(hacker: Hacker, github_url: str) -> None:
    parsed = urlparse(github_url)
    parts = [p for p in parsed.path.split("/") if p]
    if parsed.hostname not in ("github.com", "www.github.com") or len(parts) < 2:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="github_url must be a GitHub repository URL",
        )
    owner, repo = parts[0], parts[1].removesuffix(".git")

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(
                f"https://api.github.com/repos/{owner}/{repo}",
                headers={
                    "Authorization": f"Bearer {hacker.github_token}",
                    "Accept": "application/vnd.github+json",
                },
            )
    except httpx.HTTPError:
        logger.warning("Repo access check unavailable for %s/%s", owner, repo)
        return

    if resp.status_code == 401:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="GitHub token expired; please re-authenticate",
        )
    if resp.status_code == 404:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Repository {owner}/{repo} not found or not accessible to you",
        )
    if resp.status_code != 200:
        logger.warning(
            "Repo access check got %s for %s/%s", resp.status_code, owner, repo
        )
        return
    if not resp.json().get("permissions", {}).get("push", False):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"You must have push access to {owner}/{repo} to submit it",
        )


@router.post(
    "/campaigns/{campaign_id}/submit",
    response_model=SubmissionResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def submit_project(
    campaign_id: int,
    payload: SubmissionCreate,
    db: AsyncSession = Depends(get_db),
    current_hacker: Hacker = Depends(get_current_hacker)
) -> Submission:
    campaign = await db.get(Campaign, campaign_id)
    if campaign is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Campaign {campaign_id} not found",
        )
    if campaign.status != CampaignStatus.OPEN.value:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"Campaign {campaign_id} is not accepting submissions "
                f"(status: {campaign.status})"
            ),
        )


    if payload.team_size > campaign.max_team_size:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"Team size {payload.team_size} exceeds the maximum of "
                f"{campaign.max_team_size} for this campaign"
            ),
        )

    if not campaign.allow_late_submissions and datetime.now(timezone.utc) > campaign.deadline:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"The deadline for campaign {campaign_id} has passed "
                "and late submissions are not allowed"
            ),
        )

    team_submission_count = await db.scalar(
        select(func.count(Submission.id)).where(
            Submission.campaign_id == campaign_id,
            func.lower(Submission.team_name) == payload.team_name.strip().lower(),
        )
    )
    if team_submission_count >= campaign.max_submissions_per_team:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"Team '{payload.team_name}' has reached the maximum of "
                f"{campaign.max_submissions_per_team} submission(s) for this campaign"
            ),
        )

    await _verify_repo_access(current_hacker, str(payload.github_url))

    submission = Submission(
        campaign_id=campaign_id,
        hacker_id=current_hacker.id,
        team_name=payload.team_name,
        team_size=payload.team_size,
        github_url=str(payload.github_url),
        pitch_text=payload.pitch_text,
        status=SubmissionStatus.PENDING.value,
    )
    db.add(submission)
    await db.commit()
    await db.refresh(submission)

    try:
        celery_client.send_task("evaluate_submission", args=[submission.id])
    except Exception:
        logger.exception(
            "Broker dispatch failed for submission %s", submission.id
        )
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=(
                f"Submission {submission.id} was saved but could not be queued "
                "for evaluation. It remains 'pending'; retry queueing later."
            ),
        )

    return submission


@router.get("/submissions/{submission_id}", response_model=SubmissionResponse)
async def get_submission(
    submission_id: int, db: AsyncSession = Depends(get_db)
) -> Submission:
    submission = await db.get(Submission, submission_id)
    if submission is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Submission {submission_id} not found",
        )
    return submission
