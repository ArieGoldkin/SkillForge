"""MCP callbacks for real-time notifications during tool execution.

Provides integration between langchain-mcp-adapters 0.2 callbacks and SkillForge's
observability stack (Langfuse, structlog, SSE broadcasting).

Issue #444: Updated to use broadcaster factory for multi-instance support.
Uses Redis Pub/Sub when available, falls back to in-memory broadcaster.

Architecture:
    MCP Server Tool Execution
            |
            v
    langchain-mcp-adapters Callbacks (on_logging, on_progress)
            |
            v
    MCPCallbacks (this module)
            |
            +-- Langfuse observability (trace/observation updates)
            +-- Structlog (structured logging)
            +-- BroadcasterFactory (Redis/in-memory SSE for frontend progress)

Features:
    - Real-time progress updates during MCP tool execution
    - Structured logging of MCP server messages
    - Langfuse trace/observation updates for observability
    - SSE broadcasting for frontend progress bars
    - Configurable integration (enable/disable each component)

Example:
    >>> callbacks = MCPCallbacks.create(
    ...     analysis_id="abc123",
    ...     enable_langfuse=True,
    ...     enable_sse=True,
    ... )
    >>> # Use with MCP client
    >>> client = MultiServerMCPClient(config, callbacks=callbacks.to_callbacks())

Note:
    This module requires langchain-mcp-adapters >= 0.2.0 for callback support.
    For earlier versions, callbacks are ignored gracefully.

"""

from __future__ import annotations

import os
from typing import Any

from app.core.config import get_settings
from app.core.logging import get_logger
from app.shared.services.messaging.broadcaster_factory import (
    BroadcasterBackend,
    get_broadcaster,
)

logger = get_logger(__name__)


def _get_broadcaster_backend() -> BroadcasterBackend:
    """Get broadcaster backend from settings."""
    settings = get_settings()
    backend_str = settings.BROADCASTER_BACKEND.lower()
    return BroadcasterBackend(backend_str)


# ============================================================================
# Import MCP Callback Types
# ============================================================================

# Try to import from langchain-mcp-adapters (provides Protocol-based types)
try:
    from langchain_mcp_adapters.callbacks import (
        CallbackContext,
        Callbacks,
        LoggingMessageNotificationParams,
    )

    _MCP_CALLBACKS_AVAILABLE = True

except ImportError:
    # Fallback placeholder types when langchain-mcp-adapters not available
    from dataclasses import dataclass

    @dataclass
    class CallbackContext:  # type: ignore[no-redef]
        """Context provided to MCP callbacks (placeholder).

        Attributes:
            server_name: Name of the MCP server executing the tool
            tool_name: Name of the tool being executed (optional)

        """

        server_name: str
        tool_name: str | None = None

    @dataclass
    class LoggingMessageNotificationParams:  # type: ignore[no-redef]
        """Parameters for logging message notifications (placeholder).

        Attributes:
            level: Log level (debug, info, warning, error, critical)
            data: Log message content (string or structured data)
            logger: Optional logger name from the MCP server

        """

        level: str
        data: str | dict[str, Any]
        logger: str | None = None

    @dataclass
    class Callbacks:  # type: ignore[no-redef]
        """Callbacks for the LangChain MCP client (placeholder)."""

        on_logging_message: Any = None
        on_progress: Any = None

    _MCP_CALLBACKS_AVAILABLE = False


# ============================================================================
# SkillForge MCP Callbacks Implementation
# ============================================================================


class MCPCallbacks:
    """MCP callback handler with SkillForge observability integration.

    Handles real-time notifications from MCP servers during tool execution,
    integrating with Langfuse, structlog, and SSE broadcasting.

    Configuration:
        - enable_langfuse: Update Langfuse traces/observations
        - enable_sse: Broadcast progress to frontend via SSE
        - enable_logging: Log to structlog (always recommended)
        - analysis_id: For SSE channel routing (workflow:analysis_id)

    Thread Safety:
        Safe for concurrent use - all integrations are thread-safe

    Example:
        >>> callbacks = MCPCallbacks(
        ...     analysis_id="abc123",
        ...     enable_langfuse=True,
        ...     enable_sse=True,
        ... )
        >>> # Access underlying Callbacks object
        >>> langchain_callbacks = callbacks.to_callbacks()

    """

    def __init__(
        self,
        *,
        analysis_id: str | None = None,
        enable_langfuse: bool = True,
        enable_sse: bool = True,
        enable_logging: bool = True,
    ) -> None:
        """Initialize MCP callbacks.

        Args:
            analysis_id: Analysis ID for SSE channel routing
            enable_langfuse: Whether to update Langfuse traces (default: True)
            enable_sse: Whether to broadcast via SSE (default: True)
            enable_logging: Whether to log to structlog (default: True)

        """
        self.analysis_id = analysis_id
        self.enable_langfuse = enable_langfuse and self._is_langfuse_available()
        self.enable_sse = enable_sse
        self.enable_logging = enable_logging

        logger.debug(
            "mcp_callbacks_initialized",
            analysis_id=analysis_id,
            langfuse_enabled=self.enable_langfuse,
            sse_enabled=self.enable_sse,
            logging_enabled=self.enable_logging,
        )

    @classmethod
    def create(
        cls,
        *,
        analysis_id: str | None = None,
        enable_langfuse: bool = True,
        enable_sse: bool = True,
        enable_logging: bool = True,
    ) -> MCPCallbacks:
        """Create callbacks with specified configuration.

        Args:
            analysis_id: Analysis ID for SSE channel routing
            enable_langfuse: Whether to update Langfuse traces
            enable_sse: Whether to broadcast via SSE
            enable_logging: Whether to log to structlog

        Returns:
            Configured MCPCallbacks instance

        """
        return cls(
            analysis_id=analysis_id,
            enable_langfuse=enable_langfuse,
            enable_sse=enable_sse,
            enable_logging=enable_logging,
        )

    @staticmethod
    def _is_langfuse_available() -> bool:
        """Check if Langfuse is enabled and available.

        Returns:
            True if Langfuse can be used

        """
        # Check environment variable
        if os.getenv("LANGFUSE_ENABLED", "false").lower() != "true":
            return False

        # Check if langfuse package is available
        try:
            import langfuse  # noqa: F401

            return True
        except ImportError:
            logger.debug(
                "langfuse_not_available",
                message="Langfuse package not installed, callbacks will skip Langfuse integration",
            )
            return False

    # ========================================================================
    # Callback Handlers
    # ========================================================================

    async def on_logging_message(
        self,
        params: LoggingMessageNotificationParams,
        context: CallbackContext,
    ) -> None:
        """Handle logging messages from MCP servers.

        Called when an MCP server emits a log message during tool execution.
        Integrates with structlog and optionally Langfuse.

        Args:
            params: Logging message parameters (level, data, logger)
            context: Callback context (server_name, tool_name)

        """
        # Extract log data
        log_level = params.level.lower()
        log_data = params.data if isinstance(params.data, str) else str(params.data)
        mcp_logger = params.logger or "mcp_server"

        # Build log context
        log_context = {
            "mcp_server": context.server_name,
            "mcp_tool": context.tool_name,
            "mcp_logger": mcp_logger,
            "log_level": log_level,
        }

        if self.analysis_id:
            log_context["analysis_id"] = self.analysis_id

        # Log to structlog
        if self.enable_logging:
            log_method = getattr(logger, log_level, logger.info)
            log_method(
                "mcp_server_log",
                message=log_data,
                **log_context,
            )

        # Update Langfuse observation (if in trace context)
        if self.enable_langfuse:
            await self._update_langfuse_observation(
                event_type="mcp_log",
                data={
                    "level": log_level,
                    "message": log_data,
                    "server": context.server_name,
                    "tool": context.tool_name,
                    "logger": mcp_logger,
                },
            )

    async def on_progress(
        self,
        progress: float,
        total: float | None,
        message: str | None,
        context: CallbackContext,
    ) -> None:
        """Handle progress notifications from MCP servers.

        Called when an MCP server reports execution progress.
        Broadcasts to SSE for frontend progress bars and logs progress updates.

        Args:
            progress: Current progress value
            total: Total progress value (None if indeterminate)
            message: Optional progress message
            context: Callback context (server_name, tool_name)

        """
        # Calculate percentage if total is available
        percent = None
        if total is not None and total > 0:
            percent = (progress / total) * 100

        # Build progress context
        progress_data = {
            "mcp_server": context.server_name,
            "mcp_tool": context.tool_name,
            "progress": progress,
            "total": total,
            "percent": percent,
            "message": message,
        }

        if self.analysis_id:
            progress_data["analysis_id"] = self.analysis_id

        # Log progress
        if self.enable_logging:
            logger.info(
                "mcp_progress",
                **progress_data,
            )

        # Broadcast via SSE for frontend
        if self.enable_sse and self.analysis_id:
            await self._broadcast_sse_progress(
                server_name=context.server_name,
                tool_name=context.tool_name,
                progress=progress,
                total=total,
                percent=percent,
                message=message,
            )

        # Update Langfuse observation
        if self.enable_langfuse:
            await self._update_langfuse_observation(
                event_type="mcp_progress",
                data=progress_data,
            )

    # ========================================================================
    # Integration Helpers
    # ========================================================================

    async def _update_langfuse_observation(
        self,
        event_type: str,
        data: dict[str, Any],
    ) -> None:
        """Update current Langfuse observation with MCP event.

        Uses langfuse_context.update_current_observation() to add metadata
        to the current trace/observation context.

        Args:
            event_type: Type of event (mcp_log, mcp_progress)
            data: Event data to attach to observation

        """
        if not self.enable_langfuse:
            return

        try:
            from langfuse.decorators import langfuse_context  # type: ignore[import-untyped]

            # Update current observation with MCP event metadata
            langfuse_context.update_current_observation(
                metadata={
                    "mcp_event_type": event_type,
                    "mcp_event_data": data,
                }
            )

        except ImportError:
            # Langfuse not available, skip silently
            pass
        except Exception as e:  # noqa: BLE001 - Graceful degradation for observability
            # Log error but don't fail the callback
            logger.warning(
                "langfuse_observation_update_failed",
                error=str(e),
                event_type=event_type,
                exc_info=True,
            )

    async def _broadcast_sse_progress(  # noqa: PLR0913 - All parameters needed for progress events
        self,
        server_name: str,
        tool_name: str | None,
        progress: float,
        total: float | None,
        percent: float | None,
        message: str | None,
    ) -> None:
        """Broadcast progress update via SSE.

        Publishes progress event to the analysis-specific SSE channel
        for real-time frontend updates.

        Args:
            server_name: MCP server name
            tool_name: MCP tool name
            progress: Current progress value
            total: Total progress value
            percent: Progress percentage (if calculable)
            message: Progress message

        """
        if not self.enable_sse or not self.analysis_id:
            return

        try:
            # Build SSE event payload
            event_data = {
                "type": "mcp_progress",
                "server": server_name,
                "tool": tool_name or "unknown",
                "progress": progress,
                "total": total,
                "percent": round(percent, 1) if percent is not None else None,
                "message": message or f"{server_name} progress update",
            }

            # Issue #444: Get broadcaster from factory (Redis or in-memory based on config)
            broadcaster = await get_broadcaster(_get_broadcaster_backend())

            # Publish to analysis-specific channel
            channel = f"workflow:{self.analysis_id}"
            await broadcaster.publish(channel, event_data)

            logger.debug(
                "mcp_progress_broadcasted",
                channel=channel,
                server=server_name,
                tool=tool_name,
                percent=event_data["percent"],
            )

        except Exception as e:  # noqa: BLE001 - Graceful degradation for SSE
            # Log error but don't fail the callback
            logger.warning(
                "sse_broadcast_failed",
                error=str(e),
                analysis_id=self.analysis_id,
                exc_info=True,
            )

    # ========================================================================
    # LangChain MCP Adapters Integration
    # ========================================================================

    def to_callbacks(self) -> Callbacks | None:
        """Convert to langchain-mcp-adapters Callbacks object.

        Creates a Callbacks instance with this handler's methods bound
        as callback functions.

        Returns:
            Callbacks object for use with MultiServerMCPClient, or None
            if langchain-mcp-adapters 0.2 callbacks are not available

        Example:
            >>> mcp_callbacks = MCPCallbacks.create(analysis_id="abc123")
            >>> client = MultiServerMCPClient(config, callbacks=mcp_callbacks.to_callbacks())

        """
        if not _MCP_CALLBACKS_AVAILABLE:
            logger.debug(
                "mcp_callbacks_not_available",
                message="langchain-mcp-adapters not available, callbacks disabled",
            )
            return None

        return Callbacks(
            on_logging_message=self.on_logging_message,
            on_progress=self.on_progress,
        )


# ============================================================================
# Utility Functions
# ============================================================================


def create_mcp_callbacks(
    analysis_id: str | None = None,
    *,
    enable_langfuse: bool = True,
    enable_sse: bool = True,
    enable_logging: bool = True,
) -> Callbacks | None:
    """Create MCP callbacks with observability integration.

    Convenience function that creates MCPCallbacks and converts to
    langchain-mcp-adapters Callbacks format.

    Args:
        analysis_id: Analysis ID for SSE channel routing
        enable_langfuse: Whether to update Langfuse traces
        enable_sse: Whether to broadcast via SSE
        enable_logging: Whether to log to structlog

    Returns:
        Callbacks object or None if not available

    Example:
        >>> callbacks = create_mcp_callbacks(
        ...     analysis_id="abc123",
        ...     enable_langfuse=True,
        ... )
        >>> client = MultiServerMCPClient(config, callbacks=callbacks)

    """
    handler = MCPCallbacks.create(
        analysis_id=analysis_id,
        enable_langfuse=enable_langfuse,
        enable_sse=enable_sse,
        enable_logging=enable_logging,
    )
    return handler.to_callbacks()
