"""Shared pytest fixtures."""

from __future__ import annotations

from collections.abc import AsyncGenerator

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from src.core.config import Environment, Settings
from src.main.app import create_app


@pytest.fixture(scope="session")
def test_settings() -> Settings:
    """Settings for the test environment."""
    return Settings(environment=Environment.TEST, log_json=False, debug=True)


@pytest_asyncio.fixture
async def client(test_settings: Settings) -> AsyncGenerator[AsyncClient, None]:
    """An httpx AsyncClient bound to the app via ASGI transport."""
    app = create_app(test_settings)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
