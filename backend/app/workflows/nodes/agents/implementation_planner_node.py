"""Implementation planner agent node for LangGraph StateGraph."""

from langsmith import traceable

from app.core.logging import get_logger
from app.workflows.state import AnalysisState
from app.workflows.tasks.runners import run_implementation_planner_with_session

logger = get_logger(__name__)


@traceable(
    name="implementation_planner",
    run_type="chain",
    tags=["workflow", "node", "agent", "implementation_planner"],
)
async def implementation_planner_node(state: AnalysisState) -> dict[str, object]:
    """Implementation planner agent node.

    Executes implementation planning analysis and returns findings.
    Each agent node manages its own database session for parallel execution.

    Args:
        state: Current workflow state with content and analysis_id

    Returns:
        Dictionary with agent_findings containing single result
    """
    analysis_id = state["analysis_id"]
    content = state["raw_content"]
    content_type = state["content_type"]

    logger.info(
        "agent_node_started",
        agent_type="implementation_planner",
        analysis_id=analysis_id,
    )

    try:
        # Run agent with its own database session
        result = await run_implementation_planner_with_session(
            content=content,
            content_type=content_type,
            analysis_id=analysis_id,
        )

        logger.info(
            "agent_node_complete",
            agent_type="implementation_planner",
            analysis_id=analysis_id,
        )

        # Return findings as single-item list (aggregate will collect from all nodes)
        return {"agent_findings": [result]}
    except Exception as e:
        logger.error(
            "agent_node_failed",
            agent_type="implementation_planner",
            analysis_id=analysis_id,
            error=str(e),
            exc_info=True,
        )
        # Return empty findings on error (allows other agents to continue)
        return {"agent_findings": []}
