"""Exception enrichment utilities for 2025 best practices.

This module provides utilities for adding context to exceptions using Python 3.11+
add_note() functionality, wrapping external errors, and managing agent error groups.

Key Features:
- Exception enrichment with contextual notes
- Sync and async context managers for automatic enrichment
- External service error wrapping with service context
- Agent error collection from asyncio.gather results
- Retryable error detection
- Exception chain formatting for logging

Example:
    >>> # Enrich exception with context
    >>> try:
    ...     risky_operation()
    ... except Exception as e:
    ...     enrich_exception(e, user_id="123", stage="validation")
    ...     raise

    >>> # Use context manager
    >>> with exception_context(agent="key_insights", analysis_id="abc123"):
    ...     process_data()

    >>> # Async context manager
    >>> async with async_exception_context(stage="fetch", url=url):
    ...     await fetch_data()

"""

from __future__ import annotations

import contextlib
from typing import TYPE_CHECKING, Any

from app.core.exceptions import (
    AgentGroupError,
    ExternalServiceError,
    RetryableError,
)

if TYPE_CHECKING:
    from collections.abc import AsyncIterator, Iterator


def enrich_exception(exc: BaseException, **context: Any) -> None:
    """Add contextual notes to an exception using Python 3.11+ add_note().

    Each key-value pair in context becomes a note attached to the exception,
    preserving the original exception type while adding debugging information.

    Args:
        exc: The exception to enrich with contextual notes
        **context: Key-value pairs to add as notes (e.g., agent="key_insights")

    Example:
        >>> try:
        ...     analyze_document(doc_id)
        ... except ValueError as e:
        ...     enrich_exception(e, agent="key_insights", doc_id=doc_id)
        ...     raise  # Re-raise with added context

    Note:
        This function modifies the exception in-place. It should typically be
        called in an except block before re-raising the exception.

    """
    for key, value in context.items():
        exc.add_note(f"{key}={value}")


@contextlib.contextmanager
def exception_context(**context: Any) -> Iterator[None]:
    """Add notes to any exception raised within this context.

    Automatically enriches any exception raised within the context with the
    provided key-value pairs, then re-raises the exception.

    Args:
        **context: Key-value pairs to add as notes to any exception

    Yields:
        None

    Raises:
        Any exception raised in the context, enriched with context notes

    Example:
        >>> with exception_context(stage="fetch", url="https://example.com"):
        ...     data = fetch_data()  # If this raises, exception gets enriched

        >>> with exception_context(agent="key_insights", analysis_id="abc123"):
        ...     results = process_analysis()

    """
    try:
        yield
    except BaseException as e:
        enrich_exception(e, **context)
        raise


@contextlib.asynccontextmanager
async def async_exception_context(**context: Any) -> AsyncIterator[None]:
    """Asynchronous context manager that adds notes to any exception raised.

    Async version of exception_context() for use with async code. Automatically
    enriches any exception raised within the async context.

    Args:
        **context: Key-value pairs to add as notes to any exception

    Yields:
        None

    Raises:
        Any exception raised in the context, enriched with context notes

    Example:
        >>> async with async_exception_context(agent="key_insights"):
        ...     results = await analyze_content()

        >>> async with async_exception_context(stage="embedding", model="text-3-small"):
        ...     embeddings = await generate_embeddings(text)

    """
    try:
        yield
    except BaseException as e:
        enrich_exception(e, **context)
        raise


def wrap_external_error(exc: Exception, service: str) -> ExternalServiceError:
    """Wrap an external service error with service context.

    Creates an ExternalServiceError that wraps the original exception,
    preserving the exception chain while adding service identification.

    Args:
        exc: The original exception from the external service
        service: Name of the external service (e.g., "openai", "redis", "postgres")

    Returns:
        ExternalServiceError wrapping the original exception

    Example:
        >>> try:
        ...     await openai_client.embeddings.create(...)
        ... except Exception as e:
        ...     raise wrap_external_error(e, "openai")

        >>> try:
        ...     await redis.get(key)
        ... except Exception as e:
        ...     raise wrap_external_error(e, "redis")

    """
    error = ExternalServiceError(
        service_name=service,
        message=f"{service} error: {exc}",
    )
    # Preserve exception chain
    error.__cause__ = exc
    return error


def collect_agent_errors(results: list[Any]) -> AgentGroupError | None:
    """Collect errors from asyncio.gather results with return_exceptions=True.

    Filters out successful results and collects only Exception instances,
    creating an AgentGroupError if any errors occurred.

    Args:
        results: List of results from asyncio.gather(..., return_exceptions=True)

    Returns:
        AgentGroupError if any exceptions found, None otherwise

    Example:
        >>> results = await asyncio.gather(
        ...     agent1.analyze(content),
        ...     agent2.analyze(content),
        ...     agent3.analyze(content),
        ...     return_exceptions=True,
        ... )
        >>> if error := collect_agent_errors(results):
        ...     logger.error(f"Agent failures: {error}")
        ...     # Continue with successful results

    Note:
        This allows partial success - you can process successful results
        even if some agents failed.

    """
    errors = [r for r in results if isinstance(r, Exception)]
    if not errors:
        return None

    return AgentGroupError(
        f"{len(errors)} agent(s) failed",
        errors,
    )


def is_retryable(exc: Exception) -> bool:
    """Check if an exception represents a retryable/transient error.

    Determines whether an error is likely transient and should be retried,
    based on the exception type.

    Args:
        exc: The exception to check

    Returns:
        True if the error is retryable, False otherwise

    Example:
        >>> try:
        ...     await call_external_api()
        ... except Exception as e:
        ...     if is_retryable(e):
        ...         logger.warning("Retryable error, will retry")
        ...         await asyncio.sleep(backoff_delay)
        ...         await call_external_api()
        ...     else:
        ...         logger.error("Non-retryable error")
        ...         raise

    Note:
        Checks for:
        - RetryableError (explicit retry marker)
        - ConnectionError (network issues)
        - TimeoutError (operation timeout)
        - httpx.TimeoutException (HTTP client timeout)

    """
    # Check explicit RetryableError
    if isinstance(exc, RetryableError):
        return True

    # Check known transient errors
    if isinstance(exc, (ConnectionError, TimeoutError)):
        return True

    # Check httpx timeout (avoid import if not needed)
    return exc.__class__.__name__ == "TimeoutException" and exc.__class__.__module__.startswith(
        "httpx"
    )


def format_exception_chain(exc: BaseException) -> str:
    """Format exception with its __cause__ chain for logging.

    Creates a multi-line string showing the full exception chain,
    useful for detailed error logging and debugging.

    Args:
        exc: The exception to format

    Returns:
        Multi-line string showing the exception and its chain

    Example:
        >>> try:
        ...     try:
        ...         int("invalid")
        ...     except ValueError as e:
        ...         raise ExternalServiceError("redis", "Parse failed") from e
        ... except Exception as e:
        ...     logger.error(format_exception_chain(e))

        Output:
        ExternalServiceError: Parse failed
        Caused by: ValueError: invalid literal for int() with base 10: 'invalid'

    Note:
        Includes exception notes added via add_note() if present.

    """
    lines = []
    current = exc

    while current is not None:
        # Add exception type and message
        exc_type = type(current).__name__
        exc_msg = str(current)
        lines.append(f"{exc_type}: {exc_msg}")

        # Add notes if present (Python 3.11+)
        if hasattr(current, "__notes__") and current.__notes__:
            lines.extend(f"  Note: {note}" for note in current.__notes__)

        # Move to cause
        if current.__cause__:
            lines.append("Caused by:")
            current = current.__cause__
        else:
            break

    return "\n".join(lines)
