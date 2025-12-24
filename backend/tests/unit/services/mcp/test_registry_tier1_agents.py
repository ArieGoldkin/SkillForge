"""Unit tests for MCP registry Tier 1 agent configurations (Issue #436, #499)."""

import pytest

from app.shared.services.mcp.registry import (
    AGENT_TOOL_CONFIGS,
    ARTIFACT_LOAD_CAPABILITY,
    MEMORY_SEARCH_CAPABILITY,
    ToolRegistry,
)


class TestTier1AgentConfigs:
    """Test Tier 1 universal agent MCP configurations."""

    @pytest.mark.parametrize(
        "agent_type",
        ["key_insights", "pros_cons", "actionable", "audience_fit"],
    )
    def test_tier1_agent_has_config(self, agent_type: str) -> None:
        """Test each Tier 1 agent has a configuration entry."""
        assert agent_type in AGENT_TOOL_CONFIGS

    @pytest.mark.parametrize(
        "agent_type",
        ["key_insights", "pros_cons", "actionable", "audience_fit"],
    )
    def test_tier1_agent_is_enabled(self, agent_type: str) -> None:
        """Test each Tier 1 agent is enabled for tools."""
        config = AGENT_TOOL_CONFIGS[agent_type]
        assert config.enabled is True

    @pytest.mark.parametrize(
        "agent_type",
        ["key_insights", "pros_cons", "actionable", "audience_fit"],
    )
    def test_tier1_agent_has_artifact_load_capability(self, agent_type: str) -> None:
        """Test each Tier 1 agent has artifact load capability."""
        config = AGENT_TOOL_CONFIGS[agent_type]
        assert ARTIFACT_LOAD_CAPABILITY in config.capabilities

    @pytest.mark.parametrize(
        "agent_type",
        ["key_insights", "pros_cons", "actionable", "audience_fit"],
    )
    def test_tier1_agent_has_memory_search_capability(self, agent_type: str) -> None:
        """Test each Tier 1 agent has memory search capability."""
        config = AGENT_TOOL_CONFIGS[agent_type]
        assert MEMORY_SEARCH_CAPABILITY in config.capabilities

    @pytest.mark.parametrize(
        "agent_type",
        ["key_insights", "pros_cons", "actionable", "audience_fit"],
    )
    def test_tier1_agent_max_tool_calls(self, agent_type: str) -> None:
        """Test each Tier 1 agent has appropriate max_tool_calls limit."""
        config = AGENT_TOOL_CONFIGS[agent_type]
        assert config.max_tool_calls == 5

    @pytest.mark.parametrize(
        "agent_type",
        ["key_insights", "pros_cons", "actionable", "audience_fit"],
    )
    def test_tier1_agent_tool_timeout(self, agent_type: str) -> None:
        """Test each Tier 1 agent has appropriate tool timeout."""
        config = AGENT_TOOL_CONFIGS[agent_type]
        assert config.tool_timeout == 20.0


class TestToolRegistryTier1:
    """Test ToolRegistry methods with Tier 1 agents."""

    @pytest.mark.parametrize(
        "agent_type",
        ["key_insights", "pros_cons", "actionable", "audience_fit"],
    )
    def test_is_tool_enabled_returns_true(self, agent_type: str) -> None:
        """Test is_tool_enabled returns True for Tier 1 agents."""
        registry = ToolRegistry()
        assert registry.is_tool_enabled(agent_type) is True

    @pytest.mark.parametrize(
        "agent_type",
        ["key_insights", "pros_cons", "actionable", "audience_fit"],
    )
    def test_get_capabilities_returns_expected(self, agent_type: str) -> None:
        """Test get_capabilities returns artifact and memory capabilities."""
        registry = ToolRegistry()
        capabilities = registry.get_capabilities(agent_type)
        assert "skillforge:load_artifact" in capabilities
        assert "skillforge:search_memory" in capabilities

    @pytest.mark.parametrize(
        "agent_type",
        ["key_insights", "pros_cons", "actionable", "audience_fit"],
    )
    def test_tier1_agents_in_enabled_list(self, agent_type: str) -> None:
        """Test Tier 1 agents appear in list_enabled_agents."""
        registry = ToolRegistry()
        enabled_agents = registry.list_enabled_agents()
        assert agent_type in enabled_agents


class TestTier1AgentConsistency:
    """Test consistency across all Tier 1 agents."""

    def test_all_tier1_agents_have_same_capabilities(self) -> None:
        """Test all Tier 1 agents have identical capability sets."""
        tier1_agents = ["key_insights", "pros_cons", "actionable", "audience_fit"]
        capability_sets = [
            frozenset(c.capability_id for c in AGENT_TOOL_CONFIGS[agent].capabilities)
            for agent in tier1_agents
        ]
        # All should have the same capabilities
        assert len(set(capability_sets)) == 1

    def test_all_tier1_agents_have_same_limits(self) -> None:
        """Test all Tier 1 agents have identical resource limits."""
        tier1_agents = ["key_insights", "pros_cons", "actionable", "audience_fit"]
        for agent in tier1_agents:
            config = AGENT_TOOL_CONFIGS[agent]
            assert config.max_tool_calls == 5, f"{agent} has unexpected max_tool_calls"
            assert config.tool_timeout == 20.0, f"{agent} has unexpected tool_timeout"
