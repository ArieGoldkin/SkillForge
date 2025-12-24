"""Unit tests for agent registry with tier metadata.

Issue #498: Agent Registry with Tier Metadata
"""

import pytest

from app.domains.analysis.agents.registry import (
    AGENT_REGISTRY,
    AgentMetadata,
    AgentTier,
    AnalysisMode,
    get_agent_metadata,
    get_agents_by_tier,
    get_agents_for_mode,
    get_memory_enabled_agents,
    get_tool_enabled_agents,
)


class TestAgentTier:
    """Tests for AgentTier enum."""

    def test_tier_ordering(self):
        """Verify tier ordering: UNIVERSAL < VALIDATION < RESEARCH."""
        assert AgentTier.UNIVERSAL < AgentTier.VALIDATION
        assert AgentTier.VALIDATION < AgentTier.RESEARCH
        assert AgentTier.UNIVERSAL < AgentTier.RESEARCH

    def test_tier_values(self):
        """Verify tier integer values."""
        assert AgentTier.UNIVERSAL == 1
        assert AgentTier.VALIDATION == 2
        assert AgentTier.RESEARCH == 3


class TestAgentMetadata:
    """Tests for AgentMetadata dataclass."""

    def test_metadata_creation(self):
        """Test creating agent metadata."""
        meta = AgentMetadata(
            name="TEST_AGENT",
            tier=AgentTier.UNIVERSAL,
        )
        assert meta.name == "TEST_AGENT"
        assert meta.tier == AgentTier.UNIVERSAL
        assert meta.tools == []
        assert meta.requires_memory is False

    def test_metadata_with_tools(self):
        """Test metadata with tool capabilities."""
        meta = AgentMetadata(
            name="TOOL_AGENT",
            tier=AgentTier.VALIDATION,
            tools=["tavily_search", "github_api"],
        )
        assert len(meta.tools) == 2
        assert "tavily_search" in meta.tools

    def test_metadata_with_memory(self):
        """Test metadata with memory requirement."""
        meta = AgentMetadata(
            name="MEMORY_AGENT",
            tier=AgentTier.RESEARCH,
            requires_memory=True,
        )
        assert meta.requires_memory is True

    def test_metadata_is_frozen(self):
        """Test that metadata is immutable."""
        meta = AgentMetadata(name="TEST", tier=AgentTier.UNIVERSAL)
        with pytest.raises(AttributeError):
            meta.name = "CHANGED"  # type: ignore[misc]


class TestAgentRegistry:
    """Tests for AGENT_REGISTRY."""

    def test_registry_has_12_agents(self):
        """Verify registry contains all 12 agents."""
        assert len(AGENT_REGISTRY) == 12

    def test_tier1_has_4_agents(self):
        """Tier 1 (Universal) should have 4 agents."""
        tier1 = get_agents_by_tier(AgentTier.UNIVERSAL)
        assert len(tier1) == 4
        assert "key_insights" in tier1
        assert "pros_cons" in tier1
        assert "audience_fit" in tier1
        assert "actionable" in tier1

    def test_tier2_has_4_agents(self):
        """Tier 2 (Validation) should have 4 agents."""
        tier2 = get_agents_by_tier(AgentTier.VALIDATION)
        assert len(tier2) == 4
        assert "fact_validator" in tier2
        assert "source_credibility" in tier2
        assert "freshness_checker" in tier2
        assert "alternatives_finder" in tier2

    def test_tier3_has_4_agents(self):
        """Tier 3 (Research) should have 4 agents."""
        tier3 = get_agents_by_tier(AgentTier.RESEARCH)
        assert len(tier3) == 4
        assert "deep_researcher" in tier3
        assert "community_pulse" in tier3
        assert "knowledge_curator" in tier3
        assert "learning_path_advisor" in tier3

    def test_all_agents_have_valid_tier(self):
        """Every agent must have a valid tier."""
        for name, meta in AGENT_REGISTRY.items():
            assert meta.tier in AgentTier, f"{name} has invalid tier"


class TestGetAgentsForMode:
    """Tests for get_agents_for_mode function."""

    def test_quick_mode_returns_tier1_only(self):
        """Quick mode returns only Tier 1 agents."""
        agents = get_agents_for_mode(AnalysisMode.QUICK)
        assert len(agents) == 4
        assert "key_insights" in agents
        assert "fact_validator" not in agents  # Tier 2
        assert "deep_researcher" not in agents  # Tier 3

    def test_standard_mode_returns_tier1_and_tier2(self):
        """Standard mode returns Tier 1 + Tier 2 agents."""
        agents = get_agents_for_mode(AnalysisMode.STANDARD)
        assert len(agents) == 8
        assert "key_insights" in agents  # Tier 1
        assert "fact_validator" in agents  # Tier 2
        assert "deep_researcher" not in agents  # Tier 3

    def test_deep_dive_returns_all_agents(self):
        """Deep dive mode returns all agents."""
        agents = get_agents_for_mode(AnalysisMode.DEEP_DIVE)
        assert len(agents) == 12
        assert "key_insights" in agents  # Tier 1
        assert "fact_validator" in agents  # Tier 2
        assert "deep_researcher" in agents  # Tier 3

    def test_invalid_mode_raises_error(self):
        """Invalid mode raises ValueError with helpful message (Issue #502 fix)."""
        with pytest.raises(ValueError) as exc_info:
            get_agents_for_mode("invalid_mode")
        # Verify error message includes valid modes
        assert "Invalid analysis mode: 'invalid_mode'" in str(exc_info.value)
        assert "quick" in str(exc_info.value)
        assert "standard" in str(exc_info.value)
        assert "deep_dive" in str(exc_info.value)

    def test_accepts_string_modes(self):
        """Function accepts mode as plain string."""
        agents = get_agents_for_mode("quick")
        assert len(agents) == 4

    def test_accepts_enum_modes(self):
        """Function accepts mode as AnalysisMode enum."""
        agents = get_agents_for_mode(AnalysisMode.STANDARD)
        assert len(agents) == 8


class TestGetAgentMetadata:
    """Tests for get_agent_metadata function."""

    def test_get_existing_agent(self):
        """Get metadata for existing agent."""
        meta = get_agent_metadata("key_insights")
        assert meta is not None
        assert meta.name == "KEY_INSIGHTS"
        assert meta.tier == AgentTier.UNIVERSAL

    def test_get_nonexistent_agent(self):
        """Get metadata for non-existent agent returns None."""
        meta = get_agent_metadata("nonexistent_agent")
        assert meta is None


class TestToolEnabledAgents:
    """Tests for get_tool_enabled_agents function."""

    def test_returns_agents_with_tools(self):
        """Returns only agents with tool capabilities."""
        agents = get_tool_enabled_agents()
        # Agents with tools: fact_validator, freshness_checker,
        # alternatives_finder, deep_researcher
        assert len(agents) == 4
        assert "fact_validator" in agents
        assert "key_insights" not in agents  # No tools


class TestMemoryEnabledAgents:
    """Tests for get_memory_enabled_agents function."""

    def test_returns_agents_with_memory(self):
        """Returns only agents requiring memory injection."""
        agents = get_memory_enabled_agents()
        # Agents with memory: deep_researcher, knowledge_curator,
        # learning_path_advisor
        assert len(agents) == 3
        assert "deep_researcher" in agents
        assert "key_insights" not in agents  # No memory
