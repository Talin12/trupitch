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
from core.security import get_current_organizer
from models import Campaign, Organizer, Rule, Submission
from schemas import CampaignCreate, CampaignResponse, SubmissionResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/campaigns", tags=["campaigns"])


@router.post("", response_model=CampaignResponse, status_code=status.HTTP_201_CREATED)
async def create_campaign(
    payload: CampaignCreate,
    db: AsyncSession = Depends(get_db),
    organizer: Organizer = Depends(get_current_organizer),
) -> Campaign:
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

    return await _load_campaign(campaign.id, db)


@router.get("", response_model=list[CampaignResponse])
async def list_campaigns(db: AsyncSession = Depends(get_db)) -> list[Campaign]:
    # Public: the landing page lists published events only (never drafts).
    result = await db.execute(
        select(Campaign)
        .options(selectinload(Campaign.rules))
        .where(Campaign.status != CampaignStatus.DRAFT.value)
        .order_by(Campaign.id.desc())
    )
    return list(result.scalars())


@router.get("/mine", response_model=list[CampaignResponse])
async def list_my_campaigns(
    db: AsyncSession = Depends(get_db),
    organizer: Organizer = Depends(get_current_organizer),
) -> list[Campaign]:
    # Organizer dashboard: only the caller's own campaigns, all statuses.
    result = await db.execute(
        select(Campaign)
        .options(selectinload(Campaign.rules))
        .where(Campaign.organizer_id == organizer.id)
        .order_by(Campaign.id.desc())
    )
    return list(result.scalars())


@router.get("/{campaign_id}", response_model=CampaignResponse)
async def get_campaign(
    campaign_id: int, db: AsyncSession = Depends(get_db)
) -> Campaign:
    campaign = await _load_campaign(campaign_id, db)
    if campaign is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Campaign {campaign_id} not found",
        )
    return campaign


@router.get("/{campaign_id}/submissions", response_model=list[SubmissionResponse])
async def list_campaign_submissions(
    campaign_id: int,
    db: AsyncSession = Depends(get_db),
    organizer: Organizer = Depends(get_current_organizer),
) -> list[Submission]:
    campaign = await db.get(Campaign, campaign_id)
    # Return 404 (not 403) for someone else's campaign so we don't reveal
    # that a campaign with this id exists.
    if campaign is None or campaign.organizer_id != organizer.id:
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
