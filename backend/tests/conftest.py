"""Pytest configuration and fixtures."""

import pytest
from fastapi.testclient import TestClient

from app.core.config import get_settings
from app.main import app


@pytest.fixture
def client() -> TestClient:
    """Create test client for FastAPI app."""
    return TestClient(app)


@pytest.fixture
def clear_config_cache():
    """Clear config cache before and after tests."""
    # Clear cache before test
    get_settings.cache_clear()
    yield
    # Clear cache after test to avoid test pollution
    get_settings.cache_clear()


@pytest.fixture
def test_settings():
    """Override settings for testing."""
    from app.core.config import Settings

    return Settings(
        ENVIRONMENT="testing",
        LOG_LEVEL="INFO",
        CORS_ORIGINS=["http://localhost:5173"],
    )


@pytest.fixture(autouse=True)
def auto_clear_config_cache(clear_config_cache):
    """Automatically clear config cache for all tests."""
    pass

