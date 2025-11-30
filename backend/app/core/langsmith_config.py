"""LangSmith Client configuration with generator filtering.

This module configures LangSmith Client to filter out generator objects
from inputs/outputs to prevent GeneratorExit errors during LangGraph's
internal streaming cleanup.

Problem:
    LangGraph's pregel module creates internal async generators when using
    agent.astream() for streaming. LangSmith's automatic tracing tries to
    serialize these generators, causing GeneratorExit during cleanup.

Solution:
    Configure LangSmith Client with hide_inputs/hide_outputs filters that
    recursively remove generator objects from dicts/lists before serialization.
"""

import inspect
from typing import Any

from app.core.logging import get_logger

logger = get_logger(__name__)


def _is_generator(obj: Any) -> bool:
    """Check if object is a generator or async generator.

    Args:
        obj: Object to check

    Returns:
        True if object is a generator or async generator, False otherwise
    """
    return inspect.isgenerator(obj) or inspect.isasyncgen(obj) or inspect.isgeneratorfunction(obj)


def _filter_generators(obj: Any) -> Any:
    """Recursively filter out generator objects from dicts/lists.

    This function removes generator objects from nested data structures
    to prevent LangSmith from trying to serialize them.

    Args:
        obj: Object to filter (dict, list, or any other type)

    Returns:
        Filtered object with generators removed
    """
    if _is_generator(obj):
        # Replace generator with a placeholder string
        return "<generator_filtered>"
    elif isinstance(obj, dict):
        # Recursively filter dict values
        filtered = {}
        for key, value in obj.items():
            if not _is_generator(value):
                filtered[key] = _filter_generators(value)
            else:
                # Log that we're filtering a generator (debug level)
                logger.debug(
                    "langsmith_filtering_generator",
                    key=key,
                    generator_type=type(value).__name__,
                )
        return filtered
    elif isinstance(obj, (list, tuple)):
        # Recursively filter list/tuple items
        filtered_list: list[Any] = [
            _filter_generators(item) if not _is_generator(item) else "<generator_filtered>"
            for item in obj
        ]
        # Preserve tuple type if input was tuple
        if isinstance(obj, tuple):
            return tuple(filtered_list)
        return filtered_list
    elif isinstance(obj, set):
        # Recursively filter set items
        filtered_set = {
            _filter_generators(item) if not _is_generator(item) else "<generator_filtered>"
            for item in obj
        }
        return filtered_set
    else:
        # Return primitive types and other objects as-is
        return obj


def hide_inputs_with_generator_filter(inputs: dict[str, Any]) -> dict[str, Any]:
    """Filter generators from LangSmith trace inputs.

    This function is used as hide_inputs parameter for LangSmith Client.
    It removes generator objects from inputs before LangSmith tries to serialize them.

    Args:
        inputs: Input dictionary from LangSmith trace

    Returns:
        Filtered dictionary with generators removed
    """
    filtered = _filter_generators(inputs)
    # Ensure return type is dict[str, Any]
    if isinstance(filtered, dict):
        return filtered
    # Fallback (shouldn't happen, but type checker needs it)
    return {}


def hide_outputs_with_generator_filter(outputs: dict[str, Any]) -> dict[str, Any]:
    """Filter generators from LangSmith trace outputs.

    This function is used as hide_outputs parameter for LangSmith Client.
    It removes generator objects from outputs before LangSmith tries to serialize them.

    Args:
        outputs: Output dictionary from LangSmith trace

    Returns:
        Filtered dictionary with generators removed
    """
    filtered = _filter_generators(outputs)
    # Ensure return type is dict[str, Any]
    if isinstance(filtered, dict):
        return filtered
    # Fallback (shouldn't happen, but type checker needs it)
    return {}


# Global Client instance (initialized on first use)
_langsmith_client: Any = None


def get_langsmith_client() -> Any:
    """Get or create LangSmith Client with generator filtering.

    Returns:
        LangSmith Client instance with generator filtering configured,
        or None if LangSmith is disabled
    """
    global _langsmith_client

    if _langsmith_client is not None:
        return _langsmith_client

    import os

    # Only configure if LangSmith tracing is enabled
    langsmith_enabled = os.getenv("LANGCHAIN_TRACING_V2") == "true"
    if not langsmith_enabled:
        logger.debug("langsmith_not_enabled", message="LangSmith tracing disabled")
        return None

    try:
        from langsmith import Client

        # Create Client with generator filtering
        _langsmith_client = Client(
            hide_inputs=hide_inputs_with_generator_filter,
            hide_outputs=hide_outputs_with_generator_filter,
        )

        logger.info(
            "langsmith_client_configured",
            message="LangSmith Client configured with generator filtering",
            hide_inputs=True,
            hide_outputs=True,
        )

        # Verify the client is accessible
        _ = _langsmith_client.info
        logger.debug("langsmith_client_verified", message="LangSmith Client verified")

        return _langsmith_client

    except ImportError:
        logger.warning(
            "langsmith_client_import_failed",
            message="LangSmith Client not available, skipping configuration",
        )
        return None
    except Exception as e:
        logger.error(
            "langsmith_client_configuration_failed",
            error_type=type(e).__name__,
            error=str(e),
            exc_info=True,
        )
        # Don't raise - allow application to continue without LangSmith configuration
        return None


def configure_langsmith_client() -> None:
    """Configure LangSmith Client with generator filtering.

    This function initializes the global LangSmith Client to filter out generator
    objects from inputs/outputs. This prevents GeneratorExit errors that occur
    when LangSmith tries to serialize generators created by LangGraph's internal
    streaming mechanisms.

    The Client is created on first use and cached for subsequent calls.

    Note:
        This should be called during application startup, before any LangGraph
        workflows are executed. However, it's safe to call multiple times as
        the Client is cached after first creation.
    """
    get_langsmith_client()
