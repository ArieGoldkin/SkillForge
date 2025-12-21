import pytest

from app.shared.services.mcp.config import (
    MCPServerConfig,
    MCPSettings,
    MCPTransport,
    get_mcp_settings,
)
from app.shared.services.mcp.exceptions import MCPConfigurationError


@pytest.mark.unit
class TestMCPTransport:
    def test_transport_enum_values(self):
        assert MCPTransport.STDIO.value == "stdio"
        assert MCPTransport.STREAMABLE_HTTP.value == "streamable-http"

    def test_transport_enum_members(self):
        assert len(MCPTransport) == 2


class TestMCPServerConfig:
    def test_server_config_defaults(self):
        config = MCPServerConfig(
            name="test",
            transport=MCPTransport.STDIO,
            command="test-cmd",
        )
        assert config.name == "test"
        assert config.transport == MCPTransport.STDIO
        assert config.enabled is True
        assert config.args == []
        assert config.env == {}
        assert config.timeout == 30.0
        assert config.max_retries == 3

    def test_server_config_stdio_with_command(self):
        config = MCPServerConfig(
            name="github",
            transport=MCPTransport.STDIO,
            command="npx",
            args=["-y", "@modelcontextprotocol/server-github"],
        )
        config.validate()

    def test_server_config_stdio_without_command_raises_error(self):
        config = MCPServerConfig(
            name="github",
            transport=MCPTransport.STDIO,
        )
        with pytest.raises(
            MCPConfigurationError,
            match="stdio transport requires 'command' for server 'github'",
        ):
            config.validate()

    def test_server_config_streamable_http_with_url(self):
        config = MCPServerConfig(
            name="remote",
            transport=MCPTransport.STREAMABLE_HTTP,
            url="https://api.example.com/mcp",
        )
        config.validate()

    def test_server_config_streamable_http_without_url_raises_error(self):
        config = MCPServerConfig(
            name="remote",
            transport=MCPTransport.STREAMABLE_HTTP,
        )
        with pytest.raises(
            MCPConfigurationError,
            match="streamable-http transport requires 'url' for server 'remote'",
        ):
            config.validate()

    def test_server_config_to_langchain_config_stdio(self):
        config = MCPServerConfig(
            name="github",
            transport=MCPTransport.STDIO,
            command="npx",
            args=["-y", "@modelcontextprotocol/server-github"],
            env={"GITHUB_TOKEN": "test-token"},
        )
        lc_config = config.to_langchain_config()

        assert lc_config["transport"] == "stdio"
        assert lc_config["command"] == "npx"
        assert lc_config["args"] == ["-y", "@modelcontextprotocol/server-github"]
        assert lc_config["env"] == {"GITHUB_TOKEN": "test-token"}

    def test_server_config_to_langchain_config_stdio_without_env(self):
        config = MCPServerConfig(
            name="npm",
            transport=MCPTransport.STDIO,
            command="npx",
            args=["-y", "mcp-server-npm"],
        )
        lc_config = config.to_langchain_config()

        assert lc_config["transport"] == "stdio"
        assert "env" not in lc_config

    def test_server_config_to_langchain_config_streamable_http(self):
        config = MCPServerConfig(
            name="remote",
            transport=MCPTransport.STREAMABLE_HTTP,
            url="https://api.example.com/mcp",
            headers={"Authorization": "Bearer token"},
        )
        lc_config = config.to_langchain_config()

        assert lc_config["transport"] == "streamable-http"
        assert lc_config["url"] == "https://api.example.com/mcp"
        assert lc_config["headers"] == {"Authorization": "Bearer token"}


class TestMCPSettings:
    def test_settings_defaults(self):
        settings = MCPSettings()
        assert settings.enabled is True
        assert isinstance(settings.servers, dict)
        assert len(settings.servers) >= 3
        assert "github" in settings.servers
        assert "npm" in settings.servers
        assert "pypi" in settings.servers
        assert settings.default_timeout == 30.0

    def test_settings_from_env_master_switch_disabled(self, monkeypatch):
        monkeypatch.setenv("MCP_ENABLED", "false")
        settings = MCPSettings.from_env()
        assert settings.enabled is False

    def test_settings_from_env_default_timeout(self, monkeypatch):
        monkeypatch.setenv("MCP_DEFAULT_TIMEOUT", "45.5")
        settings = MCPSettings.from_env()
        assert settings.default_timeout == 45.5

    def test_settings_from_env_invalid_timeout_uses_default(self, monkeypatch):
        monkeypatch.setenv("MCP_DEFAULT_TIMEOUT", "invalid")
        settings = MCPSettings.from_env()
        assert settings.default_timeout == 30.0

    def test_settings_from_env_github_token_injection(self, monkeypatch):
        monkeypatch.setenv("GITHUB_PERSONAL_ACCESS_TOKEN", "ghp_test123")
        settings = MCPSettings.from_env()
        assert settings.servers["github"].env["GITHUB_PERSONAL_ACCESS_TOKEN"] == "ghp_test123"

    def test_settings_from_env_npm_token_injection(self, monkeypatch):
        monkeypatch.setenv("NPM_TOKEN", "npm_test456")
        settings = MCPSettings.from_env()
        assert settings.servers["npm"].env["NPM_TOKEN"] == "npm_test456"

    def test_get_enabled_servers_all_enabled(self):
        """Test that get_enabled_servers returns only enabled servers.

        Note: Default config has only github enabled (npm/pypi disabled).
        """
        settings = MCPSettings()
        enabled = settings.get_enabled_servers()
        # Only github is enabled by default
        assert len(enabled) >= 1
        assert "github" in enabled
        assert all(config.enabled for config in enabled.values())

    def test_get_enabled_servers_some_disabled(self):
        """Test that disabling a server removes it from get_enabled_servers."""
        settings = MCPSettings()
        # Enable npm first so we can test disabling github
        settings.servers["npm"].enabled = True
        settings.servers["github"].enabled = False
        enabled = settings.get_enabled_servers()
        assert "github" not in enabled
        assert "npm" in enabled


class TestGetMCPSettings:
    def test_get_mcp_settings_caching(self):
        get_mcp_settings.cache_clear()
        settings1 = get_mcp_settings()
        settings2 = get_mcp_settings()
        assert settings1 is settings2
        get_mcp_settings.cache_clear()

    def test_get_mcp_settings_cache_clear(self):
        get_mcp_settings.cache_clear()
        settings1 = get_mcp_settings()
        get_mcp_settings.cache_clear()
        settings2 = get_mcp_settings()
        assert settings1 is not settings2
        get_mcp_settings.cache_clear()
