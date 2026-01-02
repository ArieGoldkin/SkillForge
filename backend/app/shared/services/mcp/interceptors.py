"""MCP tool call interceptors using chain-of-responsibility pattern.

This module implements interceptors for the langchain-mcp-adapters 0.2 client
to provide cross-cutting concerns like authentication, retry logic, result
enrichment, and logging for MCP tool calls.

Interceptor Pattern:
    Each interceptor implements the ToolCallInterceptor protocol and can:
    - Modify the request before passing to handler
    - Call the handler (potentially multiple times for retry)
    - Modify the result after handler completes
    - Short-circuit the handler (e.g., for caching)

Architecture:
    Interceptors compose in "onion" pattern where first interceptor is outermost:
    Request -> Auth -> Retry -> Logging -> Handler -> Logging -> Retry -> Auth -> Result

Example:
    >>> from app.shared.services.mcp.config import get_mcp_settings
    >>> from langchain_mcp_adapters.client import MultiServerMCPClient
    >>>
    >>> settings = get_mcp_settings()
    >>> interceptors = create_default_interceptors(settings)
    >>> client = MultiServerMCPClient(
    ...     connections=settings.servers,
    ...     tool_interceptors=interceptors,
    ... )

Note:
    Interceptors use tenacity for retry logic and structlog for structured logging.
    All interceptors gracefully degrade on errors to avoid blocking tool calls.

"""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

import uuid_utils
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from app.core.logging import get_logger
from app.shared.services.mcp.exceptions import MCPConnectionError, MCPTimeoutError

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable

    from langchain_mcp_adapters.interceptors import (
        MCPToolCallRequest,
        MCPToolCallResult,
        ToolCallInterceptor,
    )

    from app.shared.services.mcp.config import MCPSettings

logger = get_logger(__name__)

# Retry configuration for transient failures
MCP_RETRY_ATTEMPTS = 3
MCP_RETRY_MIN_WAIT = 1.0  # seconds
MCP_RETRY_MAX_WAIT = 16.0  # seconds
MCP_RETRY_MULTIPLIER = 2.0  # exponential backoff multiplier


class AuthInterceptor:
    """Inject authentication headers into MCP tool call requests.

    Adds authentication tokens from MCPSettings configuration to requests
    based on server name routing. Only modifies requests for servers that
    have auth headers configured.

    Attributes:
        settings: MCP configuration containing auth tokens per server

    Example:
        >>> settings = MCPSettings.from_env()
        >>> auth = AuthInterceptor(settings)
        >>> # Will inject GITHUB_TOKEN for github server requests
        >>> result = await auth(request, handler)

    """

    def __init__(self, settings: MCPSettings) -> None:
        """Initialize auth interceptor with configuration.

        Args:
            settings: MCP settings containing server auth configurations

        """
        self.settings = settings

    async def __call__(
        self,
        request: MCPToolCallRequest,
        handler: Callable[[MCPToolCallRequest], Awaitable[MCPToolCallResult]],
    ) -> MCPToolCallResult:
        """Inject auth headers for configured servers.

        Args:
            request: Tool call request with server_name context
            handler: Next interceptor or actual tool execution

        Returns:
            Result from handler, unchanged

        """
        server_name = request.server_name

        # Check if this server has auth headers configured
        if server_name in self.settings.servers:
            server_config = self.settings.servers[server_name]

            # Inject headers if configured for this server
            if server_config.headers:
                # Merge existing headers with auth headers (auth headers take precedence)
                existing_headers = request.headers or {}
                merged_headers = {**existing_headers, **server_config.headers}

                # Create modified request with auth headers
                modified_request = request.override(headers=merged_headers)

                logger.debug(
                    "mcp_auth_injected",
                    server=server_name,
                    tool=request.name,
                    header_count=len(server_config.headers),
                )

                return await handler(modified_request)

        # No auth configured for this server, pass through unchanged
        return await handler(request)


class RetryInterceptor:
    """Retry tool calls on transient failures with exponential backoff.

    Uses tenacity to retry failed tool calls when errors indicate transient
    issues (connection errors, timeouts). Respects per-server max_retries
    configuration from MCPSettings.

    Attributes:
        settings: MCP configuration for per-server retry limits

    Example:
        >>> settings = MCPSettings.from_env()
        >>> retry = RetryInterceptor(settings)
        >>> # Will retry up to 3 times with exponential backoff
        >>> result = await retry(request, handler)

    """

    def __init__(self, settings: MCPSettings) -> None:
        """Initialize retry interceptor with configuration.

        Args:
            settings: MCP settings containing per-server retry limits

        """
        self.settings = settings

    async def __call__(
        self,
        request: MCPToolCallRequest,
        handler: Callable[[MCPToolCallRequest], Awaitable[MCPToolCallResult]],
    ) -> MCPToolCallResult:
        """Retry handler calls on transient failures.

        Args:
            request: Tool call request
            handler: Next interceptor or actual tool execution

        Returns:
            Result from handler

        Raises:
            MCPConnectionError: After all retry attempts exhausted
            MCPTimeoutError: After all retry attempts exhausted

        """
        server_name = request.server_name

        # Get retry configuration for this server
        max_retries = MCP_RETRY_ATTEMPTS
        if server_name in self.settings.servers:
            max_retries = self.settings.servers[server_name].max_retries

        # Track attempt number for logging
        attempt_tracker = {"count": 0}

        def before_retry_log(retry_state: Any) -> None:
            """Log warning before each retry attempt."""
            attempt_tracker["count"] = retry_state.attempt_number
            if retry_state.attempt_number > 1:
                logger.warning(
                    "mcp_tool_retry",
                    server=server_name,
                    tool=request.name,
                    attempt=retry_state.attempt_number,
                    max_retries=max_retries,
                )

        # Create retry decorator with logging
        retry_decorator = retry(
            stop=stop_after_attempt(max_retries),
            wait=wait_exponential(
                multiplier=MCP_RETRY_MULTIPLIER,
                min=MCP_RETRY_MIN_WAIT,
                max=MCP_RETRY_MAX_WAIT,
            ),
            retry=retry_if_exception_type((MCPConnectionError, MCPTimeoutError)),
            before_sleep=before_retry_log,
            reraise=True,
        )

        # Wrap handler with retry logic
        @retry_decorator
        async def handler_with_retry() -> MCPToolCallResult:
            return await handler(request)

        try:
            return await handler_with_retry()
        except (MCPConnectionError, MCPTimeoutError):
            # All retries exhausted, log and re-raise
            logger.exception(
                "mcp_tool_retry_exhausted",
                server=server_name,
                tool=request.name,
                attempts=attempt_tracker["count"],
                max_retries=max_retries,
            )
            raise


class ResultEnrichmentInterceptor:
    """Enrich tool call results with metadata for observability.

    Adds metadata to tool call results including:
    - Server name (for routing/debugging)
    - Timing information (duration in seconds)
    - Trace correlation IDs (for distributed tracing)

    Note:
        This interceptor only logs the enrichment metadata. The actual result
        object from MCP is typically immutable (CallToolResult from MCP SDK),
        so we log the metadata separately rather than modifying the result.

    Example:
        >>> enrichment = ResultEnrichmentInterceptor()
        >>> # Logs metadata about the tool call
        >>> result = await enrichment(request, handler)

    """

    async def __call__(
        self,
        request: MCPToolCallRequest,
        handler: Callable[[MCPToolCallRequest], Awaitable[MCPToolCallResult]],
    ) -> MCPToolCallResult:
        """Enrich result with timing and tracing metadata.

        Args:
            request: Tool call request
            handler: Next interceptor or actual tool execution

        Returns:
            Result from handler (unchanged, metadata logged separately)

        """
        # Generate trace ID for correlation (UUID v7 for time-ordering)
        trace_id = str(uuid_utils.uuid7())

        # Record start time
        start_time = time.time()

        try:
            # Execute handler
            result = await handler(request)

            # Calculate duration
            duration_seconds = time.time() - start_time

            # Log enrichment metadata
            logger.info(
                "mcp_result_enriched",
                server=request.server_name,
                tool=request.name,
                duration_seconds=round(duration_seconds, 3),
                trace_id=trace_id,
                success=True,
            )

            return result

        except (
            Exception
        ) as e:  # Log all MCP tool errors for observability, then re-raise for upstream handling
            # Log error with enrichment metadata
            duration_seconds = time.time() - start_time

            logger.exception(
                "mcp_result_enriched",
                server=request.server_name,
                tool=request.name,
                duration_seconds=round(duration_seconds, 3),
                trace_id=trace_id,
                success=False,
                error_type=type(e).__name__,
            )

            raise


class LoggingInterceptor:
    """Log all MCP tool calls with structured logging and Langfuse correlation.

    Logs request/response for every tool call with:
    - Structured log events (request_start, request_complete, request_error)
    - Tool name, server name, arguments
    - Timing information
    - Langfuse trace correlation (if available in request.runtime)

    This interceptor should typically be placed early in the chain to ensure
    all requests are logged, even if later interceptors modify them.

    Attributes:
        log_arguments: Whether to log full tool arguments (may contain sensitive data)

    Example:
        >>> logging_interceptor = LoggingInterceptor(log_arguments=False)
        >>> # Logs all tool calls to structured logger
        >>> result = await logging_interceptor(request, handler)

    """

    def __init__(self, log_arguments: bool = False) -> None:
        """Initialize logging interceptor.

        Args:
            log_arguments: If True, log full tool arguments. If False, only log
                          argument keys for privacy. Default is False to avoid
                          logging potentially sensitive data.

        """
        self.log_arguments = log_arguments

    async def __call__(
        self,
        request: MCPToolCallRequest,
        handler: Callable[[MCPToolCallRequest], Awaitable[MCPToolCallResult]],
    ) -> MCPToolCallResult:
        """Log tool call lifecycle events.

        Args:
            request: Tool call request with server_name, tool name, args
            handler: Next interceptor or actual tool execution

        Returns:
            Result from handler, unchanged

        """
        # Extract Langfuse trace ID if available from LangGraph runtime
        langfuse_trace_id: str | None = None
        if request.runtime and hasattr(request.runtime, "trace_id"):
            langfuse_trace_id = getattr(request.runtime, "trace_id", None)

        # Prepare arguments for logging (full args or just keys)
        log_args: dict[str, Any] | list[str] = (
            request.args if self.log_arguments else list(request.args.keys())
        )

        # Log request start
        logger.info(
            "mcp_tool_call_start",
            server=request.server_name,
            tool=request.name,
            args=log_args,
            langfuse_trace_id=langfuse_trace_id,
        )

        start_time = time.time()

        try:
            # Execute handler
            result = await handler(request)

            # Log successful completion
            duration_seconds = time.time() - start_time

            logger.info(
                "mcp_tool_call_complete",
                server=request.server_name,
                tool=request.name,
                duration_seconds=round(duration_seconds, 3),
                langfuse_trace_id=langfuse_trace_id,
            )

            return result

        except (
            Exception
        ) as e:  # Log all MCP tool errors for debugging, then re-raise for caller handling
            # Log error
            duration_seconds = time.time() - start_time

            logger.exception(
                "mcp_tool_call_error",
                server=request.server_name,
                tool=request.name,
                duration_seconds=round(duration_seconds, 3),
                langfuse_trace_id=langfuse_trace_id,
                error_type=type(e).__name__,
            )

            raise


@dataclass
class InterceptorConfig:
    """Configuration for creating default interceptors.

    Attributes:
        enable_auth: Enable authentication header injection
        enable_retry: Enable retry logic for transient failures
        enable_enrichment: Enable result metadata enrichment
        enable_logging: Enable request/response logging
        log_arguments: Log full tool arguments (may contain sensitive data)

    """

    enable_auth: bool = True
    enable_retry: bool = True
    enable_enrichment: bool = True
    enable_logging: bool = True
    log_arguments: bool = False


def create_default_interceptors(
    settings: MCPSettings,
    config: InterceptorConfig | None = None,
) -> list[ToolCallInterceptor]:
    """Create default interceptor chain for MCP tool calls.

    Creates a standard interceptor chain with authentication, retry logic,
    result enrichment, and logging. Interceptors are applied in order:
    1. Logging (outermost - logs all requests)
    2. Auth (injects headers early)
    3. Retry (retries transient failures)
    4. Enrichment (adds metadata to results)

    Args:
        settings: MCP configuration for auth tokens and retry limits
        config: Optional configuration for which interceptors to enable.
               If None, uses default configuration (all enabled).

    Returns:
        List of configured interceptors in execution order

    Example:
        >>> settings = get_mcp_settings()
        >>> # Use defaults (all enabled)
        >>> interceptors = create_default_interceptors(settings)
        >>>
        >>> # Or customize
        >>> config = InterceptorConfig(log_arguments=False, enable_enrichment=False)
        >>> interceptors = create_default_interceptors(settings, config)
        >>> client = MultiServerMCPClient(
        ...     connections=settings.servers,
        ...     tool_interceptors=interceptors,
        ... )

    Note:
        Order matters! The first interceptor in the list is the outermost layer
        (sees requests first, results last). Current order:
        Logging -> Auth -> Retry -> Enrichment -> Handler

    """
    # Use default config if not provided
    if config is None:
        config = InterceptorConfig()

    interceptors: list[ToolCallInterceptor] = []

    # Add interceptors in order (first is outermost)
    if config.enable_logging:
        interceptors.append(LoggingInterceptor(log_arguments=config.log_arguments))

    if config.enable_auth:
        interceptors.append(AuthInterceptor(settings))

    if config.enable_retry:
        interceptors.append(RetryInterceptor(settings))

    if config.enable_enrichment:
        interceptors.append(ResultEnrichmentInterceptor())

    logger.info(
        "mcp_interceptors_created",
        count=len(interceptors),
        interceptors=[type(i).__name__ for i in interceptors],
    )

    return interceptors
