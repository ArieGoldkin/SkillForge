"""Unit tests for base agent utilities."""

from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from pydantic import BaseModel

from app.domains.analysis.workflows.agents.base import (

    create_structured_agent,
    emit_agent_progress,
    save_agent_finding,
)


class MockAgentSchema(BaseModel):
    """Mock schema for agent output testing."""

    field1: str
    field2: int


@pytest.fixture
def mock_session():
    """Mock database session.

    Note: session.add() is not async, so it's a MagicMock, not AsyncMock.
    session.commit() and session.refresh() are async, so they're AsyncMock.
    session.execute() and session.scalar_one_or_none() are async.
    """
    session = AsyncMock()
    # session.add() is synchronous, not async
    session.add = MagicMock(return_value=None)
    session.commit = AsyncMock(return_value=None)
    session.refresh = AsyncMock(return_value=None)
    # Mock async methods that return results
    # Note: scalar_one_or_none() is synchronous, not async
    mock_result = MagicMock()
    mock_result.scalar_one_or_none = MagicMock(return_value=MagicMock())  # Return mock Analysis
    session.execute = AsyncMock(return_value=mock_result)
    return session


@patch("app.domains.analysis.workflows.agents.base.get_chat_model")
@patch("app.domains.analysis.workflows.agents.base.create_agent")
def test_create_structured_agent(mock_create_agent, mock_get_model):
    """Test creating agent with structured output."""
    mock_model = MagicMock()
    mock_get_model.return_value = mock_model
    mock_create_agent.return_value = MagicMock()

    create_structured_agent(
        system_prompt="Test prompt",
        response_schema=MockAgentSchema,
    )

    mock_create_agent.assert_called_once()
    # Verify ToolStrategy was used
    call_args = mock_create_agent.call_args
    assert "response_format" in call_args.kwargs


@patch("app.domains.analysis.workflows.agents.base.get_chat_model")
@patch("app.domains.analysis.workflows.agents.base.create_agent")
def test_create_structured_agent_with_task_type(mock_create_agent, mock_get_model):
    """Test creating agent with task_type for model routing."""
    mock_model = MagicMock()
    mock_get_model.return_value = mock_model
    mock_create_agent.return_value = MagicMock()

    create_structured_agent(
        system_prompt="Test prompt",
        response_schema=MockAgentSchema,
        task_type="synthesis",
    )

    # Verify get_chat_model was called with task_type
    mock_get_model.assert_called_once_with(task_type="synthesis")
    mock_create_agent.assert_called_once()


@patch("app.domains.analysis.workflows.agents.base.get_chat_model")
@patch("app.domains.analysis.workflows.agents.base.create_agent")
def test_create_structured_agent_without_task_type(mock_create_agent, mock_get_model):
    """Test creating agent without task_type passes None to model factory."""
    mock_model = MagicMock()
    mock_get_model.return_value = mock_model
    mock_create_agent.return_value = MagicMock()

    create_structured_agent(
        system_prompt="Test prompt",
        response_schema=MockAgentSchema,
    )

    # Verify get_chat_model was called with task_type=None (default)
    mock_get_model.assert_called_once_with(task_type=None)


@pytest.mark.asyncio
async def test_save_agent_finding(mock_session):
    """Test saving agent finding to database."""
    analysis_id = uuid4()
    findings: dict[str, object] = {"key": "value"}

    await save_agent_finding(
        session=mock_session,
        analysis_id=analysis_id,
        agent_type="tech_comparator",
        findings=findings,
        confidence_score=0.9,
        processing_time_ms=1000,
    )

    mock_session.add.assert_called_once()
    mock_session.commit.assert_awaited_once()
    mock_session.refresh.assert_awaited_once()


@pytest.mark.asyncio
@patch("app.domains.analysis.workflows.agents.base.emit_streaming_event")
@patch("app.domains.analysis.workflows.agents.base.get_stage_name")
async def test_emit_agent_progress_success(mock_get_stage_name, mock_emit_event):
    """Test emitting agent progress SSE event."""
    # Setup mocks
    analysis_id = str(uuid4())
    mock_get_stage_name.return_value = "tech_comparison"
    mock_emit_event.return_value = AsyncMock()

    # Call function
    await emit_agent_progress(
        analysis_id=analysis_id,
        agent_type="tech_comparator",
        status="running",
        detail="Analyzing technologies",
    )

    # Verify stage name was retrieved
    mock_get_stage_name.assert_called_once_with("tech_comparator")

    # Verify event was emitted with correct parameters
    mock_emit_event.assert_awaited_once()
    call_args = mock_emit_event.call_args
    assert call_args.args[0] == "progress"
    assert call_args.kwargs["analysis_id"] == analysis_id
    assert call_args.kwargs["stage"] == "tech_comparison"
    assert call_args.kwargs["status"] == "running"
    assert call_args.kwargs["agent_type"] == "tech_comparator"
    assert call_args.kwargs["detail"] == "Analyzing technologies"


@pytest.mark.asyncio
@patch("app.domains.analysis.workflows.agents.base.emit_streaming_event")
@patch("app.domains.analysis.workflows.agents.base.get_stage_name")
async def test_emit_agent_progress_with_kwargs(mock_get_stage_name, mock_emit_event):
    """Test emitting agent progress with additional kwargs."""
    # Setup mocks
    analysis_id = str(uuid4())
    mock_get_stage_name.return_value = "security_audit"
    mock_emit_event.return_value = AsyncMock()

    # Call with multiple kwargs
    await emit_agent_progress(
        analysis_id=analysis_id,
        agent_type="security_auditor",
        status="complete",
        findings_count=5,
        vulnerabilities_found=2,
        processing_time_ms=1500,
    )

    # Verify all kwargs were passed through
    mock_emit_event.assert_awaited_once()
    call_kwargs = mock_emit_event.call_args.kwargs
    assert call_kwargs["findings_count"] == 5
    assert call_kwargs["vulnerabilities_found"] == 2
    assert call_kwargs["processing_time_ms"] == 1500
