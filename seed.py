"""Seed a test Organizer and an open Campaign into the local database.

Run from the repo root: python seed.py
"""

import asyncio
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

# The API app uses flat imports (from models...), so put apps/api on sys.path.
sys.path.insert(0, str(Path(__file__).parent / "apps" / "api"))

from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from core.config import settings
from models import Campaign, Organizer


async def seed() -> None:
    engine = create_async_engine(settings.database_url)
    async_session = async_sessionmaker(engine, expire_on_commit=False)

    async with async_session() as session:
        # Reuse the organizer if the script was already run.
        org = (
            await session.execute(
                select(Organizer).where(Organizer.email == "admin@trupitch.local")
            )
        ).scalar_one_or_none()
        if org is None:
            org = Organizer(name="Admin User", email="admin@trupitch.local")
            session.add(org)
            await session.commit()
            await session.refresh(org)

        camp = Campaign(
            organizer_id=org.id,
            name="Test Hackathon 2026",
            deadline=datetime.now(timezone.utc) + timedelta(days=30),
            status="open",
        )
        session.add(camp)
        await session.commit()
        await session.refresh(camp)

        print(f"Success! Organizer ID: {org.id} | Campaign ID: {camp.id}")

    await engine.dispose()


asyncio.run(seed())
