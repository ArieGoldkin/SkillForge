# MCP Tool Service Architecture Design

> **Version**: 1.0.0
> **Date**: December 2025
> **Status**: Draft
> **Author**: SkillForge Team

## Executive Summary

This document defines the architecture for integrating Model Context Protocol (MCP) tools into SkillForge's LangGraph-based analysis pipeline. The design enables agents to call external tools during analysis, grounding their outputs in real-time data rather than relying solely on LLM reasoning.

## Table of Contents

1. [Architecture Overview](#architecture-overview)
2. [Key Design Decisions](#key-design-decisions)
3. [Component Architecture](#component-architecture)
4. [MCP Client Service](#mcp-client-service)
5. [Tool Registry](#tool-registry)
6. [Agent Integration](#agent-integration)
7. [Configuration System](#configuration-system)
8. [Error Handling & Resilience](#error-handling--resilience)
9. [Observability](#observability)
10. [Security Considerations](#security-considerations)
11. [Implementation Roadmap](#implementation-roadmap)

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                           SkillForge Analysis Pipeline                          │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                  │
│  ┌──────────────────────────────────────────────────────────────────────────┐   │
│  │                        LangGraph StateGraph                              │   │
│  │  ┌─────────┐    ┌───────────┐    ┌─────────────────────────────────┐    │   │
│  │  │ Extract │───►│ Supervisor │───►│      8 Analysis Agents          │    │   │
│  │  └─────────┘    └───────────┘    │  ┌─────────────────────────────┐ │    │   │
│  │                                   │  │ security_auditor            │ │    │   │
│  │                                   │  │ dependency_mapper           │ │    │   │
│  │                                   │  │ tech_comparator             │ │    │   │
│  │                                   │  │ implementation_planner      │ │    │   │
│  │                                   │  │ ...                         │ │    │   │
│  │                                   │  └──────────┬──────────────────┘ │    │   │
│  │                                   └─────────────┼─────────────────────┘    │   │
│  └─────────────────────────────────────────────────┼────────────────────────┘   │
│                                                     │                            │
│                                                     ▼                            │
│  ┌──────────────────────────────────────────────────────────────────────────┐   │
│  │                     MCP Tool Service Layer (NEW)                         │   │
│  │  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐          │   │
│  │  │  MCPClientPool  │  │  ToolRegistry   │  │ ToolExecutor    │          │   │
│  │  │                 │  │                 │  │                 │          │   │
│  │  │ • Connection    │  │ • Tool manifest │  │ • Timeout mgmt  │          │   │
│  │  │   management    │  │ • Capability    │  │ • Retry logic   │          │   │
│  │  │ • Health checks │  │   matching      │  │ • Result parse  │          │   │
│  │  │ • Load balance  │  │ • Agent→tool    │  │ • Metrics       │          │   │
│  │  └────────┬────────┘  └────────┬────────┘  └────────┬────────┘          │   │
│  │           │                    │                    │                    │   │
│  │           └────────────────────┼────────────────────┘                    │   │
│  │                                ▼                                         │   │
│  │                    ┌───────────────────────┐                             │   │
│  │                    │   LangChain Tools     │                             │   │
│  │                    │   (MCP Adapters)      │                             │   │
│  │                    └───────────┬───────────┘                             │   │
│  └────────────────────────────────┼─────────────────────────────────────────┘   │
│                                   │                                              │
└───────────────────────────────────┼──────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│                           External MCP Servers                                   │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐         │
│  │   GitHub     │  │ NPM Registry │  │ CVE Database │  │  PyPI        │         │
│  │   MCP        │  │    MCP       │  │     MCP      │  │   MCP        │         │
│  │              │  │              │  │              │  │              │         │
│  │ • get_repo   │  │ • get_pkg    │  │ • search_cve │  │ • get_pkg    │         │
│  │ • get_file   │  │ • get_vers   │  │ • get_cve    │  │ • get_vers   │         │
│  │ • list_issues│  │ • get_deps   │  │ • get_cwes   │  │ • get_deps   │         │
│  └──────────────┘  └──────────────┘  └──────────────┘  └──────────────┘         │
│                                                                                  │
│  Transport: stdio (local) | HTTP/SSE (remote)                                   │
│  Protocol: MCP 2025-03-26 (JSON-RPC 2.0)                                        │
└─────────────────────────────────────────────────────────────────────────────────┘
```

---

## Key Design Decisions

### ADR-001: Use `langchain-mcp-adapters` for MCP Integration

**Context**: Need to integrate MCP tools with existing LangChain/LangGraph agents.

**Decision**: Use official `langchain-mcp-adapters` library (v0.2.1+).

**Rationale**:
- Official LangChain support (released March 2025)
- Converts MCP tools to LangChain `BaseTool` automatically
- Supports `MultiServerMCPClient` for multiple MCP connections
- Works with LangGraph's `ToolNode` out of the box
- Handles both stdio and HTTP transports

**Consequences**:
- Requires Python 3.11+
- MCP tools appear as regular LangChain tools to agents
- Tool conversion is automatic via `load_mcp_tools()`

---

### ADR-002: Tool-Enabled vs Tool-Free Agents

**Context**: Currently agents use `ToolStrategy` for structured output without tool calling.

**Decision**: Create a dual-mode agent system:
- **Structured-only agents**: Current approach (fast, deterministic)
- **Tool-enabled agents**: New approach for agents that benefit from real-time data

**Rationale**:
- Not all agents need external tools (e.g., `trend_validator` works fine with LLM knowledge)
- Security-sensitive agents like `security_auditor` and `dependency_mapper` benefit most
- Tool calling adds latency (~200-500ms per call)
- Gradual rollout allows A/B comparison

**Agent Tool Requirements**:

| Agent | Tool-Enabled | Primary MCP Tools |
|-------|--------------|-------------------|
| `security_auditor` | ✅ Yes | `cve-database`, `github` |
| `dependency_mapper` | ✅ Yes | `npm-registry`, `pypi`, `github` |
| `tech_comparator` | ✅ Optional | `npm-registry`, `github` |
| `implementation_planner` | ❌ No | N/A |
| `performance_analyst` | ❌ No | N/A |
| `code_quality_critic` | ✅ Optional | `github` (for commit history) |
| `trend_validator` | ❌ No | N/A |
| `integration_feasibility` | ❌ No | N/A |

---

### ADR-003: Connection Lifecycle Management

**Context**: MCP connections can be expensive (especially stdio which spawns processes).

**Decision**: Implement connection pooling with lazy initialization.

**Rationale**:
- HTTP connections are cheap, but stdio spawns child processes
- LangGraph API Server warning: "stdio transport spawns child processes"
- Production should prefer HTTP/SSE transports
- Pool connections per MCP server, reuse across requests

**Implementation**:
```python
# Connection is established on first tool use, not at startup
async with mcp_client_pool.get_connection("github") as conn:
    tools = await load_mcp_tools(conn)
```

---

### ADR-004: Tool Selection Strategy

**Context**: Agents shouldn't have access to ALL tools (confusion, token overhead).

**Decision**: Implement capability-based tool filtering per agent.

**Rationale**:
- Each agent has specific tool needs
- Too many tools confuse LLMs (Anthropic recommends 2-5 tools)
- Tool schemas add to context size (~100-200 tokens each)
- Filter tools at agent creation time, not runtime

**Implementation**:
```python
AGENT_TOOL_CAPABILITIES = {
    "security_auditor": ["cve:search", "cve:get", "github:security_advisories"],
    "dependency_mapper": ["npm:get_package", "npm:get_versions", "pypi:get_package"],
}
```

---

## Component Architecture

### Directory Structure

```
backend/app/
├── services/
│   └── mcp/                          # NEW: MCP Tool Service
│       ├── __init__.py
│       ├── client.py                 # MCPClientPool - connection management
│       ├── registry.py               # ToolRegistry - tool manifest & capabilities
│       ├── executor.py               # ToolExecutor - execution with retries
│       ├── config.py                 # MCP configuration models
│       └── tools/                    # Tool-specific adapters (optional)
│           ├── __init__.py
│           ├── github.py             # GitHub-specific tool wrappers
│           ├── npm.py                # NPM registry tools
│           └── security.py           # CVE/security tools
│
├── workflows/
│   └── agents/
│       ├── base.py                   # Updated: add tool-enabled agent factory
│       ├── tool_config.py            # NEW: Agent→tool capability mapping
│       └── security_auditor.py       # Updated: use tools
│
├── core/
│   └── mcp_config.py                 # NEW: MCP settings in app config
│
└── tests/
    └── unit/
        └── services/
            └── mcp/                  # MCP service tests
                ├── test_client.py
                ├── test_registry.py
                └── test_executor.py
```

---

## MCP Client Service

### MCPClientPool (`services/mcp/client.py`)

```python
"""MCP Client Pool for managing connections to MCP servers.

Uses langchain-mcp-adapters for protocol handling with added:
- Connection pooling and lifecycle management
- Health checks and automatic reconnection
- Graceful degradation when servers unavailable
"""

from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from enum import Enum
from typing import TYPE_CHECKING

from langchain_mcp_adapters.client import MultiServerMCPClient
from langchain_core.tools import BaseTool

from app.core.logging import get_logger
from app.services.mcp.config import MCPServerConfig

if TYPE_CHECKING:
    from collections.abc import AsyncIterator

logger = get_logger(__name__)


class ConnectionState(Enum):
    """MCP connection states."""
    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    ERROR = "error"


@dataclass
class MCPConnection:
    """Wrapper for MCP server connection with state tracking."""

    server_name: str
    config: MCPServerConfig
    state: ConnectionState = ConnectionState.DISCONNECTED
    tools: list[BaseTool] = field(default_factory=list)
    last_health_check: float | None = None
    error_count: int = 0

    def is_healthy(self) -> bool:
        """Check if connection is healthy and usable."""
        return self.state == ConnectionState.CONNECTED and self.error_count < 3


class MCPClientPool:
    """Connection pool for MCP servers.

    Manages connections to multiple MCP servers with:
    - Lazy initialization (connect on first use)
    - Connection reuse across requests
    - Health monitoring and automatic recovery
    - Graceful degradation when servers fail

    Example:
        >>> pool = MCPClientPool(config)
        >>> async with pool.get_tools("github") as tools:
        ...     # tools is list[BaseTool] from GitHub MCP
        ...     result = await tools[0].ainvoke({"repo": "langchain-ai/langchain"})
    """

    def __init__(self, server_configs: dict[str, MCPServerConfig]):
        """Initialize pool with server configurations.

        Args:
            server_configs: Mapping of server names to their configurations
        """
        self._configs = server_configs
        self._connections: dict[str, MCPConnection] = {}
        self._lock = asyncio.Lock()
        self._client: MultiServerMCPClient | None = None

    async def _ensure_client(self) -> MultiServerMCPClient:
        """Lazily create the MCP client."""
        if self._client is None:
            # Convert our config to langchain-mcp-adapters format
            client_config = {}
            for name, cfg in self._configs.items():
                client_config[name] = cfg.to_langchain_config()

            self._client = MultiServerMCPClient(client_config)
            logger.info(
                "mcp_client_initialized",
                servers=list(self._configs.keys()),
            )
        return self._client

    @asynccontextmanager
    async def get_tools(
        self,
        server_name: str,
    ) -> AsyncIterator[list[BaseTool]]:
        """Get tools from an MCP server.

        Context manager that provides tools from the specified server.
        Handles connection management and error recovery.

        Args:
            server_name: Name of the MCP server to connect to

        Yields:
            List of LangChain-compatible tools from the server

        Raises:
            MCPConnectionError: If server is unavailable after retries
        """
        async with self._lock:
            if server_name not in self._configs:
                raise ValueError(f"Unknown MCP server: {server_name}")

            # Get or create connection
            if server_name not in self._connections:
                self._connections[server_name] = MCPConnection(
                    server_name=server_name,
                    config=self._configs[server_name],
                )

            conn = self._connections[server_name]

        try:
            # Load tools if not already loaded
            if not conn.tools or not conn.is_healthy():
                client = await self._ensure_client()
                conn.state = ConnectionState.CONNECTING

                try:
                    conn.tools = await client.get_tools(servers=[server_name])
                    conn.state = ConnectionState.CONNECTED
                    conn.error_count = 0

                    logger.info(
                        "mcp_tools_loaded",
                        server=server_name,
                        tool_count=len(conn.tools),
                        tools=[t.name for t in conn.tools],
                    )
                except Exception as e:
                    conn.state = ConnectionState.ERROR
                    conn.error_count += 1
                    logger.error(
                        "mcp_connection_failed",
                        server=server_name,
                        error=str(e),
                        error_count=conn.error_count,
                    )
                    raise MCPConnectionError(
                        f"Failed to connect to MCP server {server_name}: {e}"
                    ) from e

            yield conn.tools

        except Exception:
            conn.error_count += 1
            raise

    async def get_tools_for_capabilities(
        self,
        capabilities: list[str],
    ) -> list[BaseTool]:
        """Get tools matching specified capabilities.

        Args:
            capabilities: List of capability strings (e.g., ["github:get_repo", "npm:get_package"])

        Returns:
            List of tools matching any of the specified capabilities
        """
        all_tools: list[BaseTool] = []

        # Group capabilities by server
        server_caps: dict[str, list[str]] = {}
        for cap in capabilities:
            server, _, tool = cap.partition(":")
            if server not in server_caps:
                server_caps[server] = []
            if tool:
                server_caps[server].append(tool)

        # Load tools from each required server
        for server_name, tool_names in server_caps.items():
            if server_name not in self._configs:
                logger.warning(
                    "mcp_server_not_configured",
                    server=server_name,
                    requested_tools=tool_names,
                )
                continue

            async with self.get_tools(server_name) as tools:
                if tool_names:
                    # Filter to specific tools
                    filtered = [t for t in tools if t.name in tool_names]
                    all_tools.extend(filtered)
                else:
                    # No filter, include all
                    all_tools.extend(tools)

        return all_tools

    async def health_check(self) -> dict[str, bool]:
        """Check health of all configured servers.

        Returns:
            Mapping of server names to health status
        """
        results = {}
        for name in self._configs:
            try:
                async with self.get_tools(name) as tools:
                    results[name] = len(tools) > 0
            except Exception:
                results[name] = False
        return results

    async def close(self) -> None:
        """Close all connections and cleanup resources."""
        self._connections.clear()
        self._client = None
        logger.info("mcp_client_pool_closed")


class MCPConnectionError(Exception):
    """Raised when MCP server connection fails."""
    pass
```

---

## Tool Registry

### ToolRegistry (`services/mcp/registry.py`)

```python
"""Tool Registry for managing MCP tool capabilities and agent mappings.

Provides:
- Tool capability manifest
- Agent-to-tool capability mapping
- Tool filtering and selection
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from langchain_core.tools import BaseTool

from app.core.logging import get_logger

if TYPE_CHECKING:
    pass

logger = get_logger(__name__)


@dataclass
class ToolCapability:
    """Describes a tool capability for registry."""

    server: str           # MCP server name (e.g., "github")
    tool_name: str        # Tool name within server (e.g., "get_repo")
    description: str      # Human-readable description
    use_cases: list[str]  # When to use this tool

    @property
    def capability_id(self) -> str:
        """Return canonical capability ID."""
        return f"{self.server}:{self.tool_name}"


@dataclass
class AgentToolConfig:
    """Tool configuration for a specific agent."""

    agent_type: str
    enabled: bool = True
    capabilities: list[str] = field(default_factory=list)
    max_tool_calls: int = 5  # Max tool calls per agent invocation
    tool_timeout: float = 10.0  # Timeout per tool call (seconds)


# Agent-to-capability mapping
# This defines which tools each agent can access
AGENT_TOOL_CONFIGS: dict[str, AgentToolConfig] = {
    "security_auditor": AgentToolConfig(
        agent_type="security_auditor",
        enabled=True,
        capabilities=[
            "cve:search_cves",
            "cve:get_cve_details",
            "github:get_security_advisories",
            "github:get_dependabot_alerts",
        ],
        max_tool_calls=10,  # Security needs more lookups
        tool_timeout=15.0,
    ),
    "dependency_mapper": AgentToolConfig(
        agent_type="dependency_mapper",
        enabled=True,
        capabilities=[
            "npm:get_package",
            "npm:get_package_versions",
            "npm:get_dependencies",
            "pypi:get_package",
            "pypi:get_package_versions",
            "github:get_repo_dependencies",
        ],
        max_tool_calls=15,  # May need many package lookups
        tool_timeout=10.0,
    ),
    "tech_comparator": AgentToolConfig(
        agent_type="tech_comparator",
        enabled=False,  # Optional, disabled by default
        capabilities=[
            "npm:get_package",
            "github:get_repo_stats",
        ],
        max_tool_calls=5,
    ),
    "code_quality_critic": AgentToolConfig(
        agent_type="code_quality_critic",
        enabled=False,  # Optional
        capabilities=[
            "github:get_commit_history",
            "github:get_pull_requests",
        ],
        max_tool_calls=3,
    ),
    # Agents that don't need tools
    "implementation_planner": AgentToolConfig(
        agent_type="implementation_planner",
        enabled=False,
        capabilities=[],
    ),
    "performance_analyst": AgentToolConfig(
        agent_type="performance_analyst",
        enabled=False,
        capabilities=[],
    ),
    "trend_validator": AgentToolConfig(
        agent_type="trend_validator",
        enabled=False,
        capabilities=[],
    ),
    "integration_feasibility": AgentToolConfig(
        agent_type="integration_feasibility",
        enabled=False,
        capabilities=[],
    ),
}


class ToolRegistry:
    """Registry for managing tool capabilities and agent access.

    Maintains the mapping between agents and their allowed tools,
    providing filtered tool access based on agent type.

    Example:
        >>> registry = ToolRegistry()
        >>> config = registry.get_agent_config("security_auditor")
        >>> print(config.capabilities)
        ['cve:search_cves', 'cve:get_cve_details', ...]
    """

    def __init__(
        self,
        agent_configs: dict[str, AgentToolConfig] | None = None,
    ):
        """Initialize registry with agent configurations.

        Args:
            agent_configs: Custom agent configurations. Uses defaults if None.
        """
        self._configs = agent_configs or AGENT_TOOL_CONFIGS.copy()

    def get_agent_config(self, agent_type: str) -> AgentToolConfig:
        """Get tool configuration for an agent.

        Args:
            agent_type: Type of agent (e.g., "security_auditor")

        Returns:
            AgentToolConfig for the agent

        Raises:
            ValueError: If agent type is not registered
        """
        if agent_type not in self._configs:
            raise ValueError(f"Unknown agent type: {agent_type}")
        return self._configs[agent_type]

    def is_tool_enabled(self, agent_type: str) -> bool:
        """Check if tools are enabled for an agent.

        Args:
            agent_type: Type of agent

        Returns:
            True if agent has tools enabled
        """
        config = self._configs.get(agent_type)
        return config is not None and config.enabled and len(config.capabilities) > 0

    def get_capabilities(self, agent_type: str) -> list[str]:
        """Get list of capabilities for an agent.

        Args:
            agent_type: Type of agent

        Returns:
            List of capability IDs
        """
        config = self._configs.get(agent_type)
        if config is None or not config.enabled:
            return []
        return config.capabilities.copy()

    def filter_tools(
        self,
        tools: list[BaseTool],
        agent_type: str,
    ) -> list[BaseTool]:
        """Filter tools to only those allowed for an agent.

        Args:
            tools: List of all available tools
            agent_type: Agent type to filter for

        Returns:
            Filtered list of tools the agent can use
        """
        capabilities = self.get_capabilities(agent_type)
        if not capabilities:
            return []

        # Extract tool names from capabilities (server:tool_name -> tool_name)
        allowed_names = {cap.split(":", 1)[1] for cap in capabilities if ":" in cap}

        filtered = [t for t in tools if t.name in allowed_names]

        logger.debug(
            "tools_filtered_for_agent",
            agent_type=agent_type,
            original_count=len(tools),
            filtered_count=len(filtered),
            allowed_tools=[t.name for t in filtered],
        )

        return filtered

    def register_agent(self, config: AgentToolConfig) -> None:
        """Register or update an agent's tool configuration.

        Args:
            config: Agent tool configuration
        """
        self._configs[config.agent_type] = config
        logger.info(
            "agent_tool_config_registered",
            agent_type=config.agent_type,
            enabled=config.enabled,
            capability_count=len(config.capabilities),
        )
```

---

## Agent Integration

### Updated `create_structured_agent` (`workflows/agents/base.py`)

```python
"""Base utilities for agent implementation - UPDATED with MCP tool support.

This module provides shared functionality for all specialized analysis agents,
including agent creation with structured output, database persistence, and
SSE event emission.

NEW: Adds tool-enabled agent factory for MCP integration.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import TYPE_CHECKING, cast

from langchain.agents import create_agent
from langchain.agents.structured_output import ToolStrategy
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.runnables import Runnable
from langchain_core.tools import BaseTool
from pydantic import BaseModel

from app.core.agent_config import get_stage_name
from app.core.logging import get_logger
from app.core.model_factory import get_chat_model
from app.services.sse_helpers import emit_streaming_event

if TYPE_CHECKING:
    from uuid import UUID

    from sqlalchemy.ext.asyncio import AsyncSession

    from app.core.types import AnalysisID
    from app.models.agent_finding import AgentFinding

logger = get_logger(__name__)


def create_structured_agent(
    system_prompt: str,
    response_schema: type[BaseModel],
    tools: Sequence[BaseTool] | None = None,
) -> Runnable:
    """Create an agent with structured output using ToolStrategy.

    Args:
        system_prompt: System prompt for the agent
        response_schema: Pydantic model defining the expected output structure
        tools: Optional list of tools for the agent

    Returns:
        Configured agent instance with structured output support

    Note:
        ToolStrategy automatically validates output against response_schema.
        Validation errors are automatically traced by LangSmith when they occur.
    """
    model = get_chat_model()
    # Prevent multiple parallel tool calls; we expect exactly one structured response
    bound_model: Runnable = model.bind_tools(tools or [], parallel_tool_calls=False)
    agent = create_agent(
        cast(BaseChatModel, bound_model),
        tools=tools or [],
        system_prompt=system_prompt,
        response_format=ToolStrategy(response_schema),
    )
    return agent


def create_tool_enabled_agent(
    system_prompt: str,
    response_schema: type[BaseModel],
    mcp_tools: Sequence[BaseTool],
    max_tool_calls: int = 5,
) -> Runnable:
    """Create an agent that can call MCP tools during reasoning.

    Unlike create_structured_agent which uses ToolStrategy for output-only tools,
    this factory creates an agent that can invoke external tools (via MCP) during
    its reasoning process, then produce a structured response.

    Args:
        system_prompt: System prompt for the agent
        response_schema: Pydantic model defining the expected output structure
        mcp_tools: List of MCP tools the agent can call
        max_tool_calls: Maximum number of tool calls allowed per invocation

    Returns:
        Configured agent with tool calling AND structured output

    Note:
        The agent will:
        1. Receive the user prompt
        2. Optionally call MCP tools to gather real-time data
        3. Reason over the content + tool results
        4. Produce a structured response matching response_schema

    Example:
        >>> tools = await mcp_pool.get_tools_for_capabilities(["github:get_repo"])
        >>> agent = create_tool_enabled_agent(
        ...     system_prompt="You are a security auditor...",
        ...     response_schema=SecurityAudit,
        ...     mcp_tools=tools,
        ... )
        >>> result = await agent.ainvoke({"messages": [...]})
    """
    model = get_chat_model()

    # Bind tools with parallel calls enabled for efficiency
    # MCP tools are external calls that can run concurrently
    bound_model = model.bind_tools(
        list(mcp_tools),
        parallel_tool_calls=True,
    )

    # Create agent with tools AND structured output
    # The agent will call tools during reasoning, then format final response
    agent = create_agent(
        cast(BaseChatModel, bound_model),
        tools=list(mcp_tools),
        system_prompt=_enhance_prompt_for_tools(system_prompt, mcp_tools),
        response_format=ToolStrategy(response_schema),
        # Limit iterations to prevent runaway tool calls
        max_iterations=max_tool_calls + 2,  # +2 for initial + final response
    )

    logger.info(
        "tool_enabled_agent_created",
        tool_count=len(mcp_tools),
        tools=[t.name for t in mcp_tools],
        max_tool_calls=max_tool_calls,
    )

    return agent


def _enhance_prompt_for_tools(
    base_prompt: str,
    tools: Sequence[BaseTool],
) -> str:
    """Enhance system prompt with tool usage instructions.

    Adds clear guidance on when and how to use the available tools,
    preventing over-reliance or under-utilization.
    """
    tool_descriptions = "\n".join(
        f"- {t.name}: {t.description}" for t in tools
    )

    tool_guidance = f"""
## Available Tools

You have access to the following tools for real-time data lookup:

{tool_descriptions}

## Tool Usage Guidelines

1. **Use tools to verify claims**: When the content mentions specific versions,
   packages, or CVEs, use tools to verify current status.

2. **Don't over-use tools**: Only call tools when real-time data adds value.
   Trust your knowledge for general concepts and best practices.

3. **Handle tool failures gracefully**: If a tool call fails, proceed with
   your analysis noting the data gap. Don't retry failed calls.

4. **Cite tool results**: When your findings include tool data, note the source
   (e.g., "According to npm registry..." or "CVE database shows...").
"""

    return f"{base_prompt}\n\n{tool_guidance}"


# ... rest of existing base.py functions (save_agent_finding, emit_agent_progress) ...
```

### Updated Security Auditor (`workflows/agents/security_auditor.py`)

```python
"""Security Auditor Agent - UPDATED with MCP tool support.

This agent identifies security risks, vulnerabilities, and best practices
in the analyzed content. NEW: Can optionally use CVE database and GitHub
MCP tools for real-time vulnerability data.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from app.core.logging import get_logger
from app.services.mcp.registry import ToolRegistry
from app.workflows.agents.base import create_structured_agent, create_tool_enabled_agent
from app.workflows.agents.execution import run_agent_with_tracking
from app.workflows.agents.schemas.security_auditor import SecurityAudit
from app.workflows.agents.skill_level_prompts import get_skill_level_instructions

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

    from app.core.types import AnalysisID
    from app.services.mcp.client import MCPClientPool
    from app.workflows.state import AnalysisState

logger = get_logger(__name__)


SECURITY_AUDITOR_PROMPT = """You are a Security Audit Specialist. Your task is to:
1. Identify security risks and vulnerabilities in the content
2. Assess severity levels (low, medium, high, critical) based on impact and exploitability
3. Provide mitigation strategies for each identified risk
4. Recommend security best practices (OWASP Top 10, authentication, encryption, etc.)
5. Note compliance considerations (GDPR, PCI-DSS, HIPAA, etc.)

Focus on:
- Authentication and authorization vulnerabilities
- Data exposure and privacy risks
- Injection attacks (SQL, XSS, command injection)
- Insecure configurations
- API security concerns
- Dependency vulnerabilities
- Security misconfigurations

CRITICAL: You MUST include:
- security_risks: List of identified risks with type, severity, description, and mitigation
- best_practices: List of security best practices to follow
- compliance_notes: List of relevant compliance frameworks and considerations
- recommendation: Overall security recommendation with priority actions
- confidence_score: Float (0.0-1.0) representing your confidence

NUMERIC SPECIFICITY REQUIREMENTS:
- Include CVSS score where applicable (e.g., "CVSS 7.5 HIGH")
- Include CVE references for known vulnerabilities (e.g., "CVE-2024-12345")
- remediation_effort MUST be specific (e.g., "2-3 hours", "1 day refactoring")

Be thorough and prioritize critical vulnerabilities."""


async def run_security_auditor(
    content: str,
    content_type: str,
    analysis_id: AnalysisID,
    session: AsyncSession,
    state: AnalysisState,
    *,
    mcp_pool: MCPClientPool | None = None,
    tool_registry: ToolRegistry | None = None,
) -> dict[str, object]:
    """Run security auditor agent to identify security risks and vulnerabilities.

    Args:
        content: Extracted text content to analyze
        content_type: Type of content (article, video, repo)
        analysis_id: Unique identifier for this analysis
        session: Database session for persistence
        state: Current workflow state (for skill_level)
        mcp_pool: Optional MCP client pool for tool access
        tool_registry: Optional tool registry for capability filtering

    Returns:
        Dictionary with agent_type, findings, processing_time_ms
    """
    # Get skill level and inject instructions
    skill_level = state.get("skill_level", "intermediate")
    skill_instructions = get_skill_level_instructions(skill_level)
    full_prompt = f"{SECURITY_AUDITOR_PROMPT}\n\n{skill_instructions}"

    # Check if tools are enabled for this agent
    registry = tool_registry or ToolRegistry()

    if mcp_pool and registry.is_tool_enabled("security_auditor"):
        # Tool-enabled mode: Load MCP tools and create tool-calling agent
        try:
            capabilities = registry.get_capabilities("security_auditor")
            tools = await mcp_pool.get_tools_for_capabilities(capabilities)

            if tools:
                config = registry.get_agent_config("security_auditor")
                agent = create_tool_enabled_agent(
                    system_prompt=full_prompt,
                    response_schema=SecurityAudit,
                    mcp_tools=tools,
                    max_tool_calls=config.max_tool_calls,
                )

                logger.info(
                    "security_auditor_using_tools",
                    analysis_id=analysis_id,
                    tool_count=len(tools),
                    tools=[t.name for t in tools],
                )
            else:
                # No tools loaded, fall back to structured-only
                agent = create_structured_agent(
                    system_prompt=full_prompt,
                    response_schema=SecurityAudit,
                )
                logger.warning(
                    "security_auditor_no_tools_loaded",
                    analysis_id=analysis_id,
                )

        except Exception as e:
            # Tool loading failed, fall back gracefully
            logger.warning(
                "security_auditor_tool_loading_failed",
                analysis_id=analysis_id,
                error=str(e),
            )
            agent = create_structured_agent(
                system_prompt=full_prompt,
                response_schema=SecurityAudit,
            )
    else:
        # Standard mode: No tools
        agent = create_structured_agent(
            system_prompt=full_prompt,
            response_schema=SecurityAudit,
        )

    # Run agent with tracking and persistence
    return await run_agent_with_tracking(
        agent=agent,
        content=content,
        content_type=content_type,
        analysis_id=analysis_id,
        agent_type="security_auditor",
        session=session,
    )
```

---

## Configuration System

### MCP Config (`services/mcp/config.py`)

```python
"""MCP configuration models and settings.

Defines configuration for MCP servers and their connections.
Supports both stdio (local) and HTTP (remote) transports.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class MCPTransport(Enum):
    """MCP transport types."""
    STDIO = "stdio"
    HTTP = "http"
    SSE = "sse"


@dataclass
class MCPServerConfig:
    """Configuration for a single MCP server.

    Supports both local (stdio) and remote (HTTP/SSE) servers.
    """

    name: str
    transport: MCPTransport
    enabled: bool = True

    # Stdio transport settings
    command: str | None = None
    args: list[str] = field(default_factory=list)
    env: dict[str, str] = field(default_factory=dict)

    # HTTP/SSE transport settings
    url: str | None = None
    headers: dict[str, str] = field(default_factory=dict)

    # Connection settings
    timeout: float = 30.0
    max_retries: int = 3

    def to_langchain_config(self) -> dict[str, Any]:
        """Convert to langchain-mcp-adapters config format."""
        config: dict[str, Any] = {
            "transport": self.transport.value,
        }

        if self.transport == MCPTransport.STDIO:
            if not self.command:
                raise ValueError(f"stdio transport requires 'command' for {self.name}")
            config["command"] = self.command
            config["args"] = self.args
            if self.env:
                config["env"] = self.env
        else:
            if not self.url:
                raise ValueError(f"HTTP/SSE transport requires 'url' for {self.name}")
            config["url"] = self.url
            if self.headers:
                config["headers"] = self.headers

        return config


# Default MCP server configurations
# Can be overridden via environment variables or settings
DEFAULT_MCP_SERVERS: dict[str, MCPServerConfig] = {
    "github": MCPServerConfig(
        name="github",
        transport=MCPTransport.HTTP,
        url="https://mcp.github.com/v1",  # Example - use actual endpoint
        headers={},  # GITHUB_TOKEN injected at runtime
        enabled=True,
    ),
    "npm": MCPServerConfig(
        name="npm",
        transport=MCPTransport.STDIO,
        command="npx",
        args=["-y", "@anthropic/mcp-server-npm"],
        enabled=True,
    ),
    "cve": MCPServerConfig(
        name="cve",
        transport=MCPTransport.HTTP,
        url="https://mcp.cvedetails.com/v1",  # Example
        enabled=True,
    ),
    "pypi": MCPServerConfig(
        name="pypi",
        transport=MCPTransport.STDIO,
        command="uvx",
        args=["mcp-server-pypi"],
        enabled=True,
    ),
}


@dataclass
class MCPSettings:
    """Global MCP settings."""

    enabled: bool = True
    servers: dict[str, MCPServerConfig] = field(
        default_factory=lambda: DEFAULT_MCP_SERVERS.copy()
    )
    default_timeout: float = 30.0
    max_concurrent_connections: int = 5
    health_check_interval: float = 60.0

    @classmethod
    def from_env(cls) -> MCPSettings:
        """Load settings from environment variables."""
        import os

        settings = cls()

        # Override enabled status
        if os.getenv("MCP_ENABLED", "true").lower() == "false":
            settings.enabled = False

        # Inject API keys into server configs
        if github_token := os.getenv("GITHUB_TOKEN"):
            if "github" in settings.servers:
                settings.servers["github"].headers["Authorization"] = f"Bearer {github_token}"

        return settings
```

---

## Error Handling & Resilience

### Key Error Scenarios

```
┌─────────────────────────────────────────────────────────────────┐
│                    MCP Error Handling Strategy                  │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  1. Connection Failure                                          │
│     ┌─────────┐                                                 │
│     │ Retry   │──► 3 attempts with exponential backoff          │
│     └────┬────┘                                                 │
│          │ Still failing                                        │
│          ▼                                                      │
│     ┌─────────────┐                                             │
│     │ Degrade     │──► Agent runs without tools (warn in logs)  │
│     │ Gracefully  │                                             │
│     └─────────────┘                                             │
│                                                                  │
│  2. Tool Execution Timeout                                      │
│     ┌─────────┐                                                 │
│     │ Timeout │──► 10s default per tool call                    │
│     └────┬────┘                                                 │
│          │                                                      │
│          ▼                                                      │
│     ┌─────────────┐                                             │
│     │ Skip Tool   │──► Continue without that data point         │
│     │ Result      │                                             │
│     └─────────────┘                                             │
│                                                                  │
│  3. Tool Returns Error                                          │
│     ┌─────────┐                                                 │
│     │ Parse   │──► Extract error message from tool response     │
│     │ Error   │                                                 │
│     └────┬────┘                                                 │
│          ▼                                                      │
│     ┌─────────────┐                                             │
│     │ Include in  │──► "Tool X failed: <error>"                 │
│     │ Context     │    Agent decides how to proceed             │
│     └─────────────┘                                             │
│                                                                  │
│  4. Rate Limiting (429)                                         │
│     ┌─────────┐                                                 │
│     │ Back off│──► Respect Retry-After header                   │
│     └────┬────┘                                                 │
│          │ If critical                                          │
│          ▼                                                      │
│     ┌─────────────┐                                             │
│     │ Queue for   │──► Retry in background, use cached if avail │
│     │ Retry       │                                             │
│     └─────────────┘                                             │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

---

## Observability

### Metrics to Collect

```python
# Metric definitions for MCP tool service
MCP_METRICS = {
    "mcp_connection_attempts_total": Counter(
        "Total MCP connection attempts",
        labels=["server", "status"],  # status: success, failure
    ),
    "mcp_tool_calls_total": Counter(
        "Total MCP tool invocations",
        labels=["server", "tool", "status"],
    ),
    "mcp_tool_duration_seconds": Histogram(
        "MCP tool call duration",
        labels=["server", "tool"],
        buckets=[0.1, 0.5, 1.0, 2.0, 5.0, 10.0],
    ),
    "mcp_connection_pool_size": Gauge(
        "Current MCP connection pool size",
        labels=["server"],
    ),
}
```

### LangSmith Integration

All MCP tool calls are automatically traced via LangChain's built-in LangSmith integration:

```
LangSmith Trace:
├── security_auditor_node
│   ├── create_tool_enabled_agent
│   ├── agent.ainvoke
│   │   ├── LLM call (reasoning)
│   │   ├── Tool: cve:search_cves ← MCP tool call traced
│   │   │   └── {"query": "log4j", "results": [...]}
│   │   ├── Tool: github:get_security_advisories ← MCP tool call traced
│   │   │   └── {"repo": "...", "advisories": [...]}
│   │   └── LLM call (final response)
│   └── ToolStrategy validation
```

---

## Security Considerations

### API Key Management

```python
# Keys injected from environment, never in code
MCP_SERVER_SECRETS = {
    "github": "GITHUB_TOKEN",
    "npm": None,  # Public API
    "cve": "CVE_API_KEY",  # If required
}

# Keys are injected at MCPSettings.from_env()
# Never logged, never in config files
```

### Tool Call Sandboxing

- MCP tools run in separate processes (stdio) or external servers (HTTP)
- No direct access to SkillForge database or filesystem
- Tool responses are validated before use
- Maximum tool calls enforced per agent

---

## Implementation Roadmap

### Phase 1: Foundation (Week 1-2)

- [ ] Create `services/mcp/` directory structure
- [ ] Implement `MCPClientPool` with connection management
- [ ] Implement `ToolRegistry` with capability mapping
- [ ] Add MCP configuration to app settings
- [ ] Write unit tests for client and registry

### Phase 2: Agent Integration (Week 3)

- [ ] Add `create_tool_enabled_agent()` to base.py
- [ ] Update `security_auditor.py` with tool support
- [ ] Add graceful degradation when tools unavailable
- [ ] Integration tests with mock MCP server

### Phase 3: MCP Servers (Week 4)

- [ ] Set up GitHub MCP server (or find existing)
- [ ] Set up npm-registry MCP server
- [ ] Set up CVE database MCP server
- [ ] Configure production endpoints

### Phase 4: Rollout (Week 5)

- [ ] Feature flag for tool-enabled agents
- [ ] A/B testing: tool-enabled vs structured-only
- [ ] Monitor latency and accuracy metrics
- [ ] Documentation and runbook

---

## References

- [LangChain MCP Adapters](https://github.com/langchain-ai/langchain-mcp-adapters) - Official library
- [MCP Specification](https://modelcontextprotocol.io/) - Protocol documentation
- [MCP Python SDK](https://github.com/modelcontextprotocol/python-sdk) - Official Python SDK
- [LangGraph ToolNode](https://langchain-ai.github.io/langgraph/reference/prebuilt/#toolnode) - Tool execution in LangGraph

---

**Sources consulted:**
- [LangChain MCP Adapters GitHub](https://github.com/langchain-ai/langchain-mcp-adapters)
- [MCP Architecture Overview](https://modelcontextprotocol.io/docs/concepts/architecture)
- [MCP Python SDK](https://github.com/modelcontextprotocol/python-sdk)
- [LangChain Changelog - MCP Adapters](https://changelog.langchain.com/announcements/mcp-adapters-for-langchain-and-langgraph)
