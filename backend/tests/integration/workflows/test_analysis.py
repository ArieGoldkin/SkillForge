"""Integration tests for analysis workflow."""

import asyncio
import os

import pytest

from app.core.config import get_settings
from app.db.session import engine
from app.workflows.analysis import analysis_workflow

# Expected embedding dimensions for OpenAI text-embedding-3-small
EXPECTED_EMBEDDING_DIMENSIONS = 1536


@pytest.fixture
def requires_database():
    """Skip test if DATABASE_URL is not set."""
    settings = get_settings()
    if not settings.DATABASE_URL:
        pytest.skip("DATABASE_URL not configured")


@pytest.fixture
def requires_jina_api_key():
    """Skip test if JINA_API_KEY is not set."""
    if not os.environ.get("JINA_API_KEY"):
        pytest.skip("JINA_API_KEY not set in .env - skipping integration test")


@pytest.mark.asyncio
@pytest.mark.slow
@pytest.mark.external
@pytest.mark.timeout(
    150
)  # 2.5 minute max timeout - accounts for streaming/parallel execution overhead
async def test_analysis_workflow_end_to_end(requires_database, reset_engine_connections) -> None:
    """Test analysis_workflow end-to-end with real services.

    This test requires:
    - OpenAI API key configured
    - Jina API key configured
    - Database connection

    Can take 2+ minutes due to OpenAI embedding generation, streaming overhead,
    and parallel execution of embedding + supervisor tasks.

    Timeout increased to 150s to account for:
    - Streaming overhead from agent.astream()
    - Parallel execution overhead
    - Real external service response times
    - Variable network latency
    """
    settings = get_settings()
    if not settings.JINA_API_KEY:
        pytest.skip("JINA_API_KEY not configured in .env")

    # Use a simple test URL
    test_url = "https://react.dev"
    test_analysis_id = "test-integration-analysis-123"

    try:
        # Run workflow with timeout (increased for streaming/parallel overhead)
        # Add LangSmith tracing config
        workflow_config = {
            "configurable": {"thread_id": test_analysis_id},
            "run_name": f"test_analysis_{test_analysis_id}",
            "tags": ["test", "integration", "workflow"],
            "metadata": {
                "analysis_id": test_analysis_id,
                "url": test_url,
                "test_type": "end_to_end",
            },
        }
        result = await asyncio.wait_for(
            analysis_workflow.ainvoke(
                {
                    "url": test_url,
                    "analysis_id": test_analysis_id,
                },
                config=workflow_config,
            ),
            timeout=120.0,  # 120 seconds for real workflow with streaming/parallel overhead
        )

        # Verify result structure
        assert "analysis_id" in result
        assert "url" in result
        assert "raw_content" in result
        assert "extraction_metadata" in result
        assert "content_embedding" in result

        # Verify values
        assert result["analysis_id"] == test_analysis_id
        assert result["url"] == test_url
        assert len(result["raw_content"]) > 0
        assert isinstance(result["extraction_metadata"], dict)
        assert len(result["content_embedding"]) == EXPECTED_EMBEDDING_DIMENSIONS
        assert all(isinstance(x, float) for x in result["content_embedding"])
    finally:
        # Ensure engine connections are disposed
        await engine.dispose()


@pytest.mark.asyncio
@pytest.mark.slow
@pytest.mark.external
@pytest.mark.timeout(
    300
)  # 5 minute max timeout (runs twice) - accounts for streaming/parallel execution overhead
async def test_analysis_workflow_with_checkpointer(
    requires_database, reset_engine_connections
) -> None:
    """Test analysis_workflow with database checkpointer.

    This test requires:
    - OpenAI API key configured
    - Jina API key configured
    - Database connection

    Can take 2+ minutes per run due to OpenAI embedding generation, streaming overhead,
    and parallel execution. Runs twice to test checkpoint functionality.

    Timeout increased to 300s (5 minutes) to account for:
    - Two workflow runs (first run + checkpointed second run)
    - Streaming overhead from agent.astream() (both runs)
    - Parallel execution overhead (both runs)
    - Real external service response times
    - Variable network latency
    """
    settings = get_settings()
    if not settings.JINA_API_KEY:
        pytest.skip("JINA_API_KEY not configured in .env")

    test_url = "https://react.dev"
    test_analysis_id = "test-checkpointer-analysis-456"

    try:
        # Run workflow first time with timeout (increased for streaming/parallel overhead)
        workflow_config1 = {
            "configurable": {"thread_id": test_analysis_id},
            "run_name": f"test_analysis_checkpointer_run1_{test_analysis_id}",
            "tags": ["test", "integration", "workflow", "checkpointer"],
            "metadata": {
                "analysis_id": test_analysis_id,
                "url": test_url,
                "test_type": "checkpointer",
                "run": 1,
            },
        }
        result1 = await asyncio.wait_for(
            analysis_workflow.ainvoke(
                {
                    "url": test_url,
                    "analysis_id": test_analysis_id,
                },
                config=workflow_config1,
            ),
            timeout=120.0,  # 120 seconds for real workflow with streaming/parallel overhead
        )

        # Run workflow again (should use checkpoint) with timeout
        # (increased for streaming/parallel overhead)
        workflow_config2 = {
            "configurable": {"thread_id": test_analysis_id},
            "run_name": f"test_analysis_checkpointer_run2_{test_analysis_id}",
            "tags": ["test", "integration", "workflow", "checkpointer"],
            "metadata": {
                "analysis_id": test_analysis_id,
                "url": test_url,
                "test_type": "checkpointer",
                "run": 2,
            },
        }
        result2 = await asyncio.wait_for(
            analysis_workflow.ainvoke(
                {
                    "url": test_url,
                    "analysis_id": test_analysis_id,
                },
                config=workflow_config2,
            ),
            timeout=120.0,  # 120 seconds for real workflow with streaming/parallel overhead
        )

        # Verify both results are consistent
        assert result1["analysis_id"] == result2["analysis_id"]
        assert result1["url"] == result2["url"]
        assert len(result1["content_embedding"]) == len(result2["content_embedding"])
    finally:
        # Ensure engine connections are disposed
        await engine.dispose()
