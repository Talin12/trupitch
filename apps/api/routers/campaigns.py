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
    """Create a campaign and its judging rules in one atomic transaction."""
    organizer = await _resolve_organizer(payload.organizer_id, db)

    campaign = Campaign(
        organizer_id=organizer.id,
        name=payload.name,
        deadline=payload.deadline,
        status=payload.status,
        rules=[Rule(description=r.description, weight=r.weight) for r in payload.rules],
    )
    db.add(campaign)
    await db.commit()

    return await _load_campaign(campaign.id, db)


async def _resolve_organizer(
    organizer_id: int | None, db: AsyncSession
) -> Organizer:
    """Explicit organizer if given, else get-or-create the configured default."""
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
        await db.flush()
    return organizer


@router.get("", response_model=list[CampaignResponse])
async def list_campaigns(db: AsyncSession = Depends(get_db)) -> list[Campaign]:
    """All campaigns, newest first, with rules eagerly loaded."""
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
    """Retrieve campaign metadata together with its rules."""
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
    """Leaderboard: submissions ranked by score, unscored ones last."""
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
    connected client. One Redis subscription per socket.
    """
    await websocket.accept()

    redis = aioredis.from_url(settings.redis_url, decode_responses=True)
    pubsub = redis.pubsub()
    channel = f"campaign_{campaign_id}_updates"
    await pubsub.subscribe(channel)

    async def relay_pubsub_to_client() -> None:
        async for message in pubsub.listen():
            if message["type"] != "message":
                continue
            try:
                payload = json.loads(message["data"])
            except (json.JSONDecodeError, TypeError):
                logger.warning("Dropping malformed pubsub message on %s", channel)
                continue
            await websocket.send_json(payload)

    relay_task = asyncio.create_task(relay_pubsub_to_client())
    try:
        # The dashboard never sends data; this read exists to notice the
        # client going away (closed tab) the moment it happens.
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        pass
    finally:
        relay_task.cancel()
        with suppress(asyncio.CancelledError):
            await relay_task
        with suppress(Exception):
            await pubsub.unsubscribe(channel)
            await pubsub.aclose()
            await redis.aclose()


async def _load_campaign(campaign_id: int, db: AsyncSession) -> Campaign | None:
    result = await db.execute(
        select(Campaign)
        .options(selectinload(Campaign.rules))
        .where(Campaign.id == campaign_id)
    )
    return result.scalar_one_or_none()
