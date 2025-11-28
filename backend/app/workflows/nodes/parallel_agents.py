"""Native LangGraph parallel agent execution node.

This module implements parallel agent execution using LangGraph's native
parallel patterns with proper error isolation and state management.
"""

from typing import TYPE_CHECKING

from langsmith import traceable

if TYPE_CHECKING:
    pass  # BaseException and GeneratorExit are builtins, no import needed

from app.core.logging import get_logger
from app.workflows.state import AnalysisState
from app.workflows.tasks.agent_execution import execute_agents

logger = get_logger(__name__)


@traceable(
    name="parallel_agents",
    run_type="chain",
    tags=["workflow", "node", "parallel"],
)
async def execute_parallel_agents(state: AnalysisState) -> dict[str, object]:
    """Execute selected agents in parallel using native LangGraph patterns.

    This node implements the fan-out pattern for parallel agent execution.
    Each agent runs independently with its own database session, and results
    are collected via the fan-in pattern in aggregate_findings.

    Args:
        state: Current workflow state with supervisor_decision populated

    Returns:
        Dictionary with only agent_findings field (to avoid LangGraph concurrent update errors)

    """
    analysis_id = state["analysis_id"]
    raw_content = state["raw_content"]
    content_type = state["content_type"]
    supervisor_decision = state.get("supervisor_decision", {})
    agents_raw = supervisor_decision.get("agents", [])

    # Type check: ensure agents is a list
    selected_agents: list[str] = agents_raw if isinstance(agents_raw, list) else []

    if not selected_agents:
        logger.debug("workflow_no_agents_selected", analysis_id=analysis_id)
        # Return only updated fields, not entire state
        return {"agent_findings": []}

    logger.info(
        "workflow_parallel_agents_starting",
        analysis_id=analysis_id,
        selected_agents=selected_agents,
        agent_count=len(selected_agents),
    )

    try:
        # Execute agents in parallel using existing execute_agents function
        # This maintains compatibility while we transition to full StateGraph
        agent_findings = await execute_agents(
            content=raw_content,
            content_type=content_type,
            analysis_id=analysis_id,
            selected_agents=selected_agents,
        )

        findings_count = len(agent_findings) if isinstance(agent_findings, list) else 0
        logger.info(
            "workflow_parallel_agents_complete",
            analysis_id=analysis_id,
            successful_count=findings_count,
            total_count=len(selected_agents),
        )

        # Return only updated fields, not entire state
        return {"agent_findings": agent_findings}
    except Exception as e:
        logger.error(
            "workflow_parallel_agents_failed",
            analysis_id=analysis_id,
            error=str(e),
            exc_info=True,
        )
        # Set empty findings on error - don't raise, allow workflow to continue
        # with partial results
        # Return only updated fields, not entire state
        return {"agent_findings": []}
