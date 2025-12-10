from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.mcp.client import (
    MAX_CONSECUTIVE_ERRORS,
    ConnectionState,
    MCPClientPool,
    MCPConnection,
)
from app.services.mcp.config import MCPServerConfig, MCPTransport
from app.services.mcp.exceptions import MCPConnectionError


class TestConnectionState:
    def test_connection_state_enum_values(self):
        assert ConnectionState.DISCONNECTED.value == "disconnected"
        assert ConnectionState.CONNECTING.value == "connecting"
        assert ConnectionState.CONNECTED.value == "connected"
        assert ConnectionState.ERROR.value == "error"

    def test_connection_state_enum_members(self):
        assert len(ConnectionState) == 4


class TestMCPConnection:
    @pytest.fixture
    def config(self):
        return MCPServerConfig(
            name="test",
            transport=MCPTransport.STDIO,
            command="test-cmd",
        )

    def test_connection_initial_state(self, config):
        conn = MCPConnection(server_name="test", config=config)

        assert conn.server_name == "test"
        assert conn.config == config
        assert conn.state == ConnectionState.DISCONNECTED
        assert conn.tools == []
        assert conn.last_health_check is None
        assert conn.error_count == 0
        assert conn.last_error is None

    def test_connection_is_healthy_when_connected(self, config):
        conn = MCPConnection(server_name="test", config=config)
        conn.state = ConnectionState.CONNECTED
        conn.error_count = 0

        assert conn.is_healthy() is True

    def test_connection_is_not_healthy_when_disconnected(self, config):
        conn = MCPConnection(server_name="test", config=config)
        conn.state = ConnectionState.DISCONNECTED

        assert conn.is_healthy() is False

    def test_connection_is_not_healthy_with_high_error_count(self, config):
        conn = MCPConnection(server_name="test", config=config)
        conn.state = ConnectionState.CONNECTED
        conn.error_count = MAX_CONSECUTIVE_ERRORS

        assert conn.is_healthy() is False

    def test_connection_record_success(self, config):
        conn = MCPConnection(server_name="test", config=config)
        conn.error_count = 5
        conn.last_error = "Some error"

        conn.record_success()

        assert conn.error_count == 0
        assert conn.last_error is None
        assert conn.last_health_check is not None

    def test_connection_record_error(self, config):
        conn = MCPConnection(server_name="test", config=config)

        conn.record_error("Error 1")
        assert conn.error_count == 1
        assert conn.last_error == "Error 1"
        assert conn.state != ConnectionState.ERROR

    def test_connection_record_error_sets_error_state(self, config):
        conn = MCPConnection(server_name="test", config=config)
        conn.state = ConnectionState.CONNECTED

        for i in range(MAX_CONSECUTIVE_ERRORS):
            conn.record_error(f"Error {i + 1}")

        assert conn.error_count == MAX_CONSECUTIVE_ERRORS
        assert conn.state == ConnectionState.ERROR


class TestMCPClientPool:
    @pytest.fixture
    def server_configs(self):
        return {
            "github": MCPServerConfig(
                name="github",
                transport=MCPTransport.STDIO,
                command="npx",
                args=["-y", "@modelcontextprotocol/server-github"],
                enabled=True,
            ),
            "npm": MCPServerConfig(
                name="npm",
                transport=MCPTransport.STDIO,
                command="npx",
                args=["-y", "mcp-server-npm"],
                enabled=True,
            ),
            "disabled": MCPServerConfig(
                name="disabled",
                transport=MCPTransport.STDIO,
                command="test",
                enabled=False,
            ),
        }

    def test_pool_initialization(self, server_configs):
        pool = MCPClientPool(server_configs)

        assert len(pool._configs) == 2
        assert "github" in pool._configs
        assert "npm" in pool._configs
        assert "disabled" not in pool._configs
        assert pool._client is None
        assert pool._closed is False

    def test_pool_filters_disabled_servers(self, server_configs):
        pool = MCPClientPool(server_configs)
        assert "disabled" not in pool._configs

    def test_pool_get_or_create_connection(self, server_configs):
        pool = MCPClientPool(server_configs)
        conn = pool._get_or_create_connection("github")

        assert conn.server_name == "github"
        assert conn.config == server_configs["github"]
        assert conn.state == ConnectionState.DISCONNECTED

    def test_pool_get_or_create_connection_reuses(self, server_configs):
        pool = MCPClientPool(server_configs)
        conn1 = pool._get_or_create_connection("github")
        conn2 = pool._get_or_create_connection("github")

        assert conn1 is conn2

    def test_pool_get_or_create_connection_unknown_server(self, server_configs):
        pool = MCPClientPool(server_configs)

        with pytest.raises(ValueError, match="Unknown MCP server: unknown"):
            pool._get_or_create_connection("unknown")

    def test_pool_is_closed_property(self, server_configs):
        pool = MCPClientPool(server_configs)
        assert pool.is_closed is False

        pool._closed = True
        assert pool.is_closed is True

    def test_pool_get_connection_status(self, server_configs):
        pool = MCPClientPool(server_configs)
        conn = pool._get_or_create_connection("github")
        conn.state = ConnectionState.CONNECTED
        conn.tools = [MagicMock(name="tool1"), MagicMock(name="tool2")]
        conn.error_count = 1
        conn.last_error = "Test error"
        conn.last_health_check = 123.45

        status = pool.get_connection_status()

        assert "github" in status
        assert status["github"]["state"] == "connected"
        assert status["github"]["tool_count"] == 2
        assert status["github"]["error_count"] == 1
        assert status["github"]["last_error"] == "Test error"
        assert status["github"]["is_healthy"] is True


class TestMCPClientPoolAsync:
    @pytest.fixture
    def mock_client(self):
        mock = MagicMock()
        mock.get_tools = MagicMock(
            return_value=[
                MagicMock(name="github_get_repo"),
                MagicMock(name="github_get_file"),
            ]
        )
        mock.close = AsyncMock()
        mock.__aenter__ = AsyncMock(return_value=mock)
        mock.__aexit__ = AsyncMock()
        return mock

    @pytest.fixture
    def server_configs(self):
        return {
            "github": MCPServerConfig(
                name="github",
                transport=MCPTransport.STDIO,
                command="npx",
                args=["-y", "@modelcontextprotocol/server-github"],
                enabled=True,
            ),
        }

    @pytest.mark.asyncio
    async def test_pool_ensure_client_creates_client(self, server_configs, mock_client):
        pool = MCPClientPool(server_configs)

        with patch("app.services.mcp.client.MultiServerMCPClient") as mock_client_class:
            mock_client_class.return_value = mock_client
            client = await pool._ensure_client()

            assert client is mock_client
            assert pool._client is mock_client
            mock_client_class.assert_called_once()

    @pytest.mark.asyncio
    async def test_pool_ensure_client_reuses_client(self, server_configs, mock_client):
        pool = MCPClientPool(server_configs)
        pool._client = mock_client

        client = await pool._ensure_client()
        assert client is mock_client

    @pytest.mark.asyncio
    async def test_pool_ensure_client_raises_when_closed(self, server_configs):
        pool = MCPClientPool(server_configs)
        pool._closed = True

        with pytest.raises(MCPConnectionError, match="Client pool is closed"):
            await pool._ensure_client()

    @pytest.mark.asyncio
    async def test_pool_ensure_client_handles_creation_error(self, server_configs):
        pool = MCPClientPool(server_configs)

        with patch(
            "app.services.mcp.client.MultiServerMCPClient",
            side_effect=RuntimeError("Creation failed"),
        ):
            with pytest.raises(MCPConnectionError, match="Failed to create MCP client"):
                await pool._ensure_client()

    @pytest.mark.asyncio
    async def test_pool_get_tools_unknown_server(self, server_configs):
        pool = MCPClientPool(server_configs)

        with pytest.raises(ValueError, match="Unknown MCP server: unknown"):
            async with pool.get_tools("unknown"):
                pass

    @pytest.mark.asyncio
    async def test_pool_get_tools_for_capabilities_invalid_format(
        self, server_configs, mock_client
    ):
        pool = MCPClientPool(server_configs)

        with patch("app.services.mcp.client.MultiServerMCPClient") as mock_client_class:
            mock_client_class.return_value = mock_client

            tools = await pool.get_tools_for_capabilities(["invalid_capability_format"])

            assert len(tools) == 0

    @pytest.mark.asyncio
    async def test_pool_get_tools_for_capabilities_unknown_server(
        self, server_configs, mock_client
    ):
        pool = MCPClientPool(server_configs)

        with patch("app.services.mcp.client.MultiServerMCPClient") as mock_client_class:
            mock_client_class.return_value = mock_client

            tools = await pool.get_tools_for_capabilities(["unknown:tool"])

            assert len(tools) == 0

    @pytest.mark.asyncio
    async def test_pool_get_tools_for_capabilities_empty_list(self, server_configs):
        pool = MCPClientPool(server_configs)

        tools = await pool.get_tools_for_capabilities([])
        assert tools == []

    @pytest.mark.asyncio
    async def test_pool_close_cleans_up_resources(self, server_configs, mock_client):
        pool = MCPClientPool(server_configs)
        pool._client = mock_client
        conn = pool._get_or_create_connection("github")
        conn.state = ConnectionState.CONNECTED

        await pool.close()

        assert pool._closed is True
        assert len(pool._connections) == 0
        assert pool._client is None
        mock_client.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_pool_close_handles_client_without_close(self, server_configs):
        pool = MCPClientPool(server_configs)
        # Create mock without close method to test fallback to __aexit__
        mock_client_without_close = MagicMock()
        del mock_client_without_close.close  # Remove close to trigger __aexit__ fallback
        mock_client_without_close.__aexit__ = AsyncMock()
        pool._client = mock_client_without_close

        await pool.close()

        assert pool._closed is True
        mock_client_without_close.__aexit__.assert_called_once()

    @pytest.mark.asyncio
    async def test_pool_close_handles_cleanup_errors(self, server_configs, mock_client):
        pool = MCPClientPool(server_configs)
        mock_client.close.side_effect = RuntimeError("Cleanup failed")
        pool._client = mock_client

        await pool.close()

        assert pool._closed is True
        assert pool._client is None
