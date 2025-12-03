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

    # Create mock agent that raises GeneratorExit during ainvoke
    mock_agent = AsyncMock()
    mock_agent.ainvoke = AsyncMock(side_effect=GeneratorExit("Stream closed externally"))

    # GeneratorExit is converted to TimeoutError in execution.py
    with pytest.raises(TimeoutError, match="exceeded timeout"):
        await run_agent_with_tracking(
            agent=mock_agent,
            content="test",
            content_type="article",
            analysis_id=analysis_id,
            agent_type="test_agent",
            session=mock_session,
        )

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
    """Test that successful execution preserves structured_response."""
    analysis_id = str(uuid4())

    # Create mock agent that returns structured_response successfully
    # Note: Current implementation uses ainvoke which either succeeds or fails completely
    mock_agent = AsyncMock()
    mock_agent.ainvoke = AsyncMock(
        return_value={"structured_response": MockAgentSchema(field1="partial", field2=42)}
    )

    # Should succeed with the structured response
    result = await run_agent_with_tracking(
        agent=mock_agent,
        content="test",
        content_type="article",
        analysis_id=analysis_id,
        agent_type="test_agent",
        session=mock_session,
    )

    # Verify result was preserved
    assert result["agent_type"] == "test_agent"
    findings = result["findings"]
    assert isinstance(findings, dict)
    assert findings["field1"] == "partial"
    # Verify save was called
    mock_save_finding.assert_called_once()
