"""MCP Tool Service for external tool consumption.

This package provides integration with Model Context Protocol (MCP) servers,
enabling SkillForge agents to call external tools during analysis for
real-time data lookup (CVE databases, npm registry, etc.).

Architecture:
    - MCPClientPool: Connection pool for MCP servers with lazy init
    - MCPServerConfig: Configuration for MCP server connections
    - MCPConnectionError: Exception for connection failures

Example:
    >>> from app.services.mcp import MCPClientPool, get_mcp_settings
    >>> settings = get_mcp_settings()
    >>> pool = MCPClientPool(settings.servers)
    >>> async with pool.get_tools("github") as tools:
    ...     result = await tools[0].ainvoke({"repo": "langchain-ai/langchain"})

"""

from app.services.mcp.client import MCPClientPool
from app.services.mcp.config import (
    MCPServerConfig,
    MCPSettings,
    MCPTransport,
    get_mcp_settings,
)
from app.services.mcp.exceptions import (
    MCPConfigurationError,
    MCPConnectionError,
    MCPError,
    MCPTimeoutError,
    MCPToolError,
)

__all__ = [
    "MCPClientPool",
    "MCPConfigurationError",
    "MCPConnectionError",
    "MCPError",
    "MCPServerConfig",
    "MCPSettings",
    "MCPTimeoutError",
    "MCPToolError",
    "MCPTransport",
    "get_mcp_settings",
]
