"""Unit tests for agent nodes emitting failed events on exceptions."""

import time
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.domains.analysis.workflows.nodes.agents.implementation_planner_node import implementation_planner_node
from app.domains.analysis.workflows.state import AnalysisState

@pytest.mark.unit


@pytest.fixture
def mock_state():
    """Mock analysis state."""
    return {
        "analysis_id": "test-analysis-id",
        "content_type": "article",
        "content_ref": {
            "uri": "analysis://test-analysis-id/content",
            "summary": "Test content summary",
            "size_bytes": 1000,
            "content_type": "text/plain",
            "available_sections": ["summary", "full"],
        },
    }


@pytest.mark.asyncio
@patch(
    "app.workflows.nodes.agents.implementation_planner_node.run_implementation_planner_with_session",
    new_callable=AsyncMock,
)
@patch(
    "app.workflows.nodes.agents.implementation_planner_node.emit_agent_progress",
    new_callable=AsyncMock,
)
async def test_implementation_planner_emits_failed_event_on_exception(
    mock_emit, mock_runner, mock_state
):
    """Test that implementation_planner_node emits failed event when exception occurs."""
    # Mock runner to raise exception
    mock_runner.side_effect = Exception("Test error: Agent execution failed")

    result = await implementation_planner_node(mock_state)

    # Verify failed event was emitted
    assert mock_emit.called
    # Check both positional and keyword arguments
    call_args = mock_emit.call_args
    # emit_agent_progress(analysis_id, agent_type, status, **kwargs)
    assert call_args[0][1] == "implementation_planner"  # agent_type (2nd positional)
    assert call_args[0][2] == "failed"  # status (3rd positional)
    # Check kwargs
    call_kwargs = call_args[1] if len(call_args) > 1 else {}
    assert "error" in call_kwargs
    assert "Test error" in call_kwargs["error"]
    assert "error_code" in call_kwargs
    assert call_kwargs["error_code"] == "IMPLEMENTATION_PLANNER_FAILED"
    assert "processing_time_ms" in call_kwargs

    # Verify empty findings returned (allows other agents to continue)
    assert result == {"agent_findings": []}


@pytest.mark.asyncio
@patch(
    "app.workflows.nodes.agents.implementation_planner_node.run_implementation_planner_with_session"
)
@patch(
    "app.workflows.nodes.agents.implementation_planner_node.emit_agent_progress",
    new_callable=AsyncMock,
)
async def test_implementation_planner_does_not_emit_failed_on_success(
    mock_emit, mock_runner, mock_state
):
    """Test that implementation_planner_node does not emit failed event on success."""
    # Mock runner to return successful result
    mock_runner.return_value = {
        "agent_type": "implementation_planner",
        "findings": {"implementation_steps": [{"step": 1, "description": "Setup"}]},
        "confidence_score": 0.85,
        "processing_time_ms": 100,
    }

    result = await implementation_planner_node(mock_state)

    # Verify no failed event was emitted
    failed_calls = [
        call for call in mock_emit.call_args_list if call.kwargs.get("status") == "failed"
    ]
    assert len(failed_calls) == 0

    # Verify result contains findings
    assert "agent_findings" in result
    assert len(result["agent_findings"]) > 0
