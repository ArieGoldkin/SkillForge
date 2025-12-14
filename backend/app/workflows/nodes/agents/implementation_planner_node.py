"""Implementation planner agent node for LangGraph StateGraph.

Note: This node does NOT use @robust_traceable decorator because LangGraph
automatically traces all node executions. Adding @robust_traceable would
create duplicate spans in LangSmith. Runtime metadata is still updated
via get_current_run_tree().

Issue #244: Uses Handle Pattern - content loaded via content_ref (ArtifactStore)
with fallback to raw_content for backward compatibility.
"""

import time

from langsmith import get_current_run_tree

from app.core.logging import get_logger
from app.core.timeout_config import STEP_TIMEOUT
from app.workflows.state import AnalysisState
from app.workflows.tasks.runners import (
    get_fallback_content,
    has_content_available,
    run_implementation_planner_with_session,
)

logger = get_logger(__name__)


async def implementation_planner_node(state: AnalysisState) -> dict[str, object]:
    """Execute implementation planning analysis.

    Executes implementation planning analysis and returns findings.
    Each agent node manages its own database session for parallel execution.

    Issue #244: Uses Handle Pattern for content loading:
    1. Checks content_ref (preferred) or raw_content (fallback) availability
    2. Runner loads optimized content section via ArtifactStore
    3. Falls back to raw_content if artifact loading fails

    Note: LangGraph automatically traces this node. We update runtime metadata
    via get_current_run_tree() but don't add a separate tracing decorator.

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
            agent_type="implementation_planner",
            analysis_id=analysis_id,
            has_content_ref=bool(state.get("content_ref")),
            has_raw_content=bool(state.get("raw_content")),
        )
        return {"agent_findings": []}

    start_time = time.time()

    # Get LangSmith trace ID for correlation and update runtime metadata
    trace_id: str | None = None
    try:
        run_tree = get_current_run_tree()
        if run_tree:
            if hasattr(run_tree, "id"):
                trace_id = str(run_tree.id)
            # Runtime metadata updates
            run_tree.metadata["analysis_id"] = str(analysis_id)
            run_tree.metadata["content_type"] = content_type
            if run_tree.tags is not None:
                run_tree.tags.append("parallel-execution")
    except Exception:  # noqa: BLE001 - LangSmith may not be available, catch all to continue
        # LangSmith not available or not in trace context - continue without trace_id
        pass

    logger.info(
        "agent_node_started",
        agent_type="implementation_planner",
        analysis_id=analysis_id,
        state=state,
        trace_id=trace_id,
    )

    try:
        # Issue #244: Run agent with Handle Pattern - runner loads from artifact
        # get_fallback_content provides raw_content as fallback if artifact unavailable
        result = await run_implementation_planner_with_session(
            content=get_fallback_content(state),
            content_type=content_type,
            analysis_id=analysis_id,
            state=state,
        )

        duration = time.time() - start_time
        logger.info(
            "agent_node_complete",
            agent_type="implementation_planner",
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
            agent_type="implementation_planner",
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
        logger.error(
            "agent_node_failed",
            agent_type="implementation_planner",
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
