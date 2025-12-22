"""Pytest configuration and fixtures."""

import logging
import os
from collections.abc import AsyncGenerator
from pathlib import Path
from uuid import UUID

# CRITICAL: Do NOT set DATABASE_URL at module level - it prevents conftest.py from being
# importable without DATABASE_URL (required for CI import tests).
# DATABASE_URL is set in the ensure_test_env_vars fixture when tests actually need it.
# Set OPENAI_API_KEY placeholder at module level for unit tests that need it during fixture setup.
# Integration tests will override this by loading real keys from .env with override=True.
if "OPENAI_API_KEY" not in os.environ:
    os.environ["OPENAI_API_KEY"] = "sk-test-placeholder-for-unit-tests"

# CRITICAL: Disable Langfuse tracing for UNIT tests only
# Integration tests have their own conftest.py (tests/integration/conftest.py) that enables tracing
# This must be set before importing any modules that use Langfuse
# Setting these env vars prevents Langfuse from initializing background threads for unit tests
os.environ["LANGFUSE_ENABLED"] = "false"
# Also unset API keys to prevent any initialization attempts in unit tests
if "LANGFUSE_PUBLIC_KEY" in os.environ:
    del os.environ["LANGFUSE_PUBLIC_KEY"]
if "LANGFUSE_SECRET_KEY" in os.environ:
    del os.environ["LANGFUSE_SECRET_KEY"]

import pytest
import pytest_asyncio
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, get_settings
from app.main import app
from app.shared.services.messaging.broadcaster_factory import reset_broadcaster

# Note: AsyncSessionLocal, engine, and Analysis are imported lazily inside fixtures
# to avoid DATABASE_URL validation errors in CI environments without database config

# Suppress Langfuse background thread logging errors
# These loggers emit DEBUG messages during teardown that fail when stdout is closed
for _logger_name in [
    "langfuse",
    "langfuse.task_manager",
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

        # Load .env.test or .env file explicitly (override existing env vars to use correct
        # DATABASE_URL)
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

# Disable specificity validation for unit tests (mock outputs don't meet threshold)
# This allows tests to use simple mock outputs without failing specificity checks
# Production code will still enforce 0.70 threshold
os.environ.setdefault("SPECIFICITY_MIN_SCORE", "0.0")

# Set LLM_MODEL for tests - prefer Gemini 2.5 Flash if Google API key is available,
# otherwise use OpenAI if API key is available, otherwise skip tests
# This allows tests to run with Gemini/OpenAI when configured, but prevents import failures
# when langchain-google-genai/langchain-openai isn't available in IDE's Python environment
if "LLM_MODEL" not in os.environ:
    # Prefer Gemini if Google API key is available (faster, cheaper)
    google_key = os.environ.get("GOOGLE_API_KEY")
    if google_key:
        os.environ["LLM_MODEL"] = "gemini-2.5-flash"  # Use Gemini when key is available
    else:
        # Fallback to OpenAI if OpenAI key is available
        openai_key = os.environ.get("OPENAI_API_KEY") or os.environ.get("LLM_OPENAI_API_KEY")
        if openai_key:
            os.environ["LLM_MODEL"] = "gpt-4o-mini"  # Use OpenAI when key is available
    # If no API keys, tests that require LLM will be skipped


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


@pytest.fixture(autouse=True)
def ensure_test_env_vars(monkeypatch, request):
    """Ensure test environment variables are set before each test.

    This fixture runs automatically for every test and ensures:
    1. Test env vars are set (defense in depth)
    2. Settings cache is cleared for fresh settings
    3. Works even if modules were imported before conftest.py ran

    NOTE: DATABASE_URL is set here (not at module level) to allow conftest.py to be
    importable without DATABASE_URL (required for CI import tests).
    DATABASE_URL is NOT overridden if already set (e.g., from .env.test).
    This allows integration tests to use the real database configuration.

    NOTE: Smoke tests (marked with pytest.mark.smoke) skip the OPENAI_API_KEY
    placeholder to allow them to use real API keys from .env for live testing.
    """
    # Set DATABASE_URL if not already set (e.g., from .env.test)
    # This is done in the fixture (not at module level) to allow conftest.py to be
    # importable without DATABASE_URL for CI import tests.
    # Integration tests need the real DATABASE_URL (port 5437 from .env.test)
    if "DATABASE_URL" not in os.environ:
        # Use port 5437 to match Docker setup
        monkeypatch.setenv(
            "DATABASE_URL", "postgresql://dev:devpass@localhost:5437/skillforge_test"
        )

    # Skip OPENAI_API_KEY placeholder for smoke and integration tests - they need real keys
    # Check for smoke or integration marker to allow live API calls
    is_smoke_test = request.node.get_closest_marker("smoke") is not None
    is_integration_test = request.node.get_closest_marker("integration") is not None
    if not is_smoke_test and not is_integration_test:
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

    This ensures tests default to Gemini 2.5 Flash when Google API key is available,
    or OpenAI when OpenAI key is available, even if LLM_MODEL is not set in the environment.
    Individual tests can override this by setting their own LLM_MODEL.
    """
    # Only set if not already in environment (module-level setenv takes precedence)
    if "LLM_MODEL" not in os.environ:
        # Prefer Gemini if Google API key is available (faster, cheaper)
        google_key = os.environ.get("GOOGLE_API_KEY")
        if google_key:
            monkeypatch.setenv("LLM_MODEL", "gemini-2.5-flash")
        else:
            # Fallback to OpenAI if OpenAI key is available
            openai_key = os.environ.get("OPENAI_API_KEY") or os.environ.get("LLM_OPENAI_API_KEY")
            if openai_key:
                monkeypatch.setenv("LLM_MODEL", "gpt-4o-mini")
    # Reduce retry attempts for faster tests (1 instead of 3)
    if "LLM_MAX_RETRIES" not in os.environ:
        monkeypatch.setenv("LLM_MAX_RETRIES", "1")
    # Clear settings cache to pick up env vars
    get_settings.cache_clear()


@pytest.fixture
def mock_async_session_local():
    """Create a properly mocked AsyncSessionLocal for unit tests.

    This fixture provides a mock AsyncSessionLocal that returns an async context manager,
    which in turn yields a mock session. Use this in unit tests that need to mock database
    sessions without making real database connections.

    Usage:
        async def test_something(mock_async_session_local, mock_session):
            with patch("app.db.session.AsyncSessionLocal", mock_async_session_local):
                # Your test code here
                pass
    """
    from unittest.mock import AsyncMock, MagicMock

    # Create a mock session
    mock_session = MagicMock()
    mock_session.__aenter__ = AsyncMock(return_value=mock_session)
    mock_session.__aexit__ = AsyncMock(return_value=False)

    # Create a mock async context manager that yields the session
    mock_context_manager = MagicMock()
    mock_context_manager.__aenter__ = AsyncMock(return_value=mock_session)
    mock_context_manager.__aexit__ = AsyncMock(return_value=False)

    # AsyncSessionLocal itself is callable and returns the context manager
    return MagicMock(return_value=mock_context_manager)


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


async def get_test_session(timeout: float | None = None) -> AsyncSession:  # noqa: ASYNC109
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
        except Exception:  # noqa: S110
            pass  # Ignore cleanup errors when session entry failed
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
            except Exception:  # noqa: S110
                pass  # Ignore cleanup errors - session may already be closed


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
        except Exception:  # noqa: S110
            pass  # Ignore disposal errors - connections will be cleaned up later

    # Verify engine will use correct URL by checking get_async_database_url
    from app.db.session import get_async_database_url

    expected_url = get_async_database_url()
    if ":5437" not in expected_url:
        import sys

        print(f"WARNING: Expected port 5437 in URL, got: {expected_url}", file=sys.stderr)

    # Quick connectivity check with fast timeout (1.0s) to prevent hanging
    # pytest 9.0.1's improved async fixture support allows faster failure detection
    # This allows proper connection while still failing fast if DB is unavailable
    # Skip tests gracefully in CI when database is not available
    try:
        # Use AsyncSessionLocal directly with timeout protection
        # Reduced timeout to 1.0s to prevent hanging when DB is unavailable
        session = AsyncSessionLocal()
        enter_task = asyncio.create_task(session.__aenter__())
        try:
            await asyncio.wait_for(enter_task, timeout=1.0)
            try:
                # Try a simple query with fast timeout
                query_task = asyncio.create_task(session.execute(text("SELECT 1")))
                await asyncio.wait_for(query_task, timeout=1.0)
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
            except Exception:  # noqa: S110
                pass  # Ignore cleanup errors when session entry failed
            # Skip test when database is unavailable (e.g., in CI without database)
            pytest.skip("Database not available - connection timeout")
    except Exception as e:
        # Skip test when database connection fails (e.g., in CI without database)
        pytest.skip(f"Database not available - {type(e).__name__}: {e!s}")


async def _dispose_engine_safely(timeout: float) -> None:  # noqa: ASYNC109
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
    except Exception:  # noqa: S110
        # If dispose fails for any reason, continue anyway
        pass


@pytest_asyncio.fixture
async def reset_engine_connections():
    """Dispose engine connections before test to avoid event loop conflicts.

    Leverages pytest 9.0.1's improved async fixture lifecycle management:
    - Automatic cleanup for async resources (cleanup runs even on test failures)
    - Enhanced fixture scoping for async operations
    - Improved resource management with automatic finally block execution

    This ensures engine connections are created in the test's event loop,
    preventing 'attached to different loop' errors. Use this fixture for
    tests that use database connections and have event loop issues.

    Also clears the cached engine instance to force recreation with current DATABASE_URL.
    Uses non-blocking disposal with reasonable timeout (2.0s) to prevent hanging.
    pytest 9.0.1 automatically ensures cleanup runs even if tests fail.
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

    # pytest 9.0.1 automatically ensures cleanup runs even if test fails
    # No need for redundant try/finally - automatic cleanup handles it
    await _dispose_engine_safely(test_timeout)

    # Clear cached engine again after test
    session_module._engine = None
    session_module._session_factory = None


@pytest_asyncio.fixture(autouse=True)
async def cleanup_event_broadcaster():
    """Clean up event broadcaster after each test.

    Leverages pytest 9.0.1's improved async fixture lifecycle management.
    Issue #444: Uses reset_broadcaster() from factory pattern to properly
    clean up both in-memory and Redis broadcasters.

    This prevents:
    - Hanging tests from lingering event broadcaster queues
    - Flaky tests from previous test's buffered events being replayed

    pytest 9.0.1 provides automatic cleanup for async fixtures,
    ensuring resources are properly released even if tests fail.
    No need for try/finally - automatic cleanup handles it.

    Note: Event buffers were added in commit 9430387 (SSE race condition fix).
    This cleanup must reset the broadcaster to prevent test pollution.
    """
    yield
    # Issue #444: Reset broadcaster factory singleton to ensure clean state
    # This handles both in-memory and Redis broadcasters properly
    await reset_broadcaster()


@pytest_asyncio.fixture
async def db_session(
    requires_database, reset_engine_connections, check_database_available
) -> AsyncGenerator[AsyncSession]:
    """Create a test database session with automatic rollback.

    Leverages pytest 9.0.1's enhanced async fixture support:
    - Automatic lifecycle management for async resources
    - Automatic cleanup even on test failures (no redundant try/finally needed)
    - Enhanced async fixture scoping

    Yields an async session and rolls back all changes after test.
    Requires DATABASE_URL to be configured and database to be reachable.
    reset_engine_connections ensures connections are in the test's event loop.
    check_database_available ensures database is reachable before creating session.

    Uses reasonable timeout (2.0s) to allow proper connection while preventing hanging.
    pytest 9.0.1 automatically ensures proper cleanup of async resources even if tests fail.
    """
    # Create session with reasonable timeout protection (2.0s for tests)
    # This allows proper connection while preventing hanging when database is not running
    try:
        session = await get_test_session(timeout=2.0)
    except TimeoutError:
        pytest.skip("Database connection timeout - database may be unreachable")

    # Use nested transaction for automatic rollback
    # pytest 9.0.1's automatic cleanup ensures rollback runs even on test failures
    transaction = await session.begin()
    try:
        yield session
    finally:
        # Only rollback if transaction is still active
        # pytest 9.0.1 ensures this cleanup runs automatically, but we need explicit
        # rollback for transaction management
        if transaction.is_active:
            try:
                await transaction.rollback()
            except Exception:  # noqa: S110
                # Transaction may already be closed, ignore
                pass
        # pytest 9.0.1 automatically ensures session.close() runs via async generator cleanup
        # No need for redundant finally block - automatic cleanup handles it
        try:
            await session.close()
        except Exception:  # noqa: S110
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
    from app.db.models.analysis import Analysis

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


@pytest.fixture
def requires_llm():
    """Skip test if LLM is not configured or required API key is missing.

    This fixture intelligently checks for the correct API key based on the
    configured LLM_MODEL. It uses the Settings class to determine which
    provider is being used and checks for the appropriate API key.

    Supports:
    - Gemini models → checks GOOGLE_API_KEY
    - OpenAI models → checks OPENAI_API_KEY
    - Claude models → checks ANTHROPIC_API_KEY
    - Other providers → checks corresponding API key

    This is configurable via LLM_MODEL environment variable - no code changes needed
    when switching models. Just update your .env file:

        LLM_MODEL=gemini-2.5-flash
        GOOGLE_API_KEY=your_key_here

    Or:

        LLM_MODEL=gpt-4o-mini
        OPENAI_API_KEY=your_key_here
    """
    from app.core.config import LLM_PROVIDER_API_FIELDS, get_settings

    settings = get_settings()
    llm_model = settings.LLM_MODEL

    if not llm_model:
        pytest.skip("LLM_MODEL not configured")

    # Determine provider from model name using Settings class
    try:
        provider = settings.resolved_llm_provider()
    except ValueError as e:
        pytest.skip(f"Cannot determine LLM provider for model '{llm_model}': {e}")

    # Get the required API key field name for this provider
    api_field = LLM_PROVIDER_API_FIELDS.get(provider)

    if not api_field:
        pytest.skip(
            f"Unknown LLM provider '{provider}' for model '{llm_model}'. "
            "Cannot determine required API key."
        )

    # Check if the required API key is available
    # Type: ignore needed because api_field is a dynamic string attribute name
    # The values in LLM_PROVIDER_API_FIELDS are guaranteed to be valid Settings attributes
    api_key = getattr(settings, api_field, None)  # type: ignore[arg-type]

    if not api_key:
        pytest.skip(
            f"{api_field} not available (required for {provider} model '{llm_model}'). "
            f"Set {api_field} in your .env file or environment variables."
        )

    # Skip if a known placeholder/test key is provided to avoid live calls failing
    placeholder_prefixes = ("sk-test", "test-", "dummy-", "placeholder-")
    if isinstance(api_key, str) and api_key.lower().startswith(placeholder_prefixes):
        pytest.skip(f"{api_field} appears to be a placeholder; skipping external LLM tests.")
