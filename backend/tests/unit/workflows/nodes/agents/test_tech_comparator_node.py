"""Unit tests for tech_comparator_node."""

from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest

from app.domains.analysis.workflows.nodes.agents.tech_comparator_node import tech_comparator_node
from app.domains.analysis.workflows.state import AnalysisState

@pytest.mark.unit


@pytest.fixture
def sample_state() -> AnalysisState:
    """Sample state for testing."""
    return {
        "analysis_id": str(uuid4()),
        "url": "https://example.com",
        "content_type": "article",
        "skill_level": "intermediate",
        "raw_content": "React is a JavaScript library for building user interfaces.",
        "extraction_metadata": {},
        "content_embedding": [0.1] * 1536,
        "supervisor_decision": {},
        "agent_findings": [],
        "aggregated_insights": {},
        "artifact_id": None,
    }


@pytest.mark.asyncio
@patch("app.domains.analysis.workflows.nodes.agents.tech_comparator_node.run_tech_comparator_with_session")
async def test_tech_comparator_node_success(
    mock_runner: AsyncMock, sample_state: AnalysisState
) -> None:
    """Test tech_comparator_node returns findings on success."""
    mock_runner.return_value = {
        "agent_type": "tech_comparator",
        "findings": {"comparison": "React vs Vue"},
        "processing_time_ms": 1000,
    }

    result = await tech_comparator_node(sample_state)

    assert "agent_findings" in result
    assert len(result["agent_findings"]) == 1
    assert result["agent_findings"][0]["agent_type"] == "tech_comparator"
    mock_runner.assert_called_once_with(
        content=sample_state["raw_content"],
        content_type=sample_state["content_type"],
        analysis_id=sample_state["analysis_id"],
        state=sample_state,
    )


@pytest.mark.asyncio
@patch("app.domains.analysis.workflows.nodes.agents.tech_comparator_node.run_tech_comparator_with_session")
async def test_tech_comparator_node_handles_error(
    mock_runner: AsyncMock, sample_state: AnalysisState
) -> None:
    """Test tech_comparator_node handles errors gracefully."""
    mock_runner.side_effect = Exception("Agent failed")

    result = await tech_comparator_node(sample_state)

    # Should return empty findings on error (allows other agents to continue)
    assert "agent_findings" in result
    assert result["agent_findings"] == []
