"""Streaming logic for agent execution.

This module handles streaming agent responses with progress updates,
throttling, and structured response detection.
"""

import time
from typing import TYPE_CHECKING

from langchain_core.runnables import Runnable

if TYPE_CHECKING:
    pass

from app.core.constants import SSE_EVENT_THROTTLE_CHARS, SSE_EVENT_THROTTLE_MS
from app.core.logging import get_logger
from app.core.types import AnalysisID
from app.workflows.agents.base import emit_agent_progress
from app.workflows.utils.timeout_handling import handle_timeout_error

logger = get_logger(__name__)


def _should_emit_progress_event(
    current_time: float,
    last_event_time: float,
    accumulated_content: str,
    last_event_chars: int,
) -> bool:
    """Check if SSE progress event should be emitted based on throttling.

    Args:
        current_time: Current timestamp
        last_event_time: Timestamp of last emitted event
        accumulated_content: Full accumulated content so far
        last_event_chars: Character count at last event

    Returns:
        True if event should be emitted (throttle conditions met)

    """
    chars_since_last = len(accumulated_content) - last_event_chars
    time_since_last_ms = (current_time - last_event_time) * 1000
    return (
        time_since_last_ms >= SSE_EVENT_THROTTLE_MS or chars_since_last >= SSE_EVENT_THROTTLE_CHARS
    )


async def stream_agent_response(
    agent: Runnable,
    input_messages: dict[str, list[dict[str, str]]],
    analysis_id: AnalysisID,
    agent_type: str,
    timeout: float,
) -> dict[str, object]:
    """Stream agent execution with progress updates and structured response detection.

    Args:
        agent: Agent instance with streaming support
        input_messages: Input messages for the agent
        analysis_id: UUID of the analysis
        agent_type: Type of agent for logging
        timeout: Maximum time to wait for streaming

    Returns:
        Final chunk dictionary with structured_response if found

    Raises:
        GeneratorExit: If stream is closed externally
        TimeoutError: If streaming exceeds timeout
        Exception: For other streaming errors

    """
    import asyncio

    accumulated_content = ""
    final_result: dict[str, object] | None = None
    last_event_time = 0.0
    last_event_chars = 0

    async def stream_with_timeout():
        nonlocal final_result, accumulated_content, last_event_time, last_event_chars

        try:
            async for chunk in agent.astream(
                input_messages,
                stream_mode="values",
            ):
                # Check for structured_response early (robustness)
                # Preserve chunk with structured_response,
                # even if later chunks don't have it
                if isinstance(chunk, dict) and chunk.get("structured_response"):
                    # Found structured_response - preserve this chunk and exit
                    # The agent has completed its task, no need to continue streaming
                    final_result = chunk
                    logger.debug(
                        "agent_structured_response_found",
                        agent_type=agent_type,
                        analysis_id=analysis_id,
                    )
                    break  # Exit streaming loop - we have the result
                elif final_result is None or not (
                    isinstance(final_result, dict) and final_result.get("structured_response")
                ):
                    # Update final_result only if we haven't found structured_response yet
                    # This ensures we preserve the chunk with structured_response
                    final_result = chunk

                # Extract content from messages for progress updates
                if isinstance(chunk, dict) and chunk.get("messages"):
                    messages = chunk["messages"]
                    if messages:
                        latest_message = messages[-1]
                        # Extract text content for streaming preview
                        if hasattr(latest_message, "content") and latest_message.content:
                            new_content = latest_message.content[len(accumulated_content) :]
                            if new_content:
                                accumulated_content = latest_message.content

                                # Throttle SSE events to prevent overwhelming frontend
                                # Emit only if enough time has passed OR
                                # enough characters accumulated
                                current_time = time.time()
                                should_emit = _should_emit_progress_event(
                                    current_time,
                                    last_event_time,
                                    accumulated_content,
                                    last_event_chars,
                                )

                                if should_emit:
                                    # Emit SSE so frontend sees progress
                                    await emit_agent_progress(
                                        analysis_id,
                                        agent_type,
                                        "streaming",
                                        token_preview=accumulated_content[-100:],  # Last 100 chars
                                    )
                                    # Update throttling tracking
                                    last_event_time = current_time
                                    last_event_chars = len(accumulated_content)
        except GeneratorExit:
            # Stream was closed externally
            logger.warning(
                "agent_stream_closed",
                agent_type=agent_type,
                analysis_id=analysis_id,
            )
            # If we have partial result, preserve it
            if final_result is None:
                raise  # Re-raise if no result available
            # Otherwise, final_result is preserved
        except Exception as e:
            # Other streaming errors
            logger.exception(
                "agent_stream_error",
                agent_type=agent_type,
                analysis_id=analysis_id,
                error=str(e),
            )
            raise

    # Stream with timeout
    try:
        await asyncio.wait_for(
            stream_with_timeout(),
            timeout=timeout,
        )
    except (TimeoutError, GeneratorExit) as exc:
        raise handle_timeout_error(
            exc=exc,
            context=f"Agent {agent_type}",
            timeout=timeout,
            logger=logger,
            agent_type=agent_type,
            analysis_id=analysis_id,
        ) from None

    if final_result is None:
        msg = f"Agent {agent_type} stream completed with no result"
        raise RuntimeError(msg)

    return final_result
