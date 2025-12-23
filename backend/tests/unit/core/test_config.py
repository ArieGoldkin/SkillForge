"""Tests for configuration management."""

import pytest

from app.core.config import Settings, get_settings


@pytest.mark.unit
def test_settings_loads_defaults(monkeypatch):
    """Test settings load with defaults.

    Note: This test removes env vars that conftest autouse fixtures may set
    to test true default behavior.
    """
    # Clean up env vars that autouse fixtures might set or come from .env file
    monkeypatch.delenv("HOST", raising=False)
    monkeypatch.delenv("LOG_LEVEL", raising=False)
    monkeypatch.delenv("RELOAD", raising=False)
    monkeypatch.delenv("LLM_MODEL", raising=False)
    # Override ENVIRONMENT set by conftest.py line 76 to test true default
    monkeypatch.setenv("ENVIRONMENT", "development")
    get_settings.cache_clear()

    # Prevent loading from .env file by passing _env_file=None
    settings = Settings(_env_file=None)
    assert settings.ENVIRONMENT == "development"
    assert settings.LOG_LEVEL == "INFO"  # Changed default from DEBUG to INFO for security
    assert settings.PORT == 8500
    assert settings.HOST == "127.0.0.1"  # Changed default from 0.0.0.0 to 127.0.0.1 for security
    assert settings.RELOAD is False  # Changed default from True to False for security
    assert settings.API_V1_PREFIX == "/api/v1"
    get_settings.cache_clear()


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
    monkeypatch.setenv("HOST", "127.0.0.1")
    monkeypatch.setenv("RELOAD", "false")
    # Use strong password to pass production validation
    monkeypatch.setenv("DATABASE_URL", "postgresql://user:StrongP@ssw0rd123@localhost/db")
    # Set a dummy API key to pass LLM validation (default LLM_MODEL is gemini-2.5-flash)
    monkeypatch.setenv("GOOGLE_API_KEY", "test-key-for-unit-tests")
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
    monkeypatch.setenv("HOST", "127.0.0.1")
    monkeypatch.setenv("RELOAD", "false")
    monkeypatch.setenv("LOG_LEVEL", "INFO")
    # Use strong password to pass production validation
    monkeypatch.setenv("DATABASE_URL", "postgresql://user:StrongP@ssw0rd123@localhost/db")
    # Set a dummy API key to pass LLM validation (default LLM_MODEL is gemini-2.5-flash)
    monkeypatch.setenv("GOOGLE_API_KEY", "test-key-for-unit-tests")
    # Clear cache to pick up new env vars
    get_settings.cache_clear()
    settings = Settings(
        ENVIRONMENT="production", DATABASE_URL="postgresql://user:StrongP@ssw0rd123@localhost/db"
    )
    assert settings.ENVIRONMENT == "production"
    assert settings.DATABASE_URL == "postgresql://user:StrongP@ssw0rd123@localhost/db"
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
    # Set a dummy API key to pass LLM validation (default LLM_MODEL is gemini-2.5-flash)
    monkeypatch.setenv("GOOGLE_API_KEY", "test-key-for-unit-tests")
    get_settings.cache_clear()

    dev_settings = Settings(ENVIRONMENT="development")
    assert dev_settings.is_development() is True
    assert dev_settings.is_production() is False
    assert dev_settings.is_staging() is False

    # Use strong password to pass production validation
    # Set GOOGLE_API_KEY for production settings since default model is gemini-2.5-flash
    prod_settings = Settings(
        ENVIRONMENT="production",
        DATABASE_URL="postgresql://user:StrongP@ssw0rd123@localhost/db",
        HOST="127.0.0.1",
        RELOAD=False,
        LOG_LEVEL="INFO",
        GOOGLE_API_KEY="test-key-for-unit-tests",
    )
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


def test_settings_production_rejects_weak_database_password(monkeypatch):
    """Test production environment rejects weak database passwords."""
    monkeypatch.delenv("LLM_MODEL", raising=False)
    monkeypatch.setenv("ENVIRONMENT", "production")
    monkeypatch.setenv("OPENAI_API_KEY", "test-key-for-unit-tests")
    get_settings.cache_clear()

    weak_passwords = ["devpass", "password", "pass", "123456", "admin", "test"]
    for weak_pwd in weak_passwords:
        db_url = f"postgresql://user:{weak_pwd}@localhost/db"
        with pytest.raises(ValueError, match="SECURITY: Weak password detected"):
            Settings(ENVIRONMENT="production", DATABASE_URL=db_url)
    get_settings.cache_clear()


def test_settings_production_rejects_host_0_0_0_0(monkeypatch):
    """Test production environment rejects HOST=0.0.0.0."""
    monkeypatch.delenv("LLM_MODEL", raising=False)
    monkeypatch.setenv("ENVIRONMENT", "production")
    monkeypatch.setenv("DATABASE_URL", "postgresql://user:StrongP@ssw0rd123@localhost/db")
    monkeypatch.setenv("OPENAI_API_KEY", "test-key-for-unit-tests")
    get_settings.cache_clear()

    with pytest.raises(ValueError, match=r"SECURITY: HOST=0\.0\.0\.0 is not allowed"):
        Settings(
            ENVIRONMENT="production",
            HOST="0.0.0.0",
            DATABASE_URL="postgresql://user:StrongP@ssw0rd123@localhost/db",
        )
    get_settings.cache_clear()


def test_settings_production_rejects_reload_true(monkeypatch):
    """Test production environment rejects RELOAD=true."""
    monkeypatch.delenv("LLM_MODEL", raising=False)
    monkeypatch.setenv("ENVIRONMENT", "production")
    monkeypatch.setenv("HOST", "127.0.0.1")  # Override .env value
    monkeypatch.setenv("LOG_LEVEL", "INFO")  # Override .env value
    monkeypatch.setenv("DATABASE_URL", "postgresql://user:StrongP@ssw0rd123@localhost/db")
    monkeypatch.setenv("OPENAI_API_KEY", "test-key-for-unit-tests")
    get_settings.cache_clear()

    with pytest.raises(ValueError, match="SECURITY: RELOAD=true is not allowed"):
        Settings(
            ENVIRONMENT="production",
            RELOAD=True,
            DATABASE_URL="postgresql://user:StrongP@ssw0rd123@localhost/db",
        )
    get_settings.cache_clear()


def test_settings_production_rejects_debug_log_level(monkeypatch):
    """Test production environment rejects LOG_LEVEL=DEBUG."""
    monkeypatch.delenv("LLM_MODEL", raising=False)
    monkeypatch.setenv("ENVIRONMENT", "production")
    monkeypatch.setenv("HOST", "127.0.0.1")  # Override .env value
    monkeypatch.setenv("RELOAD", "false")  # Override .env value
    monkeypatch.setenv("DATABASE_URL", "postgresql://user:StrongP@ssw0rd123@localhost/db")
    monkeypatch.setenv("OPENAI_API_KEY", "test-key-for-unit-tests")
    get_settings.cache_clear()

    with pytest.raises(ValueError, match="SECURITY: LOG_LEVEL=DEBUG is not allowed"):
        Settings(
            ENVIRONMENT="production",
            LOG_LEVEL="DEBUG",
            DATABASE_URL="postgresql://user:StrongP@ssw0rd123@localhost/db",
        )
    get_settings.cache_clear()


def test_settings_production_rejects_wildcard_cors(monkeypatch):
    """Test production environment rejects CORS_ORIGINS=['*'] or empty list."""
    monkeypatch.delenv("LLM_MODEL", raising=False)
    monkeypatch.setenv("ENVIRONMENT", "production")
    monkeypatch.setenv("HOST", "127.0.0.1")  # Override .env value
    monkeypatch.setenv("RELOAD", "false")  # Override .env value
    monkeypatch.setenv("LOG_LEVEL", "INFO")  # Override .env value
    monkeypatch.setenv("DATABASE_URL", "postgresql://user:StrongP@ssw0rd123@localhost/db")
    monkeypatch.setenv("OPENAI_API_KEY", "test-key-for-unit-tests")
    get_settings.cache_clear()

    with pytest.raises(ValueError, match="SECURITY: CORS_ORIGINS must specify exact origins"):
        Settings(
            ENVIRONMENT="production",
            CORS_ORIGINS=["*"],
            DATABASE_URL="postgresql://user:StrongP@ssw0rd123@localhost/db",
        )

    with pytest.raises(ValueError, match="SECURITY: CORS_ORIGINS must specify exact origins"):
        Settings(
            ENVIRONMENT="production",
            CORS_ORIGINS=[],
            DATABASE_URL="postgresql://user:StrongP@ssw0rd123@localhost/db",
        )

    get_settings.cache_clear()


def test_settings_production_accepts_secure_config(monkeypatch):
    """Test production environment accepts secure configuration."""
    monkeypatch.delenv("LLM_MODEL", raising=False)
    monkeypatch.setenv("ENVIRONMENT", "production")
    monkeypatch.setenv("DATABASE_URL", "postgresql://user:StrongP@ssw0rd123@localhost/db")
    monkeypatch.setenv("GOOGLE_API_KEY", "test-key-for-unit-tests")
    get_settings.cache_clear()

    settings = Settings(
        ENVIRONMENT="production",
        HOST="127.0.0.1",
        RELOAD=False,
        LOG_LEVEL="INFO",
        CORS_ORIGINS=["https://app.example.com"],
        DATABASE_URL="postgresql://user:StrongP@ssw0rd123@localhost/db",
    )
    assert settings.is_production() is True
    assert settings.HOST == "127.0.0.1"
    assert settings.RELOAD is False
    assert settings.LOG_LEVEL == "INFO"
    assert settings.CORS_ORIGINS == ["https://app.example.com"]
    get_settings.cache_clear()


def test_langfuse_enabled_requires_credentials(monkeypatch):
    """Test LANGFUSE_ENABLED=true requires both public and secret keys (Issue #432)."""
    monkeypatch.delenv("LLM_MODEL", raising=False)
    get_settings.cache_clear()

    # Test missing both keys
    with pytest.raises(ValueError, match="Langfuse is enabled but credentials are missing"):
        Settings(
            LANGFUSE_ENABLED=True,
            LANGFUSE_PUBLIC_KEY=None,
            LANGFUSE_SECRET_KEY=None,
        )

    # Test missing public key
    with pytest.raises(ValueError, match="Langfuse is enabled but credentials are missing"):
        Settings(
            LANGFUSE_ENABLED=True,
            LANGFUSE_PUBLIC_KEY=None,
            LANGFUSE_SECRET_KEY="sk-test-secret",
        )

    # Test missing secret key
    with pytest.raises(ValueError, match="Langfuse is enabled but credentials are missing"):
        Settings(
            LANGFUSE_ENABLED=True,
            LANGFUSE_PUBLIC_KEY="pk-test-public",
            LANGFUSE_SECRET_KEY=None,
        )

    get_settings.cache_clear()


def test_langfuse_enabled_with_valid_credentials(monkeypatch):
    """Test LANGFUSE_ENABLED=true accepts valid credentials (Issue #432)."""
    monkeypatch.delenv("LLM_MODEL", raising=False)
    get_settings.cache_clear()

    settings = Settings(
        LANGFUSE_ENABLED=True,
        LANGFUSE_PUBLIC_KEY="pk-test-public",
        LANGFUSE_SECRET_KEY="sk-test-secret",
    )
    assert settings.LANGFUSE_ENABLED is True
    assert settings.LANGFUSE_PUBLIC_KEY == "pk-test-public"
    assert settings.LANGFUSE_SECRET_KEY == "sk-test-secret"
    get_settings.cache_clear()


def test_langfuse_disabled_allows_missing_credentials(monkeypatch):
    """Test LANGFUSE_ENABLED=false allows missing credentials (Issue #432)."""
    monkeypatch.delenv("LLM_MODEL", raising=False)
    get_settings.cache_clear()

    settings = Settings(
        LANGFUSE_ENABLED=False,
        LANGFUSE_PUBLIC_KEY=None,
        LANGFUSE_SECRET_KEY=None,
    )
    assert settings.LANGFUSE_ENABLED is False
    assert settings.LANGFUSE_PUBLIC_KEY is None
    assert settings.LANGFUSE_SECRET_KEY is None
    get_settings.cache_clear()
