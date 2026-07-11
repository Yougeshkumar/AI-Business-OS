"""Exception handlers that render the standard error envelope.

The envelope shape matches the API specification: ``code``, ``message``,
``details``, ``field_errors``, ``trace_id`` and ``timestamp``. Handlers are
registered on the FastAPI app in :mod:`src.main.app`.
"""

from __future__ import annotations

from datetime import UTC, datetime

import structlog
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from starlette.exceptions import HTTPException as StarletteHTTPException

from src.core.errors.exceptions import AppError

logger = structlog.get_logger(__name__)


class FieldError(BaseModel):
    """A single field-level validation error."""

    field: str
    code: str
    message: str


class ErrorBody(BaseModel):
    """The ``error`` object inside an error response."""

    code: str
    message: str
    details: str | None = None
    field_errors: list[FieldError] | None = None
    trace_id: str
    timestamp: str


class ErrorResponse(BaseModel):
    """Top-level error response envelope."""

    error: ErrorBody = Field(...)


def _now_iso() -> str:
    return datetime.now(UTC).isoformat()


def _trace_id(request: Request) -> str:
    value = getattr(request.state, "trace_id", None)
    return value if isinstance(value, str) else "unknown"


def _build(
    *,
    code: str,
    message: str,
    status_code: int,
    trace_id: str,
    details: str | None = None,
    field_errors: list[FieldError] | None = None,
) -> JSONResponse:
    body = ErrorResponse(
        error=ErrorBody(
            code=code,
            message=message,
            details=details,
            field_errors=field_errors,
            trace_id=trace_id,
            timestamp=_now_iso(),
        )
    )
    return JSONResponse(status_code=status_code, content=body.model_dump(mode="json"))


def register_exception_handlers(app: FastAPI) -> None:
    """Register all exception handlers on the given FastAPI application."""

    @app.exception_handler(AppError)
    async def _handle_app_error(request: Request, exc: AppError) -> JSONResponse:
        return _build(
            code=exc.code,
            message=exc.message,
            status_code=exc.status_code,
            trace_id=_trace_id(request),
            details=exc.details,
        )

    @app.exception_handler(RequestValidationError)
    async def _handle_validation(
        request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        field_errors = [
            FieldError(
                field=".".join(str(part) for part in error["loc"][1:]) or "body",
                code=str(error["type"]).upper(),
                message=str(error["msg"]),
            )
            for error in exc.errors()
        ]
        return _build(
            code="VALIDATION_ERROR",
            message="Request validation failed",
            status_code=400,
            trace_id=_trace_id(request),
            details=f"{len(field_errors)} field(s) invalid",
            field_errors=field_errors,
        )

    @app.exception_handler(StarletteHTTPException)
    async def _handle_http(
        request: Request, exc: StarletteHTTPException
    ) -> JSONResponse:
        code = {
            401: "UNAUTHENTICATED",
            403: "FORBIDDEN",
            404: "NOT_FOUND",
            405: "METHOD_NOT_ALLOWED",
            429: "RATE_LIMITED",
        }.get(exc.status_code, "HTTP_ERROR")
        return _build(
            code=code,
            message=str(exc.detail),
            status_code=exc.status_code,
            trace_id=_trace_id(request),
        )

    @app.exception_handler(Exception)
    async def _handle_unexpected(request: Request, exc: Exception) -> JSONResponse:
        trace_id = _trace_id(request)
        logger.error(
            "unhandled_exception",
            error=str(exc),
            error_type=type(exc).__name__,
            trace_id=trace_id,
        )
        return _build(
            code="INTERNAL_ERROR",
            message="An unexpected error occurred",
            status_code=500,
            trace_id=trace_id,
        )
