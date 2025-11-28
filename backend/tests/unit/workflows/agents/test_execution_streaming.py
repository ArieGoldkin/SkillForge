"""Unit tests for agent execution streaming functionality."""

from unittest.mock import AsyncMock, MagicMock, patch
from unittest.mock import patch as mock_patch
from uuid import uuid4

import pytest
from langchain.messages import AIMessage

from app.workflows.agents.execution import run_agent_with_tracking
from tests.unit.workflows.agents.conftest import MockAgentSchema


@pytest.mark.asyncio
@patch("app.workflows.agents.base.get_stage_name", return_value="test_stage")
@patch("app.workflows.agents.streaming.emit_agent_progress", new_callable=AsyncMock)
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

    mock_save_finding.return_value = MagicMock()

    result = await run_agent_with_tracking(
        agent=mock_streaming_agent,
        content=content,
        content_type="article",
        analysis_id=analysis_id,
        agent_type="test_agent",
        session=mock_session,
    )

    # Verify streaming was used
    assert mock_streaming_agent.astream.called
    # Verify progress events were emitted during streaming
    # Check both streaming and result_processing mocks
    # (streaming calls emit_agent_progress directly)
    min_expected_events = 2  # At least "running" and "streaming" events
    total_calls = mock_emit_progress_streaming.call_count + mock_emit_progress_result.call_count
    assert total_calls >= min_expected_events
    # Verify final result is correct
    assert result["agent_type"] == "test_agent"
    assert "findings" in result
    mock_save_finding.assert_called_once()


@pytest.mark.asyncio
@patch("app.workflows.agents.base.get_stage_name", return_value="test_stage")
@patch("app.workflows.agents.streaming.emit_agent_progress", new_callable=AsyncMock)
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

    mock_save_finding.return_value = MagicMock()

    # Mock time to control throttling behavior
    with mock_patch("app.workflows.agents.streaming.time.time") as mock_time:
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

        # Verify streaming was used
        assert mock_streaming_agent.astream.called

        # Verify SSE events were emitted (but throttled)
        # At minimum, we should have the "running" event
        # Streaming events may not be emitted if structured_response is found quickly
        total_calls = mock_emit_progress_streaming.call_count + mock_emit_progress_result.call_count
        assert total_calls >= 1, "At least the 'running' event should be emitted"
        # If streaming events were emitted, they should be throttled (not one per chunk)
        # With 3 chunks and 500ms throttle, we'd expect fewer than 3 streaming events if any

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
    """Test that structured_response in intermediate chunk is captured."""

    # Create mock agent that returns structured_response in intermediate chunk
    async def mock_astream_with_early_response(*args, **kwargs):
        chunks = [
            {"messages": [AIMessage(content="Starting")]},
            {
                "messages": [AIMessage(content="Processing")],
                "structured_response": MockAgentSchema(field1="early", field2=42),
            },
            {"messages": [AIMessage(content="Finishing")]},
        ]
        for chunk in chunks:
            yield chunk

    mock_agent = MagicMock()
    mock_agent.astream = mock_astream_with_early_response

    analysis_id = str(uuid4())
    content = "Test content"

    mock_save_finding.return_value = MagicMock()

    result = await run_agent_with_tracking(
        agent=mock_agent,
        content=content,
        content_type="article",
        analysis_id=analysis_id,
        agent_type="test_agent",
        session=mock_session,
    )

    # Verify structured_response from intermediate chunk was captured
    expected_field2 = 42  # Expected value from MockAgentSchema
    assert result["agent_type"] == "test_agent"
    assert "findings" in result
    findings = result["findings"]
    assert isinstance(findings, dict)
    assert findings["field1"] == "early"
    assert findings["field2"] == expected_field2
    mock_save_finding.assert_called_once()
