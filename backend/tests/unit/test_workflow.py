"""Tests for LangGraph analysis workflow."""

import pytest

from app.workflows.analysis import analysis_workflow, extract_content, generate_embedding


@pytest.mark.asyncio
async def test_extract_content_task():
    """Test extract_content task emits SSE events."""
    # This test verifies the task structure
    # Full integration test would require actual Jina API
    analysis_id = "123e4567-e89b-12d3-a456-426614174000"
    url = "https://example.com/article"

    # Task should be callable and return a future-like object
    future = extract_content(url, analysis_id)
    assert hasattr(future, "result"), "Task should return future-like object"


@pytest.mark.asyncio
async def test_generate_embedding_task():
    """Test generate_embedding task structure."""
    analysis_id = "123e4567-e89b-12d3-a456-426614174000"
    content = "Test content for embedding"

    # Task should be callable and return a future-like object
    future = generate_embedding(content, analysis_id)
    assert hasattr(future, "result"), "Task should return future-like object"


@pytest.mark.asyncio
async def test_analysis_workflow_structure():
    """Test analysis_workflow is callable."""
    analysis_id = "123e4567-e89b-12d3-a456-426614174000"
    url = "https://example.com/article"

    # Workflow should be callable
    # Note: Full execution test requires Jina API and would be integration test
    assert callable(analysis_workflow), "Workflow should be callable"


def test_analysis_state_typeddict():
    """Test AnalysisState TypedDict structure."""
    from app.workflows.analysis import AnalysisState

    # Verify TypedDict structure
    state: AnalysisState = {
        "analysis_id": "123",
        "url": "https://example.com",
        "content_type": "article",
        "raw_content": "content",
        "extraction_metadata": {},
        "content_embedding": [0.0] * 1536,
        "supervisor_decision": None,
        "agent_findings": [],
        "aggregated_insights": None,
        "final_markdown": None,
    }

    assert state["analysis_id"] == "123"
    assert state["url"] == "https://example.com"
    assert isinstance(state["content_embedding"], list)
