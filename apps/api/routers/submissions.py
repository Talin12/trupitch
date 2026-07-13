import logging

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from core.celery_client import celery_client
from core.database import get_db
from models import Campaign, Submission
from schemas import SubmissionCreate, SubmissionResponse

logger = logging.getLogger(__name__)

router = APIRouter(tags=["submissions"])


@router.post(
    "/campaigns/{campaign_id}/submit",
    response_model=SubmissionResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def submit_project(
    campaign_id: int,
    payload: SubmissionCreate,
    db: AsyncSession = Depends(get_db),
) -> Submission:
    """Ingest a submission: persist it, queue evaluation, return immediately."""
    campaign = await db.get(Campaign, campaign_id)
    if campaign is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Campaign {campaign_id} not found",
        )
    if campaign.status != "open":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"Campaign {campaign_id} is not accepting submissions "
                f"(status: {campaign.status})"
            ),
        )

    submission = Submission(
        campaign_id=campaign_id,
        team_name=payload.team_name,
        github_url=str(payload.github_url),
        pitch_text=payload.pitch_text,
        status="pending",
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
