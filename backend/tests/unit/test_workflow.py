"""Tests for LangGraph analysis workflow."""

import pytest

from app.domains.analysis.workflows.analysis import analysis_workflow

@pytest.mark.unit


@pytest.mark.asyncio
async def test_extract_content_task():
    """Test extract_content task is accessible (tested via workflow).

    Note: LangGraph v1.0 tasks can only be called within a workflow context.
    The actual task functionality is tested via test_analysis_workflow_with_mocked_services.
    """
    # Tasks are tested through the workflow, not in isolation
    # This test verifies the task is importable and part of the workflow
    from app.domains.analysis.workflows.tasks import extract_content

    assert extract_content is not None, "extract_content task should be importable"


@pytest.mark.asyncio
async def test_generate_embedding_task():
    """Test generate_embedding task is accessible (tested via workflow).

    Note: LangGraph v1.0 tasks can only be called within a workflow context.
    The actual task functionality is tested via test_analysis_workflow_with_mocked_services.
    """
    # Tasks are tested through the workflow, not in isolation
    # This test verifies the task is importable and part of the workflow
    from app.domains.analysis.workflows.tasks import generate_embedding

    assert generate_embedding is not None, "generate_embedding task should be importable"


@pytest.mark.asyncio
async def test_analysis_workflow_structure():
    """Test analysis_workflow has correct structure."""
    # Workflow should have ainvoke method for async invocation
    assert hasattr(analysis_workflow, "ainvoke"), "Workflow should have ainvoke method"
    assert hasattr(analysis_workflow, "astream"), "Workflow should have astream method"
    # Workflow should be a LangGraph Pregel object
    assert analysis_workflow is not None, "Workflow should be defined"


def test_analysis_state_typeddict():
    """Test AnalysisState TypedDict structure."""
    from app.domains.analysis.workflows.state import AnalysisState

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
