"""Unit tests for supervisor SSE event emission, including expected_total_stages."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.domains.analysis.workflows.nodes.supervisor import supervisor_route
from app.domains.analysis.workflows.nodes.supervisor_schema import AgentSelection

@pytest.mark.unit


@pytest.fixture
def mock_agent_selection_3_agents():
    """Mock AgentSelection with 3 agents."""
    return AgentSelection(
        agents=["tech_comparator", "security_auditor", "implementation_planner"],
        reasoning="Tech content needs comparison and security analysis",
        confidence=0.9,
    )


@pytest.fixture
def mock_agent_selection_8_agents():
    """Mock AgentSelection with 8 agents (maximum)."""
    return AgentSelection(
        agents=[
            "tech_comparator",
            "security_auditor",
            "implementation_planner",
            "performance_analyst",
            "code_quality_critic",
            "trend_validator",
            "dependency_mapper",
            "integration_feasibility",
        ],
        reasoning="Comprehensive analysis needed",
        confidence=0.95,
    )


@pytest.mark.asyncio
async def test_supervisor_emits_expected_total_stages_3_agents(mock_agent_selection_3_agents):
    """Test supervisor emits expected_total_stages with 3 agents (expect 8 total stages)."""
    # Mock the structured model
    mock_structured_model = MagicMock()
    mock_structured_model.ainvoke = AsyncMock(return_value=mock_agent_selection_3_agents)

    # Mock the base model
    mock_model = MagicMock()
    mock_model.with_structured_output = MagicMock(return_value=mock_structured_model)

    with (
        patch("app.workflows.nodes.supervisor.get_chat_model", return_value=mock_model),
        patch(
            "app.workflows.nodes.supervisor.emit_streaming_event", new_callable=AsyncMock
        ) as mock_emit,
    ):
        await supervisor_route(
            content="Test content for tech comparison and security analysis.",
            content_type="article",
            analysis_id="test-analysis-id",
        )

        # Find the complete event
        complete_calls = [c for c in mock_emit.call_args_list if c[1].get("status") == "complete"]
        assert len(complete_calls) > 0, "Expected complete event to be emitted"

        complete_call = complete_calls[0]
        # Verify expected_total_stages: 5 fixed stages + 3 agents = 8
        assert "expected_total_stages" in complete_call[1]
        assert complete_call[1]["expected_total_stages"] == 8
        assert complete_call[1]["agent_count"] == 3


@pytest.mark.asyncio
async def test_supervisor_emits_expected_total_stages_8_agents(mock_agent_selection_8_agents):
    """Test supervisor emits expected_total_stages with filtered agents.

    Note: Supervisor filters agents based on content type, so not all 8 agents
    may be selected. The test verifies that expected_total_stages is calculated
    correctly based on the actual filtered agents.
    """
    # Mock the structured model
    mock_structured_model = MagicMock()
    mock_structured_model.ainvoke = AsyncMock(return_value=mock_agent_selection_8_agents)

    # Mock the base model
    mock_model = MagicMock()
    mock_model.with_structured_output = MagicMock(return_value=mock_structured_model)

    with (
        patch("app.workflows.nodes.supervisor.get_chat_model", return_value=mock_model),
        patch(
            "app.workflows.nodes.supervisor.emit_streaming_event", new_callable=AsyncMock
        ) as mock_emit,
    ):
        await supervisor_route(
            content="Comprehensive technical content requiring full analysis.",
            content_type="article",
            analysis_id="test-analysis-id",
        )

        # Find the complete event
        complete_calls = [c for c in mock_emit.call_args_list if c[1].get("status") == "complete"]
        assert len(complete_calls) > 0, "Expected complete event to be emitted"

        complete_call = complete_calls[0]
        # Verify expected_total_stages is present and calculated correctly
        assert "expected_total_stages" in complete_call[1]
        agent_count = complete_call[1]["agent_count"]
        expected_total = complete_call[1]["expected_total_stages"]
        # Verify calculation: 5 fixed stages + agent_count = expected_total
        assert expected_total == 5 + agent_count
        # Verify agent_count is reasonable (supervisor may filter some agents)
        assert agent_count >= 3  # Minimum 3 agents
        assert agent_count <= 8  # Maximum 8 agents
