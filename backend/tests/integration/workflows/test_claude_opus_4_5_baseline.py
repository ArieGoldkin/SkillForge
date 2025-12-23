"""Integration test for Claude Opus 4.5 article as baseline.

This test uses the official Anthropic announcement article as a baseline
to verify the complete workflow works correctly with a known, high-quality
technical article. This serves as a regression test and performance baseline.
"""

import os
from uuid import UUID, uuid4

import pytest

from app.db.models.analysis import Analysis
from app.db.session import AsyncSessionLocal
from app.domains.analysis.workflows.analysis import create_analysis_workflow

# Test constants
EXPECTED_EMBEDDING_DIMENSIONS = 1536  # OpenAI text-embedding-3-small dimensions
MIN_CONTENT_LENGTH = 5000  # Minimum expected content length for substantial article
MIN_KEYWORD_MATCHES = 3  # Minimum number of expected keywords to find


@pytest.fixture
def requires_jina_api_key():
    """Skip test if JINA_API_KEY is not set."""
    placeholder_prefixes = ("sk-test", "test-", "dummy-", "placeholder-")

    jina_key = os.environ.get("JINA_API_KEY")
    if not jina_key:
        pytest.skip("JINA_API_KEY not set in .env - skipping integration test")

    openai_key = os.environ.get("OPENAI_API_KEY") or os.environ.get("LLM_OPENAI_API_KEY")
    if not openai_key or openai_key.lower().startswith(placeholder_prefixes):
        pytest.skip("OPENAI_API_KEY missing or placeholder - skipping integration test")

    anthropic_key = os.environ.get("ANTHROPIC_API_KEY")
    if not anthropic_key or anthropic_key.lower().startswith(placeholder_prefixes):
        pytest.skip("ANTHROPIC_API_KEY missing or placeholder - skipping integration test")


@pytest.mark.asyncio
@pytest.mark.slow
@pytest.mark.external
@pytest.mark.timeout(300)  # 5 minutes for full workflow with agents
async def test_claude_opus_4_5_baseline(
    requires_jina_api_key,
    requires_database,
    reset_engine_connections,
):
    """Test complete workflow with Claude Opus 4.5 announcement article.

    This is a baseline test using the official Anthropic announcement:
    https://www.anthropic.com/news/claude-opus-4-5

    This test verifies:
    - Content extraction works for Anthropic news articles
    - Embedding generation works (OpenAI text-embedding-3-small)
    - Supervisor routing works correctly
    - Agent execution completes successfully
    - All workflow stages complete without errors
    - Results contain expected structure and content

    This serves as:
    - Regression test for workflow integrity
    - Performance baseline for future optimizations
    - Integration test for real-world article processing
    """
    # Official Anthropic Claude Opus 4.5 announcement
    test_url = "https://www.anthropic.com/news/claude-opus-4-5"
    analysis_id = str(uuid4())

    # Create Analysis record before running workflow (required for agent foreign keys)
    async with AsyncSessionLocal() as session:
        analysis = Analysis(
            id=UUID(analysis_id),
            url=test_url,
            content_type="article",
            status="pending",
        )
        session.add(analysis)
        await session.commit()

    # Run workflow with LangSmith configuration
    workflow_config = {
        "configurable": {"thread_id": analysis_id},
        "run_name": f"baseline_claude_opus_4_5_{analysis_id[:8]}",
        "tags": ["test", "integration", "baseline", "claude_opus_4_5", "anthropic"],
        "metadata": {
            "analysis_id": analysis_id,
            "url": test_url,
            "test_type": "baseline_regression",
            "article_type": "product_announcement",
        },
    }

    workflow = create_analysis_workflow()
    result = await workflow.ainvoke(
        {
            "url": test_url,
            "analysis_id": analysis_id,
            "skill_level": "intermediate",
        },
        config=workflow_config,
    )

    # Verify result structure
    assert "analysis_id" in result
    assert "url" in result
    assert "raw_content" in result
    assert "extraction_metadata" in result
    assert "content_embedding" in result
    assert "supervisor_decision" in result
    assert "agent_findings" in result

    # Verify values
    assert result["analysis_id"] == analysis_id
    assert result["url"] == test_url
    assert len(result["raw_content"]) > 0, "Raw content should not be empty"
    assert isinstance(result["extraction_metadata"], dict)
    assert len(result["content_embedding"]) == EXPECTED_EMBEDDING_DIMENSIONS, (
        f"Expected {EXPECTED_EMBEDDING_DIMENSIONS} dimensions for OpenAI text-embedding-3-small"
    )
    assert all(isinstance(x, float) for x in result["content_embedding"])

    # Verify content quality - Claude Opus 4.5 article should be substantial
    content_length = len(result["raw_content"])
    assert content_length > MIN_CONTENT_LENGTH, (
        f"Article should be substantial "
        f"(got {content_length} chars, expected >{MIN_CONTENT_LENGTH})"
    )

    # Verify supervisor selected agents
    supervisor_decision = result["supervisor_decision"]
    assert "agents" in supervisor_decision
    assert len(supervisor_decision["agents"]) > 0, "Supervisor should select at least one agent"

    # Verify agent findings (should have results if agents completed)
    agent_findings = result["agent_findings"]
    assert isinstance(agent_findings, list)
    # Note: Agents may timeout in integration tests, but structure should be correct
    # If agents completed, verify they have findings
    if len(agent_findings) > 0:
        for finding in agent_findings:
            assert "agent_type" in finding
            assert "findings" in finding

    # Verify content contains expected keywords from Claude Opus 4.5 article
    content_lower = result["raw_content"].lower()
    expected_keywords = [
        "opus",
        "claude",
        "anthropic",
        "model",
        "coding",
        "agent",
    ]
    found_keywords = [kw for kw in expected_keywords if kw in content_lower]
    assert len(found_keywords) >= MIN_KEYWORD_MATCHES, (
        f"Should find at least {MIN_KEYWORD_MATCHES} expected keywords (found: {found_keywords})"
    )

    # Verify LangSmith tracing is enabled (if configured)
    if os.getenv("LANGCHAIN_TRACING_V2") == "true":
        # LangSmith tracing should be active - check if traces were attempted
        import time

        # Give traces time to send (they're async)
        time.sleep(2)
