"""Health check endpoints.

Provides a liveness probe (``/health``) that always returns 200 if the process
is up, and a readiness probe (``/health/ready``) that verifies connectivity to
PostgreSQL and Redis. Readiness returns 503 if any dependency is unavailable.
"""

from __future__ import annotations

from typing import Literal

import structlog
from fastapi import APIRouter, Response
from pydantic import BaseModel
from sqlalchemy import text

from src.core.cache import get_redis
from src.core.config import get_settings
from src.core.db import get_session_factory

logger = structlog.get_logger(__name__)

router = APIRouter(tags=["health"])


class HealthStatus(BaseModel):
    """Basic liveness response."""

    status: Literal["ok"]
    service: str
    version: str
    environment: str


class DependencyStatus(BaseModel):
    """Status of a single dependency."""

    name: str
    healthy: bool
    detail: str | None = None


class ReadinessStatus(BaseModel):
    """Readiness response including dependency checks."""

    status: Literal["ready", "not_ready"]
    dependencies: list[DependencyStatus]


@router.get("/health", response_model=HealthStatus, summary="Liveness probe")
async def health() -> HealthStatus:
    """Return 200 if the process is running."""
    settings = get_settings()
    return HealthStatus(
        status="ok",
        service=settings.app_name,
        version=settings.version,
        environment=settings.environment.value,
    )


async def _check_database() -> DependencyStatus:
    try:
        factory = get_session_factory()
        async with factory() as session:
            await session.execute(text("SELECT 1"))
        return DependencyStatus(name="postgresql", healthy=True)
    except Exception as exc:  # noqa: BLE001 - report any failure as unhealthy
        logger.warning("db_health_check_failed", error=str(exc))
        return DependencyStatus(
            name="postgresql", healthy=False, detail="connection failed"
        )


async def _check_redis() -> DependencyStatus:
    try:
        client = get_redis()
        await client.ping()
        return DependencyStatus(name="redis", healthy=True)
    except Exception as exc:  # noqa: BLE001 - report any failure as unhealthy
        logger.warning("redis_health_check_failed", error=str(exc))
        return DependencyStatus(name="redis", healthy=False, detail="connection failed")


@router.get(
    "/health/ready",
    response_model=ReadinessStatus,
    summary="Readiness probe",
)
async def readiness(response: Response) -> ReadinessStatus:
    """Verify PostgreSQL and Redis connectivity.

    Returns 200 when all dependencies are healthy, 503 otherwise.
    """
    dependencies = [await _check_database(), await _check_redis()]
    all_healthy = all(dep.healthy for dep in dependencies)
    if not all_healthy:
        response.status_code = 503
    return ReadinessStatus(
        status="ready" if all_healthy else "not_ready",
        dependencies=dependencies,
    )
