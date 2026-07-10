"""Application settings loaded from environment variables.

Uses pydantic-settings so every configuration value is validated and typed.
Settings are cached (see :func:`get_settings`) so the environment is parsed once
per process. This is the single source of truth for configuration; no module
reads ``os.environ`` directly.
"""

from __future__ import annotations

from enum import Enum
from functools import lru_cache

from pydantic import Field, PostgresDsn, RedisDsn, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Environment(str, Enum):
    """Deployment environment."""

    LOCAL = "local"
    DEV = "dev"
    STAGING = "staging"
    PRODUCTION = "production"
    TEST = "test"


class LogLevel(str, Enum):
    """Supported log levels."""

    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class Settings(BaseSettings):
    """Typed application configuration.

    Values are read from environment variables (or a local ``.env`` file during
    development). Field names map to upper-cased env vars, e.g. ``app_name`` maps
    to ``APP_NAME``.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # --- Application ---------------------------------------------------------
    app_name: str = Field(default="ai-bos-api")
    environment: Environment = Field(default=Environment.LOCAL)
    debug: bool = Field(default=False)
    api_v1_prefix: str = Field(default="/v1")
    version: str = Field(default="0.1.0")

    # --- Server --------------------------------------------------------------
    host: str = Field(default="0.0.0.0")  # noqa: S104
    port: int = Field(default=8000, ge=1, le=65535)

    # --- Logging -------------------------------------------------------------
    log_level: LogLevel = Field(default=LogLevel.INFO)
    log_json: bool = Field(default=True)

    # --- Database ------------------------------------------------------------
    database_url: PostgresDsn = Field(
        default=PostgresDsn("postgresql+asyncpg://aibos:aibos@localhost:5432/aibos")
    )
    database_pool_size: int = Field(default=10, ge=1, le=100)
    database_max_overflow: int = Field(default=20, ge=0, le=100)
    database_pool_timeout: int = Field(default=30, ge=1)
    database_echo: bool = Field(default=False)
    database_statement_timeout_ms: int = Field(default=30000, ge=1000)

    # --- Redis ---------------------------------------------------------------
    redis_url: RedisDsn = Field(default=RedisDsn("redis://localhost:6379/0"))
    redis_max_connections: int = Field(default=20, ge=1, le=200)

    # --- CORS ----------------------------------------------------------------
    cors_origins: list[str] = Field(default_factory=lambda: ["http://localhost:3000"])

    @field_validator("cors_origins", mode="before")
    @classmethod
    def _split_cors_origins(cls, value: object) -> object:
        """Allow a comma-separated string for ``CORS_ORIGINS`` in env files."""
        if isinstance(value, str):
            stripped = value.strip()
            if not stripped:
                return []
            return [origin.strip() for origin in stripped.split(",") if origin.strip()]
        return value

    @property
    def is_production(self) -> bool:
        """Whether the app is running in the production environment."""
        return self.environment == Environment.PRODUCTION

    @property
    def database_url_str(self) -> str:
        """Database URL as a plain string for SQLAlchemy."""
        return str(self.database_url)

    @property
    def redis_url_str(self) -> str:
        """Redis URL as a plain string."""
        return str(self.redis_url)


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return the cached, validated application settings."""
    return Settings()
