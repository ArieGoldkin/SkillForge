"""Trend validator agent node for LangGraph StateGraph."""

import time

from langsmith import get_current_run_tree, traceable

from app.core.logging import get_logger
from app.core.timeout_config import STEP_TIMEOUT
from app.workflows.state import AnalysisState
from app.workflows.tasks.runners import run_trend_validator_with_session

logger = get_logger(__name__)


async def _trend_validator_node_impl(state: AnalysisState) -> dict[str, object]:
    """Trend validator agent node implementation (without @traceable).

    Executes trend validation analysis and returns findings.
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
        agent_type="trend_validator",
        analysis_id=analysis_id,
        trace_id=trace_id,
    )

    try:
        # Run agent with its own database session
        result = await run_trend_validator_with_session(
            content=content,
            content_type=content_type,
            analysis_id=analysis_id,
        )

        duration = time.time() - start_time
        logger.info(
            "agent_node_complete",
            agent_type="trend_validator",
            analysis_id=analysis_id,
            duration_seconds=duration,
            trace_id=trace_id,
        )

        # Return findings as single-item list (aggregate will collect from all nodes)
        return {"agent_findings": [result]}
    except GeneratorExit as gen_exit:
        # GeneratorExit is a BaseException, not Exception - catch explicitly
        # This occurs when LangGraph's internal generator is closed during cleanup/timeout
        duration = time.time() - start_time
        logger.error(
            "agent_node_generator_exit",
            agent_type="trend_validator",
            analysis_id=analysis_id,
            exception_type="GeneratorExit",
            error_message=str(gen_exit),
            duration_seconds=duration,
            step_timeout=STEP_TIMEOUT,
            trace_id=trace_id,
            exc_info=True,  # Include full stack trace for debugging
            context="trend_validator_node",
            note=(
                "GeneratorExit caught in agent node. "
                "This occurs when LangGraph's pregel module closes an async generator. "
                "Check LangGraph streaming and timeout configuration."
            ),
        )
        # Return empty findings on cancellation (allows other agents to continue)
        return {"agent_findings": []}
    except BaseException as base_exc:
        # Catch other BaseExceptions (SystemExit, KeyboardInterrupt) for logging
        if isinstance(base_exc, GeneratorExit):
            # Already handled above, but catch here as safety net
            raise
        duration = time.time() - start_time
        logger.error(
            "agent_node_base_exception",
            agent_type="trend_validator",
            analysis_id=analysis_id,
            exception_type=type(base_exc).__name__,
            error_message=str(base_exc),
            duration_seconds=duration,
            trace_id=trace_id,
            exc_info=True,
        )
        # Return empty findings on error (allows other agents to continue)
        return {"agent_findings": []}
    except Exception as e:
        duration = time.time() - start_time
        logger.error(
            "agent_node_failed",
            agent_type="trend_validator",
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


# Wrap implementation with @traceable for LangSmith instrumentation
# This allows us to catch GeneratorExit before @traceable swallows it
@traceable(
    name="trend_validator",
    run_type="chain",
    tags=["workflow", "node", "agent", "trend_validator"],
)
async def trend_validator_node(state: AnalysisState) -> dict[str, object]:
    """Trend validator agent node (wrapped with @traceable).

    This wrapper ensures GeneratorExit is caught and logged before @traceable
    potentially swallows it during LangGraph's internal execution.
    """
    try:
        return await _trend_validator_node_impl(state)
    except GeneratorExit as gen_exit:
        # Catch GeneratorExit that might escape from @traceable wrapper
        # This is a safety net in case @traceable doesn't propagate it correctly
        logger.error(
            "agent_node_generator_exit_traceable_wrapper",
            agent_type="trend_validator",
            analysis_id=state.get("analysis_id", "unknown"),
            exception_type="GeneratorExit",
            error_message=str(gen_exit),
            exc_info=True,
            context="trend_validator_node_traceable_wrapper",
            note="GeneratorExit caught at @traceable wrapper level",
        )
        # Re-raise to let LangGraph handle it, but we've logged it
        raise
