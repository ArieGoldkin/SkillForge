"""Pytest configuration and fixtures."""

import logging
import os
from collections.abc import AsyncGenerator
from pathlib import Path
from uuid import UUID

# CRITICAL: Set test environment variables BEFORE any app imports
# This ensures settings are loaded with correct values when modules are first imported
# These are test-only values and won't affect production
# NOTE: DATABASE_URL should come from .env.test (port 5437) - don't override it here
# Only set a fallback if .env.test doesn't exist (for CI environments)
if "DATABASE_URL" not in os.environ:
    # Check if .env.test exists and has DATABASE_URL
    test_env_file = Path(__file__).parent.parent / ".env.test"
    if not test_env_file.exists():
        # Only set fallback if .env.test doesn't exist (for CI)
        # Use port 5437 to match Docker setup
        os.environ["DATABASE_URL"] = "postgresql://dev:devpass@localhost:5437/skillforge_test"
os.environ.setdefault("OPENAI_API_KEY", "sk-test-key-for-unit-tests")

# CRITICAL: Disable LangSmith tracing for UNIT tests only
# Integration tests have their own conftest.py (tests/integration/conftest.py) that enables tracing
# This must be set before importing any modules that use langsmith.traceable
# Setting these env vars prevents LangSmith from initializing background threads for unit tests
# Integration tests will override this in their conftest.py which runs AFTER this one
# (pytest loads conftest.py files in order: root conftest, then subdirectory conftest)
os.environ["LANGCHAIN_TRACING_V2"] = "false"
os.environ["LANGSMITH_TRACING"] = "false"
# Also unset API key to prevent any initialization attempts in unit tests
# Integration tests will restore it in their conftest.py
if "LANGSMITH_API_KEY" in os.environ:
    del os.environ["LANGSMITH_API_KEY"]
if "LANGCHAIN_API_KEY" in os.environ:
    del os.environ["LANGCHAIN_API_KEY"]

import pytest
import pytest_asyncio
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, get_settings
from app.main import app
from app.services.event_broadcaster import broadcaster

# Note: AsyncSessionLocal, engine, and Analysis are imported lazily inside fixtures
# to avoid DATABASE_URL validation errors in CI environments without database config

# Suppress LangSmith background thread logging errors
# These loggers emit DEBUG messages during teardown that fail when stdout is closed
for _logger_name in [
    "langsmith._internal._background_thread",
    "langsmith.client",
    "urllib3.connectionpool",
]:
    logging.getLogger(_logger_name).setLevel(logging.WARNING)

# Load .env.test file for tests (preferred) or .env as fallback
# This allows tests to use the correct database configuration (port 5437)
# We use python-dotenv to explicitly load the file to ensure VS Code test explorer
# and pytest both load environment variables correctly
TEST_ENV_FILE = Path(__file__).parent.parent / ".env.test"
ENV_FILE = Path(__file__).parent.parent / ".env"

# Prefer .env.test if it exists (has correct DATABASE_URL with port 5437)
env_file_to_load = TEST_ENV_FILE if TEST_ENV_FILE.exists() else ENV_FILE

if env_file_to_load.exists():
    # Explicitly load .env.test or .env using python-dotenv for VS Code test explorer compatibility
    try:
        from dotenv import load_dotenv

        # Load .env.test or .env file explicitly (override existing env vars to use correct DATABASE_URL)
        # This ensures we use port 5437 from .env.test instead of default port 5432
        load_dotenv(dotenv_path=env_file_to_load, override=True)
    except ImportError:
        # If python-dotenv is not available, fall back to setting ENV_FILE
        # The Settings class will detect this and load .env.test or .env
        os.environ["ENV_FILE"] = str(env_file_to_load)

    # Set environment variable to load .env.test or .env (for Settings class)
    os.environ["ENV_FILE"] = str(env_file_to_load)
    # Also set ENVIRONMENT=development for test mode
    # (Settings validation requires development/staging/production)
    os.environ.setdefault("ENVIRONMENT", "development")

# CRITICAL: Clear settings cache after loading .env.test
# This ensures Settings picks up the correct DATABASE_URL (port 5437) from .env.test
# Must be done after loading .env.test but before any Settings instances are created
try:
    from app.core.config import get_settings

    get_settings.cache_clear()
except ImportError:
    # Settings not imported yet, cache will be cleared when it's first imported
    pass

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
    """Create test client for FastAPI app.

    Note: This fixture requires DATABASE_URL to be configured because the app
    imports database session modules. Tests that don't need a real database
    should mock the session module or use unit test patterns that don't require
    the full FastAPI app.
    """
    settings = get_settings()
    if not settings.DATABASE_URL:
        pytest.skip("DATABASE_URL not configured - client fixture requires database")
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
def ensure_test_env_vars(monkeypatch):
    """Ensure test environment variables are set before each test.

    This fixture runs automatically for every test and ensures:
    1. Test env vars are set (defense in depth)
    2. Settings cache is cleared for fresh settings
    3. Works even if modules were imported before conftest.py ran

    NOTE: DATABASE_URL is NOT overridden if already set (e.g., from .env.test).
    This allows integration tests to use the real database configuration.
    """
    # Only set DATABASE_URL if not already set (e.g., from .env.test)
    # Integration tests need the real DATABASE_URL (port 5437 from .env.test)
    if "DATABASE_URL" not in os.environ:
        # Use port 5437 to match Docker setup
        monkeypatch.setenv("DATABASE_URL", "postgresql://test:test@localhost:5437/test")
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test-key-for-unit-tests")

    # Clear settings cache to force fresh settings instance
    get_settings.cache_clear()

    # Force reload of settings module's settings object
    # This is necessary because module-level `settings = get_settings()`
    # creates a reference that persists even after cache clear
    import app.core.config

    app.core.config.settings = get_settings()

    yield

    # Cleanup: clear cache after test
    get_settings.cache_clear()


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
    """Skip test if DATABASE_URL is not configured.

    Note: We don't check if database is reachable here to avoid hanging.
    The pool_timeout in engine config should prevent hanging if database
    is unreachable. Tests will fail quickly with timeout errors rather than
    hanging indefinitely.

    For actual connectivity checks, use check_database_available fixture
    which performs a fast (0.5s) connection test.
    """
    settings = get_settings()
    if not settings.DATABASE_URL:
        pytest.skip("DATABASE_URL not configured")


async def get_test_session(timeout: float | None = None) -> AsyncSession:
    """Create a test database session with timeout protection.

    Wraps AsyncSessionLocal() with timeout to prevent hanging if database
    is unreachable or connection pool is exhausted.

    Args:
        timeout: Timeout in seconds (defaults to 2.0 for tests - reasonable timeout)

    Returns:
        AsyncSession with timeout protection (caller must close it)

    Raises:
        asyncio.TimeoutError: If session creation times out

    """
    import asyncio

    from app.db.session import AsyncSessionLocal

    # Use reasonable timeout for tests (2 seconds) to allow proper connection
    # while still preventing hanging when PostgreSQL is not running
    if timeout is None:
        timeout = 2.0

    # Create session with timeout protection
    # AsyncSessionLocal() returns an AsyncSession which is a context manager
    # We need to enter it with timeout protection
    session = AsyncSessionLocal()
    enter_task = asyncio.create_task(session.__aenter__())
    try:
        await asyncio.wait_for(enter_task, timeout=timeout)
        return session
    except TimeoutError:
        enter_task.cancel()
        try:
            await enter_task
        except asyncio.CancelledError:
            pass
        # Try to close the session if entry failed
        try:
            await session.__aexit__(None, None, None)
        except Exception:
            pass
        raise


class TimeoutSession:
    """Context manager for timeout-protected database sessions.

    Usage:
        async with TimeoutSession(timeout=5.0) as session:
            # use session
    """

    def __init__(self, timeout: float | None = None):
        """Initialize timeout session context manager.

        Args:
            timeout: Timeout in seconds (defaults to DB_TIMEOUT)

        """
        self.timeout = timeout
        self.session: AsyncSession | None = None

    async def __aenter__(self) -> AsyncSession:
        """Enter context manager and create session with timeout."""
        self.session = await get_test_session(timeout=self.timeout)
        return self.session

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Exit context manager and close session."""
        if self.session is not None:
            try:
                await self.session.__aexit__(exc_type, exc_val, exc_tb)
            except Exception:
                pass


@pytest_asyncio.fixture
async def check_database_available(requires_database):
    """Check if database is reachable and skip test if not available.

    Performs a quick connectivity check with 2-second timeout.
    Skips the test gracefully if database is unreachable.
    Uses reasonable timeout to allow proper connection while still failing fast.

    Clears cached engine to ensure it uses current DATABASE_URL.
    """
    import asyncio

    from sqlalchemy import text

    from app.db import session as session_module
    from app.db.session import AsyncSessionLocal

    # CRITICAL: Clear cached engine BEFORE any engine access
    # This ensures engine is recreated with current DATABASE_URL (port 5437)
    # Must clear both _engine and _session_factory to force complete recreation
    old_engine = session_module._engine
    session_module._engine = None
    session_module._session_factory = None

    # Dispose old engine connections if it existed
    # This ensures we're not using stale connections with wrong port
    if old_engine is not None:
        try:
            await old_engine.dispose()
        except Exception:
            pass  # Ignore disposal errors

    # Verify engine will use correct URL by checking get_async_database_url
    from app.db.session import get_async_database_url

    expected_url = get_async_database_url()
    if ":5437" not in expected_url:
        import sys

        print(f"WARNING: Expected port 5437 in URL, got: {expected_url}", file=sys.stderr)

    # Quick connectivity check with reasonable timeout (5s for Docker)
    # This allows proper connection while still failing fast if DB is unavailable
    # Note: We don't skip here - let tests run and fail naturally if DB is unavailable
    # This allows tests to run when database is available via Docker
    try:
        # Use AsyncSessionLocal directly with timeout protection
        session = AsyncSessionLocal()
        enter_task = asyncio.create_task(session.__aenter__())
        try:
            await asyncio.wait_for(enter_task, timeout=5.0)
            try:
                # Try a simple query with timeout
                query_task = asyncio.create_task(session.execute(text("SELECT 1")))
                await asyncio.wait_for(query_task, timeout=5.0)
            finally:
                # Ensure session is closed
                await session.__aexit__(None, None, None)
        except TimeoutError:
            enter_task.cancel()
            try:
                await enter_task
            except asyncio.CancelledError:
                pass
            try:
                await session.__aexit__(None, None, None)
            except Exception:
                pass
            # Don't skip - let test fail naturally so user knows DB is unavailable
            # pytest.skip("Database connection timeout - database may be unreachable")
    except Exception as e:
        # Don't skip - let test fail naturally so user knows DB is unavailable
        # This allows tests to run when database is available via Docker
        # pytest.skip(f"Database not available: {type(e).__name__}: {e}")
        pass


async def _dispose_engine_safely(timeout: float) -> None:
    """Dispose engine connections with timeout protection.

    Uses non-blocking approach to prevent hanging if database is unreachable.
    Uses reasonable timeout (2.0s) for tests to allow proper disposal.
    """
    import asyncio

    from app.db.session import engine

    # Use reasonable timeout for tests (2.0s) to allow proper disposal
    test_timeout = min(timeout, 2.0)

    # Create a task for dispose operation
    dispose_task = asyncio.create_task(engine.dispose())

    try:
        # Wait for dispose with timeout
        await asyncio.wait_for(dispose_task, timeout=test_timeout)
    except TimeoutError:
        # Cancel the dispose task if it times out
        dispose_task.cancel()
        try:
            await dispose_task
        except asyncio.CancelledError:
            pass
        # Continue anyway - connections will be cleaned up later
    except Exception:
        # If dispose fails for any reason, continue anyway
        pass


@pytest_asyncio.fixture
async def reset_engine_connections():
    """Dispose engine connections before test to avoid event loop conflicts.

    This ensures engine connections are created in the test's event loop,
    preventing 'attached to different loop' errors. Use this fixture for
    tests that use database connections and have event loop issues.

    Also clears the cached engine instance to force recreation with current DATABASE_URL.
    Uses non-blocking disposal with reasonable timeout (2.0s) to prevent hanging.
    """
    from app.db import session as session_module

    # Clear cached engine and session factory to force recreation
    # This ensures engine uses current DATABASE_URL (important for tests)
    session_module._engine = None
    session_module._session_factory = None

    # Use reasonable timeout (2.0s) for tests
    test_timeout = 2.0

    # Dispose existing connections before test
    await _dispose_engine_safely(test_timeout)

    yield

    # Dispose after test to clean up
    await _dispose_engine_safely(test_timeout)

    # Clear cached engine again after test
    session_module._engine = None
    session_module._session_factory = None


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
async def db_session(
    requires_database, reset_engine_connections, check_database_available
) -> AsyncGenerator[AsyncSession]:
    """Create a test database session with automatic rollback.

    Yields an async session and rolls back all changes after test.
    Requires DATABASE_URL to be configured and database to be reachable.
    reset_engine_connections ensures connections are in the test's event loop.
    check_database_available ensures database is reachable before creating session.

    Uses reasonable timeout (2.0s) to allow proper connection while preventing hanging.
    """
    # Create session with reasonable timeout protection (2.0s for tests)
    # This allows proper connection while preventing hanging when database is not running
    try:
        session = await get_test_session(timeout=2.0)
    except TimeoutError:
        pytest.skip("Database connection timeout - database may be unreachable")

    try:
        # Use nested transaction for automatic rollback
        transaction = await session.begin()
        try:
            yield session
        finally:
            # Only rollback if transaction is still active
            if transaction.is_active:
                try:
                    await transaction.rollback()
                except Exception:
                    # Transaction may already be closed, ignore
                    pass
    finally:
        # Ensure session is properly closed
        try:
            await session.close()
        except Exception:
            # Session may already be closed, ignore
            pass


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
    from app.models.analysis import Analysis

    async def _create(
        analysis_id: str,
        url: str = "https://example.com",
        content_type: str = "article",
    ) -> "Analysis":
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
