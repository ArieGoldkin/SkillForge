"""Agent invocation logic with fallback strategies.

This module handles different agent invocation methods:
- Streaming (preferred)
- Async invoke (fallback)
- Sync invoke in thread pool (last resort)

Timeout handling is managed by LangGraph's step_timeout on the compiled graph.
This is the recommended approach per LangGraph best practices, avoiding
PEP 789 violations and nested timeout conflicts.
"""

import time
from typing import cast

from langchain_core.runnables import Runnable
from langsmith import get_current_run_tree

from app.core.logging import get_logger
from app.core.timeout_config import AGENT_TIMEOUT, STEP_TIMEOUT, create_runnable_config
from app.core.types import AnalysisID
from app.workflows.agents.streaming import stream_agent_response

logger = get_logger(__name__)


async def invoke_agent(
    agent: Runnable,
    input_messages: dict[str, list[dict[str, str]]],
    analysis_id: AnalysisID,
    agent_type: str,
    timeout: float = AGENT_TIMEOUT,  # Kept for logging/reference, but step_timeout handles actual timeout
) -> dict[str, object]:
    """Invoke agent - timeout handled by LangGraph's step_timeout.

    Timeout handling is managed by LangGraph's `step_timeout` on the compiled graph.
    This avoids nested timeout conflicts and PEP 789 violations.

    When streaming returns an empty dict (no result), this function raises TimeoutError
    to maintain the timeout error contract for callers.

    Args:
        agent: Agent instance to invoke
        input_messages: Input messages for the agent
        analysis_id: UUID of the analysis
        agent_type: Type of agent for logging
        timeout: Reference timeout value (for logging only - step_timeout handles actual timeout)

    Returns:
        Result dictionary from agent execution

    Raises:
        TimeoutError: If invocation returns empty result (timeout/cancellation)
        Exception: For other invocation errors

    """
    start_time = time.time()

    # Get LangSmith trace ID for correlation if available
    trace_id: str | None = None
    try:
        run_tree = get_current_run_tree()
        if run_tree and hasattr(run_tree, "id"):
            trace_id = str(run_tree.id)
    except Exception:
        # LangSmith not available or not in trace context - continue without trace_id
        pass

    # Create RunnableConfig (timeout handled by step_timeout on graph)
    config = create_runnable_config()

    # Check if agent supports streaming (must be callable)
    agent_has_streaming = callable(getattr(agent, "astream", None))
    if agent_has_streaming:
        # Stream agent execution (preferred - shows progress)
        try:
            result = await stream_agent_response(
                agent=agent,
                input_messages=input_messages,
                analysis_id=analysis_id,
                agent_type=agent_type,
                timeout=timeout,
            )
            # If streaming returned empty dict (no result), raise TimeoutError
            if not result:
                duration = time.time() - start_time
                msg = f"Agent {agent_type} exceeded timeout of {timeout}s"
                logger.warning(
                    "agent_stream_timeout",
                    agent_type=agent_type,
                    analysis_id=analysis_id,
                    timeout_reference=timeout,
                    step_timeout=STEP_TIMEOUT,
                    duration_seconds=duration,
                    trace_id=trace_id,
                    handled_gracefully=False,  # Raises TimeoutError
                )
                raise TimeoutError(msg) from None
            return result
        except TimeoutError:
            # Re-raise TimeoutError as-is (already logged in stream_agent_response)
            raise
        except Exception as e:
            duration = time.time() - start_time
            logger.error(
                "agent_invocation_error",
                agent_type=agent_type,
                analysis_id=analysis_id,
                invocation_method="streaming",
                error_type=type(e).__name__,
                error=str(e),
                duration_seconds=duration,
                timeout_reference=timeout,
                step_timeout=STEP_TIMEOUT,
                trace_id=trace_id,
                exc_info=True,
            )
            raise
    elif hasattr(agent, "ainvoke"):
        # Async invoke - no timeout wrapper (step_timeout handles it)
        try:
            result = await agent.ainvoke(input_messages, config=config)
            return cast(dict[str, object], result)
        except Exception as e:
            duration = time.time() - start_time
            logger.error(
                "agent_invocation_error",
                agent_type=agent_type,
                analysis_id=analysis_id,
                invocation_method="ainvoke",
                error_type=type(e).__name__,
                error=str(e),
                duration_seconds=duration,
                timeout_reference=timeout,
                step_timeout=STEP_TIMEOUT,
                trace_id=trace_id,
                exc_info=True,
            )
            raise
    else:
        # Sync invoke in thread pool - no timeout wrapper (step_timeout handles it)
        import asyncio

        try:
            result = await asyncio.to_thread(agent.invoke, input_messages)
            return cast(dict[str, object], result)
        except Exception as e:
            duration = time.time() - start_time
            logger.error(
                "agent_invocation_error",
                agent_type=agent_type,
                analysis_id=analysis_id,
                invocation_method="sync_thread",
                error_type=type(e).__name__,
                error=str(e),
                duration_seconds=duration,
                timeout_reference=timeout,
                step_timeout=STEP_TIMEOUT,
                trace_id=trace_id,
                exc_info=True,
            )
            raise
