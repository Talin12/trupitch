import os
from urllib.parse import urlparse

import asyncpg
import pytest
import pytest_asyncio

# The app builds its engine from DATABASE_URL at import time, so the test
# database must be selected before anything under the app is imported.
TEST_DB_URL = os.environ.setdefault(
    "TEST_DATABASE_URL",
    "postgresql+asyncpg://trupitch:trupitch@localhost:5433/trupitch_test",
)
os.environ["DATABASE_URL"] = TEST_DB_URL
os.environ.setdefault("JWT_SECRET", "test-secret-for-ci-please-change-32b")
# Force NullPool so the shared engine survives pytest-asyncio's per-test loops.
os.environ["DB_DISABLE_POOL"] = "1"

import httpx  # noqa: E402
from httpx import ASGITransport  # noqa: E402

_schema_ready = False


async def _ensure_test_database() -> None:
    """Create the test database if it doesn't exist yet.

    Connects to the always-present 'postgres' maintenance DB using the same
    host/credentials as TEST_DB_URL. In CI the DB may already be provisioned
    by the postgres service; locally this creates it on first run.
    """
    parsed = urlparse(TEST_DB_URL.replace("+asyncpg", ""))
    db_name = parsed.path.lstrip("/")
    admin_dsn = (
        f"postgresql://{parsed.username}:{parsed.password}"
        f"@{parsed.hostname}:{parsed.port or 5432}/postgres"
    )
    conn = await asyncpg.connect(admin_dsn)
    try:
        exists = await conn.fetchval(
            "SELECT 1 FROM pg_database WHERE datname = $1", db_name
        )
        if not exists:
            await conn.execute(f'CREATE DATABASE "{db_name}"')
    finally:
        await conn.close()


@pytest_asyncio.fixture
async def clean_db():
    """Create the schema once, then truncate every table before each test.

    Kept function-scoped (no session-scoped async fixture) so all async work
    runs on the per-test event loop pytest-asyncio provides.
    """
    global _schema_ready
    from sqlalchemy import text

    from core.database import async_session_maker, engine
    from models import Base

    if not _schema_ready:
        await _ensure_test_database()
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        _schema_ready = True

    async with async_session_maker() as session:
        tables = ", ".join(t.name for t in reversed(Base.metadata.sorted_tables))
        await session.execute(text(f"TRUNCATE {tables} RESTART IDENTITY CASCADE"))
        await session.commit()
    yield


@pytest_asyncio.fixture
async def client(clean_db):
    import main

    transport = ASGITransport(app=main.app)
    async with httpx.AsyncClient(
        transport=transport, base_url="http://test"
    ) as c:
        yield c


@pytest_asyncio.fixture
async def session(clean_db):
    from core.database import async_session_maker

    async with async_session_maker() as s:
        yield s


async def register_organizer(client, email="org@test.io", name="Org", password="password123"):
    """Register an organizer and return (token, organizer_id)."""
    resp = await client.post(
        "/api/auth/organizer/register",
        json={"email": email, "name": name, "password": password},
    )
    assert resp.status_code == 201, resp.text
    data = resp.json()
    return data["access_token"], data["organizer"]["id"]


def auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}
