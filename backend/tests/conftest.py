"""Pytest configuration and fixtures."""

import pytest
from fastapi.testclient import TestClient
from app.main import app


@pytest.fixture
def client() -> TestClient:
    """Create test client for FastAPI app."""
    return TestClient(app)


@pytest.fixture
def test_settings():
    """Override settings for testing."""
    from app.core.config import Settings

    return Settings(
        ENVIRONMENT="testing",
        LOG_LEVEL="INFO",
        CORS_ORIGINS=["http://localhost:5173"],
    )
