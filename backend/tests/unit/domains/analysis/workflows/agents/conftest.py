"""Shared fixtures for agent execution tests."""

import os
from unittest.mock import AsyncMock, MagicMock

import pytest
from pydantic import BaseModel


@pytest.fixture(autouse=True)
def disable_empty_findings_check():
    """Disable empty findings check for tests.

    Issue #507: Tests use mock agents that return MockAgentSchema without
    agent-specific fields (like 'alternatives' for tech_comparator).
    Setting MIN_AGENT_FINDINGS=0 disables this validation in tests.
    """
    original = os.environ.get("MIN_AGENT_FINDINGS")
    os.environ["MIN_AGENT_FINDINGS"] = "0"
    yield
    if original is None:
        os.environ.pop("MIN_AGENT_FINDINGS", None)
    else:
        os.environ["MIN_AGENT_FINDINGS"] = original


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
