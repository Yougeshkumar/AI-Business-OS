"""FastAPI application factory.

Wires together configuration, logging, middleware, exception handlers, database
and Redis lifecycle, and the health router. Business module routers are added
in later sprints; Sprint 0 ships only the platform foundation.
"""

from __future__ import annotations

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.core.cache import close_redis, init_redis
from src.core.config import Settings, get_settings
from src.core.db import dispose_engine, init_engine
from src.core.errors import register_exception_handlers
from src.core.health import router as health_router
from src.core.logging import configure_logging
from src.core.middleware import RequestContextMiddleware
from src.modules.identity.api.router import router as identity_router

logger = structlog.get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Manage startup and shutdown of shared resources."""
    settings: Settings = app.state.settings
    init_engine(settings)
    init_redis(settings)
    logger.info(
        "application_startup",
        environment=settings.environment.value,
        version=settings.version,
    )
    try:
        yield
    finally:
        await dispose_engine()
        await close_redis()
        logger.info("application_shutdown")


def create_app(settings: Settings | None = None) -> FastAPI:
    """Create and configure the FastAPI application.

    Args:
        settings: Optional settings override (used in tests).

    Returns:
        A fully configured FastAPI application.
    """
    resolved = settings or get_settings()
    configure_logging(resolved)

    app = FastAPI(
        title="AI Business Operating System API",
        version=resolved.version,
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
        lifespan=lifespan,
    )
    app.state.settings = resolved

    app.add_middleware(RequestContextMiddleware)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=resolved.cors_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=["*"],
    )

    register_exception_handlers(app)

    app.include_router(health_router)
    app.include_router(identity_router, prefix=resolved.api_v1_prefix)

    return app


app = create_app()
