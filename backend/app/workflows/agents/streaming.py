"""Streaming logic for agent execution with progress updates and throttling."""

import time
from typing import TYPE_CHECKING

from langchain_core.runnables import Runnable

if TYPE_CHECKING:
    pass

from app.core.logging import get_logger
from app.core.types import AnalysisID
from app.workflows.agents.streaming_helpers import emit_progress_if_needed
from app.workflows.utils.timeout_handling import handle_timeout_error

logger = get_logger(__name__)


def _check_timeout_remaining(
    start_time: float, timeout: float, agent_type: str, analysis_id: AnalysisID
) -> float:
    """Check remaining timeout and raise if exceeded."""
    elapsed = time.time() - start_time
    remaining_timeout = timeout - elapsed
    if remaining_timeout <= 0:
        msg = f"Agent {agent_type} exceeded timeout of {timeout}s"
        logger.warning(
            "agent_stream_timeout",
            agent_type=agent_type,
            analysis_id=analysis_id,
            timeout=timeout,
            elapsed=elapsed,
        )
        raise TimeoutError(msg)
    return remaining_timeout


async def _get_next_chunk_with_timeout(
    stream_iter,
    remaining_timeout: float,
    timeout_info: tuple[str, AnalysisID, float, float],
) -> dict[str, object] | None:
    """Get next chunk from stream with per-chunk timeout.

    Uses asyncio.timeout (Python 3.11+) which raises TimeoutError
    without cancelling the generator, avoiding GeneratorExit issues.
    """
    import asyncio
    from typing import cast

    try:
        async with asyncio.timeout(remaining_timeout):
            chunk = await stream_iter.__anext__()
            return cast(dict[str, object], chunk)
    except TimeoutError:
        # asyncio.timeout raises TimeoutError without cancelling generator
        agent_type, analysis_id, start_time, timeout = timeout_info
        msg = f"Agent {agent_type} exceeded timeout of {timeout}s"
        logger.warning(
            "agent_stream_chunk_timeout",
            agent_type=agent_type,
            analysis_id=analysis_id,
            timeout=timeout,
            elapsed=time.time() - start_time,
        )
        raise TimeoutError(msg) from None
    except StopAsyncIteration:
        return None
    except (AttributeError, GeneratorExit, RuntimeError) as exc:
        logger.debug("stream_closed", error=str(exc))
        return None


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
    timeout: float,
) -> dict[str, object]:
    """Stream agent execution with progress updates and structured response detection.

    Uses a clean timeout pattern that avoids asyncio.wait_for task cancellation,
    which causes GeneratorExit errors in LangGraph's internal astream implementation.

    Args:
        agent: Agent instance with streaming support
        input_messages: Input messages for the agent
        analysis_id: UUID of the analysis
        agent_type: Type of agent for logging
        timeout: Maximum time to wait for streaming

    Returns:
        Final chunk dictionary with structured_response if found

    Raises:
        TimeoutError: If streaming exceeds timeout
        Exception: For other streaming errors

    """
    accumulated_content = ""
    final_result: dict[str, object] | None = None
    last_event_time = 0.0
    last_event_chars = 0
    start_time = time.time()

    stream = agent.astream(input_messages, stream_mode="values")
    stream_iter = stream.__aiter__()

    try:
        while True:
            remaining_timeout = _check_timeout_remaining(
                start_time, timeout, agent_type, analysis_id
            )

            timeout_info = (agent_type, analysis_id, start_time, timeout)
            chunk = await _get_next_chunk_with_timeout(stream_iter, remaining_timeout, timeout_info)

            if chunk is None:
                break

            final_result, accumulated_content, should_break = _process_chunk(
                chunk, final_result, accumulated_content, analysis_id, agent_type
            )

            if should_break:
                break

            last_event_time, last_event_chars = await emit_progress_if_needed(
                accumulated_content, last_event_time, last_event_chars, analysis_id, agent_type
            )

    except TimeoutError as exc:
        raise handle_timeout_error(
            exc=exc,
            context=f"Agent {agent_type}",
            timeout=timeout,
            logger=logger,
            agent_type=agent_type,
            analysis_id=analysis_id,
        ) from exc
    except GeneratorExit:
        logger.warning(
            "agent_stream_generator_exit", agent_type=agent_type, analysis_id=analysis_id
        )
        if final_result is None:
            raise handle_timeout_error(
                exc=GeneratorExit(),
                context=f"Agent {agent_type}",
                timeout=timeout,
                logger=logger,
                agent_type=agent_type,
                analysis_id=analysis_id,
            ) from None
    except Exception as e:
        logger.exception(
            "agent_stream_error", agent_type=agent_type, analysis_id=analysis_id, error=str(e)
        )
        raise
    finally:
        await _cleanup_stream(stream)

    if final_result is None:
        msg = f"Agent {agent_type} stream completed with no result"
        raise RuntimeError(msg)

    return final_result
