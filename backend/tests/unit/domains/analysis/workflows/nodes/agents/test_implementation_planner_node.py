"""Unit tests for implementation_planner_node."""

from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest

from app.domains.analysis.workflows.nodes.agents.implementation_planner_node import (
    implementation_planner_node,
)
from app.domains.analysis.workflows.state import AnalysisState


@pytest.fixture
def sample_state() -> AnalysisState:
    """Sample state for testing."""
    return {
        "analysis_id": str(uuid4()),
        "url": "https://example.com",
        "content_type": "article",
        "raw_content": "Step-by-step implementation guide.",
    }


@pytest.mark.asyncio
@patch(
    "app.domains.analysis.workflows.nodes.agents.implementation_planner_node.run_implementation_planner_with_session"
)
async def test_implementation_planner_node_success(
    mock_runner: AsyncMock, sample_state: AnalysisState
) -> None:
    """Test implementation_planner_node returns findings on success."""
    mock_runner.return_value = {
        "agent_type": "implementation_planner",
        "findings": {"steps": []},
        "processing_time_ms": 1000,
    }

    result = await implementation_planner_node(sample_state)

    assert "agent_findings" in result
    assert len(result["agent_findings"]) == 1
    assert result["agent_findings"][0]["agent_type"] == "implementation_planner"


@pytest.mark.asyncio
@patch(
    "app.domains.analysis.workflows.nodes.agents.implementation_planner_node.run_implementation_planner_with_session"
)
async def test_implementation_planner_node_handles_error(
    mock_runner: AsyncMock, sample_state: AnalysisState
) -> None:
    """Test implementation_planner_node handles errors gracefully."""
    mock_runner.side_effect = Exception("Agent failed")

    result = await implementation_planner_node(sample_state)

    assert "agent_findings" in result
    assert result["agent_findings"] == []
