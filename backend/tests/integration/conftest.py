"""Integration test configuration and fixtures.

Integration tests use REAL database connections and REAL API keys.
They send traces to Langfuse for observability.

IMPORTANT: Integration tests require:
- Running PostgreSQL with pgvector (port 5437)
- Valid API keys in backend/.env (OPENAI_API_KEY or GOOGLE_API_KEY)
- Langfuse credentials (LANGFUSE_PUBLIC_KEY, LANGFUSE_SECRET_KEY)
"""

import os
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

import pytest
import pytest_asyncio
from fastapi import FastAPI
from sqlalchemy.ext.asyncio import AsyncSession

# Import app and lifespan for lifecycle initialization
from app.main import app, lifespan

# Import app and lifespan for lifecycle initialization

# CRITICAL: Load .env.test BEFORE any other imports to get test environment API keys
# Integration tests use TEST environment (.env.test), not dev (.env)
# This ensures complete separation: tests use test database, test Langfuse, etc.
_test_env_file = Path(__file__).parent.parent.parent / ".env.test"
_env_file = Path(__file__).parent.parent.parent / ".env"
# Prefer .env.test if it exists, fallback to .env for backward compatibility
env_file_to_load = _test_env_file if _test_env_file.exists() else _env_file
if env_file_to_load.exists():
    from dotenv import load_dotenv

    # Override=True ensures we get keys from test environment, not placeholders
    load_dotenv(env_file_to_load, override=True)

# Note: Langfuse tracing is configured via LANGFUSE_* environment variables
# LANGCHAIN_TRACING_V2 was used for LangSmith but is NOT needed for Langfuse

# Note: Langfuse credentials should be set via:
# 1. .env file (loaded above)
# 2. Environment variables (LANGFUSE_PUBLIC_KEY, LANGFUSE_SECRET_KEY, LANGFUSE_HOST)
# If not set, Langfuse will be disabled but tests will still run
#
# DEBUG: Check if Langfuse is configured for tracing
if os.getenv("LANGFUSE_PUBLIC_KEY") and os.getenv("LANGFUSE_SECRET_KEY"):
    print(f"✓ Langfuse configured (host: {os.getenv('LANGFUSE_HOST', 'default')})")
    _LANGFUSE_AVAILABLE = True
else:
    print("✗ Langfuse credentials not set - traces will not be sent")
    print("  Set LANGFUSE_PUBLIC_KEY and LANGFUSE_SECRET_KEY in .env to enable tracing")
    _LANGFUSE_AVAILABLE = False


# ============================================================================
# Langfuse Trace Context Fixture
# ============================================================================


@pytest.fixture(autouse=True)
def langfuse_trace_context(request):
    """Create a Langfuse trace context for each integration test.

    This fixture ensures that all LLM calls made during integration tests
    have an active trace span, eliminating the "No active span in current context"
    warning. Each test gets its own trace with the test name as the trace name.

    The trace is automatically created before the test and flushed after.
    """
    if not _LANGFUSE_AVAILABLE:
        yield  # No-op if Langfuse not configured
        return

    try:
        from langfuse import Langfuse

        langfuse = Langfuse()
        # Create a trace for this test
        trace = langfuse.trace(
            name=f"test:{request.node.name}",
            metadata={
                "test_module": request.node.module.__name__ if request.node.module else "unknown",
                "test_file": str(request.node.fspath),
            },
            tags=["integration-test"],
        )
        yield trace
        # Flush traces after test completes
        langfuse.flush()
    except Exception:
        # If Langfuse fails, don't break tests
        yield


# ============================================================================
# Test Data Creation Helpers
# ============================================================================


async def create_complete_analysis(
    db_session: AsyncSession,
    url: str | None = None,
    **kwargs,
):
    """Create a complete analysis with all required fields.

    Ensures status='complete' analyses have raw_content and extraction_metadata
    to satisfy database constraints.

    Args:
        db_session: Database session to use
        url: Optional URL (defaults to unique test URL with UUID)
        **kwargs: Additional Analysis fields (id, title, content_type, etc.)
            Note: If 'id' is provided in kwargs, it will be used; otherwise,
            PostgreSQL will auto-generate a UUIDv7 via server_default.

    Returns:
        Created Analysis instance

    Example:
        >>> analysis = await create_complete_analysis(
        ...     db_session,
        ...     title="Test Article",
        ...     raw_content="Full article content here",
        ... )

    """
    from app.db.models.analysis import Analysis

    # Let PostgreSQL generate UUIDv7 unless explicitly provided
    analysis_kwargs = {
        "url": url or f"https://example.com/test-{uuid4()}",
        "content_type": kwargs.get("content_type", "article"),
        "status": "complete",
        "raw_content": kwargs.get("raw_content", "Test content for complete analysis."),
        "extraction_metadata": kwargs.get(
            "extraction_metadata",
            {
                "title": kwargs.get("title", "Test Article"),
                "word_count": kwargs.get("word_count", 100),
                "char_count": kwargs.get("char_count", 500),
            },
        ),
        "created_at": kwargs.get("created_at", datetime.now(UTC)),
    }

    # Add any additional kwargs, including 'id' if explicitly provided
    for k, v in kwargs.items():
        if k not in ["url", "content_type", "status", "raw_content", "extraction_metadata", "created_at"]:
            analysis_kwargs[k] = v

    analysis = Analysis(**analysis_kwargs)
    db_session.add(analysis)
    await db_session.flush()
    return analysis


async def create_pending_analysis(
    db_session: AsyncSession,
    url: str | None = None,
    **kwargs,
):
    """Create a pending analysis (no content required).

    Use this for tests that don't need complete analyses. Pending analyses
    don't require raw_content or extraction_metadata.

    Args:
        db_session: Database session to use
        url: Optional URL (defaults to unique test URL with UUID)
        **kwargs: Additional Analysis fields (id, content_type, status, etc.)
            Note: If 'id' is provided in kwargs, it will be used; otherwise,
            PostgreSQL will auto-generate a UUIDv7 via server_default.

    Returns:
        Created Analysis instance

    Example:
        >>> analysis = await create_pending_analysis(
        ...     db_session,
        ...     content_type="video",
        ...     status="extracting",
        ... )

    """
    from app.db.models.analysis import Analysis

    # Let PostgreSQL generate UUIDv7 unless explicitly provided
    analysis_kwargs = {
        "url": url or f"https://example.com/test-{uuid4()}",
        "content_type": kwargs.get("content_type", "article"),
        "status": kwargs.get("status", "pending"),
    }

    # Add any additional kwargs, including 'id' if explicitly provided
    for k, v in kwargs.items():
        if k not in ["url", "content_type", "status"]:
            analysis_kwargs[k] = v

    analysis = Analysis(**analysis_kwargs)
    db_session.add(analysis)
    await db_session.flush()
    return analysis


# ============================================================================
# Agent Examples Fixture
# ============================================================================


@pytest.fixture
async def minimal_agent_examples(db_session):
    """Create minimal set of agent examples for testing.

    Creates at least one example for each expected agent type to satisfy
    few-shot integration test requirements.
    """
    from app.db.models.agent_example import AgentExample
    from app.shared.services.embeddings.service import EmbeddingService

    embedding_service = EmbeddingService()
    examples_data = [
        ("tech_comparator", "Comparing React vs Vue for state management in modern applications"),
        ("security_auditor", "Auditing API security for authentication and authorization"),
        ("implementation_planner", "Planning FastAPI endpoint implementation with error handling"),
        ("performance_analyst", "Analyzing database query performance and optimization strategies"),
        ("research_analyst", "Researching best practices for microservices architecture"),
        ("code_reviewer", "Reviewing Python code for style, performance, and security issues"),
        ("learning_path", "Creating a learning path for mastering TypeScript and React"),
    ]

    examples = []
    for agent_type, input_summary in examples_data:
        # Generate embedding for input summary
        embedding = await embedding_service.generate_embedding(input_summary[:500])
        example = AgentExample(
            agent_type=agent_type,
            input_summary=input_summary[:500],
            output_example={"findings": f"Test output for {agent_type}"},
            embedding=embedding,
            quality_score=0.9,
        )
        db_session.add(example)
        examples.append(example)

    await db_session.commit()
    return examples


@pytest_asyncio.fixture
async def app_with_lifespan() -> FastAPI:
    """Initialize FastAPI app with proper lifecycle (lifespan context manager).

    This fixture ensures app.state is properly initialized (including background_tasks)
    before tests run, matching production behavior.

    The lifespan context manager runs:
    - Startup: Initializes app.state.background_tasks, configures Langfuse, etc.
    - Shutdown: Cleans up resources

    Usage:
        @pytest.mark.asyncio
        async def test_endpoint(app_with_lifespan):
            transport = ASGITransport(app=app_with_lifespan)
            async with AsyncClient(transport=transport) as client:
                response = await client.post("/api/v1/analyze", ...)
    """
    # Run lifespan startup and shutdown
    async with lifespan(app):
        yield app
        # Lifespan shutdown runs automatically on exit
