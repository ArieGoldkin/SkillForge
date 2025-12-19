"""Code quality critic agent node for LangGraph StateGraph.

Note: This node does NOT use @robust_traceable decorator because LangGraph
automatically traces all node executions. Adding @robust_traceable would
create duplicate spans in Langfuse. Runtime metadata is still updated
via update_current_trace().

Issue #244: Uses Handle Pattern - content loaded via content_ref (ArtifactStore)
with fallback to raw_content for backward compatibility.
"""

import time

from app.core.logging import get_logger
from app.core.timeout_config import STEP_TIMEOUT
from app.core.tracing import get_current_trace_id, update_current_trace
from app.domains.analysis.workflows.agents.base import emit_agent_progress
from app.domains.analysis.workflows.state import AnalysisState
from app.domains.analysis.workflows.tasks.runners import (
    get_fallback_content,
    has_content_available,
    run_code_quality_critic_with_session,
)

logger = get_logger(__name__)


async def code_quality_critic_node(state: AnalysisState) -> dict[str, object]:
    """Code quality critic agent node.

    Executes code quality analysis and returns findings.
    Each agent node manages its own database session for parallel execution.

    Issue #244: Uses Handle Pattern for content loading:
    1. Checks content_ref (preferred) or raw_content (fallback) availability
    2. Runner loads optimized content section via ArtifactStore
    3. Falls back to raw_content if artifact loading fails

    Note: LangGraph automatically traces this node. We update runtime metadata
    via update_current_trace() but don't add a separate tracing decorator.

    Args:
        state: Current workflow state with content_ref or raw_content

    Returns:
        Dictionary with agent_findings containing single result

    """
    analysis_id = state["analysis_id"]
    content_type = state["content_type"]

    # Issue #244: Check Handle Pattern availability (content_ref or raw_content)
    if not has_content_available(state):
        logger.warning(
            "agent_node_skipped_no_content",
            agent_type="code_quality_critic",
            analysis_id=analysis_id,
            has_content_ref=bool(state.get("content_ref")),
            has_raw_content=bool(state.get("raw_content")),
        )
        return {"agent_findings": []}

    start_time = time.time()

    # Get Langfuse trace ID for correlation and update runtime metadata
    update_current_trace(
        metadata={
            "analysis_id": str(analysis_id),
            "content_type": content_type,
            "agent_name": "code_quality_critic",
        },
        tags=["parallel-execution"],
        session_id=f"analysis-{analysis_id}",
        user_id="anonymous",
    )
    trace_id = get_current_trace_id()

    logger.info(
        "agent_node_started",
        agent_type="code_quality_critic",
        analysis_id=analysis_id,
        state=state,
        trace_id=trace_id,
    )

    try:
        # Issue #244: Run agent with Handle Pattern - runner loads from artifact
        # get_fallback_content provides raw_content as fallback if artifact unavailable
        result = await run_code_quality_critic_with_session(
            content=get_fallback_content(state),
            content_type=content_type,
            analysis_id=analysis_id,
            state=state,
        )

        duration = time.time() - start_time
        logger.info(
            "agent_node_complete",
            agent_type="code_quality_critic",
            analysis_id=analysis_id,
            state=state,
            duration_seconds=duration,
            trace_id=trace_id,
        )

        # Return findings as single-item list (aggregate will collect from all nodes)
        return {"agent_findings": [result]}
    except GeneratorExit:
        # GeneratorExit during execution (cancellation/timeout) - return empty for
        # graceful degradation. Cleanup GeneratorExit is handled by robust_traceable wrapper
        duration = time.time() - start_time
        logger.warning(
            "agent_node_cancelled",
            agent_type="code_quality_critic",
            analysis_id=analysis_id,
            state=state,
            exception_type="GeneratorExit",
            duration_seconds=duration,
            step_timeout=STEP_TIMEOUT,
            trace_id=trace_id,
            handled_gracefully=True,
        )
        # Return empty findings on cancellation (allows other agents to continue)
        return {"agent_findings": []}
    except Exception as e:
        duration = time.time() - start_time
        processing_time_ms = int(duration * 1000)

        # Emit failed event using existing emit_agent_progress helper
        await emit_agent_progress(
            analysis_id,
            "code_quality_critic",
            "failed",
            error=str(e),
            error_code="CODE_QUALITY_CRITIC_FAILED",
            processing_time_ms=processing_time_ms,
        )

        logger.error(
            "agent_node_failed",
            agent_type="code_quality_critic",
            analysis_id=analysis_id,
            state=state,
            error_type=type(e).__name__,
            error=str(e),
            duration_seconds=duration,
            step_timeout=STEP_TIMEOUT,
            trace_id=trace_id,
            handled_gracefully=True,  # Returns empty findings, doesn't break workflow
            exc_info=True,
        )
        # Return empty findings on error (allows other agents to continue)
        return {"agent_findings": []}
