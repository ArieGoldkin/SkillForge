"""Aggregate agent findings into coherent results.

This module handles the fan-in pattern for collecting and synthesizing
results from parallel agent execution.
"""

from langsmith import traceable

from app.core.logging import get_logger
from app.services.sse_helpers import emit_streaming_event
from app.workflows.state import AnalysisState

logger = get_logger(__name__)


@traceable(
    name="aggregate_findings",
    run_type="chain",
    tags=["workflow", "node", "aggregation"],
)
async def aggregate_findings(state: AnalysisState) -> dict[str, object]:
    """Aggregate agent findings into coherent results.

    This function implements the fan-in pattern, collecting results from
    all parallel agent executions and synthesizing them into a unified structure.

    Args:
        state: Current workflow state with agent_findings populated

    Returns:
        Dictionary with only agent_findings field (to avoid LangGraph concurrent update errors)

    """
    analysis_id = state["analysis_id"]
    agent_findings = state.get("agent_findings", [])

    # Emit SSE event: aggregation started
    await emit_streaming_event(
        "progress",
        analysis_id=analysis_id,
        stage="aggregation",
        status="running",
        findings_count=len(agent_findings),
    )

    logger.info(
        "workflow_aggregation_started",
        analysis_id=analysis_id,
        findings_count=len(agent_findings),
    )

    try:
        # Synthesize findings from all agents
        # For now, we just collect them - future enhancement could add
        # intelligent synthesis, conflict resolution, etc.
        # Note: aggregated dict is prepared for future enhancements
        _aggregated = {
            "total_findings": len(agent_findings),
            "agents_executed": [f.get("agent_type") for f in agent_findings],
            "findings": agent_findings,
        }

        # Emit SSE event: aggregation complete
        await emit_streaming_event(
            "progress",
            analysis_id=analysis_id,
            stage="aggregation",
            status="complete",
            findings_count=len(agent_findings),
        )

        logger.info(
            "workflow_aggregation_complete",
            analysis_id=analysis_id,
            findings_count=len(agent_findings),
        )

        # Return only updated fields, not entire state
        return {"agent_findings": agent_findings}
    except Exception as e:
        # Emit SSE event: aggregation failed
        await emit_streaming_event(
            "error",
            analysis_id=analysis_id,
            stage="aggregation",
            status="failed",
            error=str(e),
            error_code="AGGREGATION_FAILED",
        )

        logger.error(
            "workflow_aggregation_failed",
            analysis_id=analysis_id,
            error=str(e),
            exc_info=True,
        )
        raise
