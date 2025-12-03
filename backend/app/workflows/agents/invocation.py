"""Agent invocation logic with fallback strategies.

This module handles different agent invocation methods:
- Async invoke (preferred - avoids GeneratorExit issues in LangSmith)
- Sync invoke in thread pool (last resort)

Note: We intentionally use ainvoke instead of astream to avoid GeneratorExit
false positives in LangSmith tracing. The astream method creates async generators
that, when closed during cleanup, trigger GeneratorExit which LangSmith logs as
errors even though the workflow completed successfully.

See: https://github.com/langchain-ai/langchain/issues/24914

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

logger = get_logger(__name__)


async def invoke_agent(
    agent: Runnable,
    input_messages: dict[str, list[dict[str, str]]],
    analysis_id: AnalysisID,
    agent_type: str,
    timeout: float = AGENT_TIMEOUT,  # For logging/reference; step_timeout handles actual timeout
) -> dict[str, object]:
    """Invoke agent using ainvoke - timeout handled by LangGraph's step_timeout.

    Uses ainvoke instead of astream to avoid GeneratorExit false positives in
    LangSmith tracing. The astream method creates async generators that trigger
    GeneratorExit during cleanup, which LangSmith incorrectly logs as errors.

    Timeout handling is managed by LangGraph's `step_timeout` on the compiled graph.
    This avoids nested timeout conflicts and PEP 789 violations.

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

    # Use ainvoke (preferred) - avoids GeneratorExit issues with astream
    # astream creates async generators that trigger false error logs in LangSmith
    if hasattr(agent, "ainvoke"):
        # Async invoke - no timeout wrapper (step_timeout handles it)
        try:
            logger.debug(
                "agent_invocation_started",
                agent_type=agent_type,
                analysis_id=analysis_id,
                invocation_method="ainvoke",
                trace_id=trace_id,
            )
            result = await agent.ainvoke(input_messages, config=config)
            duration = time.time() - start_time
            logger.info(
                "agent_invocation_success",
                agent_type=agent_type,
                analysis_id=analysis_id,
                invocation_method="ainvoke",
                duration_seconds=duration,
                trace_id=trace_id,
            )
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
