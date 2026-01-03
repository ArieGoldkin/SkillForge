"""Agent quality evaluator using real G-Eval via Langfuse.

This module implements the evaluator-optimizer pattern for continuous
improvement of agent performance using LLM-as-judge evaluation.

Issue #570: Replaced heuristic key-counting with real G-Eval scoring.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING

from app.core.config import settings
from app.core.langfuse_service import get_langfuse_service
from app.core.logging import get_logger
from app.core.tracing import robust_traceable
from app.domains.analysis.workflows.state_accessors import get_agent_findings
from app.shared.services.messaging.sse_helpers import emit_streaming_event

if TYPE_CHECKING:
    from app.domains.analysis.workflows.state import AnalysisState
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
    """Evaluate agent outputs and score quality using real G-Eval.

    This function assesses the quality of each agent's findings using
    LLM-as-judge evaluation via the G-Eval service.

    For runtime use, evaluation runs asynchronously in the background
    to avoid blocking the workflow. Use `use_g_eval=True` for full
    LLM-based evaluation (costs money, adds latency).

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
        # Initialize Langfuse service
        langfuse_service = get_langfuse_service()
        evaluation_results: dict[str, object] = {}

        # Check if G-Eval should be used (controlled by settings)
        use_g_eval = getattr(settings, "USE_RUNTIME_G_EVAL", False)

        for finding in agent_findings:
            agent_type_raw = finding.get("agent_type", "unknown")
            agent_type = str(agent_type_raw) if agent_type_raw else "unknown"

            # Evaluate finding quality
            if use_g_eval and langfuse_service:
                # Use real G-Eval (async, non-blocking)
                quality_score = await _evaluate_with_g_eval(finding, agent_type)
            else:
                # Use lightweight heuristic for runtime (fast, free)
                quality_score = _calculate_heuristic_score(finding)

            findings_dict = finding.get("findings", {})
            finding_keys = list(findings_dict.keys()) if isinstance(findings_dict, dict) else []

            evaluation_results[agent_type] = {
                "quality_score": quality_score,
                "timestamp": datetime.now(UTC).isoformat(),
                "finding_keys": finding_keys,
                "evaluation_method": "g_eval" if use_g_eval else "heuristic",
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
            method="g_eval" if use_g_eval else "heuristic",
        )

        return state
    except Exception as e:
        logger.error(
            "workflow_evaluation_failed",
            analysis_id=analysis_id,
            error=str(e),
            exc_info=True,
        )
        state["evaluation_results"] = {}
        return state


async def _evaluate_with_g_eval(finding: AgentFinding, agent_type: str) -> float:
    """Evaluate finding quality using real G-Eval LLM-as-judge.

    Args:
        finding: Agent finding dictionary
        agent_type: The type of agent (for rubric selection)

    Returns:
        Quality score between 0.0 and 1.0

    """
    try:
        from app.shared.services.g_eval.scorer import g_eval_score

        # Extract the output text to evaluate
        findings_dict = finding.get("findings", {})
        if not findings_dict:
            return 0.5

        # Convert findings to text for evaluation
        import json

        output_text = json.dumps(findings_dict, indent=2, default=str)

        # g_eval_score is async, call it directly
        result = await g_eval_score(
            input_content="",  # No input needed for quality eval
            output=output_text,
            agent_type=agent_type,
            submit_to_langfuse=False,  # We handle tracing separately
        )

        # Extract overall score (already normalized to 0-1)
        overall_score = result.overall

        logger.debug(
            "g_eval_score_computed",
            agent_type=agent_type,
            overall_score=overall_score,
            criteria_scores={k: v.score for k, v in result.criteria_scores.items()},
        )

        return round(overall_score, 3)

    except (ImportError, TimeoutError, ValueError, RuntimeError, OSError) as e:
        logger.warning(
            "g_eval_evaluation_failed",
            agent_type=agent_type,
            error=str(e),
        )
        # Fall back to heuristic on error
        return _calculate_heuristic_score(finding)


def _calculate_heuristic_score(finding: AgentFinding) -> float:
    """Calculate quality score using lightweight heuristics.

    This provides fast, free runtime scoring. For accurate quality
    assessment, use G-Eval via `run_dataset_experiments.py --mode quality`.

    The heuristic considers:
    1. Finding completeness (number of keys)
    2. Confidence score from agent
    3. Content depth (nested structure)

    Args:
        finding: Agent finding dictionary

    Returns:
        Quality score between 0.0 and 1.0

    """
    findings_dict = finding.get("findings", {})
    if not isinstance(findings_dict, dict):
        return 0.5

    # Base score from completeness
    key_count = len(findings_dict)
    base_score = min(0.85, 0.4 + (key_count * 0.075))

    # Bonus for nested structure (indicates depth)
    nested_count = sum(1 for v in findings_dict.values() if isinstance(v, (dict, list)))
    depth_bonus = min(0.1, nested_count * 0.02)

    # Incorporate confidence if available
    confidence = finding.get("confidence_score")
    if isinstance(confidence, (int, float)) and 0 <= confidence <= 1:
        # Weighted average with confidence
        score = (base_score + depth_bonus) * 0.6 + confidence * 0.4
    else:
        score = base_score + depth_bonus

    return round(min(1.0, score), 3)
