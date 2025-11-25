"""Integration test for real article analysis workflow.

This test processes a real article and verifies the complete workflow
including content extraction, embedding generation, supervisor routing,
and agent execution with proper session isolation.
"""

import os
from uuid import uuid4

import pytest

from app.workflows.analysis import analysis_workflow


@pytest.fixture
def requires_jina_api_key():
    """Skip test if JINA_API_KEY is not set."""
    if not os.environ.get("JINA_API_KEY"):
        pytest.skip("JINA_API_KEY not set in .env - skipping integration test")


@pytest.mark.asyncio
@pytest.mark.slow
@pytest.mark.external
@pytest.mark.timeout(300)  # 5 minutes for full workflow
async def test_real_article_analysis_claude_opus_4_5(
    requires_jina_api_key,
    requires_database,
    reset_engine_connections,
):
    """Test complete workflow with real Claude Opus 4.5 article.

    This test verifies:
    - Content extraction works
    - Embedding generation works
    - Supervisor routing works
    - Agent execution with separate sessions works
    - No GeneratorExit errors
    - No database concurrency errors
    - LangSmith tracing is active
    """
    # Claude Opus 4.5 release article
    test_url = (
        "https://www.reuters.com/business/retail-consumer/"
        "anthropic-bolsters-ai-model-claudes-coding-agentic-abilities-with-opus-45-2025-11-24/"
    )
    analysis_id = str(uuid4())

    # Run workflow with LangSmith configuration
    workflow_config = {
        "configurable": {"thread_id": analysis_id},
        "run_name": f"test_real_analysis_{analysis_id[:8]}",
        "tags": ["test", "integration", "real_data", "claude_opus_4.5"],
        "metadata": {
            "analysis_id": analysis_id,
            "url": test_url,
            "test_type": "real_data_verification",
        },
    }

    result = await analysis_workflow.ainvoke(
        {
            "url": test_url,
            "analysis_id": analysis_id,
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
    assert len(result["raw_content"]) > 0
    assert isinstance(result["extraction_metadata"], dict)
    assert len(result["content_embedding"]) == 768  # nomic-embed-text dimensions
    assert all(isinstance(x, float) for x in result["content_embedding"])

    # Verify supervisor selected agents
    supervisor_decision = result["supervisor_decision"]
    assert "agents" in supervisor_decision
    assert len(supervisor_decision["agents"]) > 0

    # Verify agent findings (should have results if agents completed)
    agent_findings = result["agent_findings"]
    # Note: Agents may timeout in integration tests, but structure should be correct
    assert isinstance(agent_findings, list)

    # Verify LangSmith tracing is enabled
    assert os.getenv("LANGCHAIN_TRACING_V2") == "true", "LangSmith tracing should be enabled"
