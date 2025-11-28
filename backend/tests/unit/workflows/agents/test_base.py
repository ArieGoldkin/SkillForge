"""Unit tests for base agent utilities."""

from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from pydantic import BaseModel

from app.workflows.agents.base import (
    create_structured_agent,
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


