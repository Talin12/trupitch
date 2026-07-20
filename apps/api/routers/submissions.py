"""Submission ingestion and polling.

Mounted with no extra prefix by main.py (unlike the other routers), so
the two routes below are literally /api/campaigns/{id}/submit and
/api/submissions/{id} — the campaign one lives here rather than in
campaigns.py because it's about hackers submitting, not organizers
managing campaigns.
"""

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
    """Ensure the submitted repo is one the hacker can actually push to.

    The frontend only offers the hacker's own repos, but the API must not
    trust that. Fails open only on transient GitHub errors (5xx/network),
    never on a definitive 'no access' answer.
    """
    # Extract "owner" and "repo" from a URL like
    # https://github.com/owner/repo(.git)? — anything that isn't
    # shaped like that is rejected before we ever call GitHub.
    parsed = urlparse(github_url)
    parts = [p for p in parsed.path.split("/") if p]
    if parsed.hostname not in ("github.com", "www.github.com") or len(parts) < 2:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="github_url must be a GitHub repository URL",
        )
    owner, repo = parts[0], parts[1].removesuffix(".git")

    try:
        # Ask GitHub for this repo *as the hacker* (their OAuth token),
        # not as an anonymous/app-level caller — the response includes
        # a "permissions" block reflecting what *this specific user*
        # can do with the repo.
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
        # From GitHub's perspective, "doesn't exist" and "exists but you
        # can't see it" both return 404 — either way the hacker doesn't
        # get to submit it.
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Repository {owner}/{repo} not found or not accessible to you",
        )
    if resp.status_code != 200:
        # Some other unexpected GitHub response (5xx, rate limit, etc.):
        # log it but don't block the submission over an API hiccup.
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
    """Ingest a submission: persist it, queue evaluation, return immediately.

    This is the critical hand-off point between the API and the worker:
    the row is committed to Postgres as SubmissionStatus.PENDING *before*
    the Celery task is dispatched, so even if the broker dispatch below
    fails, the submission itself is never lost — it just needs to be
    re-queued (see the except block).

    `current_hacker` comes from the Authorization: Bearer <jwt> header;
    FastAPI resolves it via the get_current_hacker dependency before this
    function body ever runs, so an unauthenticated request never reaches
    here at all (it 401s first).
    """
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

    # Deterministic entry rules (set by the organizer in the Campaign
    # Builder). These are enforced here, at ingestion, before we spend a
    # GitHub round-trip or queue any worker job.
    #
    # Note: Campaign.max_team_size is intentionally NOT enforced here —
    # a submission carries only team_name/github_url/pitch_text, never a
    # team roster, so the API has no member count to check against. It
    # stays a display-only hint until a team-membership model exists.

    # Late-submission policy: past the deadline, reject unless the campaign
    # explicitly allows late entries. deadline is stored tz-aware, so we
    # compare against tz-aware "now".
    if not campaign.allow_late_submissions and datetime.now(timezone.utc) > campaign.deadline:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"The deadline for campaign {campaign_id} has passed "
                "and late submissions are not allowed"
            ),
        )

    # Per-team submission cap: count this campaign's existing submissions
    # under the same team name (case-insensitive, so "Team A"/"team a"
    # can't trivially bypass the limit).
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
        # Fire-and-forget: the API never imports the worker's Celery app
        # (see core/celery_client.py) — this just drops a message named
        # "evaluate_submission" onto the Redis queue with the new row's
        # id, and returns immediately without waiting for it to run.
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
    """Polling endpoint: live evaluation status and final score.

    Not the primary way the dashboard gets updates (that's the WebSocket
    in campaigns.py), but a plain REST fallback for anyone who wants to
    check a single submission's status without a live connection.
    """
    submission = await db.get(Submission, submission_id)
    if submission is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Submission {submission_id} not found",
        )
    return submission
