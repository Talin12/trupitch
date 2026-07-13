"""TruPitch evaluation worker.

Run with:

    celery -A tasks worker --loglevel=info
"""

import json
import logging
import os
from pathlib import Path

from dotenv import load_dotenv

# Load the repo-root .env (OPENAI_API_KEY, GITHUB_TOKEN, REDIS_URL, ...)
# before any module reads the environment at import time.
load_dotenv(Path(__file__).resolve().parents[2] / ".env")

import redis as redis_sync
from celery import Celery
from sqlalchemy import select
from sqlalchemy.exc import OperationalError

from clients.errors import RetryableError
from constants import SubmissionStatus
from core.db import async_to_sync, get_session
from models import Rule, Submission
from pipeline.stage1_heuristics import run_stage_1
from pipeline.stage2_structure import run_stage_2
from pipeline.stage3_scoring import run_stage_3

logger = logging.getLogger(__name__)

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")

NOTES_MAX_LENGTH = 1024

celery_app = Celery("trupitch", broker=REDIS_URL, backend=REDIS_URL)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    task_track_started=True,
)

_redis = redis_sync.Redis.from_url(REDIS_URL, decode_responses=True)


def publish_update(
    campaign_id: int,
    submission_id: int,
    status: str,
    score: float | None = None,
    notes: str | None = None,
) -> None:
    """Push a live progress event to the campaign's Pub/Sub channel.

    Best-effort: the UI update is a nicety, so a Redis hiccup here must
    never fail or retry the evaluation itself.
    """
    payload = {
        "submission_id": submission_id,
        "status": status,
        "final_score": score,
        "notes": notes,
    }
    try:
        _redis.publish(f"campaign_{campaign_id}_updates", json.dumps(payload))
    except redis_sync.RedisError:
        logger.warning(
            "Pub/Sub publish failed for submission %s", submission_id, exc_info=True
        )


@celery_app.task(
    name="evaluate_submission",
    autoretry_for=(RetryableError, OperationalError, OSError),
    retry_backoff=True,
    retry_backoff_max=300,
    max_retries=5,
)
def evaluate_submission(submission_id: int) -> dict:
    """Run the 3-stage evaluation pipeline for one submission.

    Transient failures (GitHub/LLM rate limits and timeouts, DB connection
    loss) propagate as exceptions so Celery retries with exponential backoff.
    """
    return async_to_sync(_evaluate(submission_id))


async def _evaluate(submission_id: int) -> dict:
    async with get_session() as session:
        submission = await session.get(Submission, submission_id)
        if submission is None:
            # Permanent condition: retrying will never find it.
            logger.error("Submission %s not found; dropping task", submission_id)
            return {"submission_id": submission_id, "status": "not_found"}

        submission.status = SubmissionStatus.EVALUATING.value
        await session.commit()
        publish_update(
            submission.campaign_id, submission_id, SubmissionStatus.EVALUATING.value
        )

        # Stage 1 — hard heuristics (cheap gate before expensive stages)
        passed, reason = await run_stage_1(submission.github_url)
        if not passed:
            submission.status = SubmissionStatus.DISQUALIFIED.value
            submission.notes = reason
            await session.commit()
            publish_update(
                submission.campaign_id,
                submission_id,
                SubmissionStatus.DISQUALIFIED.value,
                notes=reason,
            )
            logger.info("Submission %s disqualified: %s", submission_id, reason)
            return {
                "submission_id": submission_id,
                "status": SubmissionStatus.DISQUALIFIED.value,
            }

        logger.info("Stage 1 passed for submission %s", submission_id)

        rules = [
            {"description": r.description, "weight": r.weight}
            for r in (
                await session.execute(
                    select(Rule).where(Rule.campaign_id == submission.campaign_id)
                )
            ).scalars()
        ]

        # Stage 2 — code structure analysis
        tech_summary = await run_stage_2(submission.github_url)
        logger.info("Stage 2 for submission %s: %s", submission_id, tech_summary)

        # Stage 3 — LLM qualitative scoring
        score, rationale = await run_stage_3(
            submission.pitch_text, tech_summary, rules
        )
        logger.info(
            "Stage 3 for submission %s: score=%s", submission_id, score
        )

        submission.status = SubmissionStatus.EVALUATED.value
        submission.final_score = float(score)
        submission.notes = (f"{tech_summary} | {rationale}")[:NOTES_MAX_LENGTH]
        await session.commit()
        publish_update(
            submission.campaign_id,
            submission_id,
            SubmissionStatus.EVALUATED.value,
            score=float(score),
            notes=submission.notes,
        )

        return {
            "submission_id": submission_id,
            "status": SubmissionStatus.EVALUATED.value,
            "final_score": score,
        }
