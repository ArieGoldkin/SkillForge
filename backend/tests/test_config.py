"""Tests for configuration management."""

import pytest

from app.core.config import Settings


def test_settings_loads_defaults():
    """Test settings load with defaults."""
    settings = Settings()
    assert settings.ENVIRONMENT == "development"
    assert settings.LOG_LEVEL == "DEBUG"
    assert settings.PORT == 8500


def test_settings_validates_environment():
    """Test environment validation."""
    with pytest.raises(ValueError, match="ENVIRONMENT must be one of"):
        Settings(ENVIRONMENT="invalid")


def test_settings_loads_from_env(monkeypatch):
    """Test settings load from environment variables."""
    monkeypatch.setenv("ENVIRONMENT", "production")
    monkeypatch.setenv("LOG_LEVEL", "INFO")
    settings = Settings()
    assert settings.ENVIRONMENT == "production"
    assert settings.LOG_LEVEL == "INFO"
