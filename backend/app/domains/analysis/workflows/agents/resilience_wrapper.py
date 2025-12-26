"""Resilience wrapper for agent execution with tier-based bulkheads.

Issue #533: Provides a decorator and helper function to wrap agent nodes with
tier-based bulkheads for resource isolation.

This prevents cascade failures by:
1. Circuit breaker: Fast-fail on repeated LLM API failures (in invocation.py)
2. Bulkhead: Tier-based concurrency limits to prevent resource exhaustion

Usage in agent nodes:
    >>> from app.domains.analysis.workflows.agents.resilience_wrapper import (
    ...     execute_with_resilience,
    ... )
    >>> from app.domains.analysis.agents.registry import AgentTier
    >>>
    >>> async def key_insights_node(state: AnalysisState) -> dict[str, object]:
    ...     return await execute_with_resilience(
    ...         agent_type="key_insights",
    ...         tier=AgentTier.UNIVERSAL,
    ...         fn=lambda: run_key_insights(state),
    ...     )

This wraps the agent execution with:
1. Tier-based bulkhead (from resilience.py)
2. Graceful error handling
3. Logging and observability
"""

from __future__ import annotations

from typing import TYPE_CHECKING, TypeVar

from app.core.logging import get_logger
from app.core.resilience import get_resilience_manager

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable

logger = get_logger(__name__)

T = TypeVar("T")


async def execute_with_resilience(  # noqa: UP047 - Python 3.12+ syntax
    agent_type: str,
    tier: int,  # AgentTier enum value (1, 2, 3)
    fn: Callable[[], Awaitable[T]],
) -> T:
    """Execute agent with tier-based bulkhead protection.

    This is a convenience wrapper around ResilienceManager.execute_agent()
    that provides a simple interface for agent nodes.

    Args:
        agent_type: Agent type name (for logging)
        tier: Agent tier (AgentTier.UNIVERSAL = 1, VALIDATION = 2, RESEARCH = 3)
        fn: Async function to execute (use lambda to capture state)

    Returns:
        Result from fn

    Raises:
        BulkheadFullError: If tier bulkhead queue is full
        BulkheadTimeoutError: If execution times out
        CircuitBreakerOpenError: If LLM API circuit breaker is open
        Exception: Original exception from fn

    Example:
        >>> async def my_agent_node(state: AnalysisState) -> dict[str, object]:
        ...     # Issue #441: Skip if workflow is aborting
        ...     from app.domains.analysis.workflows.utils.abort_helpers import (
        ...         check_should_abort,
        ...     )
        ...
        ...     abort_result = check_should_abort(state)
        ...     if abort_result is None:
        ...         return {}
        ...
        ...     # Execute with resilience
        ...     return await execute_with_resilience(
        ...         agent_type="my_agent",
        ...         tier=AgentTier.UNIVERSAL,
        ...         fn=lambda: run_my_agent(state),
        ...     )

    """
    resilience_manager = get_resilience_manager()

    logger.debug(
        "executing_agent_with_resilience_wrapper",
        agent_type=agent_type,
        tier=tier,
    )

    try:
        result = await resilience_manager.execute_agent(
            agent_type=agent_type,
            tier=tier,
            fn=fn,
        )
        assert result is not None  # noqa: S101 - Type guard for execute_agent
        return result
    except Exception as e:
        # Log resilience failures but re-raise for agent node error handling
        logger.warning(
            "resilience_wrapper_exception",
            agent_type=agent_type,
            tier=tier,
            error_type=type(e).__name__,
            error=str(e),
        )
        raise
