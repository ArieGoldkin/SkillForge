"""Unit tests for workflow task functions."""

from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest

from app.core.types import AnalysisID
from app.workflows.tasks import execute_agents


@pytest.mark.asyncio
@patch("app.workflows.tasks.run_tech_comparator")
@patch("app.workflows.tasks.run_integration_feasibility")
@patch("app.workflows.tasks.run_implementation_planner")
async def test_execute_agents_creates_separate_sessions(
    mock_planner,
    mock_feasibility,
    mock_comparator,
):
    """Test that execute_agents creates separate sessions for each agent."""
    # Setup mocks to return successful results
    mock_comparator.return_value = {
        "agent_type": "tech_comparator",
        "findings": {"test": "finding1"},
    }
    mock_feasibility.return_value = {
        "agent_type": "integration_feasibility",
        "findings": {"test": "finding2"},
    }
    mock_planner.return_value = {
        "agent_type": "implementation_planner",
        "findings": {"test": "finding3"},
    }

    # Mock AsyncSessionLocal to track session creation
    session_call_count = 0

    async def mock_session_context():
        """Mock session context manager."""
        nonlocal session_call_count
        session_call_count += 1
        mock_session = AsyncMock()
        return mock_session

    with patch("app.workflows.tasks.AsyncSessionLocal") as mock_session_local:
        # Create mock context managers for each session
        mock_contexts = []
        for _ in range(3):
            mock_context = AsyncMock()
            mock_context.__aenter__ = AsyncMock(return_value=AsyncMock())
            mock_context.__aexit__ = AsyncMock(return_value=None)
            mock_contexts.append(mock_context)

        mock_session_local.side_effect = mock_contexts

        analysis_id: AnalysisID = str(uuid4())
        content = "Test content"
        content_type = "article"
        selected_agents = ["tech_comparator", "integration_feasibility", "implementation_planner"]

        # Execute agents
        results = await execute_agents(content, content_type, analysis_id, selected_agents)

        # Verify results
        assert len(results) == 3
        assert all("agent_type" in r for r in results)

        # Verify each agent was called
        assert mock_comparator.called
        assert mock_feasibility.called
        assert mock_planner.called

        # Verify AsyncSessionLocal was called 3 times (once per agent)
        assert mock_session_local.call_count == 3


@pytest.mark.asyncio
@patch("app.workflows.tasks.run_tech_comparator")
async def test_execute_agents_handles_exceptions(mock_comparator):
    """Test that execute_agents handles agent exceptions gracefully."""
    # Setup mock to raise exception
    mock_comparator.side_effect = Exception("Agent failed")

    analysis_id: AnalysisID = str(uuid4())
    content = "Test content"
    content_type = "article"
    selected_agents = ["tech_comparator"]

    # Execute agents - should handle exception gracefully
    results = await execute_agents(content, content_type, analysis_id, selected_agents)

    # Should return empty list when agent fails
    assert len(results) == 0


@pytest.mark.asyncio
async def test_execute_agents_returns_empty_for_no_agents():
    """Test that execute_agents returns empty list when no agents selected."""
    analysis_id: AnalysisID = str(uuid4())
    content = "Test content"
    content_type = "article"
    selected_agents: list[str] = []

    results = await execute_agents(content, content_type, analysis_id, selected_agents)

    assert results == []
