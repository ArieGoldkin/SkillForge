"""Timeout handling utilities for agent execution.

This module provides centralized timeout error handling to eliminate
duplication across workflow modules.
"""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import structlog


def convert_generatorexit_to_timeouterror(
    exc: GeneratorExit,
    context: str,
    timeout: float,
    logger: "structlog.BoundLogger",
    **log_context: object,
) -> TimeoutError:
    """Convert GeneratorExit to TimeoutError for consistent error handling.

    GeneratorExit occurs when asyncio.wait_for times out and cancels the task.
    This closes the async generator in LangGraph's astream, which raises GeneratorExit.
    We convert it to TimeoutError for consistent error handling and to prevent
    workflow failures (since we have graceful fallbacks).

    Args:
        exc: The GeneratorExit exception that was raised
        context: Description of the operation that timed out (e.g., "Agent execution")
        timeout: The timeout value that was exceeded (in seconds)
        logger: Structured logger instance for logging
        **log_context: Additional context for logging (e.g., agent_type, analysis_id)

    Returns:
        TimeoutError with descriptive message

    """
    msg = f"{context} exceeded timeout of {timeout}s (generator closed)"
    logger.warning(
        "timeout_generator_exit",
        context=context,
        timeout=timeout,
        **log_context,
    )
    return TimeoutError(msg)


def handle_timeout_error(
    exc: TimeoutError | GeneratorExit,
    context: str,
    timeout: float,
    logger: "structlog.BoundLogger",
    **log_context: object,
) -> TimeoutError:
    """Handle timeout errors (TimeoutError or GeneratorExit) consistently.

    Converts GeneratorExit to TimeoutError and logs appropriately.
    Re-raises TimeoutError with consistent message format.

    Args:
        exc: The timeout exception (TimeoutError or GeneratorExit)
        context: Description of the operation that timed out
        timeout: The timeout value that was exceeded (in seconds)
        logger: Structured logger instance for logging
        **log_context: Additional context for logging (e.g., agent_type, analysis_id)

    Returns:
        TimeoutError with descriptive message

    Raises:
        TimeoutError: Always raises TimeoutError (converted from GeneratorExit if needed)

    """
    if isinstance(exc, GeneratorExit):
        return convert_generatorexit_to_timeouterror(
            exc=exc,
            context=context,
            timeout=timeout,
            logger=logger,
            **log_context,
        )

    # Re-raise TimeoutError with consistent message
    msg = f"{context} exceeded timeout of {timeout}s"
    logger.exception(
        "timeout_error",
        context=context,
        timeout=timeout,
        **log_context,
    )
    return TimeoutError(msg)
