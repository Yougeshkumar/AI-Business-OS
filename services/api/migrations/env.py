"""Alembic migration environment (async).

Runs migrations against the async engine configured from application settings.
The declarative ``Base.metadata`` is the autogenerate target. Business models
are imported in later sprints; Sprint 0 ships the migration harness only.
"""

from __future__ import annotations

import asyncio
from logging.config import fileConfig

from alembic import context
from sqlalchemy.engine import Connection

from src.core.config import get_settings
from src.core.db import Base, create_engine

# Import model modules so their tables register on Base.metadata before
# autogenerate runs. The import is for its registration side effect.
from src.modules.identity import models as _identity_models  # noqa: F401

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata

_settings = get_settings()
config.set_main_option("sqlalchemy.url", _settings.database_url_str)


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode (emit SQL without a DBAPI connection)."""
    context.configure(
        url=_settings.database_url_str,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
        compare_server_default=True,
        include_schemas=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def _do_run_migrations(connection: Connection) -> None:
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        compare_type=True,
        compare_server_default=True,
        include_schemas=True,
    )
    with context.begin_transaction():
        context.run_migrations()


async def run_migrations_online() -> None:
    """Run migrations in 'online' mode using the async engine."""
    engine = create_engine(_settings)
    async with engine.connect() as connection:
        await connection.run_sync(_do_run_migrations)
    await engine.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    asyncio.run(run_migrations_online())
