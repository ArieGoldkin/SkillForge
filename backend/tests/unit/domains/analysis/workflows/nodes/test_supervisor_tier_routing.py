"""Unit tests for supervisor tier-based agent routing (Issue #436).

Tests verify:
1. Analysis mode correctly filters agents by tier
2. Tier 1 (Universal) agents always run
3. Tier 2 (Validation) agents run on Standard+
4. Tier 3 (Research) agents run on Deep Dive only
5. Content-specific agents (not in registry) pass through all modes
6. Tier filtering integrates correctly with content signal filtering
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.domains.analysis.agents.registry import (
    AgentMetadata,
    AgentTier,
    AnalysisMode,
    get_agent_metadata,
    get_agents_by_tier,
    get_agents_for_mode,
    get_memory_enabled_agents,
    get_tool_enabled_agents,
)
from app.domains.analysis.workflows.nodes.supervisor import supervisor_route
from app.domains.analysis.workflows.nodes.supervisor_schema import AgentSelection


@pytest.mark.unit
class TestAgentRegistryFunctions:
    """Tests for agent registry helper functions."""

    def test_get_agents_for_mode_quick(self):
        """Quick mode returns only Tier 1 (Universal) agents."""
        agents = get_agents_for_mode("quick")

        # Should only include Tier 1 agents
        expected_tier1 = ["key_insights", "pros_cons", "audience_fit", "actionable"]
        assert set(agents) == set(expected_tier1)
        assert len(agents) == 4

    def test_get_agents_for_mode_standard(self):
        """Standard mode returns Tier 1 + Tier 2 agents."""
        agents = get_agents_for_mode("standard")

        # Should include Tier 1 + Tier 2
        expected_tier1 = ["key_insights", "pros_cons", "audience_fit", "actionable"]
        expected_tier2 = [
            "fact_validator",
            "source_credibility",
            "freshness_checker",
            "alternatives_finder",
        ]

        for agent in expected_tier1:
            assert agent in agents, f"Tier 1 agent {agent} missing from standard mode"
        for agent in expected_tier2:
            assert agent in agents, f"Tier 2 agent {agent} missing from standard mode"

        assert len(agents) == 8

    def test_get_agents_for_mode_deep_dive(self):
        """Deep dive mode returns all tier agents."""
        agents = get_agents_for_mode("deep_dive")

        # Should include all tiers
        expected_tier1 = ["key_insights", "pros_cons", "audience_fit", "actionable"]
        expected_tier2 = [
            "fact_validator",
            "source_credibility",
            "freshness_checker",
            "alternatives_finder",
        ]
        expected_tier3 = [
            "deep_researcher",
            "community_pulse",
            "knowledge_curator",
            "learning_path_advisor",
        ]

        for agent in expected_tier1 + expected_tier2 + expected_tier3:
            assert agent in agents, f"Agent {agent} missing from deep_dive mode"

        assert len(agents) == 12

    def test_get_agents_for_mode_invalid_raises_value_error(self):
        """Invalid mode raises ValueError with valid options listed.

        Strict validation is intentional:
        - Frontend TypeScript enum prevents invalid values
        - Pydantic validates API input
        - Silent fallback would waste money on Tier 3 agents
        """
        with pytest.raises(ValueError, match=r"Invalid analysis mode: 'invalid_mode'") as exc_info:
            get_agents_for_mode("invalid_mode")

        # Error message should list valid modes for debugging
        assert "quick" in str(exc_info.value)
        assert "standard" in str(exc_info.value)
        assert "deep_dive" in str(exc_info.value)

    def test_get_agent_metadata_tier1(self):
        """Tier 1 agents have correct metadata."""
        meta = get_agent_metadata("key_insights")
        assert meta is not None
        assert meta.tier == AgentTier.UNIVERSAL
        assert meta.name == "KEY_INSIGHTS"
        assert meta.tools == []
        assert meta.requires_memory is False

    def test_get_agent_metadata_tier2_with_tools(self):
        """Tier 2 agents have tool capabilities."""
        meta = get_agent_metadata("fact_validator")
        assert meta is not None
        assert meta.tier == AgentTier.VALIDATION
        assert "tavily_search" in meta.tools

        meta = get_agent_metadata("freshness_checker")
        assert meta is not None
        assert meta.tier == AgentTier.VALIDATION
        assert "github_api" in meta.tools or "npm_api" in meta.tools

    def test_get_agent_metadata_tier3_with_memory(self):
        """Tier 3 agents have memory requirements."""
        meta = get_agent_metadata("deep_researcher")
        assert meta is not None
        assert meta.tier == AgentTier.RESEARCH
        assert meta.requires_memory is True

    def test_get_agent_metadata_unknown_returns_none(self):
        """Unknown agent returns None (content-specific agents not in registry)."""
        # Content-specific agents are NOT in the tier registry
        meta = get_agent_metadata("tech_comparator")
        assert meta is None

        meta = get_agent_metadata("security_auditor")
        assert meta is None

        meta = get_agent_metadata("implementation_planner")
        assert meta is None

    def test_get_tool_enabled_agents(self):
        """Correctly identifies agents with MCP tool capabilities."""
        tool_agents = get_tool_enabled_agents()

        # Tier 2 agents with tools
        assert "fact_validator" in tool_agents
        assert "freshness_checker" in tool_agents
        assert "alternatives_finder" in tool_agents

        # Tier 3 agents with tools
        assert "deep_researcher" in tool_agents

        # Agents without tools should NOT be included
        assert "key_insights" not in tool_agents
        assert "pros_cons" not in tool_agents

    def test_get_memory_enabled_agents(self):
        """Correctly identifies agents requiring memory injection."""
        memory_agents = get_memory_enabled_agents()

        # Tier 3 agents with memory
        assert "deep_researcher" in memory_agents
        assert "knowledge_curator" in memory_agents
        assert "learning_path_advisor" in memory_agents

        # Agents without memory should NOT be included
        assert "key_insights" not in memory_agents
        assert "fact_validator" not in memory_agents

    def test_get_agents_by_tier(self):
        """Get agents for a specific tier only."""
        tier1_agents = get_agents_by_tier(AgentTier.UNIVERSAL)
        assert set(tier1_agents) == {"key_insights", "pros_cons", "audience_fit", "actionable"}

        tier2_agents = get_agents_by_tier(AgentTier.VALIDATION)
        assert set(tier2_agents) == {
            "fact_validator",
            "source_credibility",
            "freshness_checker",
            "alternatives_finder",
        }

        tier3_agents = get_agents_by_tier(AgentTier.RESEARCH)
        assert set(tier3_agents) == {
            "deep_researcher",
            "community_pulse",
            "knowledge_curator",
            "learning_path_advisor",
        }


@pytest.mark.unit
class TestSupervisorTierFiltering:
    """Tests for supervisor tier-based filtering in supervisor_route.

    These tests isolate tier filtering by mocking content-type and signal filtering
    to pass agents through, allowing us to verify tier-based filtering specifically.
    """

    @pytest.fixture
    def mock_supervisor_setup(self):
        """Create mock setup for supervisor tests."""

        def setup(llm_selected_agents: list[str]):
            """Create mock that returns specified agents from LLM."""
            mock_selection = AgentSelection(
                agents=llm_selected_agents,
                reasoning="Test selection",
                confidence=0.8,
            )

            mock_lcel_chain = MagicMock()
            mock_lcel_chain.ainvoke = AsyncMock(return_value=mock_selection)
            mock_lcel_chain.with_retry = MagicMock(return_value=mock_lcel_chain)
            mock_lcel_chain.with_fallbacks = MagicMock(return_value=mock_lcel_chain)
            mock_model = MagicMock()
            mock_model.with_structured_output = MagicMock(return_value=mock_lcel_chain)

            return mock_model

        return setup

    @pytest.fixture
    def mock_no_content_filtering(self):
        """Mock to disable content-type filtering (allow all agents through)."""

        def mock_filter(agents, content_type):
            return agents, []  # No agents excluded by content type

        return mock_filter

    @pytest.fixture
    def mock_no_signal_skip(self):
        """Mock to disable signal-based skipping.

        Issue #540: Updated to accept code_patterns parameter for standardized detection.
        """

        def mock_skip(agent_name, signals, code_patterns=None):
            return False, None  # Never skip

        return mock_skip

    @pytest.mark.asyncio
    async def test_quick_mode_excludes_tier2_agents(
        self, mock_supervisor_setup, mock_no_content_filtering, mock_no_signal_skip
    ):
        """Quick mode should exclude Tier 2 agents even if LLM selects them."""
        # LLM selects Tier 1 + Tier 2 agents
        mock_model = mock_supervisor_setup(
            [
                "key_insights",  # Tier 1 - should pass
                "pros_cons",  # Tier 1 - should pass
                "actionable",  # Tier 1 - should pass
                "fact_validator",  # Tier 2 - should be filtered out
                "implementation_planner",  # Content-specific - should pass (not in registry)
            ]
        )

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
            result = await supervisor_route(
                content="Test content for analysis",
                content_type="article",
                analysis_id="test-tier-quick",
                analysis_mode="quick",  # Quick mode = Tier 1 only
            )

            decision = result["supervisor_decision"]
            agents = decision["agents"]

            # Tier 1 agents should be present
            assert "key_insights" in agents
            assert "pros_cons" in agents

            # Tier 2 agent should be filtered out by tier filtering
            assert "fact_validator" not in agents

            # Content-specific agent should pass through (not in registry)
            assert "implementation_planner" in agents

    @pytest.mark.asyncio
    async def test_standard_mode_includes_tier2_excludes_tier3(
        self, mock_supervisor_setup, mock_no_content_filtering, mock_no_signal_skip
    ):
        """Standard mode includes Tier 1+2 but excludes Tier 3."""
        mock_model = mock_supervisor_setup(
            [
                "key_insights",  # Tier 1
                "fact_validator",  # Tier 2
                "deep_researcher",  # Tier 3 - should be filtered out
            ]
        )

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
            result = await supervisor_route(
                content="Test content for analysis",
                content_type="article",
                analysis_id="test-tier-standard",
                analysis_mode="standard",
            )

            decision = result["supervisor_decision"]
            agents = decision["agents"]

            # Tier 1 + 2 should be present
            assert "key_insights" in agents
            assert "fact_validator" in agents

            # Tier 3 should be filtered out
            assert "deep_researcher" not in agents

    @pytest.mark.asyncio
    async def test_deep_dive_includes_all_tiers(
        self, mock_supervisor_setup, mock_no_content_filtering, mock_no_signal_skip
    ):
        """Deep dive mode includes all tier agents."""
        mock_model = mock_supervisor_setup(
            [
                "key_insights",  # Tier 1
                "fact_validator",  # Tier 2
                "deep_researcher",  # Tier 3
            ]
        )

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
            result = await supervisor_route(
                content="Test content for analysis",
                content_type="article",
                analysis_id="test-tier-deep",
                analysis_mode="deep_dive",
            )

            decision = result["supervisor_decision"]
            agents = decision["agents"]

            # All tiers should be present
            assert "key_insights" in agents
            assert "fact_validator" in agents
            assert "deep_researcher" in agents

    @pytest.mark.asyncio
    async def test_content_specific_agents_always_pass_through(
        self, mock_supervisor_setup, mock_no_content_filtering, mock_no_signal_skip
    ):
        """Content-specific agents (not in registry) pass through all modes."""
        # These are the OLD 8 agents that are NOT in the tier registry
        content_specific_agents = [
            "tech_comparator",
            "security_auditor",
            "implementation_planner",
            "dependency_mapper",
        ]

        mock_model = mock_supervisor_setup(content_specific_agents)

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
            # Test in quick mode - all should still pass (not in tier registry)
            result = await supervisor_route(
                content="Test content for analysis",
                content_type="article",
                analysis_id="test-content-specific",
                analysis_mode="quick",  # Most restrictive mode
            )

            decision = result["supervisor_decision"]
            agents = decision["agents"]

            # Content-specific agents should pass through regardless of mode
            # (they're not in tier registry, so tier filtering doesn't affect them)
            for agent in content_specific_agents:
                assert agent in agents, (
                    f"Content-specific agent {agent} should pass through in quick mode"
                )

    @pytest.mark.asyncio
    async def test_default_mode_is_standard(
        self, mock_supervisor_setup, mock_no_content_filtering, mock_no_signal_skip
    ):
        """Default analysis_mode should be 'standard' (Tier 1+2)."""
        mock_model = mock_supervisor_setup(
            [
                "key_insights",
                "fact_validator",
                "deep_researcher",  # Tier 3 - should be filtered
            ]
        )

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
            # Call without analysis_mode (uses default)
            result = await supervisor_route(
                content="Test content",
                content_type="article",
                analysis_id="test-default-mode",
            )

            decision = result["supervisor_decision"]
            agents = decision["agents"]

            # Standard mode (default) should include Tier 1+2
            assert "key_insights" in agents
            assert "fact_validator" in agents

            # Tier 3 should be excluded (standard doesn't include deep_dive)
            assert "deep_researcher" not in agents


@pytest.mark.unit
class TestTierModeEnumValues:
    """Tests for AnalysisMode enum values."""

    def test_analysis_mode_values(self):
        """Verify AnalysisMode enum has correct values."""
        assert AnalysisMode.QUICK.value == "quick"
        assert AnalysisMode.STANDARD.value == "standard"
        assert AnalysisMode.DEEP_DIVE.value == "deep_dive"

    def test_agent_tier_ordering(self):
        """Verify AgentTier enum has correct ordering for cumulative logic."""
        assert AgentTier.UNIVERSAL < AgentTier.VALIDATION < AgentTier.RESEARCH
        assert AgentTier.UNIVERSAL == 1
        assert AgentTier.VALIDATION == 2
        assert AgentTier.RESEARCH == 3


@pytest.mark.unit
class TestAgentMetadataDataclass:
    """Tests for AgentMetadata dataclass behavior."""

    def test_frozen_immutability(self):
        """AgentMetadata should be immutable (frozen dataclass)."""
        from dataclasses import FrozenInstanceError

        meta = AgentMetadata(
            name="TEST",
            tier=AgentTier.UNIVERSAL,
        )

        with pytest.raises(FrozenInstanceError):
            meta.name = "MODIFIED"

    def test_default_values(self):
        """Verify default values for optional fields."""
        meta = AgentMetadata(
            name="TEST",
            tier=AgentTier.UNIVERSAL,
        )

        assert meta.tools == []
        assert meta.requires_memory is False

    def test_with_all_fields(self):
        """Test AgentMetadata with all fields populated."""
        meta = AgentMetadata(
            name="DEEP_AGENT",
            tier=AgentTier.RESEARCH,
            tools=["tavily_search", "github_api"],
            requires_memory=True,
        )

        assert meta.name == "DEEP_AGENT"
        assert meta.tier == AgentTier.RESEARCH
        assert meta.tools == ["tavily_search", "github_api"]
        assert meta.requires_memory is True
