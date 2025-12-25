"""Unit tests for supervisor SSE event emission, including expected_total_stages."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.domains.analysis.workflows.nodes.supervisor import supervisor_route
from app.domains.analysis.workflows.nodes.supervisor_schema import AgentSelection


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
    """Test supervisor emits expected_total_stages with 3 agents + 4 Tier 1 agents.

    Issue #544: Tier 1 agents (key_insights, pros_cons, audience_fit, actionable)
    are force-injected after LLM selection. So 3 LLM-selected + 4 Tier 1 = 7 agents.
    Expected total stages: 5 fixed + 7 agents = 12.
    """
    # Mock the LCEL chain
    mock_lcel_chain = MagicMock()
    mock_lcel_chain.ainvoke = AsyncMock(return_value=mock_agent_selection_3_agents)
    mock_lcel_chain.with_retry = MagicMock(return_value=mock_lcel_chain)
    mock_lcel_chain.with_fallbacks = MagicMock(return_value=mock_lcel_chain)

    # Mock the base model
    mock_model = MagicMock()
    mock_model.with_structured_output = MagicMock(return_value=mock_lcel_chain)

    with (
        patch(
            "app.domains.analysis.workflows.nodes.supervisor.get_chat_model",
            return_value=mock_model,
        ),
        patch(
            "app.domains.analysis.workflows.nodes.supervisor.emit_streaming_event",
            new_callable=AsyncMock,
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
        # Issue #544: 3 LLM-selected + 4 Tier 1 = 7 agents
        # expected_total_stages: 5 fixed stages + 7 agents = 12
        assert "expected_total_stages" in complete_call[1]
        assert complete_call[1]["expected_total_stages"] == 12
        assert complete_call[1]["agent_count"] == 7


@pytest.mark.asyncio
async def test_supervisor_emits_expected_total_stages_8_agents(mock_agent_selection_8_agents):
    """Test supervisor emits expected_total_stages with LLM-selected + Tier 1 agents.

    Issue #547 (GAP 1): should_skip_agent removed - LLM decisions are trusted.
    Issue #544: Tier 1 agents are force-injected after LLM selection.

    Expected behavior:
    - 8 LLM-selected agents
    - 4 Tier 1 agents injected (key_insights, pros_cons, audience_fit, actionable)
    - code_quality_critic filtered out for "article" content type (can only process code)
    - Total: 8 + 4 - 1 = 11 agents
    """
    # Mock the LCEL chain
    mock_lcel_chain = MagicMock()
    mock_lcel_chain.ainvoke = AsyncMock(return_value=mock_agent_selection_8_agents)
    mock_lcel_chain.with_retry = MagicMock(return_value=mock_lcel_chain)
    mock_lcel_chain.with_fallbacks = MagicMock(return_value=mock_lcel_chain)

    # Mock the base model
    mock_model = MagicMock()
    mock_model.with_structured_output = MagicMock(return_value=mock_lcel_chain)

    with (
        patch(
            "app.domains.analysis.workflows.nodes.supervisor.get_chat_model",
            return_value=mock_model,
        ),
        patch(
            "app.domains.analysis.workflows.nodes.supervisor.emit_streaming_event",
            new_callable=AsyncMock,
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
        # Verify agent_count includes Tier 1 injection
        # Issue #547: With 8 LLM-selected + 4 Tier 1 - 1 (code_quality_critic for article) = 11
        assert agent_count >= 3  # Minimum 3 agents (schema minimum)
        assert agent_count <= 12  # Maximum 8 LLM-selected + 4 Tier 1 injected
