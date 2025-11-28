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
    # Set astream to None so hasattr check fails and it falls back to ainvoke
    agent.astream = None
    # Mock ainvoke (async) which is preferred, fallback to invoke if not available
    agent.ainvoke = AsyncMock(
        return_value={"structured_response": MockAgentSchema(field1="test", field2=42)}
    )
    return agent


@pytest.fixture
def mock_streaming_agent():
    """Mock agent with streaming support."""

    async def create_stream(*args, **kwargs):
        # Simulate streaming chunks - create new generator each time
        chunks = [
            {"messages": [AIMessage(content="Analyzing")]},
            {"messages": [AIMessage(content="Analyzing integration")]},
            {
                "messages": [AIMessage(content="Analyzing integration feasibility")],
                "structured_response": MockAgentSchema(field1="test", field2=42),
            },
        ]
        for chunk in chunks:
            yield chunk

    agent = MagicMock()

    # Create a callable that returns async generator (not awaitable itself)
    def astream_wrapper(*args, **kwargs):
        return create_stream(*args, **kwargs)

    # Wrap in MagicMock to track calls
    agent.astream = MagicMock(side_effect=astream_wrapper)
    return agent
