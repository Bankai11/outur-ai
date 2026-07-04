"""Application configuration — loaded from environment variables via Pydantic Settings."""

from __future__ import annotations

from enum import StrEnum
from functools import lru_cache
from typing import Annotated

from pydantic import AnyUrl, Field, PostgresDsn, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Environment(StrEnum):
    """Valid deployment environments."""

    DEVELOPMENT = "development"
    STAGING = "staging"
    PRODUCTION = "production"
    TESTING = "testing"


class LogFormat(StrEnum):
    JSON = "json"
    CONSOLE = "console"


class LogLevel(StrEnum):
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class Settings(BaseSettings):
    """
    Central application settings.

    All values can be overridden via environment variables or a .env file.
    Pydantic-Settings handles coercion, validation, and defaults.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ── Application ────────────────────────────────────────────────────────
    app_name: str = Field(default="Outur AI", description="Human-readable application name")
    app_version: str = Field(default="0.1.0")
    app_env: Environment = Field(default=Environment.DEVELOPMENT)
    app_debug: bool = Field(default=False)
    app_secret_key: str = Field(default="CHANGE_ME", min_length=32)

    # ── Server ─────────────────────────────────────────────────────────────
    host: str = Field(default="0.0.0.0")
    port: int = Field(default=8000, ge=1, le=65535)
    workers: int = Field(default=1, ge=1)
    reload: bool = Field(default=False)

    # ── Database ───────────────────────────────────────────────────────────
    database_url: str = Field(
        default="postgresql+asyncpg://outur:outur_pass@localhost:5432/outur_ai",
        description="Full async PostgreSQL connection URL",
    )
    database_pool_size: int = Field(default=10, ge=1)
    database_max_overflow: int = Field(default=20, ge=0)
    database_pool_timeout: int = Field(default=30, ge=5)

    # ── Queue / Cache ──────────────────────────────────────────────────────
    redis_url: str = Field(
        default="redis://localhost:6379/0",
        description="Redis connection URL for ARQ and caching",
    )

    # ── Logging ────────────────────────────────────────────────────────────
    log_level: LogLevel = Field(default=LogLevel.INFO)
    log_format: LogFormat = Field(default=LogFormat.JSON)
    log_file: str = Field(default="", description="Path to log file; empty = stdout only")

    # ── Antigravity / Gemini ───────────────────────────────────────────────
    gemini_api_key: str = Field(default="", description="Google Gemini API key")
    antigravity_env: str = Field(default="local", description="local | cloud")
    gemini_model: str = Field(default="gemini-2.0-flash-exp")

    # ── Authentication ─────────────────────────────────────────────────────
    jwt_secret_key: str = Field(default="CHANGE_ME", min_length=32)
    jwt_algorithm: str = Field(default="HS256")
    jwt_access_token_expire_minutes: int = Field(default=30, ge=1)
    jwt_refresh_token_expire_days: int = Field(default=7, ge=1)

    # ── CORS ───────────────────────────────────────────────────────────────
    cors_origins: list[str] = Field(
        default=["http://localhost:3000", "http://localhost:8000"]
    )
    cors_allow_credentials: bool = Field(default=True)

    # ── Computed Properties ────────────────────────────────────────────────
    @property
    def is_production(self) -> bool:
        return self.app_env == Environment.PRODUCTION

    @property
    def is_development(self) -> bool:
        return self.app_env == Environment.DEVELOPMENT

    @property
    def is_testing(self) -> bool:
        return self.app_env == Environment.TESTING

    @model_validator(mode="after")
    def validate_production_secrets(self) -> "Settings":
        """Enforce that placeholder secrets are replaced in production."""
        if self.is_production:
            if self.app_secret_key == "CHANGE_ME":
                raise ValueError("app_secret_key must be set in production")
            if self.jwt_secret_key == "CHANGE_ME":
                raise ValueError("jwt_secret_key must be set in production")
            if not self.gemini_api_key:
                raise ValueError("gemini_api_key must be set in production")
        return self


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """
    Return a cached singleton Settings instance.

    Using lru_cache means the .env file is only parsed once per process.
    In tests, call ``get_settings.cache_clear()`` before overriding.
    """
    return Settings()
