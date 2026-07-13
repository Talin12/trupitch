"""Isolated async database access for the worker.

Celery tasks are synchronous; they run async DB work through
`async_to_sync`. Each call creates a fresh engine on the current event
loop (NullPool) because asyncpg pools cannot be shared across the
short-lived loops that `asyncio.run` creates per task.
"""

import asyncio
import os
from collections.abc import AsyncGenerator, Coroutine
from contextlib import asynccontextmanager
from typing import Any, TypeVar

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

DATABASE_URL = os.getenv(
    "DATABASE_URL", "postgresql+asyncpg://trupitch:trupitch@localhost:5433/trupitch"
)

T = TypeVar("T")


def async_to_sync(coro: Coroutine[Any, Any, T]) -> T:
    """Run an async coroutine to completion from a synchronous Celery task."""
    return asyncio.run(coro)


@asynccontextmanager
async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """Yield a database session bound to an engine on the current loop."""
    engine = create_async_engine(DATABASE_URL, poolclass=NullPool)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    try:
        async with factory() as session:
            yield session
    finally:
        await engine.dispose()
