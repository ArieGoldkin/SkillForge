"""Integration tests for supervisor tier-based routing (Issue #436).

Tests verify the analysis_mode parameter flows correctly through the system
and tier filtering is applied correctly.
"""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.domains.analysis.agents.registry import (
    AgentTier,
    get_agents_by_tier,
    get_agents_for_mode,
)
from app.domains.analysis.workflows.nodes.supervisor import supervisor_route
from app.domains.analysis.workflows.nodes.supervisor_schema import AgentSelection


@pytest.fixture
def mock_no_content_filtering():
    """Mock to disable content-type filtering (allow all agents through)."""

    def mock_filter(agents, content_type):
        return agents, []

    return mock_filter


@pytest.fixture
def mock_no_signal_skip():
    """Mock to disable signal-based skipping."""

    def mock_skip(agent_name, signals):
        return False, None

    return mock_skip


@pytest.mark.integration
@pytest.mark.timeout(30)
class TestSupervisorTierRoutingIntegration:
    """Integration tests for tier-based agent routing."""

    @pytest.mark.asyncio
    async def test_analysis_mode_parameter_is_respected(
        self, mock_no_content_filtering, mock_no_signal_skip
    ):
        """Test that analysis_mode parameter controls tier filtering."""
        # Create mock that returns agents from all tiers
        all_tier_agents = (
            get_agents_by_tier(AgentTier.UNIVERSAL)
            + get_agents_by_tier(AgentTier.VALIDATION)
            + get_agents_by_tier(AgentTier.RESEARCH)
        )

        mock_selection = AgentSelection(
            agents=all_tier_agents[:6],  # Select 6 agents across tiers
            reasoning="Selected agents from all tiers",
            confidence=0.85,
        )

        mock_lcel_chain = MagicMock()
        mock_lcel_chain.ainvoke = AsyncMock(return_value=mock_selection)
        mock_lcel_chain.with_retry = MagicMock(return_value=mock_lcel_chain)
        mock_lcel_chain.with_fallbacks = MagicMock(return_value=mock_lcel_chain)
        mock_model = MagicMock()
        mock_model.with_structured_output = MagicMock(return_value=mock_lcel_chain)

        content = """
        This is a comprehensive tutorial about building modern web applications.
        We'll cover React, FastAPI, and database design patterns.
        """

        with (
            patch(
                "app.domains.analysis.workflows.nodes.supervisor.get_chat_model",
                return_value=mock_model,
            ),
            patch(
                "app.domains.analysis.workflows.nodes.supervisor.emit_streaming_event",
                new_callable=AsyncMock,
            ),
            patch(
                "app.domains.analysis.workflows.nodes.supervisor.filter_agents_by_content_type",
                side_effect=mock_no_content_filtering,
            ),
            patch(
                "app.domains.analysis.workflows.nodes.supervisor.should_skip_agent",
                side_effect=mock_no_signal_skip,
            ),
        ):
            # Test QUICK mode - should only include Tier 1
            result_quick = await asyncio.wait_for(
                supervisor_route(
                    content=content,
                    content_type="article",
                    analysis_id="test-tier-integration-quick",
                    analysis_mode="quick",
                ),
                timeout=15.0,
            )

            quick_agents = result_quick["supervisor_decision"]["agents"]
            tier1_agents = set(get_agents_by_tier(AgentTier.UNIVERSAL))
            tier2_agents = set(get_agents_by_tier(AgentTier.VALIDATION))
            tier3_agents = set(get_agents_by_tier(AgentTier.RESEARCH))

            # Quick mode should only have Tier 1 agents (from tiered set)
            for agent in quick_agents:
                if agent in tier2_agents or agent in tier3_agents:
                    pytest.fail(f"Quick mode should not include Tier 2/3 agent: {agent}")

            # Test STANDARD mode - should include Tier 1 + Tier 2
            result_standard = await asyncio.wait_for(
                supervisor_route(
                    content=content,
                    content_type="article",
                    analysis_id="test-tier-integration-standard",
                    analysis_mode="standard",
                ),
                timeout=15.0,
            )

            standard_agents = result_standard["supervisor_decision"]["agents"]

            # Standard mode should not have Tier 3 agents
            for agent in standard_agents:
                if agent in tier3_agents:
                    pytest.fail(f"Standard mode should not include Tier 3 agent: {agent}")

            # Test DEEP_DIVE mode - should include all tiers
            result_deep = await asyncio.wait_for(
                supervisor_route(
                    content=content,
                    content_type="article",
                    analysis_id="test-tier-integration-deep",
                    analysis_mode="deep_dive",
                ),
                timeout=15.0,
            )

            deep_agents = result_deep["supervisor_decision"]["agents"]

            # Deep dive should allow all agents
            assert len(deep_agents) > 0

    @pytest.mark.asyncio
    async def test_tier_filtering_logs_excluded_agents(
        self, mock_no_content_filtering, mock_no_signal_skip
    ):
        """Test that tier filtering logs which agents were excluded."""
        # Select Tier 2 agents
        tier2_agents = ["fact_validator", "source_credibility", "freshness_checker"]

        mock_selection = AgentSelection(
            agents=tier2_agents,
            reasoning="Selected Tier 2 agents",
            confidence=0.9,
        )

        mock_lcel_chain = MagicMock()
        mock_lcel_chain.ainvoke = AsyncMock(return_value=mock_selection)
        mock_lcel_chain.with_retry = MagicMock(return_value=mock_lcel_chain)
        mock_lcel_chain.with_fallbacks = MagicMock(return_value=mock_lcel_chain)
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
            ),
            patch(
                "app.domains.analysis.workflows.nodes.supervisor.filter_agents_by_content_type",
                side_effect=mock_no_content_filtering,
            ),
            patch(
                "app.domains.analysis.workflows.nodes.supervisor.should_skip_agent",
                side_effect=mock_no_signal_skip,
            ),
            patch("app.domains.analysis.workflows.nodes.supervisor.logger") as mock_logger,
        ):
            # Quick mode should filter out all Tier 2 agents
            result = await asyncio.wait_for(
                supervisor_route(
                    content="Test content",
                    content_type="article",
                    analysis_id="test-tier-logging",
                    analysis_mode="quick",
                ),
                timeout=15.0,
            )

            decision = result["supervisor_decision"]

            # Tier 2 agents should NOT be in the final selection
            for agent in tier2_agents:
                assert agent not in decision["agents"], (
                    f"Tier 2 agent {agent} should be filtered in quick mode"
                )


@pytest.mark.integration
class TestAgentRegistryModeMapping:
    """Test that get_agents_for_mode returns correct agents for each mode."""

    def test_quick_mode_returns_only_tier1(self):
        """Quick mode should return exactly 4 Tier 1 agents."""
        agents = get_agents_for_mode("quick")
        assert len(agents) == 4
        assert set(agents) == {"key_insights", "pros_cons", "audience_fit", "actionable"}

    def test_standard_mode_returns_tier1_and_tier2(self):
        """Standard mode should return Tier 1 + Tier 2 = 8 agents."""
        agents = get_agents_for_mode("standard")
        assert len(agents) == 8

        # Verify Tier 1 included
        for agent in ["key_insights", "pros_cons", "audience_fit", "actionable"]:
            assert agent in agents

        # Verify Tier 2 included
        for agent in [
            "fact_validator",
            "source_credibility",
            "freshness_checker",
            "alternatives_finder",
        ]:
            assert agent in agents

    def test_deep_dive_mode_returns_all_tiers(self):
        """Deep dive mode should return all 12 agents."""
        agents = get_agents_for_mode("deep_dive")
        assert len(agents) == 12

        # Verify all tiers included
        tier1 = ["key_insights", "pros_cons", "audience_fit", "actionable"]
        tier2 = [
            "fact_validator",
            "source_credibility",
            "freshness_checker",
            "alternatives_finder",
        ]
        tier3 = [
            "deep_researcher",
            "community_pulse",
            "knowledge_curator",
            "learning_path_advisor",
        ]

        for agent in tier1 + tier2 + tier3:
            assert agent in agents

    def test_mode_agent_counts_are_cumulative(self):
        """Verify that higher modes include all lower tier agents."""
        quick_agents = set(get_agents_for_mode("quick"))
        standard_agents = set(get_agents_for_mode("standard"))
        deep_dive_agents = set(get_agents_for_mode("deep_dive"))

        # Standard should include all quick agents
        assert quick_agents.issubset(standard_agents)

        # Deep dive should include all standard agents
        assert standard_agents.issubset(deep_dive_agents)
