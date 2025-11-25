"""Pytest configuration and fixtures."""

import os
from collections.abc import AsyncGenerator
from pathlib import Path
from uuid import UUID

import pytest
import pytest_asyncio
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, get_settings
from app.db.session import AsyncSessionLocal, engine
from app.main import app
from app.models.analysis import Analysis
from app.services.event_broadcaster import broadcaster

# Load .env.test if it exists for integration tests
# This allows tests to use real API keys from .env.test
TEST_ENV_FILE = Path(__file__).parent.parent / ".env.test"
if TEST_ENV_FILE.exists():
    # Set environment variable to load .env.test
    # The Settings class will detect this and load .env.test
    os.environ["ENV_FILE"] = str(TEST_ENV_FILE)
    # Also set ENVIRONMENT=development for test mode
    # (Settings validation requires development/staging/production)
    os.environ.setdefault("ENVIRONMENT", "development")

# Set LLM_MODEL for tests - use OpenAI if API key is available, otherwise skip tests
# This allows tests to run with OpenAI when configured, but prevents import failures
# when langchain-openai isn't available in IDE's Python environment
if "LLM_MODEL" not in os.environ:
    # Check if OpenAI API key is available
    openai_key = os.environ.get("OPENAI_API_KEY") or os.environ.get("LLM_OPENAI_API_KEY")
    if openai_key:
        os.environ["LLM_MODEL"] = "gpt-5-mini"  # Use OpenAI when key is available
    # If no OpenAI key, tests that require LLM will be skipped


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
        ENVIRONMENT="development",
        LOG_LEVEL="INFO",
        CORS_ORIGINS=["http://localhost:5173"],
    )


@pytest.fixture(autouse=True)
def auto_clear_config_cache(clear_config_cache):
    """Automatically clear config cache for all tests."""
    pass


@pytest.fixture(autouse=True)
def ensure_llm_model_set(monkeypatch):
    """Ensure LLM_MODEL is set for tests (if not already set in environment).

    This ensures tests default to OpenAI when API key is available
    even if LLM_MODEL is not set in the environment. Individual tests
    can override this by setting their own LLM_MODEL.
    """
    # Only set if not already in environment (module-level setenv takes precedence)
    if "LLM_MODEL" not in os.environ:
        # Only set if OpenAI key is available
        openai_key = os.environ.get("OPENAI_API_KEY") or os.environ.get("LLM_OPENAI_API_KEY")
        if openai_key:
            monkeypatch.setenv("LLM_MODEL", "gpt-5-mini")
    # Reduce retry delays for faster tests (0.1s base instead of 1.0s)
    if "LLM_RETRY_DELAY_BASE" not in os.environ:
        monkeypatch.setenv("LLM_RETRY_DELAY_BASE", "0.1")
    # Clear settings cache to pick up env vars
    get_settings.cache_clear()


@pytest.fixture
def requires_database():
    """Skip test if DATABASE_URL is not configured."""
    settings = get_settings()
    if not settings.DATABASE_URL:
        pytest.skip("DATABASE_URL not configured")


@pytest_asyncio.fixture
async def reset_engine_connections():
    """Dispose engine connections before test to avoid event loop conflicts.

    This ensures engine connections are created in the test's event loop,
    preventing 'attached to different loop' errors. Use this fixture for
    tests that use database connections and have event loop issues.
    """
    # Dispose existing connections before test
    await engine.dispose()
    yield
    # Dispose after test to clean up
    await engine.dispose()


@pytest_asyncio.fixture(autouse=True)
async def cleanup_event_broadcaster():
    """Clean up event broadcaster after each test.

    Clears all channels and subscriptions to prevent hanging tests
    from lingering event broadcaster queues.
    """
    yield
    # Clear all channels and subscriptions
    broadcaster._channels.clear()


@pytest_asyncio.fixture
async def db_session(requires_database, reset_engine_connections) -> AsyncGenerator[AsyncSession]:
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


@pytest_asyncio.fixture
async def create_test_analysis(db_session):
    """Create a test Analysis record for use in agent tests.

    Returns a helper function that creates an Analysis record with the given parameters.
    The analysis is automatically rolled back after the test due to db_session fixture.

    Usage:
        async def test_my_agent(create_test_analysis, db_session):
            analysis_id = str(uuid4())
            analysis = await create_test_analysis(
                analysis_id=analysis_id,
                url="https://example.com",
                content_type="article"
            )
            # Now you can use analysis_id with agents
    """

    async def _create(
        analysis_id: str,
        url: str = "https://example.com",
        content_type: str = "article",
    ) -> Analysis:
        """Create an Analysis record in the database."""
        analysis = Analysis(
            id=UUID(analysis_id),
            url=url,
            content_type=content_type,
            status="pending",
        )
        db_session.add(analysis)
        await db_session.commit()
        await db_session.refresh(analysis)
        return analysis

    return _create
