"""Fixtures for MCP integration tests.

Provides mock MCP tools, server configurations, and client pool
fixtures for testing end-to-end MCP flows without requiring
actual MCP server processes.

Mocking Strategy:
- Level 1: Mock MCPClientPool methods (lightweight)
- Level 2: Mock MultiServerMCPClient (behavioral) - DEFAULT
- Level 3: Real MCP servers (requires external setup)
"""

from unittest.mock import AsyncMock, MagicMock

import pytest
from langchain_core.tools import BaseTool

from app.services.mcp.client import ConnectionState, MCPClientPool, MCPConnection
from app.services.mcp.config import MCPServerConfig, MCPTransport

# ============================================================================
# Mock Tool Fixtures
# ============================================================================


@pytest.fixture
def mock_github_search_code_tool():
    """Mock GitHub search_code MCP tool.

    Note: Tool name matches registry capability (search_code, not github_search_code).
    """
    tool = MagicMock(spec=BaseTool)
    tool.name = "search_code"  # Matches registry capability
    tool.description = "Search code across GitHub repositories"
    tool.ainvoke = AsyncMock(
        return_value={
            "results": [
                {"file": "src/auth.py", "snippet": "def authenticate(user):"},
            ]
        }
    )
    return tool


@pytest.fixture
def mock_github_get_security_advisories_tool():
    """Mock GitHub get_security_advisories MCP tool."""
    tool = MagicMock(spec=BaseTool)
    tool.name = "get_security_advisories"  # Matches registry capability
    tool.description = "Get security advisories for a repository"
    tool.ainvoke = AsyncMock(
        return_value={
            "advisories": [
                {"id": "GHSA-1234", "severity": "HIGH", "summary": "XSS vulnerability"},
            ]
        }
    )
    return tool


@pytest.fixture
def mock_npm_get_package_tool():
    """Mock npm get_package MCP tool."""
    tool = MagicMock(spec=BaseTool)
    tool.name = "get_package"  # Matches registry capability (npm:get_package)
    tool.description = "Get npm package metadata"
    tool.ainvoke = AsyncMock(
        return_value={
            "name": "react",
            "version": "18.2.0",
            "dependencies": {"loose-envify": "^1.1.0"},
        }
    )
    return tool


@pytest.fixture
def mock_pypi_get_package_tool():
    """Mock PyPI get_package MCP tool."""
    tool = MagicMock(spec=BaseTool)
    tool.name = "get_package"  # Same name as npm (differentiated by server)
    tool.description = "Get PyPI package information"
    tool.ainvoke = AsyncMock(
        return_value={
            "name": "fastapi",
            "version": "0.109.0",
            "requires_python": ">=3.8",
        }
    )
    return tool


@pytest.fixture
def mock_github_get_repo_tool():
    """Mock GitHub get_repo MCP tool."""
    tool = MagicMock(spec=BaseTool)
    tool.name = "get_repo"  # Matches registry capability
    tool.description = "Get GitHub repository details"
    tool.ainvoke = AsyncMock(
        return_value={
            "name": "langchain",
            "owner": "langchain-ai",
            "stars": 75000,
        }
    )
    return tool


@pytest.fixture
def all_mock_tools(
    mock_github_search_code_tool,
    mock_github_get_security_advisories_tool,
    mock_npm_get_package_tool,
    mock_pypi_get_package_tool,
    mock_github_get_repo_tool,
):
    """All mock MCP tools combined."""
    return [
        mock_github_search_code_tool,
        mock_github_get_security_advisories_tool,
        mock_npm_get_package_tool,
        mock_pypi_get_package_tool,
        mock_github_get_repo_tool,
    ]


# ============================================================================
# Server Configuration Fixtures
# ============================================================================


@pytest.fixture
def github_server_config():
    """GitHub MCP server configuration."""
    return MCPServerConfig(
        name="github",
        transport=MCPTransport.STDIO,
        command="npx",
        args=["-y", "@anthropic/mcp-server-github"],
        env={"GITHUB_PERSONAL_ACCESS_TOKEN": "test-token"},
        enabled=True,
        timeout=30.0,
        max_retries=3,
    )


@pytest.fixture
def npm_server_config():
    """Npm MCP server configuration."""
    return MCPServerConfig(
        name="npm",
        transport=MCPTransport.STDIO,
        command="npx",
        args=["-y", "@anthropic/mcp-server-npm"],
        enabled=True,
        timeout=30.0,
        max_retries=3,
    )


@pytest.fixture
def pypi_server_config():
    """PyPI MCP server configuration."""
    return MCPServerConfig(
        name="pypi",
        transport=MCPTransport.STDIO,
        command="uvx",
        args=["mcp-server-pypi"],
        enabled=True,
        timeout=30.0,
        max_retries=3,
    )


@pytest.fixture
def disabled_server_config():
    """Disabled MCP server configuration for testing filtering."""
    return MCPServerConfig(
        name="disabled_server",
        transport=MCPTransport.STDIO,
        command="echo",
        enabled=False,
    )


@pytest.fixture
def all_server_configs(
    github_server_config,
    npm_server_config,
    pypi_server_config,
):
    """All enabled server configurations."""
    return {
        "github": github_server_config,
        "npm": npm_server_config,
        "pypi": pypi_server_config,
    }


@pytest.fixture
def server_configs_with_disabled(
    github_server_config,
    npm_server_config,
    disabled_server_config,
):
    """Server configurations including a disabled server."""
    return {
        "github": github_server_config,
        "npm": npm_server_config,
        "disabled_server": disabled_server_config,
    }


# ============================================================================
# MCPClientPool Fixtures
# ============================================================================


@pytest.fixture
def mcp_pool(all_server_configs):
    """MCPClientPool with real configs but no client initialized."""
    return MCPClientPool(all_server_configs)


@pytest.fixture
def mcp_pool_with_mock_client(all_server_configs, all_mock_tools):
    """MCPClientPool with mocked MultiServerMCPClient.

    This is the primary fixture for integration tests - it uses the real
    MCPClientPool logic but mocks the underlying MCP server communication.
    """
    pool = MCPClientPool(all_server_configs)

    # Create mock client that mimics MultiServerMCPClient behavior
    mock_client = MagicMock()
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=None)
    mock_client.get_tools = MagicMock(return_value=all_mock_tools)
    mock_client.close = AsyncMock()  # Mock close as async

    # Inject the mock client
    pool._client = mock_client

    return pool


@pytest.fixture
def mcp_pool_with_github_only(github_server_config, mock_github_search_code_tool):
    """MCPClientPool with only GitHub server for focused tests."""
    pool = MCPClientPool({"github": github_server_config})

    mock_client = MagicMock()
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=None)
    mock_client.get_tools = MagicMock(return_value=[mock_github_search_code_tool])

    pool._client = mock_client
    return pool


# ============================================================================
# Connection State Fixtures
# ============================================================================


@pytest.fixture
def connected_connection(github_server_config, mock_github_search_code_tool):
    """MCPConnection in CONNECTED state with tools loaded."""
    conn = MCPConnection(
        server_name="github",
        config=github_server_config,
        state=ConnectionState.CONNECTED,
        tools=[mock_github_search_code_tool],
    )
    conn.record_success()
    return conn


@pytest.fixture
def error_connection(github_server_config):
    """MCPConnection in ERROR state after multiple failures."""
    conn = MCPConnection(
        server_name="github",
        config=github_server_config,
        state=ConnectionState.ERROR,
    )
    # Record 3 errors to trigger circuit breaker
    conn.record_error("Connection refused")
    conn.record_error("Connection refused")
    conn.record_error("Connection refused")
    return conn


# ============================================================================
# Failure Simulation Fixtures
# ============================================================================


@pytest.fixture
def failing_pool(all_server_configs):
    """MCPClientPool that fails on tool loading."""
    from app.services.mcp.exceptions import MCPConnectionError

    pool = MCPClientPool(all_server_configs)

    mock_client = MagicMock()
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=None)
    mock_client.get_tools = MagicMock(
        side_effect=MCPConnectionError("Connection refused", server_name="github")
    )

    pool._client = mock_client
    return pool


@pytest.fixture
def intermittent_pool(all_server_configs, all_mock_tools):
    """MCPClientPool that fails once then succeeds (for retry testing)."""
    pool = MCPClientPool(all_server_configs)

    call_count = 0

    def intermittent_get_tools():
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            from app.services.mcp.exceptions import MCPConnectionError

            msg = "Transient failure"
            raise MCPConnectionError(msg, server_name="github")
        return all_mock_tools

    mock_client = MagicMock()
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=None)
    mock_client.get_tools = MagicMock(side_effect=intermittent_get_tools)

    pool._client = mock_client
    return pool


# ============================================================================
# Registry Fixtures
# ============================================================================


@pytest.fixture
def tool_registry():
    """Real ToolRegistry with default agent configurations."""
    from app.services.mcp.registry import ToolRegistry

    return ToolRegistry()


# ============================================================================
# Pytest Markers
# ============================================================================


def pytest_configure(config):
    """Register custom markers for MCP tests."""
    config.addinivalue_line("markers", "mcp: MCP-related tests")
    config.addinivalue_line("markers", "mcp_integration: Full MCP integration flow")
    config.addinivalue_line("markers", "requires_mcp: Tests requiring MCP to be enabled")
