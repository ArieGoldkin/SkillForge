"""MCP service exception hierarchy.

Provides structured exception types for MCP operations with clear
categorization for error handling and resilience patterns.

Exception Hierarchy:
    MCPError (base)
    ├── MCPConnectionError - Server connection failures
    ├── MCPTimeoutError - Tool execution timeouts
    ├── MCPToolError - Tool invocation failures
    └── MCPConfigurationError - Invalid configuration
"""

from __future__ import annotations


class MCPError(Exception):
    """Base exception for all MCP-related errors.

    Attributes:
        message: Human-readable error description
        server_name: Name of the MCP server (if applicable)
        details: Additional error context

    """

    def __init__(
        self,
        message: str,
        *,
        server_name: str | None = None,
        details: dict | None = None,
    ) -> None:
        """Initialize MCP error.

        Args:
            message: Error description
            server_name: Optional MCP server name for context
            details: Optional additional error details

        """
        super().__init__(message)
        self.message = message
        self.server_name = server_name
        self.details = details or {}

    def __str__(self) -> str:
        """Format error with server context if available."""
        if self.server_name:
            return f"[{self.server_name}] {self.message}"
        return self.message


class MCPConnectionError(MCPError):
    """Raised when MCP server connection fails.

    This includes:
    - Server unreachable (network issues)
    - Authentication failures
    - Server process spawn failures (stdio)
    - Connection pool exhausted

    Example:
        >>> raise MCPConnectionError(
        ...     "Failed to connect",
        ...     server_name="github",
        ...     details={"attempts": 3, "last_error": "Connection refused"},
        ... )

    """

    pass


class MCPTimeoutError(MCPError):
    """Raised when MCP tool execution times out.

    Attributes:
        timeout_seconds: The timeout threshold that was exceeded
        tool_name: Name of the tool that timed out

    """

    def __init__(
        self,
        message: str,
        *,
        server_name: str | None = None,
        tool_name: str | None = None,
        timeout_seconds: float | None = None,
        details: dict | None = None,
    ) -> None:
        """Initialize timeout error.

        Args:
            message: Error description
            server_name: MCP server name
            tool_name: Name of the tool that timed out
            timeout_seconds: The timeout threshold exceeded
            details: Additional context

        """
        super().__init__(message, server_name=server_name, details=details)
        self.tool_name = tool_name
        self.timeout_seconds = timeout_seconds


class MCPToolError(MCPError):
    """Raised when MCP tool invocation fails.

    This includes:
    - Tool not found
    - Invalid tool arguments
    - Tool execution errors
    - Tool returned error response

    Attributes:
        tool_name: Name of the tool that failed
        error_code: Optional error code from tool response

    """

    def __init__(
        self,
        message: str,
        *,
        server_name: str | None = None,
        tool_name: str | None = None,
        error_code: str | None = None,
        details: dict | None = None,
    ) -> None:
        """Initialize tool error.

        Args:
            message: Error description
            server_name: MCP server name
            tool_name: Name of the failed tool
            error_code: Error code from tool response
            details: Additional context

        """
        super().__init__(message, server_name=server_name, details=details)
        self.tool_name = tool_name
        self.error_code = error_code


class MCPConfigurationError(MCPError):
    """Raised when MCP configuration is invalid.

    This includes:
    - Missing required configuration
    - Invalid transport type
    - Missing command for stdio transport
    - Missing URL for HTTP transport

    """

    pass
