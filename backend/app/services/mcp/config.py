"""MCP configuration models and settings.

Defines configuration for MCP servers and their connections.
Supports both stdio (local subprocess) and Streamable HTTP (remote) transports.

Configuration Sources:
    1. Environment variables (MCP_ENABLED, GITHUB_TOKEN, etc.)
    2. Default server configurations
    3. Runtime overrides

Transport Types:
    - STDIO: Local subprocess, spawns MCP server as child process
    - STREAMABLE_HTTP: Remote Streamable HTTP MCP server (MCP spec 2025-03-26)

Note:
    SSE transport was deprecated in MCP spec 2025-03-26 in favor of Streamable HTTP.
    See: https://modelcontextprotocol.io/specification/2025-03-26/basic/transports

Example:
    >>> settings = MCPSettings.from_env()
    >>> if settings.enabled:
    ...     pool = MCPClientPool(settings.servers)

"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from enum import Enum
from functools import lru_cache
from typing import Any


class MCPTransport(Enum):
    """MCP transport types.

    Each transport has different characteristics:
    - STDIO: Low latency, spawns child process, best for local tools
    - STREAMABLE_HTTP: Unified HTTP transport with streaming support (MCP spec 2025-03-26)

    Note:
        SSE was deprecated in MCP spec 2025-03-26. Use STREAMABLE_HTTP instead.
        Streamable HTTP uses a single POST endpoint that can stream responses,
        with support for resumption tokens for reconnection.

    """

    STDIO = "stdio"
    STREAMABLE_HTTP = "streamable-http"


@dataclass
class MCPServerConfig:
    """Configuration for a single MCP server.

    Supports both local (stdio) and remote (Streamable HTTP) servers.

    Attributes:
        name: Unique identifier for the server
        transport: Transport type (stdio or streamable-http)
        enabled: Whether this server is enabled
        command: Command to spawn (stdio only)
        args: Command arguments (stdio only)
        env: Environment variables (stdio only)
        url: Server URL (Streamable HTTP only)
        headers: HTTP headers (Streamable HTTP only)
        timeout: Connection/request timeout in seconds
        max_retries: Maximum retry attempts on failure

    Example:
        >>> config = MCPServerConfig(
        ...     name="github",
        ...     transport=MCPTransport.STDIO,
        ...     command="npx",
        ...     args=["-y", "@modelcontextprotocol/server-github"],
        ...     env={"GITHUB_PERSONAL_ACCESS_TOKEN": "..."},
        ... )

    """

    name: str
    transport: MCPTransport
    enabled: bool = True

    # Stdio transport settings
    command: str | None = None
    args: list[str] = field(default_factory=list)
    env: dict[str, str] = field(default_factory=dict)

    # Streamable HTTP transport settings
    url: str | None = None
    headers: dict[str, str] = field(default_factory=dict)

    # Connection settings
    timeout: float = 30.0
    max_retries: int = 3

    def validate(self) -> None:
        """Validate configuration is complete for transport type.

        Raises:
            MCPConfigurationError: If configuration is invalid

        """
        from app.services.mcp.exceptions import MCPConfigurationError

        if self.transport == MCPTransport.STDIO and not self.command:
            msg = f"stdio transport requires 'command' for server '{self.name}'"
            raise MCPConfigurationError(msg, server_name=self.name)

        if self.transport == MCPTransport.STREAMABLE_HTTP and not self.url:
            msg = f"{self.transport.value} transport requires 'url' for server '{self.name}'"
            raise MCPConfigurationError(msg, server_name=self.name)

    def to_langchain_config(self) -> dict[str, Any]:
        """Convert to langchain-mcp-adapters config format.

        Returns:
            Dictionary compatible with MultiServerMCPClient

        Raises:
            MCPConfigurationError: If configuration is invalid

        """
        self.validate()

        config: dict[str, Any] = {
            "transport": self.transport.value,
        }

        if self.transport == MCPTransport.STDIO:
            config["command"] = self.command
            config["args"] = self.args
            if self.env:
                config["env"] = self.env
        else:
            config["url"] = self.url
            if self.headers:
                config["headers"] = self.headers

        return config


def _create_default_servers() -> dict[str, MCPServerConfig]:
    """Create default MCP server configurations.

    Returns:
        Dictionary of server name to configuration

    Note:
        API keys and tokens should be injected via environment
        variables at runtime, not hardcoded here.

    """
    return {
        "github": MCPServerConfig(
            name="github",
            transport=MCPTransport.STDIO,
            command="npx",
            args=["-y", "@modelcontextprotocol/server-github"],
            env={},  # GITHUB_PERSONAL_ACCESS_TOKEN injected at runtime
            enabled=True,
            timeout=30.0,
        ),
        "npm": MCPServerConfig(
            name="npm",
            transport=MCPTransport.STDIO,
            command="npx",
            args=["-y", "mcp-server-npm"],
            enabled=True,
            timeout=20.0,
        ),
        "pypi": MCPServerConfig(
            name="pypi",
            transport=MCPTransport.STDIO,
            command="uvx",
            args=["mcp-server-pypi"],
            enabled=True,
            timeout=20.0,
        ),
    }


@dataclass
class MCPSettings:
    """Global MCP settings.

    Controls overall MCP functionality and server configurations.

    Attributes:
        enabled: Master switch for MCP functionality
        servers: Dictionary of configured MCP servers
        default_timeout: Default timeout for all operations
        max_concurrent_connections: Max simultaneous MCP connections
        health_check_interval: Seconds between health checks

    Example:
        >>> settings = MCPSettings.from_env()
        >>> if settings.enabled:
        ...     for name, server in settings.servers.items():
        ...         print(f"{name}: {server.transport.value}")

    """

    enabled: bool = True
    servers: dict[str, MCPServerConfig] = field(default_factory=_create_default_servers)
    default_timeout: float = 30.0
    max_concurrent_connections: int = 5
    health_check_interval: float = 60.0

    @classmethod
    def from_env(cls) -> MCPSettings:
        """Load settings from environment variables.

        Environment Variables:
            MCP_ENABLED: Master switch (default: true)
            MCP_DEFAULT_TIMEOUT: Default timeout seconds
            GITHUB_PERSONAL_ACCESS_TOKEN: GitHub API token
            NPM_TOKEN: NPM registry token (optional)

        Returns:
            MCPSettings instance configured from environment

        """
        settings = cls()

        # Master switch
        if os.getenv("MCP_ENABLED", "true").lower() == "false":
            settings.enabled = False

        # Default timeout
        if timeout_str := os.getenv("MCP_DEFAULT_TIMEOUT"):
            try:
                settings.default_timeout = float(timeout_str)
            except ValueError:
                pass

        # Inject GitHub token if available and server is configured
        github_token = os.getenv("GITHUB_PERSONAL_ACCESS_TOKEN")
        if github_token and "github" in settings.servers:
            settings.servers["github"].env["GITHUB_PERSONAL_ACCESS_TOKEN"] = github_token

        # Inject NPM token (optional) if available and server is configured
        npm_token = os.getenv("NPM_TOKEN")
        if npm_token and "npm" in settings.servers:
            settings.servers["npm"].env["NPM_TOKEN"] = npm_token

        return settings

    def get_enabled_servers(self) -> dict[str, MCPServerConfig]:
        """Get only enabled server configurations.

        Returns:
            Dictionary of enabled server name to configuration

        """
        return {name: config for name, config in self.servers.items() if config.enabled}


@lru_cache
def get_mcp_settings() -> MCPSettings:
    """Get cached MCP settings instance.

    Uses LRU cache to avoid reloading configuration.
    Cache should be cleared in tests.

    Returns:
        Cached MCPSettings instance

    """
    return MCPSettings.from_env()
