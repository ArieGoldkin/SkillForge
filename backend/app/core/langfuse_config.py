"""Langfuse observability configuration.

This module configures Langfuse for LLM observability, replacing Langfuse.
Langfuse handles async generators natively - no workarounds needed!

Benefits over Langfuse:
- Self-hosted (FREE, no per-trace costs)
- Native async generator handling (no filtering workarounds)
- ClickHouse for fast analytics at scale
- Native MCP server at /api/public/mcp
"""

import os
from typing import Any

from app.core.logging import get_logger

logger = get_logger(__name__)

# Global Langfuse client instance (singleton)
_langfuse_client: Any = None


def get_langfuse_client() -> Any:
    """Get or create Langfuse client singleton.

    Returns:
        Langfuse client instance, or None if Langfuse is disabled

    """
    global _langfuse_client  # noqa: PLW0603 - Module-level singleton pattern

    if _langfuse_client is not None:
        return _langfuse_client

    # Check if Langfuse is enabled
    langfuse_enabled = os.getenv("LANGFUSE_ENABLED", "false").lower() == "true"
    if not langfuse_enabled:
        logger.debug("langfuse_not_enabled", message="Langfuse tracing disabled")
        return None

    # Check for required credentials
    public_key = os.getenv("LANGFUSE_PUBLIC_KEY")
    secret_key = os.getenv("LANGFUSE_SECRET_KEY")

    if not public_key or not secret_key:
        logger.warning(
            "langfuse_credentials_missing",
            message="Langfuse enabled but LANGFUSE_PUBLIC_KEY or LANGFUSE_SECRET_KEY not set",
            public_key_set=bool(public_key),
            secret_key_set=bool(secret_key),
        )
        return None

    try:
        from langfuse import Langfuse

        # Create Langfuse client - auto-configures from environment variables:
        # LANGFUSE_PUBLIC_KEY, LANGFUSE_SECRET_KEY, LANGFUSE_HOST
        _langfuse_client = Langfuse(
            public_key=public_key,
            secret_key=secret_key,
            host=os.getenv("LANGFUSE_HOST", "http://localhost:3000"),
            release=os.getenv("LANGFUSE_RELEASE"),
            tracing_enabled=True,
        )

        logger.info(
            "langfuse_client_configured",
            message="Langfuse client configured successfully",
            host=os.getenv("LANGFUSE_HOST", "http://localhost:3000"),
        )

        return _langfuse_client

    except ImportError:
        logger.warning(
            "langfuse_import_failed",
            message="Langfuse package not installed, run: poetry add langfuse",
        )
        return None
    except Exception as e:
        logger.error(
            "langfuse_configuration_failed",
            error_type=type(e).__name__,
            error=str(e),
            exc_info=True,
        )
        return None


def configure_langfuse_client() -> None:
    """Configure Langfuse client on application startup.

    This should be called during application lifespan startup.
    Unlike Langfuse, no generator filtering workarounds are needed.

    """
    client = get_langfuse_client()
    if client:
        logger.info(
            "langfuse_startup_complete",
            message="Langfuse observability ready",
        )


def flush_langfuse() -> None:
    """Flush pending Langfuse events.

    Call this before application shutdown or in serverless environments
    to ensure all traces are sent.

    """
    if _langfuse_client is not None:
        try:
            _langfuse_client.flush()
            logger.debug("langfuse_flushed", message="Langfuse events flushed")
        except Exception as e:
            logger.error(
                "langfuse_flush_failed",
                error=str(e),
                exc_info=True,
            )


def shutdown_langfuse() -> None:
    """Shutdown Langfuse client gracefully.

    Call this during application shutdown.

    """
    global _langfuse_client  # noqa: PLW0603

    if _langfuse_client is not None:
        try:
            _langfuse_client.flush()
            _langfuse_client.shutdown()
            logger.info("langfuse_shutdown_complete", message="Langfuse client shutdown")
        except Exception as e:
            logger.error(
                "langfuse_shutdown_failed",
                error=str(e),
                exc_info=True,
            )
        finally:
            _langfuse_client = None


def submit_langfuse_score(
    *,
    trace_id: str | None = None,
    name: str,
    value: float,
    comment: str | None = None,
) -> None:
    """Submit a score to Langfuse for quality tracking.

    Scores enable quality analytics in Langfuse UI including:
    - Score distributions over time
    - Filtering traces by score
    - Correlation analysis between scores

    Args:
        trace_id: Trace ID to attach score to (uses current if not provided)
        name: Score name (e.g., "relevance", "depth", "coherence")
        value: Score value (typically 0.0 to 1.0)
        comment: Optional comment explaining the score

    Example:
        >>> from app.core.langfuse_config import submit_langfuse_score
        >>> submit_langfuse_score(name="relevance", value=0.85, comment="High relevance")

    """
    langfuse_enabled = os.getenv("LANGFUSE_ENABLED", "false").lower() == "true"
    if not langfuse_enabled:
        return

    client = get_langfuse_client()
    if not client:
        return

    try:
        # If no trace_id provided, try to get current trace
        if trace_id is None:
            trace_id = client.get_current_trace_id()

        if trace_id is None:
            logger.debug(
                "langfuse_score_skipped_no_trace",
                message="No trace context available for score submission",
                score_name=name,
            )
            return

        client.score(
            trace_id=str(trace_id),
            name=name,
            value=value,
            comment=comment,
        )

        logger.debug(
            "langfuse_score_submitted",
            trace_id=str(trace_id),
            score_name=name,
            score_value=value,
        )

    except Exception as e:  # noqa: BLE001 - Graceful degradation for observability
        logger.warning(
            "langfuse_score_failed",
            error=str(e),
            score_name=name,
            exc_info=True,
        )


def get_langfuse_callback_handler() -> Any:
    """Get Langfuse CallbackHandler for LangChain integration.

    This callback handler captures LLM calls with token counts and costs,
    enabling full observability in Langfuse including:
    - Input/output tokens
    - Cost tracking per model
    - LLM generation spans with metadata

    Note: Langfuse v3 CallbackHandler auto-configures from environment variables:
    - LANGFUSE_PUBLIC_KEY
    - LANGFUSE_SECRET_KEY
    - LANGFUSE_HOST

    Returns:
        CallbackHandler instance, or None if Langfuse is disabled

    Example:
        >>> from app.core.langfuse_config import get_langfuse_callback_handler
        >>> callbacks = [get_langfuse_callback_handler()] if get_langfuse_callback_handler() else []
        >>> result = await chain.ainvoke(input, config={"callbacks": callbacks})

    """
    # Check if Langfuse is enabled
    langfuse_enabled = os.getenv("LANGFUSE_ENABLED", "false").lower() == "true"
    if not langfuse_enabled:
        return None

    # Check for required credentials (CallbackHandler reads from env vars)
    public_key = os.getenv("LANGFUSE_PUBLIC_KEY")
    secret_key = os.getenv("LANGFUSE_SECRET_KEY")

    if not public_key or not secret_key:
        return None

    try:
        from langfuse.langchain import CallbackHandler

        # Langfuse v3 CallbackHandler auto-configures from environment variables
        # No need to pass credentials explicitly
        handler = CallbackHandler()

        logger.debug(
            "langfuse_callback_created",
            message="Langfuse CallbackHandler created for LangChain integration",
        )

        return handler

    except ImportError:
        logger.warning(
            "langfuse_callback_import_failed",
            message="langfuse.langchain not available - install langfuse[langchain]",
        )
        return None
    except Exception:
        logger.exception("langfuse_callback_failed")
        return None
