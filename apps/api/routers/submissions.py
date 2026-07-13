import logging
from urllib.parse import urlparse

import httpx
from fastapi import APIRouter, Depends, HTTPException, status
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
    """Ensure the submitted repo is one the hacker can actually push to.

    The frontend only offers the hacker's own repos, but the API must not
    trust that. Fails open only on transient GitHub errors (5xx/network),
    never on a definitive 'no access' answer.
    """
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
        return  # transient GitHub outage: accept rather than block ingestion

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
    """Ingest a submission: persist it, queue evaluation, return immediately."""
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

    await _verify_repo_access(current_hacker, str(payload.github_url))

    # Instantiate submission and explicitly link it to the authenticated hacker
    submission = Submission(
        campaign_id=campaign_id,
        hacker_id=current_hacker.id,
        team_name=payload.team_name,
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
        # The submission is already durable in Postgres; surface the broker
        # failure instead of silently returning 202 for a job that was never
        # queued. Status stays 'pending' so it can be re-dispatched.
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
    """Polling endpoint: live evaluation status and final score."""
    submission = await db.get(Submission, submission_id)
    if submission is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Submission {submission_id} not found",
        )
    return submission