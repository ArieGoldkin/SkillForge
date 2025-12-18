"""Unit tests for basic agent execution logic."""

import uuid
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import UUID, uuid4

import pytest

from app.core.types import AnalysisID
from app.domains.analysis.workflows.agents.execution import run_agent_with_tracking

@pytest.mark.unit


@pytest.mark.asyncio
@patch("app.core.agent_config.get_stage_name", return_value="test_stage")
@patch("app.domains.analysis.workflows.agents.execution.emit_agent_progress", new_callable=AsyncMock)
@patch("app.domains.analysis.workflows.agents.result_processing.save_agent_finding", new_callable=AsyncMock)
async def test_run_agent_with_tracking_success(
    mock_save_finding,
    mock_emit_progress,
    mock_get_stage_name,
    mock_agent,
    mock_session,
):
    """Test successful agent execution with tracking."""
    analysis_id = str(uuid4())
    content = "Test content"
    content_type = "article"

    mock_save_finding.return_value = MagicMock()

    result = await run_agent_with_tracking(
        agent=mock_agent,
        content=content,
        content_type=content_type,
        analysis_id=analysis_id,
        agent_type="tech_comparator",  # Use valid agent type
        session=mock_session,
    )

    assert result["agent_type"] == "tech_comparator"
    assert "findings" in result
    assert "processing_time_ms" in result
    mock_emit_progress.assert_called()
    mock_save_finding.assert_called_once()


@pytest.mark.asyncio
@patch("app.core.agent_config.get_stage_name", return_value="test_stage")
@patch("app.domains.analysis.workflows.agents.execution.emit_agent_progress", new_callable=AsyncMock)
async def test_run_agent_with_tracking_no_structured_response(
    mock_emit_progress,
    mock_get_stage_name,
    mock_session,
):
    """Test error when agent doesn't return structured_response."""
    analysis_id = str(uuid4())
    mock_agent = MagicMock()
    mock_agent.astream = None  # Explicitly disable streaming to use ainvoke
    mock_agent.ainvoke = AsyncMock(return_value={})  # No structured_response

    with pytest.raises(RuntimeError, match="did not return structured_response"):
        await run_agent_with_tracking(
            agent=mock_agent,
            content="test",
            content_type="article",
            analysis_id=analysis_id,
            agent_type="tech_comparator",  # Use valid agent type
            session=mock_session,
        )


@pytest.mark.asyncio
@patch("app.core.agent_config.get_stage_name", return_value="test_stage")
@patch("app.domains.analysis.workflows.agents.execution.emit_agent_progress", new_callable=AsyncMock)
@patch("app.domains.analysis.workflows.agents.result_processing.save_agent_finding", new_callable=AsyncMock)
async def test_run_agent_with_tracking_non_uuid_analysis_id(
    mock_save_finding,
    mock_emit_progress,
    mock_get_stage_name,
    mock_agent,
    mock_session,
):
    """Test that non-UUID analysis_id strings are converted to UUIDs."""
    analysis_id = "dev-test-opus-4-5"  # Non-UUID string
    content = "Test content"

    mock_save_finding.return_value = MagicMock()

    result = await run_agent_with_tracking(
        agent=mock_agent,
        content=content,
        content_type="article",
        analysis_id=analysis_id,
        agent_type="tech_comparator",  # Use valid agent type
        session=mock_session,
    )

    # Verify save_agent_finding was called with a UUID
    assert mock_save_finding.called
    call_args = mock_save_finding.call_args
    called_analysis_id = call_args.kwargs["analysis_id"]
    assert isinstance(called_analysis_id, UUID)
    # Verify it's deterministic - same string = same UUID
    namespace = UUID("6ba7b810-9dad-11d1-80b4-00c04fd430c8")
    expected_uuid = uuid.uuid5(namespace, analysis_id)
    assert called_analysis_id == expected_uuid

    # Verify result still works
    assert result["agent_type"] == "tech_comparator"


@pytest.mark.asyncio
@patch("app.core.agent_config.get_stage_name", return_value="test_stage")
@patch("app.domains.analysis.workflows.agents.execution.emit_agent_progress", new_callable=AsyncMock)
@patch("app.domains.analysis.workflows.agents.result_processing.save_agent_finding", new_callable=AsyncMock)
async def test_run_agent_with_tracking_valid_uuid_string(
    mock_save_finding,
    mock_emit_progress,
    mock_get_stage_name,
    mock_agent,
    mock_session,
):
    """Test that valid UUID strings work correctly (regression test)."""
    analysis_id = str(uuid4())  # Valid UUID string
    content = "Test content"

    mock_save_finding.return_value = MagicMock()

    result = await run_agent_with_tracking(
        agent=mock_agent,
        content=content,
        content_type="article",
        analysis_id=analysis_id,
        agent_type="tech_comparator",  # Use valid agent type
        session=mock_session,
    )

    # Verify save_agent_finding was called with the same UUID
    assert mock_save_finding.called
    call_args = mock_save_finding.call_args
    called_analysis_id = call_args.kwargs["analysis_id"]
    assert isinstance(called_analysis_id, UUID)
    assert str(called_analysis_id) == analysis_id  # Should match exactly

    assert result["agent_type"] == "tech_comparator"


@pytest.mark.asyncio
@patch("app.core.agent_config.get_stage_name", return_value="test_stage")
@patch("app.domains.analysis.workflows.agents.execution.emit_agent_progress", new_callable=AsyncMock)
@patch("app.domains.analysis.workflows.agents.result_processing.save_agent_finding", new_callable=AsyncMock)
async def test_run_agent_with_tracking_content_truncation(
    mock_save_finding,
    mock_emit_progress,
    mock_get_stage_name,
    mock_agent,
    mock_session,
):
    """Test that content is truncated to 12000 chars for agent efficiency.

    Note: Increased from 1500 to 12000 chars to allow agents to analyze
    meaningful article content rather than just boilerplate.
    """
    analysis_id = str(uuid4())
    # Create content longer than 12000 chars
    long_content = "x" * 15000

    mock_save_finding.return_value = MagicMock()

    result = await run_agent_with_tracking(
        agent=mock_agent,
        content=long_content,
        content_type="article",
        analysis_id=analysis_id,
        agent_type="tech_comparator",  # Use valid agent type
        session=mock_session,
    )

    # Verify agent was called with truncated content
    assert mock_agent.ainvoke.called
    call_args = mock_agent.ainvoke.call_args
    input_messages = call_args[0][0] if call_args[0] else {}
    messages = input_messages.get("messages", [])
    if messages:
        user_message = messages[0].get("content", "")
        # Content should be truncated to 12000 chars (plus header text)
        assert "Content Type: article" in user_message
        # Extract just the content part (after "Content:\n")
        content_part = (
            user_message.split("Content:\n", 1)[1] if "Content:\n" in user_message else ""
        )
        max_content_length = 12000  # Default max_content_length for agents
        assert len(content_part) <= max_content_length
        assert result["agent_type"] == "tech_comparator"


@pytest.mark.asyncio
@patch("app.core.agent_config.get_stage_name", return_value="test_stage")
@patch("app.domains.analysis.workflows.agents.execution.emit_agent_progress", new_callable=AsyncMock)
@patch("app.domains.analysis.workflows.agents.result_processing.save_agent_finding", new_callable=AsyncMock)
async def test_run_agent_with_tracking_uuid_object(
    mock_save_finding,
    mock_emit_progress,
    mock_get_stage_name,
    mock_agent,
    mock_session,
):
    """Test that UUID objects (not strings) work correctly."""
    analysis_id: AnalysisID = str(uuid4())  # Convert to string for AnalysisID type
    content = "Test content"

    mock_save_finding.return_value = MagicMock()

    result = await run_agent_with_tracking(
        agent=mock_agent,
        content=content,
        content_type="article",
        analysis_id=analysis_id,
        agent_type="tech_comparator",  # Use valid agent type
        session=mock_session,
    )

    # Verify save_agent_finding was called with the same UUID object
    assert mock_save_finding.called
    call_args = mock_save_finding.call_args
    called_analysis_id = call_args.kwargs["analysis_id"]
    assert isinstance(called_analysis_id, UUID)
    assert str(called_analysis_id) == analysis_id  # Compare string representations

    assert result["agent_type"] == "tech_comparator"


@pytest.mark.asyncio
@patch("app.core.agent_config.get_stage_name", return_value="test_stage")
@patch("app.domains.analysis.workflows.agents.execution.emit_agent_progress", new_callable=AsyncMock)
@patch("app.shared.services.messaging.sse_helpers.persist_progress_event_async", new_callable=AsyncMock)
async def test_agent_execution_converts_generatorexit_to_timeouterror(
    mock_persist,
    mock_emit_progress,
    mock_get_stage_name,
    mock_session,
):
    """Test that GeneratorExit from invoke_agent is handled and re-raised for workflow cancellation."""
    from app.domains.analysis.workflows.agents.execution import _run_agent_with_tracking_impl

    mock_agent = MagicMock()
    mock_agent.astream = None  # Disable streaming to use ainvoke path

    with patch("app.domains.analysis.workflows.agents.execution.invoke_agent", new_callable=AsyncMock) as mock_invoke:
        # Mock invoke_agent to raise GeneratorExit (simulating workflow cancellation)
        mock_invoke.side_effect = GeneratorExit("Generator closed by cancellation")

        # GeneratorExit should be caught, handled (cancellation tracking), and re-raised
        from app.domains.analysis.workflows.agents.execution import AgentExecutionConfig, AgentExecutionParams

        params = AgentExecutionParams(
            agent=mock_agent,
            content="test content",
            content_type="article",
            analysis_id=AnalysisID(str(uuid4())),  # Use valid UUID string
            agent_type="tech_comparator",  # Use valid agent type
        )
        config = AgentExecutionConfig(session=mock_session)

        # GeneratorExit should be re-raised after handling
        with pytest.raises(GeneratorExit):
            await _run_agent_with_tracking_impl(params=params, config=config)


@pytest.mark.asyncio
@patch("app.core.agent_config.get_stage_name", return_value="test_stage")
@patch("app.domains.analysis.workflows.agents.execution.emit_agent_progress", new_callable=AsyncMock)
@patch("app.shared.services.messaging.sse_helpers.persist_progress_event_async", new_callable=AsyncMock)
async def test_agent_execution_handles_timeouterror(
    mock_persist,
    mock_emit_progress,
    mock_get_stage_name,
    mock_session,
):
    """Test that TimeoutError from invoke_agent is handled correctly."""
    from app.domains.analysis.workflows.agents.execution import _run_agent_with_tracking_impl

    mock_agent = MagicMock()
    mock_agent.astream = None  # Disable streaming to use ainvoke path

    with patch("app.domains.analysis.workflows.agents.execution.invoke_agent", new_callable=AsyncMock) as mock_invoke:
        # Mock invoke_agent to raise TimeoutError
        mock_invoke.side_effect = TimeoutError("Agent exceeded timeout")

        # Should re-raise TimeoutError
        from app.domains.analysis.workflows.agents.execution import AgentExecutionConfig, AgentExecutionParams

        params = AgentExecutionParams(
            agent=mock_agent,
            content="test content",
            content_type="article",
            analysis_id=AnalysisID(str(uuid4())),  # Use valid UUID string
            agent_type="tech_comparator",  # Use valid agent type
        )
        config = AgentExecutionConfig(session=mock_session)

        with pytest.raises(TimeoutError, match="exceeded timeout"):
            await _run_agent_with_tracking_impl(params=params, config=config)
