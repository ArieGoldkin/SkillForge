"""Performance analyst agent node for LangGraph StateGraph."""

import time

from langsmith import get_current_run_tree, traceable

from app.core.logging import get_logger
from app.core.timeout_config import STEP_TIMEOUT
from app.workflows.state import AnalysisState
from app.workflows.tasks.runners import run_performance_analyst_with_session

logger = get_logger(__name__)


@traceable(
    name="performance_analyst",
    run_type="chain",
    tags=["workflow", "node", "agent", "performance_analyst"],
)
async def performance_analyst_node(state: AnalysisState) -> dict[str, object]:
    """Performance analyst agent node.

    Executes performance analysis and returns findings.
    Each agent node manages its own database session for parallel execution.

    Args:
        state: Current workflow state with content and analysis_id

    Returns:
        Dictionary with agent_findings containing single result
    """
    analysis_id = state["analysis_id"]
    content = state["raw_content"]
    content_type = state["content_type"]

    start_time = time.time()

    # Get LangSmith trace ID for correlation if available
    trace_id: str | None = None
    try:
        run_tree = get_current_run_tree()
        if run_tree and hasattr(run_tree, "id"):
            trace_id = str(run_tree.id)
    except Exception:
        # LangSmith not available or not in trace context - continue without trace_id
        pass

    logger.info(
        "agent_node_started",
        agent_type="performance_analyst",
        analysis_id=analysis_id,
        trace_id=trace_id,
    )

    try:
        # Run agent with its own database session
        result = await run_performance_analyst_with_session(
            content=content,
            content_type=content_type,
            analysis_id=analysis_id,
        )

        duration = time.time() - start_time
        logger.info(
            "agent_node_complete",
            agent_type="performance_analyst",
            analysis_id=analysis_id,
            duration_seconds=duration,
            trace_id=trace_id,
        )

        # Return findings as single-item list (aggregate will collect from all nodes)
        return {"agent_findings": [result]}
    except GeneratorExit:
        # GeneratorExit is a BaseException, not Exception - catch explicitly
        # Safety net: With step_timeout only, this should rarely occur.
        # If it does, it's handled gracefully for graceful degradation.
        duration = time.time() - start_time
        logger.warning(
            "agent_node_cancelled",
            agent_type="performance_analyst",
            analysis_id=analysis_id,
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
            agent_type="performance_analyst",
            analysis_id=analysis_id,
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
