"""Agent quality evaluator using LangSmith evaluation.

This module implements the evaluator-optimizer pattern for continuous
improvement of agent performance based on LangSmith evaluation results.
"""

from datetime import UTC, datetime

from langsmith import Client, traceable

from app.core.logging import get_logger
from app.services.sse_helpers import emit_streaming_event
from app.workflows.state import AnalysisState

logger = get_logger(__name__)


@traceable(
    name="evaluate_agent_quality",
    run_type="chain",
    tags=["workflow", "evaluation"],
)
async def evaluate_agent_quality(state: AnalysisState) -> AnalysisState:
    """Evaluate agent outputs and score quality using LangSmith.

    This function implements the evaluator pattern, assessing the quality
    of each agent's findings and storing evaluation results in the state.

    Args:
        state: Current workflow state with agent_findings populated

    Returns:
        Updated state with evaluation_results populated

    """
    analysis_id = state["analysis_id"]
    agent_findings = state.get("agent_findings", [])

    if not agent_findings:
        logger.debug("workflow_no_findings_to_evaluate", analysis_id=analysis_id)
        state["evaluation_results"] = {}
        return state

    logger.info(
        "workflow_evaluation_started",
        analysis_id=analysis_id,
        findings_count=len(agent_findings),
    )

    try:
        # LangSmith client available for future enhancements
        _ = Client()  # noqa: F841
        evaluation_results: dict[str, object] = {}

        for finding in agent_findings:
            agent_type_raw = finding.get("agent_type", "unknown")
            # Ensure agent_type is a string
            agent_type = str(agent_type_raw) if agent_type_raw else "unknown"

            # Evaluate finding quality
            # For now, use a simple heuristic - future enhancement can use
            # LangSmith evaluation API for more sophisticated scoring
            quality_score = _calculate_quality_score(finding)

            findings_dict = finding.get("findings", {})
            finding_keys = list(findings_dict.keys()) if isinstance(findings_dict, dict) else []

            evaluation_results[agent_type] = {
                "quality_score": quality_score,
                "timestamp": datetime.now(UTC).isoformat(),
                "finding_keys": finding_keys,
            }

            # Emit evaluation event
            await emit_streaming_event(
                "evaluation",
                analysis_id=analysis_id,
                stage=agent_type,
                status="complete",
                quality_score=quality_score,
            )

        state["evaluation_results"] = evaluation_results

        logger.info(
            "workflow_evaluation_complete",
            analysis_id=analysis_id,
            evaluated_count=len(evaluation_results),
        )

        return state
    except Exception as e:
        logger.error(
            "workflow_evaluation_failed",
            analysis_id=analysis_id,
            error=str(e),
            exc_info=True,
        )
        # Set empty evaluation results on error
        state["evaluation_results"] = {}
        return state


def _calculate_quality_score(finding: dict[str, object]) -> float:
    """Calculate quality score for an agent finding.

    Simple heuristic-based scoring. Future enhancement can use LangSmith
    evaluation API for more sophisticated quality assessment.

    Args:
        finding: Agent finding dictionary

    Returns:
        Quality score between 0.0 and 1.0

    """
    findings_dict = finding.get("findings", {})
    if not isinstance(findings_dict, dict):
        return 0.5  # Default score if findings structure is unexpected

    # Simple heuristic: more keys = more comprehensive = higher score
    # This is a placeholder - real implementation would use LangSmith evaluation
    key_count = len(findings_dict)
    base_score = min(0.9, 0.5 + (key_count * 0.1))

    # Adjust based on confidence if available
    confidence = finding.get("confidence_score")
    if isinstance(confidence, (int, float)) and 0 <= confidence <= 1:
        base_score = (base_score + confidence) / 2

    return round(base_score, 2)
