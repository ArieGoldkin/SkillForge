"""MCP Client Pool for managing connections to MCP servers.

Uses langchain-mcp-adapters for protocol handling with added:
- Connection pooling and lifecycle management
- Health checks and automatic reconnection
- Graceful degradation when servers unavailable
- Lazy initialization (connect on first use)

Architecture:
    MCPClientPool manages connections to multiple MCP servers.
    Each server connection is wrapped in MCPConnection for state tracking.
    Tools are loaded lazily on first request and cached for reuse.

Example:
    >>> pool = MCPClientPool({"github": github_config})
    >>> async with pool.get_tools("github") as tools:
    ...     result = await tools[0].ainvoke({"repo": "owner/repo"})
    >>> await pool.close()

"""

from __future__ import annotations

import asyncio
import logging
import time
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from enum import Enum
from typing import TYPE_CHECKING, Any

from tenacity import (
    before_sleep_log,
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from app.core.logging import get_logger
from app.shared.services.mcp.callbacks import MCPCallbacks
from app.shared.services.mcp.exceptions import MCPConnectionError, MCPTimeoutError
from app.shared.services.mcp.interceptors import create_default_interceptors

if TYPE_CHECKING:
    from collections.abc import AsyncIterator, Awaitable, Callable

    from langchain_core.tools import BaseTool

    from app.shared.services.mcp.config import MCPServerConfig, MCPSettings

logger = get_logger(__name__)

# Circuit breaker threshold - mark connection as ERROR after this many failures
MAX_CONSECUTIVE_ERRORS = 3

# Retry configuration constants
MCP_RETRY_ATTEMPTS = 3
MCP_RETRY_MIN_WAIT = 1.0  # seconds
MCP_RETRY_MAX_WAIT = 16.0  # seconds
MCP_RETRY_MULTIPLIER = 2.0  # exponential backoff multiplier


async def execute_with_timeout[T](
    coro: Awaitable[T],
    timeout_seconds: float,
    operation_name: str,
    server_name: str | None = None,
) -> T:
    """Execute an awaitable with timeout enforcement.

    Wraps any async operation with asyncio.timeout to ensure it completes
    within the specified time limit. Converts TimeoutError to MCPTimeoutError
    with rich context for debugging and monitoring.

    Args:
        coro: The awaitable to execute
        timeout_seconds: Maximum execution time in seconds
        operation_name: Name for logging (e.g., "load_tools", "tool_call")
        server_name: Optional MCP server name for context

    Returns:
        Result of the awaitable

    Raises:
        MCPTimeoutError: If timeout exceeded, with context about the operation

    Example:
        >>> result = await execute_with_timeout(
        ...     client.load_tools(),
        ...     timeout_seconds=30.0,
        ...     operation_name="load_tools",
        ...     server_name="github",
        ... )

    """
    try:
        async with asyncio.timeout(timeout_seconds):
            return await coro
    except TimeoutError as e:
        logger.warning(
            "mcp_operation_timeout",
            operation=operation_name,
            server=server_name,
            timeout_seconds=timeout_seconds,
        )
        msg = f"{operation_name} timed out after {timeout_seconds}s"
        raise MCPTimeoutError(
            msg,
            server_name=server_name,
            tool_name=operation_name,
            timeout_seconds=timeout_seconds,
        ) from e


def create_mcp_retry_decorator(
    max_attempts: int = MCP_RETRY_ATTEMPTS,
    min_wait: float = MCP_RETRY_MIN_WAIT,
    max_wait: float = MCP_RETRY_MAX_WAIT,
) -> Callable[[Callable[..., Awaitable[Any]]], Callable[..., Awaitable[Any]]]:
    """Create a retry decorator for MCP operations.

    Returns a tenacity retry decorator configured for MCP-specific error
    handling with exponential backoff. Only retries on transient errors
    (connection failures, timeouts), not on permanent errors.

    Args:
        max_attempts: Maximum number of retry attempts (default: 3)
        min_wait: Minimum wait time between retries in seconds (default: 1.0)
        max_wait: Maximum wait time between retries in seconds (default: 16.0)

    Returns:
        Configured retry decorator

    Example:
        >>> @create_mcp_retry_decorator(max_attempts=3)
        ... async def load_tools_with_retry():
        ...     return await client.load_tools()

    Note:
        The decorator logs before each retry using structlog at WARNING level.
        Wait times follow exponential backoff: 1s, 2s, 4s, 8s, 16s (capped)

    """
    return retry(
        stop=stop_after_attempt(max_attempts),
        wait=wait_exponential(multiplier=MCP_RETRY_MULTIPLIER, min=min_wait, max=max_wait),
        retry=retry_if_exception_type((MCPConnectionError, MCPTimeoutError)),
        before_sleep=before_sleep_log(logging.getLogger(__name__), logging.WARNING),
        reraise=True,
    )


class ConnectionState(Enum):
    """MCP connection states for lifecycle tracking.

    State Transitions:
        DISCONNECTED -> CONNECTING -> CONNECTED
        CONNECTED -> ERROR (on failure)
        ERROR -> CONNECTING (on retry)

    """

    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    ERROR = "error"


@dataclass
class MCPConnection:
    """Wrapper for MCP server connection with state tracking.

    Tracks connection state, loaded tools, and error history
    to support health monitoring and automatic recovery.

    Attributes:
        server_name: Unique identifier for the server
        config: Server configuration
        state: Current connection state
        tools: Cached tools from the server
        last_health_check: Timestamp of last successful health check
        error_count: Consecutive error count for circuit breaking
        last_error: Most recent error message

    """

    server_name: str
    config: MCPServerConfig
    state: ConnectionState = ConnectionState.DISCONNECTED
    tools: list[BaseTool] = field(default_factory=list)
    last_health_check: float | None = None
    error_count: int = 0
    last_error: str | None = None

    def is_healthy(self) -> bool:
        """Check if connection is healthy and usable.

        A connection is healthy if:
        - State is CONNECTED
        - Error count is below threshold

        Returns:
            True if connection can be used

        """
        return self.state == ConnectionState.CONNECTED and self.error_count < MAX_CONSECUTIVE_ERRORS

    def record_success(self) -> None:
        """Record successful operation, reset error count."""
        self.error_count = 0
        self.last_error = None
        self.last_health_check = time.time()

    def record_error(self, error: str) -> None:
        """Record failed operation.

        Args:
            error: Error message for debugging

        """
        self.error_count += 1
        self.last_error = error
        if self.error_count >= MAX_CONSECUTIVE_ERRORS:
            self.state = ConnectionState.ERROR


class MCPClientPool:
    """Connection pool for MCP servers.

    Manages connections to multiple MCP servers with:
    - Lazy initialization (connect on first use)
    - Connection reuse across requests
    - Health monitoring and automatic recovery
    - Graceful degradation when servers fail

    Thread Safety:
        Uses asyncio.Lock for connection management.
        Safe for concurrent use within a single event loop.

    Example:
        >>> pool = MCPClientPool(config)
        >>> async with pool.get_tools("github") as tools:
        ...     # tools is list[BaseTool] from GitHub MCP
        ...     result = await tools[0].ainvoke({"repo": "langchain-ai/langchain"})

    """

    def __init__(
        self,
        server_configs: dict[str, MCPServerConfig],
        *,
        settings: MCPSettings | None = None,
        analysis_id: str | None = None,
        enable_interceptors: bool = True,
        enable_callbacks: bool = True,
    ) -> None:
        """Initialize pool with server configurations.

        Args:
            server_configs: Mapping of server names to their configurations.
                          Only enabled servers will be used.
            settings: Optional MCP settings for interceptor configuration.
                     Required if enable_interceptors is True.
            analysis_id: Optional analysis ID for SSE callback routing.
            enable_interceptors: Whether to use 0.2 interceptors (auth, retry, etc.)
            enable_callbacks: Whether to use 0.2 callbacks (progress, logging)

        """
        # Filter to only enabled servers
        self._configs = {name: config for name, config in server_configs.items() if config.enabled}
        self._connections: dict[str, MCPConnection] = {}
        self._lock = asyncio.Lock()
        self._client: MultiServerMCPClient | None = None
        self._closed = False

        # 0.2 features configuration
        self._settings = settings
        self._analysis_id = analysis_id
        self._enable_interceptors = enable_interceptors
        self._enable_callbacks = enable_callbacks

        logger.info(
            "mcp_client_pool_initialized",
            server_count=len(self._configs),
            servers=list(self._configs.keys()),
            interceptors_enabled=enable_interceptors,
            callbacks_enabled=enable_callbacks,
        )

    async def _ensure_client(self) -> MultiServerMCPClient:
        """Lazily create the MCP client with 0.2 features.

        Creates a MultiServerMCPClient with all configured servers.
        The client handles actual MCP protocol communication.

        0.2 Features:
            - tool_name_prefix=True: Tools prefixed with server name
            - tool_interceptors: Auth, retry, logging, enrichment chain
            - callbacks: Progress and logging notifications from MCP servers

        Returns:
            Initialized MultiServerMCPClient

        Raises:
            MCPConnectionError: If client creation fails

        """
        if self._closed:
            msg = "Client pool is closed"
            raise MCPConnectionError(msg, details={"state": "closed"})

        if self._client is None:
            try:
                # Convert our config to langchain-mcp-adapters format
                client_config = {}
                for name, cfg in self._configs.items():
                    client_config[name] = cfg.to_langchain_config()

                # Build 0.2 features
                interceptors = None
                callbacks = None

                # Create interceptors chain if enabled and settings provided
                if self._enable_interceptors and self._settings:
                    # Use defaults: all interceptors enabled, log_arguments=False for privacy
                    interceptors = create_default_interceptors(self._settings)
                    logger.debug(
                        "mcp_interceptors_configured",
                        interceptor_count=len(interceptors),
                    )

                # Create callbacks if enabled
                if self._enable_callbacks:
                    mcp_callbacks = MCPCallbacks.create(
                        analysis_id=self._analysis_id,
                        enable_langfuse=True,
                        enable_sse=bool(self._analysis_id),  # Only SSE if we have analysis_id
                        enable_logging=True,
                    )
                    callbacks = mcp_callbacks.to_callbacks()
                    logger.debug(
                        "mcp_callbacks_configured",
                        analysis_id=self._analysis_id,
                    )

                # Create client with 0.2 features
                # tool_name_prefix=True: Tools get prefixed with server name
                # (e.g., github_get_repo)
                self._client = MultiServerMCPClient(
                    client_config,
                    tool_name_prefix=True,  # 0.2 feature: built-in server prefixing
                    tool_interceptors=interceptors,  # 0.2 feature: interceptor chain
                    callbacks=callbacks,  # 0.2 feature: progress/logging notifications
                )

                logger.info(
                    "mcp_client_created",
                    servers=list(self._configs.keys()),
                    tool_name_prefix=True,
                    interceptors_enabled=interceptors is not None,
                    callbacks_enabled=callbacks is not None,
                )
            except Exception as e:
                logger.exception(
                    "mcp_client_creation_failed",
                    error=str(e),
                )
                msg = f"Failed to create MCP client: {e}"
                raise MCPConnectionError(
                    msg,
                    details={"error_type": type(e).__name__},
                ) from e

        return self._client

    def _get_or_create_connection(self, server_name: str) -> MCPConnection:
        """Get existing connection or create new one.

        Args:
            server_name: Name of the MCP server

        Returns:
            MCPConnection for the server

        Raises:
            ValueError: If server is not configured

        """
        if server_name not in self._configs:
            available = list(self._configs.keys())
            msg = f"Unknown MCP server: {server_name}. Available: {available}"
            raise ValueError(msg)

        if server_name not in self._connections:
            self._connections[server_name] = MCPConnection(
                server_name=server_name,
                config=self._configs[server_name],
            )

        return self._connections[server_name]

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
            ValueError: If server is not configured

        Example:
            >>> async with pool.get_tools("github") as tools:
            ...     for tool in tools:
            ...         print(f"{tool.name}: {tool.description}")

        """
        async with self._lock:
            conn = self._get_or_create_connection(server_name)

        try:
            # Load tools if not already loaded or connection unhealthy
            if not conn.tools or not conn.is_healthy():
                await self._load_tools(conn)

            yield conn.tools
            conn.record_success()

        except MCPConnectionError:
            # Re-raise connection errors
            raise
        except Exception as e:
            conn.record_error(str(e))
            logger.exception(
                "mcp_tool_access_failed",
                server=server_name,
                error=str(e),
                error_count=conn.error_count,
            )
            msg = f"Failed to access tools from {server_name}: {e}"
            raise MCPConnectionError(
                msg,
                server_name=server_name,
                details={"error_type": type(e).__name__},
            ) from e

    async def _load_tools(self, conn: MCPConnection) -> None:
        """Load tools from MCP server into connection with retry logic.

        Uses exponential backoff retry for transient failures and timeout
        enforcement for tool loading operations.

        Args:
            conn: Connection to load tools for

        Raises:
            MCPConnectionError: If tool loading fails after all retries
            MCPTimeoutError: If tool loading exceeds timeout

        """
        conn.state = ConnectionState.CONNECTING

        # Get timeout and max_retries from config
        timeout = conn.config.timeout if conn.config else 30.0
        max_retries = conn.config.max_retries if conn.config else MCP_RETRY_ATTEMPTS

        # Create retry decorator with config-based settings
        retry_decorator = create_mcp_retry_decorator(max_attempts=max_retries)

        @retry_decorator
        async def _load_with_retry() -> list[BaseTool]:
            """Inner function with retry logic."""
            client = await self._ensure_client()

            # Load tools with timeout enforcement
            async def _do_load() -> list[BaseTool]:
                # Use new 0.2.1 API: get_tools(server_name=...)
                # Check if get_tools is async or sync
                tools_result = client.get_tools(server_name=conn.server_name)  # type: ignore[attr-defined]
                # If it's a coroutine, await it; otherwise use directly
                if hasattr(tools_result, "__await__"):
                    tools: list[BaseTool] = await tools_result
                else:
                    tools: list[BaseTool] = tools_result
                return tools

            tools = await execute_with_timeout(
                _do_load(),
                timeout_seconds=timeout,
                operation_name="load_tools",
                server_name=conn.server_name,
            )

            # With tool_name_prefix=True (0.2 feature), tools are already
            # prefixed with server name (e.g., github_get_repo) by the client.
            # No manual filtering needed - just return the tools.
            return list(tools)

        try:
            conn.tools = await _load_with_retry()
            conn.state = ConnectionState.CONNECTED
            conn.record_success()

            logger.info(
                "mcp_tools_loaded",
                server=conn.server_name,
                tool_count=len(conn.tools),
                tools=[t.name for t in conn.tools],
            )

        except (MCPConnectionError, MCPTimeoutError) as e:
            conn.state = ConnectionState.ERROR
            conn.record_error(str(e))
            raise

        except Exception as e:
            conn.state = ConnectionState.ERROR
            conn.record_error(str(e))

            logger.exception(
                "mcp_tool_loading_failed",
                server=conn.server_name,
                error=str(e),
                error_count=conn.error_count,
            )

            msg = f"Failed to load tools from {conn.server_name}: {e}"
            raise MCPConnectionError(
                msg,
                server_name=conn.server_name,
                details={
                    "error_type": type(e).__name__,
                    "error_count": conn.error_count,
                },
            ) from e

    async def get_tools_for_capabilities(
        self,
        capabilities: list[str],
    ) -> list[BaseTool]:
        """Get tools matching specified capabilities.

        Capabilities use format "server:tool_name" to specify which
        tools to load from which servers.

        Args:
            capabilities: List of capability strings
                         e.g., ["github:get_repo", "npm:get_package"]

        Returns:
            List of tools matching any of the specified capabilities.
            Returns empty list if no capabilities match.

        Example:
            >>> tools = await pool.get_tools_for_capabilities(
            ...     [
            ...         "github:get_repo",
            ...         "github:get_file_contents",
            ...         "npm:get_package",
            ...     ]
            ... )

        """
        if not capabilities:
            return []

        all_tools: list[BaseTool] = []

        # Group capabilities by server
        server_caps: dict[str, list[str]] = {}
        for cap in capabilities:
            if ":" not in cap:
                logger.warning(
                    "mcp_invalid_capability_format",
                    capability=cap,
                    expected_format="server:tool_name",
                )
                continue

            server, tool_name = cap.split(":", 1)
            if server not in server_caps:
                server_caps[server] = []
            server_caps[server].append(tool_name)

        # Load tools from each required server
        for server_name, tool_names in server_caps.items():
            if server_name not in self._configs:
                logger.warning(
                    "mcp_server_not_configured",
                    server=server_name,
                    requested_tools=tool_names,
                )
                continue

            try:
                async with self.get_tools(server_name) as tools:
                    # Filter to requested tools
                    for tool in tools:
                        # Check if tool name matches any requested capability
                        tool_base_name = tool.name.replace(f"{server_name}_", "")
                        if tool_base_name in tool_names or tool.name in tool_names:
                            all_tools.append(tool)

            except MCPConnectionError as e:
                # Log but continue - graceful degradation
                logger.warning(
                    "mcp_capability_loading_failed",
                    server=server_name,
                    error=str(e),
                    requested_tools=tool_names,
                )
                continue

        logger.info(
            "mcp_capabilities_loaded",
            requested=capabilities,
            loaded_count=len(all_tools),
            loaded_tools=[t.name for t in all_tools],
        )

        return all_tools

    async def health_check(self) -> dict[str, bool]:
        """Check health of all configured servers.

        Attempts to connect to each server and load tools.
        Results indicate which servers are available.

        Returns:
            Mapping of server names to health status

        Example:
            >>> health = await pool.health_check()
            >>> print(health)
            {"github": True, "npm": True, "pypi": False}

        """
        results: dict[str, bool] = {}

        for name in self._configs:
            try:
                async with self.get_tools(name) as tools:
                    results[name] = len(tools) > 0
            except MCPConnectionError as e:
                logger.warning(
                    "mcp_health_check_failed",
                    server=name,
                    error=str(e),
                )
                results[name] = False

        logger.info(
            "mcp_health_check_complete",
            results=results,
            healthy_count=sum(results.values()),
            total_count=len(results),
        )

        return results

    async def close(self) -> None:
        """Close all connections and cleanup resources.

        Should be called when shutting down the application
        to properly cleanup child processes (stdio) and
        network connections (HTTP/SSE).

        """
        self._closed = True

        # Clear all connections
        for conn in self._connections.values():
            conn.state = ConnectionState.DISCONNECTED
            conn.tools = []

        self._connections.clear()

        # Close the underlying client
        # Note: langchain-mcp-adapters 0.2.1 doesn't require explicit cleanup
        # The client handles its own lifecycle internally
        if self._client is not None:
            self._client = None

        logger.info("mcp_client_pool_closed")

    @property
    def is_closed(self) -> bool:
        """Check if pool is closed."""
        return self._closed

    def get_connection_status(self) -> dict[str, dict]:
        """Get status of all connections for monitoring.

        Returns:
            Dictionary with connection status for each server

        """
        status = {}
        for name, conn in self._connections.items():
            status[name] = {
                "state": conn.state.value,
                "tool_count": len(conn.tools),
                "error_count": conn.error_count,
                "last_error": conn.last_error,
                "last_health_check": conn.last_health_check,
                "is_healthy": conn.is_healthy(),
            }
        return status


# Lazy import to avoid import errors when langchain-mcp-adapters not installed
try:
    from langchain_mcp_adapters.client import MultiServerMCPClient
except ImportError:

    class MultiServerMCPClient:
        """Placeholder when langchain-mcp-adapters not installed."""

        def __init__(self, config: dict) -> None:
            """Raise ImportError when MCP adapters not installed.

            Args:
                config: Server configuration (ignored, raises immediately)

            Raises:
                ImportError: Always raised to indicate missing dependency

            """
            del config  # Unused, we raise immediately
            msg = (
                "langchain-mcp-adapters is required for MCP integration. "
                "Install with: pip install langchain-mcp-adapters"
            )
            raise ImportError(msg)
