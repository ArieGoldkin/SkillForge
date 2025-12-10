"""MCP Tool Service for external tool consumption.

This package provides integration with Model Context Protocol (MCP) servers,
enabling SkillForge agents to call external tools during analysis for
real-time data lookup (CVE databases, npm registry, etc.).

Architecture:
    - MCPClientPool: Connection pool for MCP servers with lazy init
    - MCPServerConfig: Configuration for MCP server connections
    - ToolRegistry: Manages which tools each agent can access
    - MCPConnectionError: Exception for connection failures

Example:
    >>> from app.services.mcp import MCPClientPool, get_mcp_settings, ToolRegistry
    >>> settings = get_mcp_settings()
    >>> pool = MCPClientPool(settings.servers)
    >>> registry = ToolRegistry()
    >>> async with pool.get_tools("github") as tools:
    ...     # Filter tools for specific agent
    ...     agent_tools = registry.filter_tools(tools, "security_auditor")
    ...     result = await agent_tools[0].ainvoke({"query": "CVE-2024"})

"""

from app.services.mcp.client import (
    MCP_RETRY_ATTEMPTS,
    MCP_RETRY_MAX_WAIT,
    MCP_RETRY_MIN_WAIT,
    MCP_RETRY_MULTIPLIER,
    MCPClientPool,
    create_mcp_retry_decorator,
    execute_with_timeout,
)
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
from app.services.mcp.registry import (
    AGENT_TOOL_CONFIGS,
    AgentToolConfig,
    ToolCapability,
    ToolRegistry,
)

__all__ = [
    "AGENT_TOOL_CONFIGS",
    "MCP_RETRY_ATTEMPTS",
    "MCP_RETRY_MAX_WAIT",
    "MCP_RETRY_MIN_WAIT",
    "MCP_RETRY_MULTIPLIER",
    "AgentToolConfig",
    "MCPClientPool",
    "MCPConfigurationError",
    "MCPConnectionError",
    "MCPError",
    "MCPServerConfig",
    "MCPSettings",
    "MCPTimeoutError",
    "MCPToolError",
    "MCPTransport",
    "ToolCapability",
    "ToolRegistry",
    "create_mcp_retry_decorator",
    "execute_with_timeout",
    "get_mcp_settings",
]
