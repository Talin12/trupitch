"""Alembic migration environment (async engine).

Reads the database URL from application settings and targets
Base.metadata so `alembic revision --autogenerate` picks up all
models imported in the `models` package. This file is invoked
automatically by every `alembic` CLI command (revision, upgrade,
downgrade) — it's not meant to be run directly.
"""

import asyncio
from logging.config import fileConfig

from alembic import context
from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config

from core.config import settings
from models import Base

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Override whatever sqlalchemy.url is (or isn't) in alembic.ini with the
# same DATABASE_URL the running app uses, so migrations always target
# the database the API is actually configured for.
config.set_main_option("sqlalchemy.url", settings.database_url)

# The full set of tables Alembic diffs the live database against when
# autogenerating a migration — populated by importing models/__init__.py.
target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """Emit SQL to stdout without a live database connection.

    Used by `alembic upgrade head --sql` to print the DDL instead of
    executing it — useful for reviewing a migration before running it
    against a real database.
    """
    context.configure(
        url=config.get_main_option("sqlalchemy.url"),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
    )

    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    """Synchronous body run inside the async connection below via
    `connection.run_sync` — Alembic's migration runner itself is sync,
    so this bridges it into our async engine setup.
    """
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        compare_type=True,
    )

    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    """Open one throwaway async engine (NullPool: no connection pooling
    needed for a one-shot CLI command), run the migration, then dispose
    of it — this process exits right after anyway.
    """
    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)

    await connectable.dispose()


def run_migrations_online() -> None:
    """Entry point for the normal (non---sql, real-database) case."""
    asyncio.run(run_async_migrations())


# Alembic calls this module as a script; which path we take depends on
# whether the command was run with `--sql` (offline) or not (online).
if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
