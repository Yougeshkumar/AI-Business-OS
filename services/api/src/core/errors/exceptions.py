"""Application exception hierarchy.

Every error raised by the application derives from :class:`AppError`, which
carries the machine-readable ``code`` and HTTP ``status_code`` needed to build
the standard error envelope defined in the API specification.
"""

from __future__ import annotations


class AppError(Exception):
    """Base class for all application errors.

    Attributes:
        code: Machine-readable error code (e.g. ``VALIDATION_ERROR``).
        message: Human-readable summary.
        status_code: HTTP status code to return.
        details: Optional additional context.
    """

    code: str = "INTERNAL_ERROR"
    status_code: int = 500
    message: str = "An unexpected error occurred"

    def __init__(
        self,
        message: str | None = None,
        *,
        details: str | None = None,
    ) -> None:
        self.message = message or self.message
        self.details = details
        super().__init__(self.message)


class BadRequestError(AppError):
    """Malformed request."""

    code = "BAD_REQUEST"
    status_code = 400
    message = "The request was malformed"


class ValidationError(AppError):
    """Field validation failed."""

    code = "VALIDATION_ERROR"
    status_code = 400
    message = "Request validation failed"


class UnauthenticatedError(AppError):
    """Missing or invalid authentication."""

    code = "UNAUTHENTICATED"
    status_code = 401
    message = "Authentication is required"


class ForbiddenError(AppError):
    """Authenticated but not permitted."""

    code = "FORBIDDEN"
    status_code = 403
    message = "You do not have permission to perform this action"


class NotFoundError(AppError):
    """Resource does not exist."""

    code = "NOT_FOUND"
    status_code = 404
    message = "The requested resource was not found"


class ConflictError(AppError):
    """Resource conflict."""

    code = "CONFLICT"
    status_code = 409
    message = "The request conflicts with the current state"


class RateLimitedError(AppError):
    """Too many requests."""

    code = "RATE_LIMITED"
    status_code = 429
    message = "Too many requests"


class ServiceUnavailableError(AppError):
    """Temporary dependency failure."""

    code = "SERVICE_UNAVAILABLE"
    status_code = 503
    message = "The service is temporarily unavailable"
