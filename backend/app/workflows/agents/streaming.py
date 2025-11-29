"""Streaming logic for agent execution with progress updates and throttling.

Timeout handling is managed by LangGraph's step_timeout on the compiled graph.
This module focuses on streaming iteration without application-level timeouts
to avoid PEP 789 violations (yielding in cancellation scopes).
"""

import time
from typing import TYPE_CHECKING, cast

from langchain_core.runnables import Runnable, RunnableConfig
from langsmith import get_current_run_tree

if TYPE_CHECKING:
    pass

from app.core.logging import get_logger
from app.core.timeout_config import STEP_TIMEOUT, create_runnable_config
from app.core.types import AnalysisID
from app.workflows.agents.streaming_helpers import emit_progress_if_needed

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


async def _cleanup_stream(stream) -> None:
    """Clean up async stream with proper error handling."""
    try:
        if hasattr(stream, "aclose"):
            await stream.aclose()
    except (AttributeError, GeneratorExit, RuntimeError):
        pass


async def stream_agent_response(
    agent: Runnable,
    input_messages: dict[str, list[dict[str, str]]],
    analysis_id: AnalysisID,
    agent_type: str,
    timeout: float,  # Kept for logging/reference, but step_timeout handles actual timeout
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
        timeout: Reference timeout value (for logging only - actual timeout handled by model and step_timeout)

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

    # Stream agent execution - no timeout wrapper (step_timeout handles it)
    stream = agent.astream(input_messages, config=config, stream_mode="values")
    stream_iter = stream.__aiter__()

    try:
        # Iterate stream directly - step_timeout will cancel if needed
        while True:
            try:
                chunk = await stream_iter.__anext__()
                chunk = cast(dict[str, object], chunk)
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

            if should_break:
                break

            last_event_time, last_event_chars = await emit_progress_if_needed(
                accumulated_content, last_event_time, last_event_chars, analysis_id, agent_type
            )

    except GeneratorExit:
        # Safety net - shouldn't occur with step_timeout only, but handle gracefully
        duration = time.time() - start_time
        has_partial_result = final_result is not None
        accumulated_length = len(accumulated_content)

        logger.warning(
            "agent_stream_cancelled",
            agent_type=agent_type,
            analysis_id=analysis_id,
            timeout_reference=timeout,
            step_timeout=STEP_TIMEOUT,
            duration_seconds=duration,
            has_partial_result=has_partial_result,
            accumulated_content_length=accumulated_length,
            trace_id=trace_id,
            exception_type="GeneratorExit",
            handled_gracefully=True,
        )
        await _cleanup_stream(stream)
        # Return partial result if available, otherwise empty dict
        return final_result if final_result is not None else {}
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
    finally:
        await _cleanup_stream(stream)

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

    return final_result
