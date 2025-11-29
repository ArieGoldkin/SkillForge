"""Integration feasibility agent node for LangGraph StateGraph."""

from langsmith import traceable

from app.core.logging import get_logger
from app.workflows.state import AnalysisState
from app.workflows.tasks.runners import run_integration_feasibility_with_session

logger = get_logger(__name__)


@traceable(
    name="integration_feasibility",
    run_type="chain",
    tags=["workflow", "node", "agent", "integration_feasibility"],
)
async def integration_feasibility_node(state: AnalysisState) -> dict[str, object]:
    """Integration feasibility agent node.

    Executes integration feasibility analysis and returns findings.
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
        agent_type="integration_feasibility",
        analysis_id=analysis_id,
    )

    try:
        # Run agent with its own database session
        result = await run_integration_feasibility_with_session(
            content=content,
            content_type=content_type,
            analysis_id=analysis_id,
        )

        logger.info(
            "agent_node_complete",
            agent_type="integration_feasibility",
            analysis_id=analysis_id,
        )

        # Return findings as single-item list (aggregate will collect from all nodes)
        return {"agent_findings": [result]}
    except Exception as e:
        logger.error(
            "agent_node_failed",
            agent_type="integration_feasibility",
            analysis_id=analysis_id,
            error=str(e),
            exc_info=True,
        )
        # Return empty findings on error (allows other agents to continue)
        return {"agent_findings": []}
