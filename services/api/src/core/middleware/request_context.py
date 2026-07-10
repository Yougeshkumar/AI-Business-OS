"""Request-context middleware.

Generates (or accepts) a request id and trace id per request, binds them to the
structlog context so every log line within the request carries them, and echoes
them back as ``X-Request-Id`` and ``X-Trace-Id`` response headers.
"""

from __future__ import annotations

import time
import uuid
from collections.abc import Awaitable, Callable

import structlog
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

logger = structlog.get_logger(__name__)

RequestHandler = Callable[[Request], Awaitable[Response]]


def _new_id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:24]}"


class RequestContextMiddleware(BaseHTTPMiddleware):
    """Attach request/trace identifiers and structured access logging."""

    async def dispatch(self, request: Request, call_next: RequestHandler) -> Response:
        request_id = request.headers.get("X-Request-Id") or _new_id("req")
        trace_id = request.headers.get("X-Trace-Id") or _new_id("tr")

        request.state.request_id = request_id
        request.state.trace_id = trace_id

        structlog.contextvars.clear_contextvars()
        structlog.contextvars.bind_contextvars(
            request_id=request_id,
            trace_id=trace_id,
        )

        start = time.perf_counter()
        try:
            response = await call_next(request)
        finally:
            elapsed_ms = round((time.perf_counter() - start) * 1000, 2)
            logger.info(
                "http_request",
                method=request.method,
                path=request.url.path,
                latency_ms=elapsed_ms,
            )

        response.headers["X-Request-Id"] = request_id
        response.headers["X-Trace-Id"] = trace_id
        return response
