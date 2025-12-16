"""Unit tests for MCP Tool Registry and Agent Capability Mapping.

Tests the registry system that controls which MCP tools each content analysis
agent can access.
"""

from unittest.mock import MagicMock

import pytest

from app.shared.services.mcp.registry import (

@pytest.mark.unit
    AGENT_TOOL_CONFIGS,
    AgentToolConfig,
    ToolCapability,
    ToolRegistry,
)


class TestToolCapability:
    """Test ToolCapability dataclass for capability identification."""

    def test_capability_id_format(self):
        """Verify capability ID follows 'server:tool' format."""
        cap = ToolCapability(server="github", tool_name="get_repo")
        assert cap.capability_id == "github:get_repo"

    def test_capability_with_description(self):
        """Test capability with optional description."""
        cap = ToolCapability(
            server="npm",
            tool_name="search",
            description="Search NPM packages",
        )
        assert cap.capability_id == "npm:search"
        assert cap.description == "Search NPM packages"

    def test_capability_equality(self):
        """Two capabilities with same server/tool should have same capability_id."""
        cap1 = ToolCapability(server="github", tool_name="get_repo")
        cap2 = ToolCapability(
            server="github",
            tool_name="get_repo",
            description="Different description",
        )
        assert cap1.capability_id == cap2.capability_id


class TestAgentToolConfig:
    """Test AgentToolConfig dataclass for agent tool configuration."""

    def test_config_defaults(self):
        """Verify default values for agent tool configuration."""
        config = AgentToolConfig(
            agent_type="test_agent",
            capabilities=[],
        )
        assert config.agent_type == "test_agent"
        assert config.enabled is False
        assert config.capabilities == []
        assert config.max_tool_calls == 10
        assert config.tool_timeout == 30.0

    def test_config_with_all_fields(self):
        """Test configuration with all fields populated."""
        capabilities = [
            ToolCapability(server="github", tool_name="get_repo"),
            ToolCapability(server="npm", tool_name="search"),
        ]
        config = AgentToolConfig(
            agent_type="test_agent",
            enabled=True,
            capabilities=capabilities,
            max_tool_calls=15,
            tool_timeout=45.0,
        )
        assert config.agent_type == "test_agent"
        assert config.enabled is True
        assert len(config.capabilities) == 2
        assert config.max_tool_calls == 15
        assert config.tool_timeout == 45.0

    def test_config_disabled_by_default(self):
        """Test that agents are disabled by default."""
        config = AgentToolConfig(
            agent_type="disabled_agent",
            capabilities=[],
        )
        assert config.enabled is False

    def test_config_with_capabilities(self):
        """Test configuration with multiple capabilities."""
        config = AgentToolConfig(
            agent_type="security_auditor",
            enabled=True,
            capabilities=[
                ToolCapability(server="github", tool_name="get_security_advisories"),
                ToolCapability(server="github", tool_name="get_vulnerability_alerts"),
            ],
        )
        assert len(config.capabilities) == 2
        assert config.capabilities[0].server == "github"


class TestAgentToolConfigs:
    """Test the AGENT_TOOL_CONFIGS default configuration dictionary."""

    def test_default_configs_exist(self):
        """Verify AGENT_TOOL_CONFIGS dictionary exists and is not empty."""
        assert isinstance(AGENT_TOOL_CONFIGS, dict)
        assert len(AGENT_TOOL_CONFIGS) > 0

    def test_all_8_agents_configured(self):
        """Verify all 8 content analysis agents are configured."""
        expected_agents = [
            "security_auditor",
            "dependency_mapper",
            "tech_comparator",
            "code_quality_critic",
            "implementation_planner",
            "performance_analyst",
            "trend_validator",
            "integration_feasibility",
        ]
        for agent in expected_agents:
            assert agent in AGENT_TOOL_CONFIGS, f"Missing agent: {agent}"

    def test_security_auditor_config(self):
        """Verify security_auditor has github capabilities and is enabled."""
        config = AGENT_TOOL_CONFIGS["security_auditor"]
        assert config.enabled is True
        assert len(config.capabilities) > 0
        # Should have github-based capabilities
        servers = {cap.server for cap in config.capabilities}
        assert "github" in servers

    def test_dependency_mapper_config(self):
        """Verify dependency_mapper has npm/pypi/github capabilities."""
        config = AGENT_TOOL_CONFIGS["dependency_mapper"]
        assert config.enabled is True
        assert len(config.capabilities) > 0
        servers = {cap.server for cap in config.capabilities}
        # Should support package managers
        assert servers & {"npm", "pypi", "github"}

    def test_all_agents_have_memory_search(self):
        """Verify all agents have memory search capability (Issue #245).

        After implementing Agent Memory Access (RAG), all agents should have
        the search_memory capability for reactive recall.
        """
        for agent_type, config in AGENT_TOOL_CONFIGS.items():
            # All agents should be enabled now with at least memory search
            assert config.enabled is True, f"{agent_type} should be enabled"
            capability_names = [cap.tool_name for cap in config.capabilities]
            assert "search_memory" in capability_names, (
                f"{agent_type} should have search_memory capability"
            )


class TestToolRegistry:
    """Test ToolRegistry class for managing agent tool access."""

    @pytest.fixture
    def sample_config(self):
        """Create a sample agent configuration for testing."""
        return AgentToolConfig(
            agent_type="test_agent",
            enabled=True,
            capabilities=[
                ToolCapability(server="github", tool_name="get_repo"),
                ToolCapability(server="npm", tool_name="search"),
            ],
        )

    @pytest.fixture
    def disabled_config(self):
        """Create a disabled agent configuration."""
        return AgentToolConfig(
            agent_type="disabled_agent",
            enabled=False,
            capabilities=[],
        )

    def test_registry_initialization_default(self):
        """Test registry initializes with default AGENT_TOOL_CONFIGS."""
        registry = ToolRegistry()
        assert registry is not None
        # Should have all default agents
        assert len(registry.list_enabled_agents()) > 0

    def test_registry_initialization_custom(self, sample_config):
        """Test registry initializes with custom configuration."""
        custom_configs = {"test_agent": sample_config}
        registry = ToolRegistry(agent_configs=custom_configs)
        assert "test_agent" in registry.list_enabled_agents()

    def test_get_agent_config_exists(self, sample_config):
        """Test retrieving existing agent configuration."""
        registry = ToolRegistry({"test_agent": sample_config})
        config = registry.get_agent_config("test_agent")
        assert config.agent_type == "test_agent"
        assert config.enabled is True

    def test_get_agent_config_unknown_raises_keyerror(self):
        """Test that unknown agent raises KeyError."""
        registry = ToolRegistry({})
        with pytest.raises(KeyError, match="unknown_agent"):
            registry.get_agent_config("unknown_agent")

    def test_is_tool_enabled_true_with_capabilities(self, sample_config):
        """Test is_tool_enabled returns True for enabled agent with capabilities."""
        registry = ToolRegistry({"test_agent": sample_config})
        assert registry.is_tool_enabled("test_agent") is True

    def test_is_tool_enabled_false_when_disabled(self, disabled_config):
        """Test is_tool_enabled returns False for disabled agent."""
        registry = ToolRegistry({"disabled_agent": disabled_config})
        assert registry.is_tool_enabled("disabled_agent") is False

    def test_is_tool_enabled_false_when_no_capabilities(self):
        """Test is_tool_enabled returns False when agent has no capabilities."""
        config = AgentToolConfig(
            agent_type="no_caps_agent",
            enabled=True,
            capabilities=[],
        )
        registry = ToolRegistry({"no_caps_agent": config})
        assert registry.is_tool_enabled("no_caps_agent") is False

    def test_is_tool_enabled_false_unknown_agent(self):
        """Test is_tool_enabled returns False for unknown agent."""
        registry = ToolRegistry({})
        assert registry.is_tool_enabled("unknown_agent") is False

    def test_get_capabilities_enabled_agent(self, sample_config):
        """Test get_capabilities returns capability IDs for enabled agent."""
        registry = ToolRegistry({"test_agent": sample_config})
        caps = registry.get_capabilities("test_agent")
        assert len(caps) == 2
        assert "github:get_repo" in caps
        assert "npm:search" in caps

    def test_get_capabilities_disabled_agent_returns_empty(self, disabled_config):
        """Test get_capabilities returns empty list for disabled agent."""
        registry = ToolRegistry({"disabled_agent": disabled_config})
        caps = registry.get_capabilities("disabled_agent")
        assert caps == []

    def test_get_capabilities_unknown_agent_returns_empty(self):
        """Test get_capabilities returns empty list for unknown agent."""
        registry = ToolRegistry({})
        caps = registry.get_capabilities("unknown_agent")
        assert caps == []

    def test_filter_tools_matching(self, sample_config):
        """Test filter_tools returns only matching tools for agent.

        The filter_tools method matches tool.name against tool_name directly.
        """
        registry = ToolRegistry({"test_agent": sample_config})

        # Create mock tools with name attributes matching tool_name
        mock_tool_match1 = MagicMock()
        mock_tool_match1.name = "get_repo"  # Matches tool_name directly

        mock_tool_match2 = MagicMock()
        mock_tool_match2.name = "search"  # Matches tool_name directly

        mock_tool_no_match = MagicMock()
        mock_tool_no_match.name = "get_package"  # No match

        tools = [mock_tool_match1, mock_tool_match2, mock_tool_no_match]
        filtered = registry.filter_tools(tools, "test_agent")  # type: ignore[arg-type]

        assert len(filtered) == 2
        tool_names = {tool.name for tool in filtered}
        assert "get_repo" in tool_names
        assert "search" in tool_names
        assert "get_package" not in tool_names

    def test_filter_tools_none_matching(self, sample_config):
        """Test filter_tools returns empty list when no tools match."""
        registry = ToolRegistry({"test_agent": sample_config})

        mock_tool = MagicMock()
        mock_tool.name = "get_package"  # No match

        filtered = registry.filter_tools([mock_tool], "test_agent")  # type: ignore[arg-type]
        assert len(filtered) == 0

    def test_filter_tools_disabled_agent_returns_empty(self, disabled_config):
        """Test filter_tools returns empty list for disabled agent."""
        registry = ToolRegistry({"disabled_agent": disabled_config})

        mock_tool = MagicMock()
        mock_tool.name = "get_repo"

        filtered = registry.filter_tools([mock_tool], "disabled_agent")  # type: ignore[arg-type]
        assert len(filtered) == 0

    def test_register_agent_new(self):
        """Test registering a new agent configuration."""
        registry = ToolRegistry({})
        new_config = AgentToolConfig(
            agent_type="new_agent",
            enabled=True,
            capabilities=[
                ToolCapability(server="github", tool_name="get_repo"),
            ],
        )
        registry.register_agent(new_config)
        assert "new_agent" in registry.list_enabled_agents()
        assert registry.is_tool_enabled("new_agent") is True

    def test_register_agent_override_existing(self, sample_config):
        """Test registering an agent overrides existing configuration."""
        registry = ToolRegistry({"test_agent": sample_config})

        # Verify original config
        assert len(registry.get_capabilities("test_agent")) == 2

        # Override with new config
        override_config = AgentToolConfig(
            agent_type="test_agent",
            enabled=True,
            capabilities=[
                ToolCapability(server="pypi", tool_name="get_package"),
            ],
        )
        registry.register_agent(override_config)

        # Verify override took effect
        caps = registry.get_capabilities("test_agent")
        assert len(caps) == 1
        assert "pypi:get_package" in caps

    def test_list_enabled_agents(self, sample_config, disabled_config):
        """Test list_enabled_agents returns only enabled agents with capabilities."""
        registry = ToolRegistry(
            {
                "test_agent": sample_config,
                "disabled_agent": disabled_config,
            }
        )
        enabled = registry.list_enabled_agents()
        assert "test_agent" in enabled
        assert "disabled_agent" not in enabled

    def test_list_enabled_agents_with_no_capabilities_excluded(self):
        """Test list_enabled_agents excludes agents with no capabilities."""
        config_no_caps = AgentToolConfig(
            agent_type="no_caps_agent",
            enabled=True,
            capabilities=[],
        )
        registry = ToolRegistry({"no_caps_agent": config_no_caps})
        enabled = registry.list_enabled_agents()
        assert "no_caps_agent" not in enabled

    def test_get_all_required_servers(self, sample_config):
        """Test get_all_required_servers returns unique server names."""
        config2 = AgentToolConfig(
            agent_type="agent2",
            enabled=True,
            capabilities=[
                ToolCapability(server="github", tool_name="get_file"),
                ToolCapability(server="pypi", tool_name="get_package"),
            ],
        )
        registry = ToolRegistry(
            {
                "test_agent": sample_config,
                "agent2": config2,
            }
        )
        servers = registry.get_all_required_servers()
        assert isinstance(servers, set)
        assert servers == {"github", "npm", "pypi"}

    def test_get_all_required_servers_excludes_disabled(self, sample_config, disabled_config):
        """Test get_all_required_servers excludes disabled agents."""
        disabled_with_caps = AgentToolConfig(
            agent_type="disabled_with_caps",
            enabled=False,
            capabilities=[
                ToolCapability(server="pypi", tool_name="search"),
            ],
        )
        registry = ToolRegistry(
            {
                "test_agent": sample_config,
                "disabled_agent": disabled_config,
                "disabled_with_caps": disabled_with_caps,
            }
        )
        servers = registry.get_all_required_servers()
        # Should only include servers from enabled agents
        assert servers == {"github", "npm"}
        assert "pypi" not in servers
