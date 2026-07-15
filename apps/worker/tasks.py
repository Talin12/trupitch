"""TruPitch evaluation worker.

This is the Celery entrypoint: it defines the `evaluate_submission` task
that the API enqueues (by name only — see apps/api/core/celery_client.py)
every time a hacker submits a project. This one task runs the entire
3-stage pipeline (heuristics -> code structure -> LLM scoring) for a
single submission, from start to finish, in one go.

Run with:

    celery -A tasks worker --loglevel=info
"""

import json
import logging
import os
from pathlib import Path

from dotenv import load_dotenv

# Load the repo-root .env (OPENAI_API_KEY, GITHUB_TOKEN, REDIS_URL, ...)
# before any module reads the environment at import time. This must run
# before the `import redis`/`Celery(...)` lines below, since those read
# REDIS_URL from the environment immediately at import time.
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

# Submission.notes is a String(1024) column; truncate here so a long
# tech summary + LLM rationale never fails the DB write.
NOTES_MAX_LENGTH = 1024

# The actual Celery application. Same broker as the API's celery_client,
# but this is the process that *registers and runs* tasks — the API's
# copy only ever calls send_task() and never executes anything itself.
celery_app = Celery("trupitch", broker=REDIS_URL, backend=REDIS_URL)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    task_track_started=True,
)

# Plain (non-Celery) Redis client used only for Pub/Sub publishing — see
# publish_update() below. Separate from the Celery broker connection.
_redis = redis_sync.Redis.from_url(REDIS_URL, decode_responses=True)


def publish_update(
    campaign_id: int,
    submission_id: int,
    status: str,
    score: float | None = None,
    notes: str | None = None,
    stage: str | None = None,
) -> None:
    """Push a live progress event to the campaign's Pub/Sub channel.

    Every FastAPI WebSocket connection for this campaign
    (apps/api/routers/campaigns.py's campaign_updates_ws) is subscribed
    to `campaign_{campaign_id}_updates` and relays whatever gets
    published here straight to the browser. This is the *only* way the
    frontend finds out about progress before the pipeline finishes —
    there's no polling involved.

    `stage` is an ephemeral pipeline-progress hint (not persisted to the
    DB) so the frontend can render a live stepper instead of a single
    static "evaluating" state.

    Best-effort: the UI update is a nicety, so a Redis hiccup here must
    never fail or retry the evaluation itself.
    """
    payload = {
        "submission_id": submission_id,
        "status": status,
        "final_score": score,
        "notes": notes,
        "stage": stage,
    }
    try:
        _redis.publish(f"campaign_{campaign_id}_updates", json.dumps(payload))
    except redis_sync.RedisError:
        # Deliberately swallowed: a failed live-update push must never
        # blow up (or retry) the actual evaluation task.
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

    This is a synchronous function (Celery tasks are sync by default);
    all the actual work is async, so it's immediately handed off to
    `async_to_sync`, which spins up an event loop for the duration of
    this one task and tears it down afterward.

    Transient failures (GitHub/LLM rate limits and timeouts, DB connection
    loss) propagate as exceptions so Celery retries with exponential backoff
    (via `autoretry_for` above — up to 5 attempts, backing off up to 300s
    between them). Anything *not* in that exception tuple is treated as a
    permanent failure and is not retried.
    """
    return async_to_sync(_evaluate(submission_id))


async def _evaluate(submission_id: int) -> dict:
    """The actual pipeline body, run inside a single DB session for the
    whole lifetime of this submission's evaluation.
    """
    async with get_session() as session:
        submission = await session.get(Submission, submission_id)
        if submission is None:
            # Permanent condition: retrying will never find it.
            logger.error("Submission %s not found; dropping task", submission_id)
            return {"submission_id": submission_id, "status": "not_found"}

        # Mark as in-progress immediately, before any real work starts,
        # so the dashboard shows "evaluating" the instant the worker
        # picks the job up rather than only once Stage 1 finishes.
        submission.status = SubmissionStatus.EVALUATING.value
        await session.commit()
        publish_update(
            submission.campaign_id,
            submission_id,
            SubmissionStatus.EVALUATING.value,
            stage="verifying_repo",
        )

        # Stage 1 — hard heuristics (cheap gate before expensive stages).
        # Currently just "does this GitHub repo exist and resolve" — see
        # pipeline/stage1_heuristics.py. Failing here short-circuits the
        # rest of the pipeline entirely: no code analysis, no LLM call.
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
        publish_update(
            submission.campaign_id,
            submission_id,
            SubmissionStatus.EVALUATING.value,
            stage="analyzing_code",
        )

        # Load this campaign's judging rubric (weighted rules) so Stage 3
        # can score the submission against the organizer's actual
        # criteria rather than some generic rubric.
        rules = [
            {"description": r.description, "weight": r.weight}
            for r in (
                await session.execute(
                    select(Rule).where(Rule.campaign_id == submission.campaign_id)
                )
            ).scalars()
        ]

        # Stage 2 — code structure analysis: languages used + dependency
        # manifests present (package.json, requirements.txt, etc.). See
        # pipeline/stage2_structure.py. Produces a plain-text summary
        # that both a human and the LLM below can read.
        tech_summary = await run_stage_2(submission.github_url)
        logger.info("Stage 2 for submission %s: %s", submission_id, tech_summary)
        publish_update(
            submission.campaign_id,
            submission_id,
            SubmissionStatus.EVALUATING.value,
            stage="ai_scoring",
        )

        # Stage 3 — LLM qualitative scoring: the pitch, the Stage 2 tech
        # summary, and the campaign's rules are sent to an LLM, which
        # returns a single weighted score (0-100) plus a short rationale.
        # See pipeline/stage3_scoring.py and clients/llm.py.
        score, rationale = await run_stage_3(
            submission.pitch_text, tech_summary, rules
        )
        logger.info(
            "Stage 3 for submission %s: score=%s", submission_id, score
        )

        submission.status = SubmissionStatus.EVALUATED.value
        submission.final_score = float(score)
        # Store both the machine-generated tech summary and the LLM's
        # rationale in one field, separated by " | " — the frontend
        # dashboard splits on that separator to show them in two
        # distinct panels (see Dashboard.tsx's SubmissionRow).
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
