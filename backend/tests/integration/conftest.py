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

# CRITICAL: Load .env BEFORE any other imports to get real API keys
# Integration tests need real keys, not placeholders
_env_file = Path(__file__).parent.parent.parent / ".env"
if _env_file.exists():
    from dotenv import load_dotenv

    # Override=True ensures we get real keys from .env, not placeholders
    load_dotenv(_env_file, override=True)

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
else:
    print("✗ Langfuse credentials not set - traces will not be sent")
    print("  Set LANGFUSE_PUBLIC_KEY and LANGFUSE_SECRET_KEY in .env to enable tracing")


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

    analysis = Analysis(
        id=kwargs.get("id", uuid4()),
        url=url or f"https://example.com/test-{uuid4()}",
        content_type=kwargs.get("content_type", "article"),
        status="complete",
        raw_content=kwargs.get("raw_content", "Test content for complete analysis."),
        extraction_metadata=kwargs.get(
            "extraction_metadata",
            {
                "title": kwargs.get("title", "Test Article"),
                "word_count": kwargs.get("word_count", 100),
                "char_count": kwargs.get("char_count", 500),
            },
        ),
        created_at=kwargs.get("created_at", datetime.now(UTC)),
        **{
            k: v
            for k, v in kwargs.items()
            if k
            not in [
                "id",
                "url",
                "content_type",
                "status",
                "raw_content",
                "extraction_metadata",
                "created_at",
            ]
        },
    )
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

    analysis = Analysis(
        id=kwargs.get("id", uuid4()),
        url=url or f"https://example.com/test-{uuid4()}",
        content_type=kwargs.get("content_type", "article"),
        status=kwargs.get("status", "pending"),
        **{k: v for k, v in kwargs.items() if k not in ["id", "url", "content_type", "status"]},
    )
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
