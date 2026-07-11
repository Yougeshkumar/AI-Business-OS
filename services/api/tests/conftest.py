"""Shared pytest fixtures.

Two tiers:

* ``client`` — ASGI httpx client for tests that need no database (health,
  request validation, auth error paths).
* Database fixtures (``db_engine``, ``db_session``, ``api_client``) — bound to a
  real async engine from ``DATABASE_URL``. If no database is reachable, these
  are skipped so the unit suite still runs anywhere.
"""

from __future__ import annotations

import os
from collections.abc import AsyncGenerator

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

from src.core.config import Environment, Settings
from src.core.db import Base, create_engine

# Import models so their tables register on Base.metadata.
from src.modules.identity import models as _models  # noqa: F401
from src.main.app import create_app

_PERMISSIONS = [
    ("users", "read"),
    ("users", "write"),
    ("crm", "read"),
    ("crm", "write"),
    ("analytics", "read"),
]


@pytest.fixture(scope="session")
def test_settings() -> Settings:
    """Settings for the test environment."""
    return Settings(
        environment=Environment.TEST,
        log_json=False,
        debug=True,
        jwt_secret_key="test-secret-key-for-pytest-abcdefghijklmnop",
    )


@pytest_asyncio.fixture
async def client(test_settings: Settings) -> AsyncGenerator[AsyncClient, None]:
    """An httpx AsyncClient bound to the app via ASGI transport (no DB)."""
    app = create_app(test_settings)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest_asyncio.fixture(scope="session")
async def db_engine() -> AsyncGenerator[AsyncEngine, None]:
    """Create the schema on a real database, or skip if none is reachable."""
    if not os.environ.get("DATABASE_URL"):
        pytest.skip("DATABASE_URL not set; skipping database-backed tests")

    settings = Settings(environment=Environment.TEST, log_json=False)
    engine = create_engine(settings)
    try:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
    except Exception as exc:  # noqa: BLE001 - unreachable DB -> skip, don't fail
        await engine.dispose()
        pytest.skip(f"Database not reachable: {exc}")

    yield engine

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


async def _truncate(factory: async_sessionmaker[AsyncSession]) -> None:
    from sqlalchemy import text

    async with factory() as cleanup:
        await cleanup.execute(
            text(
                "TRUNCATE refresh_tokens, role_permissions, users, roles, "
                "permissions, organizations RESTART IDENTITY CASCADE"
            )
        )
        await cleanup.commit()


@pytest_asyncio.fixture
async def db_session(
    db_engine: AsyncEngine,
) -> AsyncGenerator[AsyncSession, None]:
    """A clean session per test; truncates identity tables afterwards."""
    factory = async_sessionmaker(
        bind=db_engine, class_=AsyncSession, expire_on_commit=False
    )
    async with factory() as session:
        yield session
        await session.rollback()
    await _truncate(factory)


@pytest_asyncio.fixture
async def api_client(
    db_engine: AsyncEngine,
) -> AsyncGenerator[AsyncClient, None]:
    """httpx client bound to an app whose DB dependency uses the test engine.

    Seeds the permission catalog, overrides the session dependency, and cleans
    the identity tables afterwards.
    """
    from src.core.deps import db_session as db_session_dep
    from src.modules.identity.models import Permission

    factory = async_sessionmaker(
        bind=db_engine, class_=AsyncSession, expire_on_commit=False
    )

    async with factory() as seed:
        for resource, action in _PERMISSIONS:
            seed.add(Permission(resource=resource, action=action))
        await seed.commit()

    async def _override_db_session() -> AsyncGenerator[AsyncSession, None]:
        async with factory() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise

    settings = Settings(
        environment=Environment.TEST,
        log_json=False,
        jwt_secret_key="api-test-secret-abcdefghijklmnopqrstuvwx",
    )
    app = create_app(settings)
    app.dependency_overrides[db_session_dep] = _override_db_session

    transport = ASGITransport(app=app)
    try:
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            yield ac
    finally:
        app.dependency_overrides.clear()
        await _truncate(factory)
