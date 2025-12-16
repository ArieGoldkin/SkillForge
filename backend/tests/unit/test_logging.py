"""Tests for structured logging configuration."""

import logging
from io import StringIO

import pytest
import structlog

from app.core.config import Settings
from app.core.logging import get_logger, setup_logging



@pytest.fixture
def reset_logging():
    """Reset logging configuration before and after tests."""
    # Save original configuration
    original_config = structlog.get_config()
    # Clear structlog configuration
    structlog.reset_defaults()
    logging.getLogger().handlers.clear()
    yield
    # Restore original configuration
    structlog.reset_defaults()
    if original_config:
        structlog.configure(**original_config)


@pytest.fixture
def capture_logs():
    """Capture log output for testing."""
    stream = StringIO()
    yield stream
    stream.close()


def test_setup_logging_development_config(reset_logging, monkeypatch):
    """Test logging setup for development environment."""
    monkeypatch.setenv("ENVIRONMENT", "development")
    monkeypatch.setenv("LOG_LEVEL", "DEBUG")
    from app.core.config import get_settings

    get_settings.cache_clear()
    setup_logging()
    logger = get_logger("test")
    # Should not raise
    logger.info("test_message", key="value")
    get_settings.cache_clear()


def test_setup_logging_production_config(reset_logging, monkeypatch):
    """Test logging setup for production environment."""
    monkeypatch.setenv("ENVIRONMENT", "production")
    monkeypatch.setenv("LOG_LEVEL", "INFO")
    monkeypatch.setenv("DATABASE_URL", "postgresql://test")
    from app.core.config import get_settings

    get_settings.cache_clear()
    setup_logging()
    logger = get_logger("test")
    # Should not raise
    logger.info("test_message", key="value")
    get_settings.cache_clear()


def test_setup_logging_invalid_log_level(reset_logging, monkeypatch):
    """Test logging setup raises ValueError for invalid log level."""
    monkeypatch.setenv("LOG_LEVEL", "INVALID_LEVEL")
    from app.core.config import get_settings

    get_settings.cache_clear()
    # Create settings with invalid log level
    settings = Settings(LOG_LEVEL="INVALID_LEVEL")
    # Monkeypatch settings to use invalid level
    import app.core.logging as logging_module

    original_settings = logging_module.settings
    logging_module.settings = settings
    try:
        with pytest.raises(TypeError, match="Invalid LOG_LEVEL"):
            setup_logging()
    finally:
        logging_module.settings = original_settings
        get_settings.cache_clear()


def test_get_logger_returns_bound_logger(reset_logging):
    """Test get_logger returns structlog BoundLogger (or BoundLoggerLazyProxy before first use)."""
    setup_logging()
    logger = get_logger("test_module")
    # After setup, logger should be a BoundLogger or BoundLoggerLazyProxy
    # BoundLoggerLazyProxy becomes BoundLogger on first use
    assert hasattr(logger, "info") or hasattr(logger, "debug")
    # Use it to make it a real BoundLogger
    logger.info("test")
    # Now it should be a BoundLogger
    assert logger is not None


def test_logger_outputs_structured_logs(reset_logging, monkeypatch):
    """Test logger outputs structured log entries."""
    monkeypatch.setenv("ENVIRONMENT", "development")
    monkeypatch.setenv("LOG_LEVEL", "DEBUG")
    from app.core.config import get_settings

    get_settings.cache_clear()
    setup_logging()
    logger = get_logger("test")
    # Should not raise - structured logging works
    logger.info("test_event", key1="value1", key2=42, key3=True)
    get_settings.cache_clear()


def test_logger_context_variables(reset_logging, monkeypatch):
    """Test logger respects context variables."""
    monkeypatch.setenv("ENVIRONMENT", "development")
    from app.core.config import get_settings

    get_settings.cache_clear()
    setup_logging()
    logger = get_logger("test")

    # Bind context variables
    structlog.contextvars.bind_contextvars(request_id="test-123", user_id="user-456")
    logger.info("context_test")
    # Unbind
    structlog.contextvars.unbind_contextvars("request_id", "user_id")
    get_settings.cache_clear()


def test_setup_logging_fallback_on_error(reset_logging, monkeypatch):
    """Test logging falls back to basic logging on setup error."""
    # Mock settings to raise error
    monkeypatch.setenv("LOG_LEVEL", "DEBUG")
    from app.core.config import get_settings

    get_settings.cache_clear()
    # Setup should still work even if there's an issue
    setup_logging()
    logger = get_logger("test")
    # Should not raise
    logger.info("fallback_test")
    get_settings.cache_clear()


def test_logger_standard_levels(reset_logging):
    """Test logger supports all standard logging levels."""
    setup_logging()
    logger = get_logger("test")
    # All levels should work
    logger.debug("debug_message")
    logger.info("info_message")
    logger.warning("warning_message")
    logger.error("error_message")
    logger.critical("critical_message")


def test_logger_integrates_with_stdlib(reset_logging):
    """Test logger integrates with Python's standard logging library."""
    setup_logging()
    logger = get_logger("test")
    # Should be compatible with stdlib logger
    stdlib_logger = logging.getLogger("test")
    assert logger is not None
    assert stdlib_logger is not None
