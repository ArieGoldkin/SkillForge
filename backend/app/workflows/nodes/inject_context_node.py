"""Proactive memory context injection node for LangGraph StateGraph.

Issue #300: Enable Proactive Memory Recall
This node fetches relevant memories from past analyses and injects them
into the workflow state BEFORE agents are invoked. This implements the
proactive recall pattern from Google ADK's Context Engineering.
"""

import asyncio
import time

from app.core.logging import get_logger
from app.db.session import get_session_factory
from app.services.memory.proactive_recall import (
    fetch_proactive_context,
    format_memory_context,
)
from app.workflows.state import AnalysisState

logger = get_logger(__name__)


async def inject_context_node(state: AnalysisState) -> dict[str, object]:
    """Inject proactive memory context into state for downstream agents.

    This node runs BEFORE the supervisor and agent fan-out, fetching relevant
    memories from past analyses and making them available to all agents.

    The context is stored in state["proactive_context"] as a formatted string
    ready to be prepended to agent prompts.

    Args:
        state: Current workflow state with content and analysis_id

    Returns:
        Dictionary with proactive_context field containing formatted memory context

    """
    analysis_id = state["analysis_id"]
    raw_content = state.get("raw_content", "")

    if not raw_content:
        logger.warning(
            "inject_context_skipped_no_content",
            analysis_id=analysis_id,
        )
        return {"proactive_context": ""}

    start_time = time.time()

    logger.info(
        "inject_context_started",
        analysis_id=analysis_id,
        content_length=len(raw_content),
    )

    try:
        # Create a summary of the content for similarity search
        # Use first 1000 chars as a reasonable summary for vector search
        content_summary = raw_content[:1000]

        # Fetch proactive context with 30 second timeout to prevent hanging
        async with asyncio.timeout(30):
            # Fetch proactive context for each agent type
            # We'll fetch a generic context that applies to all agents
            # Individual agents can filter what's relevant to them
            session_factory = get_session_factory()
            async with session_factory() as session:
                # Fetch with agent_type="all" to get cross-agent relevant memories
                # Each agent will receive the same base context
                snippets = await fetch_proactive_context(
                    session=session,
                    content_summary=content_summary,
                    agent_type="all",  # Generic context for all agents
                    limit=5,  # Fetch top 5 most relevant memories
                    threshold=0.65,  # Lower threshold to be more inclusive
                )

        # Format memory snippets into context string
        memory_context = format_memory_context(snippets)

        duration_ms = int((time.time() - start_time) * 1000)

        logger.info(
            "inject_context_complete",
            analysis_id=analysis_id,
            snippets_count=len(snippets),
            context_length=len(memory_context),
            duration_ms=duration_ms,
        )

        return {"proactive_context": memory_context}

    except TimeoutError:
        duration_ms = int((time.time() - start_time) * 1000)

        logger.warning(
            "inject_context_timeout",
            analysis_id=analysis_id,
            duration_ms=duration_ms,
            timeout_seconds=30,
        )

        # Fail open: return empty context to allow workflow to continue
        return {"proactive_context": ""}

    except Exception as e:
        duration_ms = int((time.time() - start_time) * 1000)

        logger.error(
            "inject_context_failed",
            analysis_id=analysis_id,
            error_type=type(e).__name__,
            error=str(e),
            duration_ms=duration_ms,
            exc_info=True,
        )

        # Graceful degradation: return empty context on error
        # This allows the workflow to continue without proactive context
        return {"proactive_context": ""}
