"""Agent invocation logic with fallback strategies.

This module handles different agent invocation methods:
- Async invoke (preferred)
- Sync invoke in thread pool (last resort)

Note: Langfuse handles async generators natively, but we continue using ainvoke
for consistency and to avoid any potential generator cleanup issues.

Issue #299-304: Added asyncio.timeout() wrapper for LLM calls.
The LangGraph step_timeout only applies at graph node boundaries, but LLM API
calls can hang indefinitely waiting for a response. The asyncio.timeout wrapper
raises TimeoutError after the specified duration, which:
1. Triggers the with_fallbacks() chain to use fallback model
2. Ensures the workflow doesn't hang forever at "synthesizing"
3. Provides explicit timeout control independent of LangGraph
"""

import asyncio
import time
from typing import cast

from langchain_core.runnables import Runnable

from app.core.logging import get_logger
from app.core.timeout_config import AGENT_TIMEOUT, STEP_TIMEOUT, create_runnable_config
from app.core.tracing import get_current_trace_id
from app.core.types import AnalysisID

logger = get_logger(__name__)


async def invoke_agent(
    agent: Runnable,
    input_messages: dict[str, list[dict[str, str]]],
    analysis_id: AnalysisID,
    agent_type: str,
    timeout: float = AGENT_TIMEOUT,  # For logging/reference; step_timeout handles actual timeout  # noqa: ASYNC109 - Parameter for logging, not timeout control
) -> dict[str, object]:
    """Invoke agent using ainvoke - timeout handled by LangGraph's step_timeout.

    Uses ainvoke instead of astream to avoid GeneratorExit false positives in
    Langfuse tracing. The astream method creates async generators that trigger
    GeneratorExit during cleanup, which Langfuse incorrectly logs as errors.

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

    # Get Langfuse trace ID for correlation if available
    trace_id = get_current_trace_id()

    # Create RunnableConfig (timeout handled by step_timeout on graph)
    config = create_runnable_config()

    # Use ainvoke (preferred) - avoids GeneratorExit issues with astream
    # astream creates async generators that trigger false error logs in Langfuse
    if hasattr(agent, "ainvoke"):
        # Issue #299-304: Wrap with asyncio.timeout to prevent indefinite hanging
        # The timeout parameter is now actively used (not just for logging)
        # This raises TimeoutError which triggers with_fallbacks() chain
        try:
            logger.debug(
                "agent_invocation_started",
                agent_type=agent_type,
                analysis_id=analysis_id,
                invocation_method="ainvoke",
                timeout_seconds=timeout,
                trace_id=trace_id,
            )
            # asyncio.timeout raises TimeoutError if the call exceeds timeout
            # This is essential for triggering with_fallbacks() on hanging LLM calls
            async with asyncio.timeout(timeout):
                result = await agent.ainvoke(input_messages, config=config)
            duration = time.time() - start_time

            # Extract usage metadata (LangChain-Core 1.2.4+ feature)
            if hasattr(result, "usage_metadata") and result.usage_metadata:
                usage = result.usage_metadata
                logger.info(
                    "agent_token_usage",
                    agent_type=agent_type,
                    analysis_id=str(analysis_id),
                    input_tokens=usage.get("input_tokens", 0),
                    output_tokens=usage.get("output_tokens", 0),
                    total_tokens=usage.get("total_tokens", 0),
                )

            logger.info(
                "agent_invocation_success",
                agent_type=agent_type,
                analysis_id=analysis_id,
                invocation_method="ainvoke",
                duration_seconds=duration,
                trace_id=trace_id,
            )
            return cast("dict[str, object]", result)
        except TimeoutError:
            # Issue #299-304: Explicit timeout - convert to TimeoutError for with_fallbacks()
            duration = time.time() - start_time
            timeout_msg = f"Agent {agent_type} timed out after {timeout}s"
            logger.warning(
                "agent_invocation_timeout",
                agent_type=agent_type,
                analysis_id=analysis_id,
                invocation_method="ainvoke",
                timeout_seconds=timeout,
                duration_seconds=duration,
                trace_id=trace_id,
                message=f"{timeout_msg}, triggering fallback",
            )
            # Raise TimeoutError to trigger with_fallbacks() chain
            raise TimeoutError(timeout_msg) from None
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
        # Sync invoke in thread pool with timeout
        try:
            async with asyncio.timeout(timeout):
                result = await asyncio.to_thread(agent.invoke, input_messages)
            return cast("dict[str, object]", result)
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
