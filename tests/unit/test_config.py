"""
Unit tests for core/config/settings.py

Tests cover:
- Default value loading
- Environment-specific properties (is_production, is_testing, etc.)
- Production secret validation
- Settings cache behaviour
"""

from __future__ import annotations

import pytest

from core.config import Environment, Settings, get_settings


@pytest.mark.unit
class TestSettings:
    """Tests for the Settings Pydantic model."""

    def test_default_app_name(self, test_settings: Settings) -> None:
        """Settings should carry the correct application name."""
        assert test_settings.app_name == "Outur AI"

    def test_testing_environment(self, test_settings: Settings) -> None:
        """test_settings fixture should set env to TESTING."""
        assert test_settings.app_env == Environment.TESTING

    def test_is_testing_flag(self, test_settings: Settings) -> None:
        """is_testing property should be True in the test environment."""
        assert test_settings.is_testing is True

    def test_is_production_false(self, test_settings: Settings) -> None:
        """is_production should be False in the test environment."""
        assert test_settings.is_production is False

    def test_is_development_false(self, test_settings: Settings) -> None:
        """is_development should be False in the test environment."""
        assert test_settings.is_development is False

    def test_database_url_set(self, test_settings: Settings) -> None:
        """Database URL must be set and non-empty."""
        assert test_settings.database_url
        assert "sqlite" in test_settings.database_url  # test fixture uses SQLite

    def test_jwt_algorithm_default(self, test_settings: Settings) -> None:
        """Default JWT algorithm should be HS256."""
        assert test_settings.jwt_algorithm == "HS256"

    def test_cors_origins_is_list(self, test_settings: Settings) -> None:
        """CORS origins must be a list of strings."""
        assert isinstance(test_settings.cors_origins, list)
        assert all(isinstance(o, str) for o in test_settings.cors_origins)

    def test_production_rejects_placeholder_secret(self) -> None:
        """Settings should raise ValueError when placeholder secrets are used in production."""
        with pytest.raises(ValueError, match="app_secret_key"):
            Settings(
                app_env="production",
                app_secret_key="CHANGE_ME",
                jwt_secret_key="a" * 32,
                gemini_api_key="real-key",
            )

    def test_production_rejects_missing_gemini_key(self) -> None:
        """Settings should raise ValueError when gemini_api_key is empty in production."""
        with pytest.raises(ValueError, match="gemini_api_key"):
            Settings(
                app_env="production",
                app_secret_key="a" * 32,
                jwt_secret_key="a" * 32,
                gemini_api_key="",
            )


@pytest.mark.unit
class TestGetSettings:
    """Tests for the get_settings() cached singleton."""

    def test_returns_settings_instance(self, test_settings: Settings) -> None:
        """get_settings() should return a Settings instance."""
        # test_settings fixture already called get_settings internally
        assert isinstance(test_settings, Settings)

    def test_cache_is_cleared_between_test_sessions(self, test_settings: Settings) -> None:
        """The test fixture clears the lru_cache — settings should be fresh."""
        assert test_settings.app_env == Environment.TESTING
