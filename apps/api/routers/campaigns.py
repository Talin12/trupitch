"""Campaign CRUD, the public leaderboard, and the live-update WebSocket.

Mounted under /api/campaigns by main.py, so every route below is
relative to that prefix (e.g. `@router.get("")` -> GET /api/campaigns).
"""

import asyncio
import json
import logging
from contextlib import suppress

import redis.asyncio as aioredis
from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    WebSocket,
    WebSocketDisconnect,
    status,
)
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from core.config import settings
from core.constants import CampaignStatus
from core.database import get_db
from models import Campaign, Organizer, Rule, Submission
from schemas import CampaignCreate, CampaignResponse, SubmissionResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/campaigns", tags=["campaigns"])


@router.post("", response_model=CampaignResponse, status_code=status.HTTP_201_CREATED)
async def create_campaign(
    payload: CampaignCreate, db: AsyncSession = Depends(get_db)
) -> Campaign:
    """Create a campaign and its judging rules in one atomic transaction.

    Used by the Campaign Builder UI. Because `campaign.rules` is built
    from Rule objects and attached before the single `db.commit()`,
    either the whole campaign-plus-rubric is saved, or none of it is —
    there's no way to end up with a campaign that has zero rules due to
    a mid-request failure.
    """
    organizer = await _resolve_organizer(payload.organizer_id, db)

    campaign = Campaign(
        organizer_id=organizer.id,
        name=payload.name,
        start_date=payload.start_date,
        deadline=payload.deadline,
        status=payload.status,
        max_team_size=payload.max_team_size,
        max_submissions_per_team=payload.max_submissions_per_team,
        allow_late_submissions=payload.allow_late_submissions,
        rules=[Rule(description=r.description, weight=r.weight) for r in payload.rules],
    )
    db.add(campaign)
    await db.commit()

    # Re-fetch with rules eagerly loaded (selectinload) rather than just
    # returning `campaign` directly: after commit, accessing
    # campaign.rules would otherwise trigger a lazy load, which raises
    # under SQLAlchemy's async mode instead of silently working.
    return await _load_campaign(campaign.id, db)


async def _resolve_organizer(
    organizer_id: int | None, db: AsyncSession
) -> Organizer:
    """Explicit organizer if given, else get-or-create the configured default.

    There's no organizer login yet, so when the frontend omits
    organizer_id entirely (the normal case today), every campaign ends
    up owned by one shared "default organizer" row identified by
    settings.admin_email — created lazily here the first time it's
    needed, then reused on every subsequent call.
    """
    if organizer_id is not None:
        organizer = await db.get(Organizer, organizer_id)
        if organizer is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Organizer {organizer_id} not found",
            )
        return organizer

    organizer = (
        await db.execute(
            select(Organizer).where(Organizer.email == settings.admin_email)
        )
    ).scalar_one_or_none()
    if organizer is None:
        organizer = Organizer(email=settings.admin_email, name=settings.admin_name)
        db.add(organizer)
        # flush (not commit) so `organizer.id` is populated by Postgres
        # immediately, without ending the transaction the caller
        # (create_campaign) is still in the middle of.
        await db.flush()
    return organizer


@router.get("", response_model=list[CampaignResponse])
async def list_campaigns(db: AsyncSession = Depends(get_db)) -> list[Campaign]:
    """All campaigns, newest first, with rules eagerly loaded.

    Powers both the hacker-facing Home page (filtered client-side to
    status == "open") and the organizer dashboard's campaign switcher.
    """
    result = await db.execute(
        select(Campaign)
        .options(selectinload(Campaign.rules))
        .order_by(Campaign.id.desc())
    )
    return list(result.scalars())


@router.get("/{campaign_id}", response_model=CampaignResponse)
async def get_campaign(
    campaign_id: int, db: AsyncSession = Depends(get_db)
) -> Campaign:
    """Retrieve campaign metadata together with its rules.

    Used by EventPage.tsx to show the event details and rubric a hacker
    is about to submit against.
    """
    campaign = await _load_campaign(campaign_id, db)
    if campaign is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Campaign {campaign_id} not found",
        )
    return campaign


@router.get("/{campaign_id}/submissions", response_model=list[SubmissionResponse])
async def list_campaign_submissions(
    campaign_id: int, db: AsyncSession = Depends(get_db)
) -> list[Submission]:
    """Leaderboard: submissions ranked by score, unscored ones last.

    `.nulls_last()` is what keeps pending/evaluating/disqualified
    submissions (final_score IS NULL) at the bottom instead of sorting
    unpredictably alongside — or ahead of — real scores. The dashboard
    fetches this once on load, then keeps rows fresh via the WebSocket
    below rather than re-polling this endpoint.
    """
    campaign = await db.get(Campaign, campaign_id)
    if campaign is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Campaign {campaign_id} not found",
        )
    result = await db.execute(
        select(Submission)
        .where(Submission.campaign_id == campaign_id)
        .order_by(Submission.final_score.desc().nulls_last(), Submission.id)
    )
    return list(result.scalars())


@router.websocket("/{campaign_id}/ws")
async def campaign_updates_ws(websocket: WebSocket, campaign_id: int) -> None:
    """Stream worker evaluation updates for a campaign over WebSocket.

    Bridges the Redis Pub/Sub channel `campaign_{id}_updates` to the
    connected client. One Redis subscription per socket. The worker
    (apps/worker/tasks.py, function publish_update) is the only thing
    that ever publishes to this channel — this route only relays.
    """
    await websocket.accept()

    # A dedicated Redis connection + pubsub object per WebSocket
    # connection (not shared/pooled) — each browser tab gets its own
    # independent subscription, cleaned up when that tab disconnects.
    redis = aioredis.from_url(settings.redis_url, decode_responses=True)
    pubsub = redis.pubsub()
    channel = f"campaign_{campaign_id}_updates"
    await pubsub.subscribe(channel)

    async def relay_pubsub_to_client() -> None:
        """Forward every Pub/Sub message on this channel to the browser
        as JSON, forever, until the task is cancelled below."""
        async for message in pubsub.listen():
            # pubsub.listen() also yields the initial "subscribe"
            # confirmation message; only "message" type entries are
            # actual published events worth forwarding.
            if message["type"] != "message":
                continue
            try:
                payload = json.loads(message["data"])
            except (json.JSONDecodeError, TypeError):
                logger.warning("Dropping malformed pubsub message on %s", channel)
                continue
            await websocket.send_json(payload)

    # Run the relay concurrently with the receive loop below — a
    # WebSocket route needs to both push (relay) and pull (detect
    # disconnect) at the same time, which asyncio.create_task enables.
    relay_task = asyncio.create_task(relay_pubsub_to_client())
    try:
        # The dashboard never sends data; this read exists to notice the
        # client going away (closed tab) the moment it happens.
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        pass
    finally:
        # Always tear down the relay task and the Redis subscription,
        # whether the client disconnected cleanly or an error occurred —
        # otherwise every dropped tab would leak a Redis connection.
        relay_task.cancel()
        with suppress(asyncio.CancelledError):
            await relay_task
        with suppress(Exception):
            await pubsub.unsubscribe(channel)
            await pubsub.aclose()
            await redis.aclose()


async def _load_campaign(campaign_id: int, db: AsyncSession) -> Campaign | None:
    """Shared query used by both create_campaign and get_campaign so
    both endpoints return the exact same shape (rules eagerly loaded).
    """
    result = await db.execute(
        select(Campaign)
        .options(selectinload(Campaign.rules))
        .where(Campaign.id == campaign_id)
    )
    return result.scalar_one_or_none()
