"""Integration tests for the health endpoints."""

from __future__ import annotations

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_liveness_returns_200(client: AsyncClient) -> None:
    resp = await client.get("/health")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ok"
    assert body["service"] == "ai-bos-api"


@pytest.mark.asyncio
async def test_liveness_sets_trace_headers(client: AsyncClient) -> None:
    resp = await client.get("/health")
    assert "X-Trace-Id" in resp.headers
    assert "X-Request-Id" in resp.headers


@pytest.mark.asyncio
async def test_openapi_available(client: AsyncClient) -> None:
    resp = await client.get("/openapi.json")
    assert resp.status_code == 200
    assert resp.json()["info"]["title"] == "AI Business Operating System API"
