"""Async SQLAlchemy engine and session factory."""

from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from core.config import settings

# One engine (and its connection pool) for the whole process, created once
# at import time. `pool_pre_ping=True` makes the pool test a connection
# with a cheap SELECT before handing it out, so a connection that Postgres
# silently closed (e.g. after being idle) doesn't surface as a confusing
# error mid-request — it just gets quietly replaced.
engine = create_async_engine(settings.database_url, echo=False, pool_pre_ping=True)

# Factory for AsyncSession objects bound to the engine above.
# expire_on_commit=False means attributes on ORM objects stay readable
# after a commit (FastAPI often serializes the response *after* the
# request handler commits, so this avoids lazy-load errors at that point).
async_session_maker = async_sessionmaker(
    engine, class_=AsyncSession, expire_on_commit=False
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency yielding a database session per request.

    Usage: `db: AsyncSession = Depends(get_db)` in a route signature.
    FastAPI opens the session before the handler runs and closes it
    (via the `async with`) once the handler returns, so every request
    gets its own isolated session that is always cleaned up.
    """
    async with async_session_maker() as session:
        yield session
