import os
from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.pool import NullPool

from core.config import settings

# Under the test suite (which drives the app across many short-lived event
# loops) a pooled connection can outlive the loop that created it, raising
# "attached to a different loop". NullPool opens a fresh connection per use,
# sidestepping that; production keeps the pooled, pre-pinged engine.
if os.getenv("DB_DISABLE_POOL"):
    engine = create_async_engine(settings.database_url, echo=False, poolclass=NullPool)
else:
    engine = create_async_engine(
        settings.database_url, echo=False, pool_pre_ping=True
    )

async_session_maker = async_sessionmaker(
    engine, class_=AsyncSession, expire_on_commit=False
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with async_session_maker() as session:
        yield session
