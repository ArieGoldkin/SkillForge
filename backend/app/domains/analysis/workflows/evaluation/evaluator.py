"""Agent quality evaluator using Langfuse evaluation.

This module implements the evaluator-optimizer pattern for continuous
improvement of agent performance based on Langfuse evaluation results.
"""

from datetime import UTC, datetime

from app.core.config import settings
from app.core.langfuse_service import get_langfuse_service
from app.core.logging import get_logger
from app.core.tracing import robust_traceable
from app.domains.analysis.workflows.state import AnalysisState
from app.domains.analysis.workflows.state_accessors import get_agent_findings
from app.shared.services.messaging.sse_helpers import emit_streaming_event
from app.shared.types import AgentFinding

logger = get_logger(__name__)


@robust_traceable(
    name="evaluate_agent_quality",
    run_type="chain",
    tags=["workflow", "evaluation"],
    metadata={
        "environment": settings.ENVIRONMENT,
        "workflow_type": "evaluation",
        "component": "evaluator",
    },
)
async def evaluate_agent_quality(state: AnalysisState) -> AnalysisState:
    """Evaluate agent outputs and score quality using Langfuse.

    This function implements the evaluator pattern, assessing the quality
    of each agent's findings and storing evaluation results in the state.

    Args:
        state: Current workflow state with agent_findings populated

    Returns:
        Updated state with evaluation_results populated

    """
    # Issue #539: Defensive state access
    analysis_id = state.get("analysis_id")
    if not analysis_id:
        logger.error("evaluation_missing_analysis_id")
        state["evaluation_results"] = {}
        return state

    agent_findings = get_agent_findings(state)

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
        # Langfuse service available for future enhancements
        _ = get_langfuse_service()
        evaluation_results: dict[str, object] = {}

        for finding in agent_findings:
            agent_type_raw = finding.get("agent_type", "unknown")
            # Ensure agent_type is a string
            agent_type = str(agent_type_raw) if agent_type_raw else "unknown"

            # Evaluate finding quality
            # For now, use a simple heuristic - future enhancement can use
            # Langfuse evaluation API for more sophisticated scoring
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

        state["evaluation_results"] = evaluation_results  # type: ignore[typeddict-item]

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


def _calculate_quality_score(finding: AgentFinding) -> float:
    """Calculate quality score for an agent finding.

    Simple heuristic-based scoring. Future enhancement can use Langfuse
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
    # This is a placeholder - real implementation would use Langfuse evaluation
    key_count = len(findings_dict)
    base_score = min(0.9, 0.5 + (key_count * 0.1))

    # Adjust based on confidence if available
    confidence = finding.get("confidence_score")
    if isinstance(confidence, (int, float)) and 0 <= confidence <= 1:
        base_score = (base_score + confidence) / 2

    return round(base_score, 2)
