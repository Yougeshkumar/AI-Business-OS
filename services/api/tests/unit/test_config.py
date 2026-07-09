"""Tests for the settings module."""

from __future__ import annotations

from src.core.config import Environment, Settings, get_settings


def test_default_settings_load() -> None:
    settings = Settings()
    assert settings.app_name == "ai-bos-api"
    assert settings.api_v1_prefix == "/v1"
    assert settings.port == 8000


def test_cors_origins_from_csv_string() -> None:
    settings = Settings(cors_origins="http://a.com, http://b.com")
    assert settings.cors_origins == ["http://a.com", "http://b.com"]


def test_is_production_flag() -> None:
    prod = Settings(environment=Environment.PRODUCTION)
    assert prod.is_production is True
    local = Settings(environment=Environment.LOCAL)
    assert local.is_production is False


def test_get_settings_is_cached() -> None:
    assert get_settings() is get_settings()
