"""Streaming logic for agent execution with progress updates and throttling.

Timeout handling is managed by LangGraph's step_timeout on the compiled graph.
This module focuses on streaming iteration without application-level timeouts
to avoid PEP 789 violations (yielding in cancellation scopes).

Uses contextlib.aclosing() to ensure generators are properly closed, preventing
GeneratorExit during LangGraph cleanup.
"""

import inspect
import time
from contextlib import aclosing
from typing import cast, overload

from langchain_core.runnables import Runnable

from app.core.langfuse_service import get_langfuse_service
from app.core.logging import get_logger
from app.core.timeout_config import STEP_TIMEOUT, create_runnable_config
from app.core.tracing import get_current_trace_id
from app.core.tracing_constants import calculate_llm_cost
from app.core.types import AnalysisID
from app.domains.analysis.workflows.agents.streaming_helpers import emit_progress_if_needed

logger = get_logger(__name__)


def _process_chunk(
    chunk: dict[str, object],
    final_result: dict[str, object] | None,
    accumulated_content: str,
    analysis_id: AnalysisID,
    agent_type: str,
) -> tuple[dict[str, object] | None, str, bool]:
    """Process chunk and update state."""
    should_break = False
    if isinstance(chunk, dict) and chunk.get("structured_response"):
        final_result = chunk
        logger.debug(
            "agent_structured_response_found", agent_type=agent_type, analysis_id=analysis_id
        )
        should_break = True
    elif final_result is None or not (
        isinstance(final_result, dict) and final_result.get("structured_response")
    ):
        final_result = chunk
    if isinstance(chunk, dict) and chunk.get("messages"):
        messages = chunk["messages"]
        if messages and isinstance(messages, list) and len(messages) > 0:
            latest_message = messages[-1]
            if hasattr(latest_message, "content") and latest_message.content:
                new_content = latest_message.content[len(accumulated_content) :]
                if new_content:
                    accumulated_content = latest_message.content
    return final_result, accumulated_content, should_break


# Removed _cleanup_stream - aclosing() context manager handles cleanup automatically


async def stream_agent_response(  # noqa: PLR0912, PLR0915 - Complex streaming logic
    agent: Runnable,
    input_messages: dict[str, list[dict[str, str]]],
    analysis_id: AnalysisID,
    agent_type: str,
    # Kept for logging/reference, but step_timeout handles actual timeout
    timeout: float,  # noqa: ASYNC109
) -> dict[str, object]:
    """Stream agent execution - timeout handled by LangGraph's step_timeout and model-level timeout.

    This function iterates the agent stream without application-level timeouts.
    Timeout handling is managed by:
    1. LangGraph's `step_timeout` on the compiled graph (node-level timeout)
    2. LangChain's model-level `timeout` parameter (API call timeout)

    This avoids PEP 789 violations (yielding in cancellation scopes) that occur
    when using `asyncio.timeout()` with async generators.

    Args:
        agent: Agent instance with streaming support
        input_messages: Input messages for the agent
        analysis_id: UUID of the analysis
        agent_type: Type of agent for logging
        timeout: Reference timeout value (
            for logging only; actual timeout handled by model and step_timeout
        )

    Returns:
        Final chunk dictionary with structured_response if found, or empty dict
        if stream ends without result

    Note:
        - Model-level timeout (from init_chat_model) applies to individual API calls
        - Graph-level step_timeout applies to entire node execution
        - GeneratorExit handling is a safety net for cancellation signals
        - LangChain's built-in retry (max_retries) handles transient failures automatically

    """
    start_time = time.time()
    accumulated_content = ""
    final_result: dict[str, object] | None = None
    last_event_time = 0.0
    last_event_chars = 0

    # Token usage tracking (LangChain-Core 1.2.4+)
    total_tokens = 0
    input_tokens = 0
    output_tokens = 0
    model_name = "unknown"  # Track model name for cost calculation

    # Get Langfuse trace ID for correlation if available
    trace_id = get_current_trace_id()

    # Create RunnableConfig (timeout handled by step_timeout on graph)
    config = create_runnable_config()

    # Stream agent execution - use aclosing() to ensure proper generator cleanup
    # This prevents GeneratorExit during LangGraph cleanup
    stream = agent.astream(input_messages, config=config, stream_mode="values")

    try:
        # Use aclosing() context manager to ensure generator is fully consumed and closed
        # aclosing() returns the same generator object, ensuring proper cleanup
        # Type ignore: agent.astream returns AsyncIterator which supports aclose()
        async with aclosing(stream) as stream_gen:  # type: ignore[type-var]
            stream_iter = stream_gen.__aiter__()

            try:
                # Iterate stream directly - step_timeout will cancel if needed
                while True:
                    try:
                        chunk = await stream_iter.__anext__()
                        chunk = cast("dict[str, object]", chunk)
                    except StopAsyncIteration:
                        break
                    except (AttributeError, GeneratorExit, RuntimeError) as exc:
                        # Stream closed or cancelled - handle gracefully
                        duration = time.time() - start_time
                        logger.debug(
                            "stream_closed",
                            agent_type=agent_type,
                            analysis_id=analysis_id,
                            error_type=type(exc).__name__,
                            error=str(exc),
                            duration_seconds=duration,
                            trace_id=trace_id,
                        )
                        break

                    final_result, accumulated_content, should_break = _process_chunk(
                        chunk, final_result, accumulated_content, analysis_id, agent_type
                    )

                    # Extract usage metadata from streaming chunks (LangChain-Core 1.2.4+)
                    if hasattr(chunk, "usage_metadata") and chunk.usage_metadata:
                        metadata = chunk.usage_metadata
                        # Accumulate token counts from streaming chunks
                        input_tokens = getattr(metadata, "input_tokens", input_tokens)
                        output_tokens += getattr(metadata, "output_tokens", 0)
                        total_tokens = input_tokens + output_tokens

                    # Extract model name from response metadata for cost tracking
                    if hasattr(chunk, "response_metadata") and chunk.response_metadata:
                        # Try common model name fields from different providers
                        metadata = chunk.response_metadata
                        model_name = (
                            metadata.get("model")
                            or metadata.get("model_name")
                            or metadata.get("model_id")
                            or model_name  # Keep previous value if not found
                        )

                    if should_break:
                        break

                    last_event_time, last_event_chars = await emit_progress_if_needed(
                        accumulated_content,
                        last_event_time,
                        last_event_chars,
                        analysis_id,
                        agent_type,
                    )
            except GeneratorExit:
                # Suppress GeneratorExit during cleanup - aclosing() handles it properly
                # This is expected when generator is closed during cleanup
                duration = time.time() - start_time
                logger.debug(
                    "agent_stream_generator_exit",
                    agent_type=agent_type,
                    analysis_id=analysis_id,
                    duration_seconds=duration,
                    trace_id=trace_id,
                    note="GeneratorExit during cleanup - normal behavior, suppressed",
                )
                # Return partial result if available, otherwise empty dict
                return final_result if final_result is not None else {}
        # Generator is automatically closed by aclosing() context manager
    except Exception as e:
        duration = time.time() - start_time
        has_partial_result = final_result is not None
        accumulated_length = len(accumulated_content)

        logger.error(
            "agent_stream_error",
            agent_type=agent_type,
            analysis_id=analysis_id,
            error_type=type(e).__name__,
            error=str(e),
            duration_seconds=duration,
            timeout_reference=timeout,
            step_timeout=STEP_TIMEOUT,
            has_partial_result=has_partial_result,
            accumulated_content_length=accumulated_length,
            trace_id=trace_id,
            exc_info=True,  # Include full stack trace
        )
        raise

    # Log final token usage if any tokens were consumed
    if total_tokens > 0:
        logger.info(
            "streaming_llm_usage",
            agent_type=agent_type,
            analysis_id=str(analysis_id),
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            total_tokens=total_tokens,
            trace_id=trace_id,
        )

        # Calculate and submit cost to Langfuse (graceful degradation)
        if model_name != "unknown" and input_tokens > 0:
            try:
                cost_usd = calculate_llm_cost(
                    model=model_name,
                    input_tokens=input_tokens,
                    output_tokens=output_tokens,
                )

                # Submit cost as Langfuse score
                langfuse_service = get_langfuse_service()
                langfuse_service.submit_score(
                    name="cost_usd",
                    value=cost_usd,
                    comment=f"{model_name}: {input_tokens}in + {output_tokens}out = ${cost_usd:.6f}",
                )
                logger.debug(
                    "streaming_cost_tracked",
                    agent_type=agent_type,
                    analysis_id=str(analysis_id),
                    model=model_name,
                    cost_usd=cost_usd,
                )
            except Exception as e:  # noqa: BLE001 - Graceful degradation for observability
                # Don't fail agent execution if cost tracking fails
                logger.debug("streaming_cost_tracking_failed", error=str(e))

    # If we have a result, return it; otherwise return empty dict for graceful degradation
    if final_result is None:
        duration = time.time() - start_time
        logger.warning(
            "agent_stream_no_result",
            agent_type=agent_type,
            analysis_id=analysis_id,
            duration_seconds=duration,
            accumulated_content_length=len(accumulated_content),
            trace_id=trace_id,
        )
        return {}  # Return empty dict instead of raising - allows graceful degradation

    # CRITICAL: Ensure no generator objects are returned in the result
    # Langfuse cannot serialize generators, and LangGraph's state cannot contain them
    # This prevents GeneratorExit errors during LangGraph cleanup
    if isinstance(final_result, dict):
        # Check for generators in the result dict
        for key, value in final_result.items():
            if inspect.isgenerator(value) or inspect.isasyncgen(value):
                logger.error(
                    "agent_result_contains_generator",
                    agent_type=agent_type,
                    analysis_id=analysis_id,
                    key=key,
                    generator_type=type(value).__name__,
                    trace_id=trace_id,
                    note=(
                        "Generator object found in agent result. "
                        "This should never happen - generators must be consumed before returning. "
                        "Removing generator from result to prevent Langfuse serialization errors."
                    ),
                )
                # Remove generator from result
                final_result = {k: v for k, v in final_result.items() if k != key}
            elif isinstance(value, (dict, list)):
                # Recursively check nested structures
                _check_for_generators_recursive(value, agent_type, analysis_id, trace_id, path=key)

    return final_result


@overload
def _check_for_generators_recursive(
    obj: dict[str, object],
    agent_type: str,
    analysis_id: AnalysisID,
    trace_id: str | None,
    path: str = "",
) -> None: ...


@overload
def _check_for_generators_recursive(
    obj: list[object],
    agent_type: str,
    analysis_id: AnalysisID,
    trace_id: str | None,
    path: str = "",
) -> None: ...


@overload
def _check_for_generators_recursive(
    obj: object,
    agent_type: str,
    analysis_id: AnalysisID,
    trace_id: str | None,
    path: str = "",
) -> None: ...


def _check_for_generators_recursive(
    obj: dict[str, object] | list[object] | object,
    agent_type: str,
    analysis_id: AnalysisID,
    trace_id: str | None,
    path: str = "",
) -> None:
    """Recursively check for generators in nested structures and log warnings.

    Args:
        obj: Object to check (dict, list, or any other type)
        agent_type: Type of agent for logging
        analysis_id: UUID of the analysis
        trace_id: Langfuse trace ID
        path: Current path in nested structure (for logging)

    """
    if inspect.isgenerator(obj) or inspect.isasyncgen(obj):
        logger.error(
            "agent_result_contains_generator_nested",
            agent_type=agent_type,
            analysis_id=analysis_id,
            path=path,
            generator_type=type(obj).__name__,
            trace_id=trace_id,
            note=(
                "Generator object found in nested structure. "
                "This should never happen - generators must be consumed before returning."
            ),
        )
    elif isinstance(obj, dict):
        for key, value in obj.items():
            current_path = f"{path}.{key}" if path else str(key)
            _check_for_generators_recursive(value, agent_type, analysis_id, trace_id, current_path)
    elif isinstance(obj, (list, tuple)):
        for idx, item in enumerate(obj):
            current_path = f"{path}[{idx}]" if path else f"[{idx}]"
            _check_for_generators_recursive(item, agent_type, analysis_id, trace_id, current_path)
