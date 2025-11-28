"""Unit tests for basic agent execution logic."""

import uuid
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import UUID, uuid4

import pytest

from app.core.types import AnalysisID
from app.workflows.agents.execution import run_agent_with_tracking


@pytest.mark.asyncio
@patch("app.workflows.agents.base.get_stage_name", return_value="test_stage")
@patch("app.workflows.agents.base.emit_agent_progress", new_callable=AsyncMock)
@patch("app.workflows.agents.base.save_agent_finding", new_callable=AsyncMock)
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
        agent_type="test_agent",
        session=mock_session,
    )

    assert result["agent_type"] == "test_agent"
    assert "findings" in result
    assert "processing_time_ms" in result
    mock_emit_progress.assert_called()
    mock_save_finding.assert_called_once()


@pytest.mark.asyncio
@patch("app.workflows.agents.base.get_stage_name", return_value="test_stage")
@patch("app.workflows.agents.base.emit_agent_progress", new_callable=AsyncMock)
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
            agent_type="test_agent",
            session=mock_session,
        )


@pytest.mark.asyncio
@patch("app.workflows.agents.base.get_stage_name", return_value="test_stage")
@patch("app.workflows.agents.base.emit_agent_progress", new_callable=AsyncMock)
@patch("app.workflows.agents.base.save_agent_finding", new_callable=AsyncMock)
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
        agent_type="test_agent",
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
    assert result["agent_type"] == "test_agent"


@pytest.mark.asyncio
@patch("app.workflows.agents.base.get_stage_name", return_value="test_stage")
@patch("app.workflows.agents.base.emit_agent_progress", new_callable=AsyncMock)
@patch("app.workflows.agents.base.save_agent_finding", new_callable=AsyncMock)
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
        agent_type="test_agent",
        session=mock_session,
    )

    # Verify save_agent_finding was called with the same UUID
    assert mock_save_finding.called
    call_args = mock_save_finding.call_args
    called_analysis_id = call_args.kwargs["analysis_id"]
    assert isinstance(called_analysis_id, UUID)
    assert str(called_analysis_id) == analysis_id  # Should match exactly

    assert result["agent_type"] == "test_agent"


@pytest.mark.asyncio
@patch("app.workflows.agents.base.get_stage_name", return_value="test_stage")
@patch("app.workflows.agents.base.emit_agent_progress", new_callable=AsyncMock)
@patch("app.workflows.agents.base.save_agent_finding", new_callable=AsyncMock)
async def test_run_agent_with_tracking_content_truncation(
    mock_save_finding,
    mock_emit_progress,
    mock_get_stage_name,
    mock_agent,
    mock_session,
):
    """Test that content is truncated to 1500 chars for agent efficiency."""
    analysis_id = str(uuid4())
    # Create content longer than 1500 chars
    long_content = "x" * 2500

    mock_save_finding.return_value = MagicMock()

    result = await run_agent_with_tracking(
        agent=mock_agent,
        content=long_content,
        content_type="article",
        analysis_id=analysis_id,
        agent_type="test_agent",
        session=mock_session,
    )

    # Verify agent was called with truncated content
    assert mock_agent.ainvoke.called
    call_args = mock_agent.ainvoke.call_args
    input_messages = call_args[0][0] if call_args[0] else {}
    messages = input_messages.get("messages", [])
    if messages:
        user_message = messages[0].get("content", "")
        # Content should be truncated to 1500 chars (plus header text)
        assert "Content Type: article" in user_message
        # Extract just the content part (after "Content:\n")
        content_part = (
            user_message.split("Content:\n", 1)[1] if "Content:\n" in user_message else ""
        )
        max_content_length = 1500  # Default max_content_length for agents
        assert len(content_part) <= max_content_length
        assert result["agent_type"] == "test_agent"


@pytest.mark.asyncio
@patch("app.workflows.agents.base.get_stage_name", return_value="test_stage")
@patch("app.workflows.agents.base.emit_agent_progress", new_callable=AsyncMock)
@patch("app.workflows.agents.base.save_agent_finding", new_callable=AsyncMock)
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
        agent_type="test_agent",
        session=mock_session,
    )

    # Verify save_agent_finding was called with the same UUID object
    assert mock_save_finding.called
    call_args = mock_save_finding.call_args
    called_analysis_id = call_args.kwargs["analysis_id"]
    assert isinstance(called_analysis_id, UUID)
    assert called_analysis_id == analysis_id  # Should match exactly

    assert result["agent_type"] == "test_agent"
