"""MCP Tool Service for external tool consumption.

This package provides integration with Model Context Protocol (MCP) servers,
enabling SkillForge agents to call external tools during analysis for
real-time data lookup (CVE databases, npm registry, etc.).

Architecture:
    - MCPClientPool: Connection pool for MCP servers with lazy init
    - MCPServerConfig: Configuration for MCP server connections
    - MCPCallbacks: Real-time callbacks for tool execution (Langfuse, SSE, logging)
    - ToolRegistry: Manages which tools each agent can access
    - MCPConnectionError: Exception for connection failures

Example:
    >>> from app.shared.services.mcp import MCPClientPool, get_mcp_settings, ToolRegistry
    >>> settings = get_mcp_settings()
    >>> pool = MCPClientPool(settings.servers)
    >>> registry = ToolRegistry()
    >>> async with pool.get_tools("github") as tools:
    ...     # Filter tools for specific agent
    ...     agent_tools = registry.filter_tools(tools, "security_auditor")
    ...     result = await agent_tools[0].ainvoke({"query": "CVE-2024"})

"""

from app.shared.services.mcp.batch import (
    MAX_BATCH_SIZE,
    ActionableError,
    BatchResult,
    FailedItem,
    PackageInfo,
    SuccessItem,
    VulnerabilityInfo,
    batch_check_dependencies,
    batch_check_vulnerabilities,
    execute_batch,
)
from app.shared.services.mcp.callbacks import (
    MCPCallbacks,
    create_mcp_callbacks,
)
from app.shared.services.mcp.client import (
    MCP_RETRY_ATTEMPTS,
    MCP_RETRY_MAX_WAIT,
    MCP_RETRY_MIN_WAIT,
    MCP_RETRY_MULTIPLIER,
    MCPClientPool,
    create_mcp_retry_decorator,
    execute_with_timeout,
)
from app.shared.services.mcp.config import (
    MCPServerConfig,
    MCPSettings,
    MCPTransport,
    get_mcp_settings,
)
from app.shared.services.mcp.exceptions import (
    MCPConfigurationError,
    MCPConnectionError,
    MCPError,
    MCPTimeoutError,
    MCPToolError,
)
from app.shared.services.mcp.interceptors import (
    AuthInterceptor,
    InterceptorConfig,
    LoggingInterceptor,
    ResultEnrichmentInterceptor,
    RetryInterceptor,
    create_default_interceptors,
)
from app.shared.services.mcp.registry import (
    AGENT_TOOL_CONFIGS,
    ARTIFACT_LOAD_CAPABILITY,
    AgentToolConfig,
    ToolCapability,
    ToolRegistry,
)

__all__ = [
    "AGENT_TOOL_CONFIGS",
    "ARTIFACT_LOAD_CAPABILITY",
    "MAX_BATCH_SIZE",
    "MCP_RETRY_ATTEMPTS",
    "MCP_RETRY_MAX_WAIT",
    "MCP_RETRY_MIN_WAIT",
    "MCP_RETRY_MULTIPLIER",
    "ActionableError",
    "AgentToolConfig",
    "AuthInterceptor",
    "BatchResult",
    "FailedItem",
    "InterceptorConfig",
    "LoggingInterceptor",
    "MCPCallbacks",
    "MCPClientPool",
    "MCPConfigurationError",
    "MCPConnectionError",
    "MCPError",
    "MCPServerConfig",
    "MCPSettings",
    "MCPTimeoutError",
    "MCPToolError",
    "MCPTransport",
    "PackageInfo",
    "ResultEnrichmentInterceptor",
    "RetryInterceptor",
    "SuccessItem",
    "ToolCapability",
    "ToolRegistry",
    "VulnerabilityInfo",
    "batch_check_dependencies",
    "batch_check_vulnerabilities",
    "create_default_interceptors",
    "create_mcp_callbacks",
    "create_mcp_retry_decorator",
    "execute_batch",
    "execute_with_timeout",
    "get_mcp_settings",
]
