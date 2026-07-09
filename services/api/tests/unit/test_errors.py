"""Tests for the error hierarchy."""

from __future__ import annotations

from src.core.errors import (
    AppError,
    ForbiddenError,
    NotFoundError,
    ValidationError,
)


def test_app_error_defaults() -> None:
    err = AppError()
    assert err.code == "INTERNAL_ERROR"
    assert err.status_code == 500


def test_specific_errors_have_correct_status() -> None:
    assert NotFoundError().status_code == 404
    assert ForbiddenError().status_code == 403
    assert ValidationError().status_code == 400


def test_custom_message_and_details() -> None:
    err = NotFoundError("Deal not found", details="deal_id=123")
    assert err.message == "Deal not found"
    assert err.details == "deal_id=123"
