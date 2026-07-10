"""Errors package."""

from src.core.errors.exceptions import (
    AppError,
    BadRequestError,
    ConflictError,
    ForbiddenError,
    NotFoundError,
    RateLimitedError,
    ServiceUnavailableError,
    UnauthenticatedError,
    ValidationError,
)
from src.core.errors.handlers import (
    ErrorBody,
    ErrorResponse,
    FieldError,
    register_exception_handlers,
)

__all__ = [
    "AppError",
    "BadRequestError",
    "ConflictError",
    "ErrorBody",
    "ErrorResponse",
    "FieldError",
    "ForbiddenError",
    "NotFoundError",
    "RateLimitedError",
    "ServiceUnavailableError",
    "UnauthenticatedError",
    "ValidationError",
    "register_exception_handlers",
]
