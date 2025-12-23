"""Unit tests for agent nodes emitting failed events on exceptions.

Tests specific error handling for 2025 best practices:
- TimeoutError: Specific timeout handling with TIMEOUT error codes
- ValueError: Specificity validation failures with SPECIFICITY_FAILED codes
- Exception: Generic fallbacks for unexpected errors
"""

from unittest.mock import AsyncMock, patch

import pytest

from app.domains.analysis.workflows.nodes.agents.dependency_mapper_node import (
    dependency_mapper_node,
)
from app.domains.analysis.workflows.nodes.agents.implementation_planner_node import (
    implementation_planner_node,
)


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
    "app.domains.analysis.workflows.nodes.agents.implementation_planner_node.record_agent_execution",
    new_callable=AsyncMock,
)
@patch(
    "app.domains.analysis.workflows.nodes.agents.implementation_planner_node.run_implementation_planner_with_session",
    new_callable=AsyncMock,
)
@patch(
    "app.domains.analysis.workflows.nodes.agents.implementation_planner_node.emit_agent_progress",
    new_callable=AsyncMock,
)
async def test_implementation_planner_emits_failed_event_on_exception(
    mock_emit, mock_runner, mock_record, mock_state
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
    "app.domains.analysis.workflows.nodes.agents.implementation_planner_node.record_agent_execution",
    new_callable=AsyncMock,
)
@patch(
    "app.domains.analysis.workflows.nodes.agents.implementation_planner_node.run_implementation_planner_with_session"
)
@patch(
    "app.domains.analysis.workflows.nodes.agents.implementation_planner_node.emit_agent_progress",
    new_callable=AsyncMock,
)
async def test_implementation_planner_does_not_emit_failed_on_success(
    mock_emit, mock_runner, mock_record, mock_state
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


# 2025 Best Practices: Specific Error Handling Tests
# Test one representative agent (dependency_mapper) for all error types
# Other agents follow the same pattern and are covered by existing tests


@pytest.mark.asyncio
@patch(
    "app.domains.analysis.workflows.agents.base.record_agent_execution",
    new_callable=AsyncMock,
)
@patch("app.domains.analysis.workflows.agents.base.emit_agent_progress", new_callable=AsyncMock)
async def test_dependency_mapper_handles_timeout_error_with_specific_code(
    mock_emit, mock_record, mock_state
):
    """Test that dependency_mapper handles TimeoutError with specific error code (2025 best practice)."""
    with patch(
        "app.domains.analysis.workflows.nodes.agents.dependency_mapper_node.run_dependency_mapper_with_session",
        side_effect=TimeoutError("Execution timeout"),
    ):
        result = await dependency_mapper_node(mock_state)

        # Verify empty findings returned (graceful degradation)
        assert result == {"agent_findings": []}

        # Verify specific timeout error was emitted
        assert mock_emit.called
        call_args = mock_emit.call_args
        assert call_args[0][1] == "dependency_mapper"  # agent_type parameter
        assert call_args[0][2] == "failed"  # status parameter
        call_kwargs = call_args[1] if len(call_args) > 1 else {}
        assert call_kwargs.get("error") == "Agent execution timed out"
        assert call_kwargs.get("error_code") == "DEPENDENCY_MAPPER_TIMEOUT"
        assert "processing_time_ms" in call_kwargs


@pytest.mark.asyncio
@patch(
    "app.domains.analysis.workflows.agents.base.record_agent_execution",
    new_callable=AsyncMock,
)
@patch("app.domains.analysis.workflows.agents.base.emit_agent_progress", new_callable=AsyncMock)
async def test_dependency_mapper_handles_specificity_validation_error_with_specific_code(
    mock_emit, mock_record, mock_state
):
    """Test that dependency_mapper handles ValueError (specificity failures) with specific error code (2025 best practice)."""
    with patch(
        "app.domains.analysis.workflows.nodes.agents.dependency_mapper_node.run_dependency_mapper_with_session",
        side_effect=ValueError("Specificity score 0.65 below threshold 0.70"),
    ):
        result = await dependency_mapper_node(mock_state)

        # Verify empty findings returned (graceful degradation)
        assert result == {"agent_findings": []}

        # Verify specific specificity error was emitted
        assert mock_emit.called
        call_args = mock_emit.call_args
        assert call_args[0][1] == "dependency_mapper"  # agent_type parameter
        assert call_args[0][2] == "failed"  # status parameter
        call_kwargs = call_args[1] if len(call_args) > 1 else {}
        assert "Specificity validation failed" in call_kwargs.get("error", "")
        assert call_kwargs.get("error_code") == "DEPENDENCY_MAPPER_SPECIFICITY_FAILED"
        assert "processing_time_ms" in call_kwargs


@pytest.mark.asyncio
@patch(
    "app.domains.analysis.workflows.agents.base.record_agent_execution",
    new_callable=AsyncMock,
)
@patch("app.domains.analysis.workflows.agents.base.emit_agent_progress", new_callable=AsyncMock)
async def test_dependency_mapper_handles_generic_exception_with_fallback_code(
    mock_emit, mock_record, mock_state
):
    """Test that dependency_mapper handles generic exceptions with fallback error code (2025 best practice)."""
    with patch(
        "app.domains.analysis.workflows.nodes.agents.dependency_mapper_node.run_dependency_mapper_with_session",
        side_effect=ConnectionError("Database connection failed"),
    ):
        result = await dependency_mapper_node(mock_state)

        # Verify empty findings returned (graceful degradation)
        assert result == {"agent_findings": []}

        # Verify generic error was emitted with specific error code
        assert mock_emit.called
        call_args = mock_emit.call_args
        assert call_args[0][1] == "dependency_mapper"  # agent_type parameter
        assert call_args[0][2] == "failed"  # status parameter
        call_kwargs = call_args[1] if len(call_args) > 1 else {}
        assert "Database connection failed" in call_kwargs.get("error", "")
        assert call_kwargs.get("error_code") == "DEPENDENCY_MAPPER_FAILED"
        assert "processing_time_ms" in call_kwargs
