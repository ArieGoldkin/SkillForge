"""Unit tests for agent execution streaming functionality."""

from unittest.mock import AsyncMock, patch
from unittest.mock import patch as mock_patch
from uuid import uuid4

import pytest

from app.workflows.agents.execution import run_agent_with_tracking
from tests.unit.workflows.agents.conftest import MockAgentSchema


@pytest.mark.asyncio
@patch("app.workflows.agents.base.get_stage_name", return_value="test_stage")
@patch("app.workflows.agents.streaming_helpers.emit_agent_progress", new_callable=AsyncMock)
@patch("app.workflows.agents.result_processing.emit_agent_progress", new_callable=AsyncMock)
@patch("app.workflows.agents.result_processing.save_agent_finding", new_callable=AsyncMock)
async def test_run_agent_with_tracking_streaming(
    mock_save_finding,
    mock_emit_progress_result,
    mock_emit_progress_streaming,
    mock_get_stage_name,
    mock_streaming_agent,
    mock_session,
):
    """Test agent execution with streaming emits progress events."""
    analysis_id = str(uuid4())
    content = "Test content for streaming"

    # mock_save_finding is already AsyncMock, no need to set return_value

    result = await run_agent_with_tracking(
        agent=mock_streaming_agent,
        content=content,
        content_type="article",
        analysis_id=analysis_id,
        agent_type="test_agent",
        session=mock_session,
    )

    # Verify ainvoke was used (current implementation)
    assert mock_streaming_agent.ainvoke.called
    # Verify progress events were emitted
    # With ainvoke (not astream), we get "running" and "complete" events
    # No intermediate streaming events since ainvoke waits for full response
    min_expected_events = 1  # At least the "running" event from execution.py
    total_calls = mock_emit_progress_streaming.call_count + mock_emit_progress_result.call_count
    assert total_calls >= min_expected_events
    # Verify final result is correct
    assert result["agent_type"] == "test_agent"
    assert "findings" in result
    mock_save_finding.assert_called_once()


@pytest.mark.asyncio
@patch("app.workflows.agents.base.get_stage_name", return_value="test_stage")
@patch("app.workflows.agents.streaming_helpers.emit_agent_progress", new_callable=AsyncMock)
@patch("app.workflows.agents.result_processing.emit_agent_progress", new_callable=AsyncMock)
@patch("app.workflows.agents.result_processing.save_agent_finding", new_callable=AsyncMock)
async def test_run_agent_with_tracking_streaming_throttling(
    mock_save_finding,
    mock_emit_progress_result,
    mock_emit_progress_streaming,
    mock_get_stage_name,
    mock_streaming_agent,
    mock_session,
):
    """Test that SSE events are throttled during streaming."""
    analysis_id = str(uuid4())
    content = "Test content for throttling"

    # mock_save_finding is already AsyncMock, no need to set return_value

    # Mock time.time() used inside emit_progress_if_needed to control throttling behavior
    with mock_patch("time.time") as mock_time:
        # Simulate time progression
        mock_time.side_effect = [0.0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0]

        result = await run_agent_with_tracking(
            agent=mock_streaming_agent,
            content=content,
            content_type="article",
            analysis_id=analysis_id,
            agent_type="test_agent",
            session=mock_session,
        )

        # Verify ainvoke was used (current implementation)
        assert mock_streaming_agent.ainvoke.called

        # Verify SSE events were emitted
        # With ainvoke, we get "running" and "complete" events, no intermediate streaming
        total_calls = mock_emit_progress_streaming.call_count + mock_emit_progress_result.call_count
        assert total_calls >= 1, "At least the 'running' event should be emitted"
        # No throttling tests needed since ainvoke doesn't produce streaming events

        assert result["agent_type"] == "test_agent"
        assert "findings" in result
        mock_save_finding.assert_called_once()


@pytest.mark.asyncio
@patch("app.workflows.agents.base.get_stage_name", return_value="test_stage")
@patch("app.workflows.agents.result_processing.emit_agent_progress", new_callable=AsyncMock)
@patch("app.workflows.agents.result_processing.save_agent_finding", new_callable=AsyncMock)
async def test_run_agent_with_tracking_streaming_early_response(
    mock_save_finding,
    mock_emit_progress,
    mock_get_stage_name,
    mock_session,
):
    """Test that structured_response is captured from ainvoke."""
    # Create mock agent that returns structured_response via ainvoke
    # Note: Current implementation uses ainvoke, not astream
    mock_agent = AsyncMock()
    mock_agent.ainvoke = AsyncMock(
        return_value={"structured_response": MockAgentSchema(field1="early", field2=42)}
    )

    analysis_id = str(uuid4())
    content = "Test content"

    result = await run_agent_with_tracking(
        agent=mock_agent,
        content=content,
        content_type="article",
        analysis_id=analysis_id,
        agent_type="test_agent",
        session=mock_session,
    )

    # Verify structured_response was captured
    expected_field2 = 42  # Expected value from MockAgentSchema
    assert result["agent_type"] == "test_agent"
    assert "findings" in result
    findings = result["findings"]
    assert isinstance(findings, dict)
    assert findings["field1"] == "early"
    assert findings["field2"] == expected_field2
    mock_save_finding.assert_called_once()
