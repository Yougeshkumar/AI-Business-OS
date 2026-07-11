"""Structured logging configuration.

Emits one JSON object per log line in non-local environments and a
human-readable console renderer during local development. Standard fields
(timestamp, level, service, environment) are bound globally; request-scoped
fields (trace_id, tenant_id, user_id) are bound by middleware.
"""

from __future__ import annotations

import logging
import sys
from typing import Any, cast

import structlog
from structlog.types import Processor

from src.core.config import Settings


def configure_logging(settings: Settings) -> None:
    """Configure structlog and the stdlib logging bridge.

    Args:
        settings: Application settings controlling log level and format.
    """
    log_level = getattr(logging, settings.log_level.value)

    shared_processors: list[Processor] = [
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso", utc=True),
        structlog.processors.StackInfoRenderer(),
        _add_service_context(settings),
    ]

    if settings.log_json:
        renderer: Processor = structlog.processors.JSONRenderer()
    else:
        renderer = structlog.dev.ConsoleRenderer(colors=True)

    structlog.configure(
        processors=[*shared_processors, renderer],
        wrapper_class=structlog.make_filtering_bound_logger(log_level),
        logger_factory=structlog.PrintLoggerFactory(file=sys.stdout),
        cache_logger_on_first_use=True,
    )

    # Route stdlib logging (uvicorn, sqlalchemy) through structlog formatting.
    handler = logging.StreamHandler(sys.stdout)
    formatter = structlog.stdlib.ProcessorFormatter(
        processor=renderer,
        foreign_pre_chain=shared_processors,
    )
    handler.setFormatter(formatter)

    root_logger = logging.getLogger()
    root_logger.handlers.clear()
    root_logger.addHandler(handler)
    root_logger.setLevel(log_level)

    for noisy in ("uvicorn.access", "uvicorn.error", "sqlalchemy.engine"):
        logging.getLogger(noisy).handlers.clear()
        logging.getLogger(noisy).propagate = True


def _add_service_context(settings: Settings) -> Processor:
    """Return a processor that binds static service-identifying fields."""

    def processor(
        _logger: Any,
        _method: str,
        event_dict: dict[str, Any],
    ) -> dict[str, Any]:
        event_dict.setdefault("service", settings.app_name)
        event_dict.setdefault("environment", settings.environment.value)
        event_dict.setdefault("version", settings.version)
        return event_dict

    return cast(Processor, processor)


def get_logger(name: str | None = None) -> structlog.stdlib.BoundLogger:
    """Return a configured bound structlog logger.

    Args:
        name: Optional logger name.

    Returns:
        Configured bound logger.
    """
    return cast(structlog.stdlib.BoundLogger, structlog.get_logger(name))
