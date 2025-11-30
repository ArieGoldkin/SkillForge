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
    timeout: float = AGENT_TIMEOUT,  # For logging/reference; step_timeout handles actual timeout
) -> dict[str, object]:
    """Invoke agent - timeout handled by LangGraph's step_timeout.

    Timeout handling is managed by LangGraph's `step_timeout` on the compiled graph.
    This avoids nested timeout conflicts and PEP 789 violations.

    When streaming returns an empty dict, this means the agent cannot process the content
    (e.g., wrong content type), not a timeout. Returns empty dict gracefully to allow
    workflow to continue with other agents.

    Args:
        agent: Agent instance to invoke
        input_messages: Input messages for the agent
        analysis_id: UUID of the analysis
        agent_type: Type of agent for logging
        timeout: Reference timeout value (for logging only - step_timeout handles actual timeout)

    Returns:
        Result dictionary from agent execution, or empty dict if agent cannot process content

    Raises:
        TimeoutError: If actual timeout occurred during execution
        Exception: For other invocation errors

    """
    start_time = time.time()

    # Get LangSmith trace ID for correlation if available
    trace_id: str | None = None
    try:
        run_tree = get_current_run_tree()
        if run_tree and hasattr(run_tree, "id"):
            trace_id = str(run_tree.id)
    except Exception:  # noqa: BLE001 - LangSmith may not be available, catch all to continue
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
            # Empty dict means agent can't process content, not a timeout
            # Return gracefully to allow workflow to continue with other agents
            if not result:
                duration = time.time() - start_time
                logger.info(
                    "agent_empty_result",
                    agent_type=agent_type,
                    analysis_id=analysis_id,
                    duration_seconds=duration,
                    timeout_reference=timeout,
                    step_timeout=STEP_TIMEOUT,
                    trace_id=trace_id,
                    reason="agent_cannot_process_content_type",
                    handled_gracefully=True,  # Returns empty dict, doesn't break workflow
                )
                return {}  # Return empty dict gracefully, not raise TimeoutError
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
