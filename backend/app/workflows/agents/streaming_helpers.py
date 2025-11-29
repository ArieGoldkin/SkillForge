"""Helper functions for streaming agent responses.

This module contains helper functions for SSE progress emission and throttling.
Extracted from streaming.py to reduce file size and improve modularity.
"""

from app.core.constants import SSE_EVENT_THROTTLE_CHARS, SSE_EVENT_THROTTLE_MS
from app.core.types import AnalysisID
from app.workflows.agents.base import emit_agent_progress


def should_emit_progress_event(
    current_time: float,
    last_event_time: float,
    accumulated_content: str,
    last_event_chars: int,
) -> bool:
    """Check if SSE progress event should be emitted based on throttling."""
    chars_since_last = len(accumulated_content) - last_event_chars
    time_since_last_ms = (current_time - last_event_time) * 1000
    return (
        time_since_last_ms >= SSE_EVENT_THROTTLE_MS or chars_since_last >= SSE_EVENT_THROTTLE_CHARS
    )


async def emit_progress_if_needed(
    accumulated_content: str,
    last_event_time: float,
    last_event_chars: int,
    analysis_id: AnalysisID,
    agent_type: str,
) -> tuple[float, int]:
    """Emit SSE progress event if throttling conditions met."""
    import time

    current_time = time.time()
    if should_emit_progress_event(
        current_time, last_event_time, accumulated_content, last_event_chars
    ):
        await emit_agent_progress(
            analysis_id, agent_type, "streaming", token_preview=accumulated_content[-100:]
        )
        return current_time, len(accumulated_content)
    return last_event_time, last_event_chars


