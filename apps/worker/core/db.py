"""Isolated async database access for the worker.

Celery tasks are synchronous; they run async DB work through
`async_to_sync`. Each call creates a fresh engine on the current event
loop (NullPool) because asyncpg pools cannot be shared across the
short-lived loops that `asyncio.run` creates per task — reusing a pool
created on a now-closed event loop is a classic source of hard-to-debug
"attached to a different loop" errors, which is why this trades a
little per-task connection overhead for correctness.
"""

import asyncio
import os
from collections.abc import AsyncGenerator, Coroutine
from contextlib import asynccontextmanager
from typing import Any, TypeVar

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

# Falls back to the local-dev Postgres (host port 5433, see
# docker-compose.yml) if DATABASE_URL isn't set in the environment.
DATABASE_URL = os.getenv(
    "DATABASE_URL", "postgresql+asyncpg://trupitch:trupitch@localhost:5433/trupitch"
)

T = TypeVar("T")


def async_to_sync(coro: Coroutine[Any, Any, T]) -> T:
    """Run an async coroutine to completion from a synchronous Celery task.

    `asyncio.run` creates a brand-new event loop, runs the coroutine to
    completion, then closes that loop — exactly the lifecycle a single
    Celery task invocation needs, since Celery itself has no event loop
    of its own to reuse.
    """
    return asyncio.run(coro)


@asynccontextmanager
async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """Yield a database session bound to an engine on the current loop.

    Used as `async with get_session() as session:` inside tasks.py.
    Creating the engine here (rather than at module level) is what
    guarantees it's always bound to whichever event loop `async_to_sync`
    just created for this task — see the module docstring above.
    """
    engine = create_async_engine(DATABASE_URL, poolclass=NullPool)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    try:
        async with factory() as session:
            yield session
    finally:
        # Always dispose the engine when the task is done, since a new
        # one gets created fresh on the next task anyway — nothing here
        # is meant to be long-lived.
        await engine.dispose()
