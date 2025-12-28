"""Agent invocation logic with fallback strategies and circuit breaker.

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

Issue #533: Added circuit breaker for LLM API calls.
Prevents cascade failures by detecting repeated LLM failures and failing fast.
"""

import asyncio
import time
from typing import cast

from langchain_core.runnables import Runnable

from app.core.langfuse_service import get_langfuse_service
from app.core.logging import get_logger
from app.core.resilience import get_resilience_manager
from app.core.timeout_config import AGENT_TIMEOUT, STEP_TIMEOUT, create_runnable_config
from app.core.tracing import get_current_trace_id
from app.core.tracing_constants import calculate_llm_cost
from app.core.types import AnalysisID

logger = get_logger(__name__)


def _track_llm_cost(
    result: dict[str, object] | None,
    agent_type: str,
    analysis_id: AnalysisID,
) -> None:
    """Extract usage metadata and submit cost tracking to Langfuse.

    Args:
        result: Agent invocation result with usage_metadata
        agent_type: Type of agent for logging
        analysis_id: UUID of the analysis

    """
    if result is None or not hasattr(result, "usage_metadata") or not result.usage_metadata:
        return

    usage = result.usage_metadata
    input_tokens = usage.get("input_tokens", 0)  # type: ignore[union-attr]
    output_tokens = usage.get("output_tokens", 0)  # type: ignore[union-attr]
    total_tokens = usage.get("total_tokens", 0)  # type: ignore[union-attr]

    logger.info(
        "agent_token_usage",
        agent_type=agent_type,
        analysis_id=str(analysis_id),
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        total_tokens=total_tokens,
    )

    # Extract model name from response metadata for cost tracking
    model_name = "unknown"
    response_metadata = getattr(result, "response_metadata", None)
    if response_metadata and isinstance(response_metadata, dict):
        # Try common model name fields from different providers
        model_name = (
            response_metadata.get("model")
            or response_metadata.get("model_name")
            or response_metadata.get("model_id")
            or "unknown"
        )

    # Calculate and submit cost to Langfuse
    if model_name != "unknown" and input_tokens > 0:
        cost_usd = calculate_llm_cost(
            model=model_name,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
        )

        # Submit cost as Langfuse score
        try:
            langfuse_service = get_langfuse_service()
            if langfuse_service is not None:
                langfuse_service.submit_score(
                    name="cost_usd",
                    value=cost_usd,
                    comment=f"{model_name}: {input_tokens}in + {output_tokens}out = ${cost_usd:.6f}",
                )
            logger.debug(
                "agent_cost_tracked",
                agent_type=agent_type,
                analysis_id=str(analysis_id),
                model=model_name,
                cost_usd=cost_usd,
            )
        except Exception as e:  # noqa: BLE001 - Graceful degradation for observability
            # Don't fail agent execution if cost tracking fails
            logger.debug("agent_cost_tracking_failed", error=str(e))


async def invoke_agent(
    agent: Runnable,
    input_messages: dict[str, list[dict[str, str]]],
    analysis_id: AnalysisID,
    agent_type: str,
    # For logging/reference; step_timeout handles actual timeout
    timeout: float = AGENT_TIMEOUT,  # noqa: ASYNC109
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

    # Issue #564: Extract prompt client from agent metadata for CallbackHandler linkage
    # The prompt is passed through agent.with_config(metadata={"langfuse_prompt_client": ...})
    langfuse_prompt = None
    try:
        if hasattr(agent, "config") and agent.config:
            agent_metadata = getattr(agent.config, "metadata", {}) or {}
            langfuse_prompt = agent_metadata.get("langfuse_prompt_client")
            if langfuse_prompt:
                logger.debug(
                    "prompt_extracted_for_linkage",
                    prompt_name=getattr(langfuse_prompt, "name", "unknown"),
                    agent_type=agent_type,
                    analysis_id=analysis_id,
                )
    except Exception as e:  # noqa: BLE001 - Graceful degradation for observability
        # Prompt metadata extraction may fail if agent config format changes
        # Continue invocation without Langfuse prompt linkage
        logger.debug("Prompt extraction for Langfuse linkage failed, continuing: %s", e)

    # Create RunnableConfig with Langfuse prompt for observation linkage
    # Issue #564: Passing langfuse_prompt to callback handler links it to the generation
    config = create_runnable_config(langfuse_prompt=langfuse_prompt)

    # Issue #533: Get circuit breaker for LLM API resilience
    resilience_manager = get_resilience_manager()
    circuit_breaker = resilience_manager.get_circuit_breaker("llm_api")

    # Use ainvoke (preferred) - avoids GeneratorExit issues with astream
    # astream creates async generators that trigger false error logs in Langfuse
    if hasattr(agent, "ainvoke"):
        # Issue #299-304: Wrap with asyncio.timeout to prevent indefinite hanging
        # Issue #533: Wrap with circuit breaker to prevent cascade failures
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
                circuit_state=circuit_breaker.state.value,
            )

            # Issue #533: Wrap LLM call with circuit breaker
            async def protected_llm_call() -> dict[str, object]:
                # asyncio.timeout raises TimeoutError if the call exceeds timeout
                # This is essential for triggering with_fallbacks() on hanging LLM calls
                async with asyncio.timeout(timeout):
                    return await agent.ainvoke(input_messages, config=config)

            result = await circuit_breaker.call(protected_llm_call)
            duration = time.time() - start_time

            # Track token usage and LLM cost in Langfuse
            _track_llm_cost(result, agent_type, analysis_id)

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
