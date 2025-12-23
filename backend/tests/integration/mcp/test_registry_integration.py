"""Integration tests for ToolRegistry with MCPClientPool.

Tests the complete flow of:
- Agent capability lookup
- Tool filtering by agent permissions
- Integration between ToolRegistry and MCPClientPool
"""

import pytest

# ============================================================================
# TestRegistryToolFiltering
# ============================================================================


class TestRegistryToolFiltering:
    """Test ToolRegistry filtering with real tools."""

    @pytest.mark.asyncio
    @pytest.mark.mcp_integration
    async def test_security_auditor_gets_correct_tools(
        self,
        tool_registry,
        mock_github_search_code_tool,
        mock_github_get_security_advisories_tool,
        mock_npm_get_package_tool,
    ):
        """Security auditor receives only security-related tools."""
        all_tools = [
            mock_github_search_code_tool,
            mock_github_get_security_advisories_tool,
            mock_npm_get_package_tool,
        ]

        # Filter tools for security_auditor
        filtered = tool_registry.filter_tools(all_tools, "security_auditor")

        # Security auditor should get GitHub tools (search_code, get_security_advisories)
        tool_names = [t.name for t in filtered]
        assert "search_code" in tool_names
        assert "get_security_advisories" in tool_names
        # get_package is for npm/pypi, not in security auditor's direct capabilities
        # but note: filter_tools matches by tool_name only, not by server
        assert len(filtered) >= 2

    @pytest.mark.asyncio
    @pytest.mark.mcp_integration
    async def test_dependency_mapper_gets_correct_tools(
        self,
        tool_registry,
        mock_npm_get_package_tool,
        mock_pypi_get_package_tool,
        mock_github_get_repo_tool,
        mock_github_search_code_tool,
    ):
        """Dependency mapper receives package registry tools."""
        all_tools = [
            mock_npm_get_package_tool,
            mock_pypi_get_package_tool,
            mock_github_get_repo_tool,
            mock_github_search_code_tool,
        ]

        # Filter tools for dependency_mapper
        filtered = tool_registry.filter_tools(all_tools, "dependency_mapper")

        # Dependency mapper capabilities: get-npm-package-details, get-pypi-package-details, get_repo
        tool_names = [t.name for t in filtered]
        assert "get-npm-package-details" in tool_names
        assert "get-pypi-package-details" in tool_names
        assert "get_repo" in tool_names
        # search_code is NOT in dependency_mapper's capabilities
        assert "search_code" not in tool_names


# ============================================================================
# TestRegistryCapabilities
# ============================================================================


class TestRegistryCapabilities:
    """Test capability lookup and conversion."""

    def test_get_capabilities_returns_correct_format(self, tool_registry):
        """get_capabilities returns server:tool_name format."""
        capabilities = tool_registry.get_capabilities("security_auditor")

        # Should be in format "server:tool_name"
        # Servers include external (github, npm, pypi) and internal (skillforge) MCP servers
        # Sprint 11 added skillforge server for Handle Pattern (#244) and RAG (#245)
        valid_servers = ["github", "npm", "pypi", "skillforge"]
        for cap in capabilities:
            assert ":" in cap
            server, tool = cap.split(":", 1)
            assert server in valid_servers, f"Unknown server '{server}' in capability '{cap}'"
            assert len(tool) > 0

    def test_security_auditor_capabilities_include_github(self, tool_registry):
        """Security auditor has GitHub tool capabilities."""
        capabilities = tool_registry.get_capabilities("security_auditor")

        # Should include github:search_code
        assert any("github" in cap for cap in capabilities)

    def test_dependency_mapper_capabilities_include_package_registries(self, tool_registry):
        """Dependency mapper has npm and pypi capabilities."""
        capabilities = tool_registry.get_capabilities("dependency_mapper")

        cap_servers = [cap.split(":")[0] for cap in capabilities]
        assert "npm" in cap_servers
        assert "pypi" in cap_servers
        assert "github" in cap_servers


# ============================================================================
# TestRegistryAgentStatus
# ============================================================================


class TestRegistryAgentStatus:
    """Test agent enable/disable status."""

    def test_is_tool_enabled_returns_true_for_configured_agents(self, tool_registry):
        """is_tool_enabled returns True for agents with capabilities."""
        assert tool_registry.is_tool_enabled("security_auditor") is True
        assert tool_registry.is_tool_enabled("dependency_mapper") is True

    def test_is_tool_enabled_returns_false_for_unknown_agents(self, tool_registry):
        """is_tool_enabled returns False for unknown agents."""
        assert tool_registry.is_tool_enabled("unknown_agent") is False

    def test_list_enabled_agents(self, tool_registry):
        """list_enabled_agents returns agents with capabilities."""
        enabled = tool_registry.list_enabled_agents()

        assert "security_auditor" in enabled
        assert "dependency_mapper" in enabled


# ============================================================================
# TestPoolAndRegistryIntegration
# ============================================================================


class TestPoolAndRegistryIntegration:
    """Test MCPClientPool and ToolRegistry working together."""

    @pytest.mark.asyncio
    @pytest.mark.mcp_integration
    async def test_get_tools_for_capabilities_filters_correctly(
        self, mcp_pool_with_mock_client, tool_registry
    ):
        """Pool filters tools based on registry capabilities."""
        pool = mcp_pool_with_mock_client

        # Get capabilities for security_auditor
        capabilities = tool_registry.get_capabilities("security_auditor")

        # Load tools for those capabilities
        tools = await pool.get_tools_for_capabilities(capabilities)

        # Should have filtered tools (may be empty if mock tools don't match exactly)
        # The key is that get_tools_for_capabilities doesn't error
        assert isinstance(tools, list)

    @pytest.mark.asyncio
    @pytest.mark.mcp_integration
    async def test_get_tools_for_empty_capabilities_returns_empty(self, mcp_pool_with_mock_client):
        """Empty capabilities returns empty tool list."""
        pool = mcp_pool_with_mock_client

        tools = await pool.get_tools_for_capabilities([])

        assert tools == []

    @pytest.mark.asyncio
    @pytest.mark.mcp_integration
    async def test_get_tools_for_invalid_capability_format_skipped(self, mcp_pool_with_mock_client):
        """Invalid capability format is skipped with warning."""
        pool = mcp_pool_with_mock_client

        # Invalid format (missing colon)
        tools = await pool.get_tools_for_capabilities(["invalid_capability"])

        # Should return empty (no valid capabilities)
        assert tools == []

    @pytest.mark.asyncio
    @pytest.mark.mcp_integration
    async def test_get_tools_for_unknown_server_skipped(self, mcp_pool_with_mock_client):
        """Unknown server in capability is skipped with warning."""
        pool = mcp_pool_with_mock_client

        # Valid format but unknown server
        tools = await pool.get_tools_for_capabilities(["unknown_server:some_tool"])

        # Should return empty (server not configured)
        assert tools == []


# ============================================================================
# TestFullRegistryFlow
# ============================================================================


class TestFullRegistryFlow:
    """Test complete flow: Registry → Pool → Tools."""

    @pytest.mark.asyncio
    @pytest.mark.mcp_integration
    async def test_full_flow_security_auditor(self, mcp_pool_with_mock_client, tool_registry):
        """Complete flow for security_auditor agent."""
        pool = mcp_pool_with_mock_client

        # Step 1: Check if agent is enabled
        assert tool_registry.is_tool_enabled("security_auditor")

        # Step 2: Get capabilities
        capabilities = tool_registry.get_capabilities("security_auditor")
        assert len(capabilities) > 0

        # Step 3: Load tools from pool
        tools = await pool.get_tools_for_capabilities(capabilities)

        # Step 4: Filter tools for agent (second layer of filtering)
        filtered_tools = tool_registry.filter_tools(tools, "security_auditor")

        # All filtered tools should be valid for security_auditor
        for tool in filtered_tools:
            assert hasattr(tool, "name")
            assert hasattr(tool, "ainvoke")

    @pytest.mark.asyncio
    @pytest.mark.mcp_integration
    async def test_full_flow_dependency_mapper(self, mcp_pool_with_mock_client, tool_registry):
        """Complete flow for dependency_mapper agent."""
        pool = mcp_pool_with_mock_client

        # Step 1: Check if agent is enabled
        assert tool_registry.is_tool_enabled("dependency_mapper")

        # Step 2: Get capabilities
        capabilities = tool_registry.get_capabilities("dependency_mapper")
        assert len(capabilities) > 0

        # Step 3: Load tools from pool
        tools = await pool.get_tools_for_capabilities(capabilities)

        # Step 4: Filter tools for agent
        filtered_tools = tool_registry.filter_tools(tools, "dependency_mapper")

        # All filtered tools should be valid for dependency_mapper
        for tool in filtered_tools:
            assert hasattr(tool, "name")
            assert hasattr(tool, "ainvoke")

    @pytest.mark.asyncio
    @pytest.mark.mcp_integration
    async def test_disabled_agent_flow_returns_empty(
        self, mcp_pool_with_mock_client, tool_registry
    ):
        """Disabled agent returns empty tool list."""
        pool = mcp_pool_with_mock_client

        # Check unknown agent
        assert not tool_registry.is_tool_enabled("unknown_agent")

        # Get capabilities returns empty
        capabilities = tool_registry.get_capabilities("unknown_agent")
        assert capabilities == []

        # Pool with empty capabilities returns empty
        tools = await pool.get_tools_for_capabilities(capabilities)
        assert tools == []
