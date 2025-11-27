"""Tests for configuration management."""

import pytest

from app.core.config import Settings, get_settings


def test_settings_loads_defaults(monkeypatch):
    """Test settings load with defaults.

    Note: This test removes env vars that conftest autouse fixtures may set
    to test true default behavior. HOST is not tested because it may come
    from .env file in local development.
    """
    # Clean up env vars that autouse fixtures might set
    monkeypatch.delenv("HOST", raising=False)
    monkeypatch.delenv("LLM_MODEL", raising=False)
    get_settings.cache_clear()

    settings = Settings()
    assert settings.ENVIRONMENT == "development"
    assert settings.LOG_LEVEL == "DEBUG"
    assert settings.PORT == 8500
    # HOST varies: 127.0.0.1 (code default) or 0.0.0.0 (from .env in local dev)
    assert settings.HOST in ("127.0.0.1", "0.0.0.0")
    assert settings.API_V1_PREFIX == "/api/v1"


def test_settings_validates_environment():
    """Test environment validation."""
    with pytest.raises(ValueError, match="ENVIRONMENT must be one of"):
        Settings(ENVIRONMENT="invalid")


def test_settings_loads_from_env(monkeypatch):
    """Test settings load from environment variables."""
    # Clean up env vars that autouse fixtures might set
    monkeypatch.delenv("LLM_MODEL", raising=False)
    monkeypatch.setenv("ENVIRONMENT", "production")
    monkeypatch.setenv("LOG_LEVEL", "INFO")
    monkeypatch.setenv("DATABASE_URL", "postgresql://test:test@localhost/db")
    # Set a dummy API key to pass LLM validation (default LLM_MODEL is gpt-5-mini)
    monkeypatch.setenv("OPENAI_API_KEY", "test-key-for-unit-tests")
    # Clear cache to pick up new env vars
    get_settings.cache_clear()
    settings = Settings()
    assert settings.ENVIRONMENT == "production"
    assert settings.LOG_LEVEL == "INFO"
    # Restore cache
    get_settings.cache_clear()


def test_settings_production_validation_requires_database_url(monkeypatch):
    """Test production environment requires DATABASE_URL."""
    # Clean up env vars that autouse fixtures might set
    monkeypatch.delenv("LLM_MODEL", raising=False)
    monkeypatch.setenv("ENVIRONMENT", "production")
    monkeypatch.delenv("DATABASE_URL", raising=False)
    # Clear cache to pick up new env vars
    get_settings.cache_clear()
    with pytest.raises(ValueError, match="DATABASE_URL is required in production"):
        Settings(ENVIRONMENT="production", DATABASE_URL=None)
    # Restore cache
    get_settings.cache_clear()


def test_settings_production_validation_with_database_url(monkeypatch):
    """Test production environment passes validation with DATABASE_URL."""
    # Clean up env vars that autouse fixtures might set
    monkeypatch.delenv("LLM_MODEL", raising=False)
    monkeypatch.setenv("ENVIRONMENT", "production")
    monkeypatch.setenv("DATABASE_URL", "postgresql://user:pass@localhost/db")
    # Set a dummy API key to pass LLM validation (default LLM_MODEL is gpt-5-mini)
    monkeypatch.setenv("OPENAI_API_KEY", "test-key-for-unit-tests")
    # Clear cache to pick up new env vars
    get_settings.cache_clear()
    settings = Settings(
        ENVIRONMENT="production", DATABASE_URL="postgresql://user:pass@localhost/db"
    )
    assert settings.ENVIRONMENT == "production"
    assert settings.DATABASE_URL == "postgresql://user:pass@localhost/db"
    # Restore cache
    get_settings.cache_clear()


def test_settings_caching_returns_same_instance():
    """Test get_settings() caches Settings instance using lru_cache."""
    # Clear cache first
    get_settings.cache_clear()
    settings1 = get_settings()
    settings2 = get_settings()
    # Should be the same instance (cached)
    assert settings1 is settings2
    # Restore cache
    get_settings.cache_clear()


def test_settings_helper_methods(monkeypatch):
    """Test helper methods for environment checks."""
    # Clean up env vars that autouse fixtures might set
    monkeypatch.delenv("LLM_MODEL", raising=False)
    # Set a dummy API key to pass LLM validation (default LLM_MODEL is gpt-5-mini)
    monkeypatch.setenv("OPENAI_API_KEY", "test-key-for-unit-tests")
    get_settings.cache_clear()

    dev_settings = Settings(ENVIRONMENT="development")
    assert dev_settings.is_development() is True
    assert dev_settings.is_production() is False
    assert dev_settings.is_staging() is False

    prod_settings = Settings(ENVIRONMENT="production", DATABASE_URL="postgresql://test")
    assert prod_settings.is_development() is False
    assert prod_settings.is_production() is True
    assert prod_settings.is_staging() is False

    staging_settings = Settings(ENVIRONMENT="staging")
    assert staging_settings.is_development() is False
    assert staging_settings.is_production() is False
    assert staging_settings.is_staging() is True


def test_settings_cors_origins_default():
    """Test CORS origins default value."""
    settings = Settings()
    assert isinstance(settings.CORS_ORIGINS, list)
    assert "http://localhost:5173" in settings.CORS_ORIGINS


def test_settings_optional_fields():
    """Test optional fields can be None."""
    settings = Settings()
    # DATABASE_URL and JINA_API_KEY are optional
    assert settings.DATABASE_URL is None or isinstance(settings.DATABASE_URL, str)
    assert settings.JINA_API_KEY is None or isinstance(settings.JINA_API_KEY, str)
