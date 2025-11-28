"""Unit tests for agent execution error handling."""

from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from langchain.messages import AIMessage

from app.workflows.agents.execution import run_agent_with_tracking
from tests.unit.workflows.agents.conftest import MockAgentSchema


@pytest.mark.asyncio
@patch("app.workflows.agents.base.get_stage_name", return_value="test_stage")
@patch("app.workflows.agents.result_processing.emit_agent_progress", new_callable=AsyncMock)
@patch("app.workflows.agents.result_processing.save_agent_finding", new_callable=AsyncMock)
async def test_run_agent_with_tracking_generatorexit_handling(
    mock_save_finding,
    mock_emit_progress,
    mock_get_stage_name,
    mock_session,
):
    """Test that GeneratorExit is properly handled and SSE events are emitted."""
    analysis_id = str(uuid4())

    # Create mock agent that raises GeneratorExit during streaming
    async def mock_astream_with_generatorexit(*args, **kwargs):
        chunks = [
            {"messages": [AIMessage(content="Starting")]},
        ]
        for chunk in chunks:
            yield chunk
        # Raise GeneratorExit after first chunk (simulating stream closure)
        raise GeneratorExit("Stream closed externally")

    mock_agent = MagicMock()
    mock_agent.astream = mock_astream_with_generatorexit

    # GeneratorExit from stream should be caught and handled, not re-raised
    # The agent should fail gracefully with proper SSE events
    with pytest.raises(RuntimeError, match="did not return structured_response"):
        await run_agent_with_tracking(
            agent=mock_agent,
            content="test",
            content_type="article",
            analysis_id=analysis_id,
            agent_type="test_agent",
            session=mock_session,
        )

    # Verify stream closure was logged
    assert mock_emit_progress.called
    # Verify save_agent_finding was NOT called (agent didn't complete)
    mock_save_finding.assert_not_called()


@pytest.mark.asyncio
@patch("app.workflows.agents.base.get_stage_name", return_value="test_stage")
@patch("app.workflows.agents.result_processing.emit_agent_progress", new_callable=AsyncMock)
@patch("app.workflows.agents.result_processing.save_agent_finding", new_callable=AsyncMock)
async def test_run_agent_with_tracking_generatorexit_with_partial_result(
    mock_save_finding,
    mock_emit_progress,
    mock_get_stage_name,
    mock_session,
):
    """Test that GeneratorExit preserves partial result if available."""
    analysis_id = str(uuid4())

    # Create mock agent that raises GeneratorExit but has partial structured_response
    async def mock_astream_with_partial_result(*args, **kwargs):
        chunks = [
            {
                "messages": [AIMessage(content="Processing")],
                "structured_response": MockAgentSchema(field1="partial", field2=42),
            },
        ]
        for chunk in chunks:
            yield chunk
        # Raise GeneratorExit after structured_response is found
        raise GeneratorExit("Stream closed externally")

    mock_agent = MagicMock()
    mock_agent.astream = mock_astream_with_partial_result

    # Should succeed because we have partial result
    result = await run_agent_with_tracking(
        agent=mock_agent,
        content="test",
        content_type="article",
        analysis_id=analysis_id,
        agent_type="test_agent",
        session=mock_session,
    )

    # Verify result was preserved despite GeneratorExit
    assert result["agent_type"] == "test_agent"
    findings = result["findings"]
    assert isinstance(findings, dict)
    assert findings["field1"] == "partial"
    # Verify save was called (partial result was saved)
    mock_save_finding.assert_called_once()
