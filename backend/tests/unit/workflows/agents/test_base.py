"""Unit tests for base agent utilities."""

from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from pydantic import BaseModel

from app.workflows.agents.base import (
    create_structured_agent,
    run_agent_with_tracking,
    save_agent_finding,
)


class MockAgentSchema(BaseModel):
    """Mock schema for agent output testing."""

    field1: str
    field2: int


@pytest.fixture
def mock_session():
    """Mock database session."""
    session = AsyncMock()
    session.add = MagicMock()
    session.commit = AsyncMock()
    session.refresh = AsyncMock()
    return session


@pytest.fixture
def mock_agent():
    """Mock agent instance."""
    agent = MagicMock()
    agent.invoke = MagicMock(
        return_value={"structured_response": MockAgentSchema(field1="test", field2=42)}
    )
    return agent


@patch("app.workflows.agents.base.get_chat_model")
@patch("app.workflows.agents.base.create_agent")
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


@pytest.mark.asyncio
@patch("app.workflows.agents.base.emit_agent_progress")
@patch("app.workflows.agents.base.save_agent_finding")
async def test_run_agent_with_tracking_success(
    mock_save_finding,
    mock_emit_progress,
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
@patch("app.workflows.agents.base.emit_agent_progress")
async def test_run_agent_with_tracking_no_structured_response(
    mock_emit_progress,
    mock_session,
):
    """Test error when agent doesn't return structured_response."""
    analysis_id = str(uuid4())
    mock_agent = MagicMock()
    mock_agent.invoke = MagicMock(return_value={})  # No structured_response

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
async def test_save_agent_finding(mock_session):
    """Test saving agent finding to database."""
    analysis_id = uuid4()
    findings = {"key": "value"}

    await save_agent_finding(
        session=mock_session,
        analysis_id=analysis_id,
        agent_type="test_agent",
        findings=findings,
        confidence_score=0.9,
        processing_time_ms=1000,
    )

    mock_session.add.assert_called_once()
    mock_session.commit.assert_awaited_once()
    mock_session.refresh.assert_awaited_once()
