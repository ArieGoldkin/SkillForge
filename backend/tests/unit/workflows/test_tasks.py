"""Unit tests for workflow task functions."""

from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest

from app.core.types import AnalysisID
from app.workflows.tasks import execute_agents


@pytest.mark.asyncio
@patch(
    "app.workflows.tasks.agent_execution.run_tech_comparator_with_session", new_callable=AsyncMock
)
@patch(
    "app.workflows.tasks.agent_execution.run_integration_feasibility_with_session",
    new_callable=AsyncMock,
)
@patch(
    "app.workflows.tasks.agent_execution.run_implementation_planner_with_session",
    new_callable=AsyncMock,
)
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

    analysis_id: AnalysisID = str(uuid4())
    content = "Test content"
    content_type = "article"
    selected_agents = ["tech_comparator", "integration_feasibility", "implementation_planner"]

    # Execute agents (mocks handle session management)
    results = await execute_agents(content, content_type, analysis_id, selected_agents)

    # Verify results
    assert len(results) == 3
    assert all("agent_type" in r for r in results)

    # Verify each agent runner was called
    assert mock_comparator.called
    assert mock_feasibility.called
    assert mock_planner.called


@pytest.mark.asyncio
@patch(
    "app.workflows.tasks.agent_execution.run_tech_comparator_with_session", new_callable=AsyncMock
)
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


@pytest.mark.asyncio
@patch(
    "app.workflows.tasks.agent_execution.run_tech_comparator_with_session", new_callable=AsyncMock
)
async def test_execute_agents_handles_generatorexit(mock_comparator):
    """Test that execute_agents handles GeneratorExit gracefully."""
    # Setup mock to raise GeneratorExit
    mock_comparator.side_effect = GeneratorExit("Stream closed externally")

    analysis_id: AnalysisID = str(uuid4())
    content = "Test content"
    content_type = "article"
    selected_agents = ["tech_comparator"]

    # Execute agents - should handle GeneratorExit gracefully
    results = await execute_agents(content, content_type, analysis_id, selected_agents)

    # Should return empty list when agent raises GeneratorExit
    assert len(results) == 0
