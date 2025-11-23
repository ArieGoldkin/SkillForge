"""Pytest configuration and fixtures."""

import os
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, get_settings
from app.db.session import AsyncSessionLocal
from app.main import app

# Load .env.test if it exists for integration tests
# This allows tests to use real API keys from .env.test
TEST_ENV_FILE = Path(__file__).parent.parent / ".env.test"
if TEST_ENV_FILE.exists():
    # Set environment variable to load .env.test
    # The Settings class will detect this and load .env.test
    os.environ["ENV_FILE"] = str(TEST_ENV_FILE)
    # Also set ENVIRONMENT=testing to trigger test mode
    os.environ.setdefault("ENVIRONMENT", "testing")


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
    return Settings(
        ENVIRONMENT="testing",
        LOG_LEVEL="INFO",
        CORS_ORIGINS=["http://localhost:5173"],
    )


@pytest.fixture(autouse=True)
def auto_clear_config_cache(clear_config_cache):
    """Automatically clear config cache for all tests."""
    pass


@pytest.fixture
def requires_database():
    """Skip test if DATABASE_URL is not configured."""
    from app.core.config import settings

    if not settings.DATABASE_URL:
        pytest.skip("DATABASE_URL not configured")


@pytest.fixture
async def reset_engine_connections():
    """Dispose engine connections before test to avoid event loop conflicts.

    This ensures engine connections are created in the test's event loop,
    preventing 'attached to different loop' errors. Use this fixture for
    tests that use database connections and have event loop issues.
    """
    from app.db.session import engine

    # Dispose existing connections before test
    await engine.dispose()
    yield
    # Dispose after test to clean up
    await engine.dispose()


@pytest.fixture
async def db_session(requires_database, reset_engine_connections) -> AsyncSession:
    """Create a test database session with automatic rollback.

    Yields an async session and rolls back all changes after test.
    Requires DATABASE_URL to be configured.
    reset_engine_connections ensures connections are in the test's event loop.
    """
    async with AsyncSessionLocal() as session:
        # Use nested transaction for automatic rollback
        transaction = await session.begin()
        try:
            yield session
        finally:
            await transaction.rollback()
