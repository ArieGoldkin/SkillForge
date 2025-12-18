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
