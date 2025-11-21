"""Pytest configuration and fixtures."""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.db.session import AsyncSessionLocal, engine
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


@pytest.fixture(scope="function")
async def db_session() -> AsyncSession:
    """Create a test database session.

    Yields an async session and ensures proper cleanup after test.
    Uses nested transaction for automatic rollback.
    """
    async with AsyncSessionLocal() as session:
        async with session.begin() as transaction:
            yield session
            await transaction.rollback()
