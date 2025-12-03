"""Shared fixtures for agent execution tests."""

from unittest.mock import AsyncMock, MagicMock

import pytest
from langchain.messages import AIMessage
from pydantic import BaseModel


class MockAgentSchema(BaseModel):
    """Mock schema for agent output testing."""

    field1: str
    field2: int


@pytest.fixture
def mock_session():
    """Mock database session.

    Note: session.add() is synchronous, not async, so it's a MagicMock.
    session.execute(), commit(), and refresh() are async, so they're AsyncMock.
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


@pytest.fixture
def mock_agent():
    """Mock agent instance."""
    agent = MagicMock()
    # Set astream to None so hasattr check fails and it falls back to ainvoke
    agent.astream = None
    # Mock ainvoke (async) which is preferred, fallback to invoke if not available
    agent.ainvoke = AsyncMock(
        return_value={"structured_response": MockAgentSchema(field1="test", field2=42)}
    )
    return agent


@pytest.fixture
def mock_streaming_agent():
    """Mock agent with ainvoke support (current implementation uses ainvoke, not astream)."""
    agent = AsyncMock()
    # Mock ainvoke to return structured response
    agent.ainvoke = AsyncMock(
        return_value={"structured_response": MockAgentSchema(field1="test", field2=42)}
    )
    return agent
