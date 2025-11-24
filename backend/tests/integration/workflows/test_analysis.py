"""Integration tests for analysis workflow."""

import os

import pytest

from app.core.config import get_settings
from app.workflows.analysis import analysis_workflow

# Expected embedding dimensions for nomic-embed-text
EXPECTED_EMBEDDING_DIMENSIONS = 768


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
async def test_analysis_workflow_end_to_end(requires_database) -> None:
    """Test analysis_workflow end-to-end with real services.

    This test requires:
    - Ollama running on localhost:11434 with nomic-embed-text model
    - Jina API key configured
    - Database connection

    Can take 2+ minutes due to Ollama embedding generation.
    """
    settings = get_settings()
    if not settings.JINA_API_KEY:
        pytest.skip("JINA_API_KEY not configured in .env")

    # Use a simple test URL
    test_url = "https://react.dev"
    test_analysis_id = "test-integration-analysis-123"

    # Run workflow
    result = await analysis_workflow.ainvoke(
        {
            "url": test_url,
            "analysis_id": test_analysis_id,
        },
        config={"configurable": {"thread_id": test_analysis_id}},
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


@pytest.mark.asyncio
@pytest.mark.slow
@pytest.mark.external
async def test_analysis_workflow_with_checkpointer(requires_database) -> None:
    """Test analysis_workflow with database checkpointer.

    This test requires:
    - Ollama running on localhost:11434 with nomic-embed-text model
    - Jina API key configured
    - Database connection

    Can take 2+ minutes due to Ollama embedding generation (runs twice).
    """
    settings = get_settings()
    if not settings.JINA_API_KEY:
        pytest.skip("JINA_API_KEY not configured in .env")

    test_url = "https://react.dev"
    test_analysis_id = "test-checkpointer-analysis-456"

    # Run workflow first time
    result1 = await analysis_workflow.ainvoke(
        {
            "url": test_url,
            "analysis_id": test_analysis_id,
        },
        config={"configurable": {"thread_id": test_analysis_id}},
    )

    # Run workflow again (should use checkpoint)
    result2 = await analysis_workflow.ainvoke(
        {
            "url": test_url,
            "analysis_id": test_analysis_id,
        },
        config={"configurable": {"thread_id": test_analysis_id}},
    )

    # Verify both results are consistent
    assert result1["analysis_id"] == result2["analysis_id"]
    assert result1["url"] == result2["url"]
    assert len(result1["content_embedding"]) == len(result2["content_embedding"])
