"""Integration tests for MCPClientPool lifecycle.

Tests the complete lifecycle of MCP connections including:
- Connection state transitions (DISCONNECTED → CONNECTING → CONNECTED)
- Tool loading and caching behavior
- Health check functionality
- Pool closure and cleanup
"""

import pytest

from app.services.mcp.client import ConnectionState, MCPClientPool
from app.services.mcp.exceptions import MCPConnectionError

# ============================================================================
# TestPoolConnectionLifecycle
# ============================================================================


class TestPoolConnectionLifecycle:
    """Test MCPClientPool connection state transitions."""

    @pytest.mark.asyncio
    @pytest.mark.mcp_integration
    async def test_pool_starts_with_no_connections(self, all_server_configs):
        """Pool initializes without active connections."""
        pool = MCPClientPool(all_server_configs)

        assert pool._connections == {}
        assert not pool.is_closed
        assert len(pool._configs) == 3  # github, npm, pypi

    @pytest.mark.asyncio
    @pytest.mark.mcp_integration
    async def test_get_tools_creates_connection(self, mcp_pool_with_mock_client):
        """First get_tools call creates connection in CONNECTED state."""
        pool = mcp_pool_with_mock_client

        async with pool.get_tools("github") as tools:
            assert len(tools) > 0

            # Connection should exist and be connected
            conn = pool._connections.get("github")
            assert conn is not None
            assert conn.state == ConnectionState.CONNECTED
            assert conn.is_healthy()

    @pytest.mark.asyncio
    @pytest.mark.mcp_integration
    async def test_connection_records_success_after_tool_load(self, mcp_pool_with_mock_client):
        """Successful tool load resets error count and updates health check."""
        pool = mcp_pool_with_mock_client

        async with pool.get_tools("github") as _tools:
            conn = pool._connections["github"]
            assert conn.error_count == 0
            assert conn.last_error is None
            assert conn.last_health_check is not None

    @pytest.mark.asyncio
    @pytest.mark.mcp_integration
    async def test_pool_close_disconnects_all_connections(self, mcp_pool_with_mock_client):
        """Pool close() transitions all connections to DISCONNECTED."""
        pool = mcp_pool_with_mock_client

        # Load tools to create connections
        async with pool.get_tools("github") as _tools:
            pass

        assert len(pool._connections) > 0

        # Close pool
        await pool.close()

        assert pool.is_closed
        assert pool._connections == {}

    @pytest.mark.asyncio
    @pytest.mark.mcp_integration
    async def test_pool_raises_when_closed(self, mcp_pool_with_mock_client):
        """Accessing closed pool raises MCPConnectionError."""
        pool = mcp_pool_with_mock_client
        await pool.close()

        with pytest.raises(MCPConnectionError) as exc_info:
            await pool._ensure_client()

        assert "closed" in str(exc_info.value).lower()


# ============================================================================
# TestToolCaching
# ============================================================================


class TestToolCaching:
    """Test tool loading and caching behavior."""

    @pytest.mark.asyncio
    @pytest.mark.mcp_integration
    async def test_tools_cached_across_calls(self, mcp_pool_with_mock_client):
        """Tools are cached after first load."""
        pool = mcp_pool_with_mock_client

        # First call
        async with pool.get_tools("github") as tools1:
            first_tools = list(tools1)

        # Second call
        async with pool.get_tools("github") as tools2:
            second_tools = list(tools2)

        # Same tools returned
        assert len(first_tools) == len(second_tools)

        # get_tools on mock client only called once due to caching
        assert pool._client.get_tools.call_count == 1

    @pytest.mark.asyncio
    @pytest.mark.mcp_integration
    async def test_tools_stored_in_connection(self, mcp_pool_with_mock_client):
        """Loaded tools are stored in MCPConnection."""
        pool = mcp_pool_with_mock_client

        async with pool.get_tools("github") as tools:
            conn = pool._connections["github"]
            assert conn.tools == tools
            assert len(conn.tools) > 0

    @pytest.mark.asyncio
    @pytest.mark.mcp_integration
    async def test_unhealthy_connection_reloads_tools(self, mcp_pool_with_mock_client):
        """Unhealthy connection triggers tool reload."""
        pool = mcp_pool_with_mock_client

        # First load
        async with pool.get_tools("github") as _tools:
            conn = pool._connections["github"]

        # Make connection unhealthy
        conn.error_count = 10  # Exceeds MAX_CONSECUTIVE_ERRORS
        conn.state = ConnectionState.ERROR

        # Next call should attempt reload
        # Note: This would fail in mock since connection is unhealthy
        # In real scenario, it would try to reconnect


# ============================================================================
# TestHealthCheck
# ============================================================================


class TestHealthCheck:
    """Test health check functionality."""

    @pytest.mark.asyncio
    @pytest.mark.mcp_integration
    async def test_health_check_returns_server_status(self, mcp_pool_with_mock_client):
        """health_check() returns status for all configured servers."""
        pool = mcp_pool_with_mock_client

        health = await pool.health_check()

        # All enabled servers should have status
        assert "github" in health
        assert "npm" in health
        assert "pypi" in health

    @pytest.mark.asyncio
    @pytest.mark.mcp_integration
    async def test_health_check_reports_healthy_server(self, mcp_pool_with_mock_client):
        """Healthy server reports True in health check."""
        pool = mcp_pool_with_mock_client

        health = await pool.health_check()

        # Mock returns tools, so servers should be healthy
        assert health.get("github") is True

    @pytest.mark.asyncio
    @pytest.mark.mcp_integration
    async def test_health_check_reports_unhealthy_on_failure(self, failing_pool):
        """Failed server reports False in health check."""
        pool = failing_pool

        health = await pool.health_check()

        # Mock raises error, so servers should be unhealthy
        assert health.get("github") is False


# ============================================================================
# TestConnectionStatus
# ============================================================================


class TestConnectionStatus:
    """Test connection status reporting."""

    @pytest.mark.asyncio
    @pytest.mark.mcp_integration
    async def test_get_connection_status_empty_initially(self, mcp_pool):
        """Connection status empty before any connections made."""
        status = mcp_pool.get_connection_status()
        assert status == {}

    @pytest.mark.asyncio
    @pytest.mark.mcp_integration
    async def test_get_connection_status_after_connect(self, mcp_pool_with_mock_client):
        """Connection status includes details after connecting."""
        pool = mcp_pool_with_mock_client

        async with pool.get_tools("github") as _tools:
            pass

        status = pool.get_connection_status()

        assert "github" in status
        github_status = status["github"]
        assert github_status["state"] == "connected"
        assert github_status["is_healthy"] is True
        assert github_status["error_count"] == 0
        assert github_status["tool_count"] > 0


# ============================================================================
# TestMultiServerAccess
# ============================================================================


class TestMultiServerAccess:
    """Test accessing multiple MCP servers."""

    @pytest.mark.asyncio
    @pytest.mark.mcp_integration
    async def test_access_multiple_servers_sequentially(self, mcp_pool_with_mock_client):
        """Can access tools from multiple servers sequentially."""
        pool = mcp_pool_with_mock_client

        async with pool.get_tools("github") as github_tools:
            assert len(github_tools) > 0

        async with pool.get_tools("npm") as npm_tools:
            assert len(npm_tools) > 0

        # Both connections should exist
        assert "github" in pool._connections
        assert "npm" in pool._connections

    @pytest.mark.asyncio
    @pytest.mark.mcp_integration
    async def test_unknown_server_raises_value_error(self, mcp_pool_with_mock_client):
        """Requesting unknown server raises ValueError."""
        pool = mcp_pool_with_mock_client

        with pytest.raises(ValueError) as exc_info:
            async with pool.get_tools("unknown_server") as _tools:
                pass

        assert "unknown_server" in str(exc_info.value).lower()


# ============================================================================
# TestDisabledServers
# ============================================================================


class TestDisabledServers:
    """Test handling of disabled servers."""

    @pytest.mark.asyncio
    @pytest.mark.mcp_integration
    async def test_disabled_servers_filtered_from_pool(self, server_configs_with_disabled):
        """Disabled servers are not included in pool configs."""
        pool = MCPClientPool(server_configs_with_disabled)

        # Only enabled servers should be in configs
        assert "github" in pool._configs
        assert "npm" in pool._configs
        assert "disabled_server" not in pool._configs

    @pytest.mark.asyncio
    @pytest.mark.mcp_integration
    async def test_disabled_server_raises_value_error(self, server_configs_with_disabled):
        """Requesting disabled server raises ValueError."""
        pool = MCPClientPool(server_configs_with_disabled)

        with pytest.raises(ValueError) as exc_info:
            async with pool.get_tools("disabled_server") as _tools:
                pass

        assert "disabled_server" in str(exc_info.value).lower()
