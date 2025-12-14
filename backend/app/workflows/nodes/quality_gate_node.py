"""Quality gate node for validating synthesized insights.

This node runs after aggregation/synthesis to validate the quality of
generated insights using LLM-as-judge evaluators. If quality scores fall
below threshold, it triggers a retry (up to 2 attempts).

Issue #301: Add quality validation gate to ensure high-quality artifacts.
"""

import asyncio
import time

from langsmith import get_current_run_tree

from app.core.logging import get_logger
from app.evaluation.evaluators.quality import (
    create_quality_evaluator,
)
from app.workflows.state import AnalysisState

logger = get_logger(__name__)

# Quality gate configuration
QUALITY_THRESHOLD = 0.7  # Minimum score (0-1) to pass gate
MAX_RETRY_ATTEMPTS = 2  # Maximum retry attempts (0-indexed, so 0, 1, 2 = 3 total attempts)

# Aspects to evaluate
QUALITY_ASPECTS = ["relevance", "depth", "coherence"]


async def quality_gate_node(state: AnalysisState) -> dict[str, object]:
    """Quality gate validation node.

    Evaluates synthesized insights using LLM-as-judge evaluators for:
    - Relevance: How relevant are the insights to the input content?
    - Depth: How thorough and detailed is the analysis?
    - Coherence: How well-structured and clear are the insights?

    If average quality score < 0.7 threshold, triggers retry (up to 2 attempts).
    Quality scores are added to state for observability.

    Note: LangGraph automatically traces this node. We update runtime metadata
    via get_current_run_tree() but don't add a separate tracing decorator.

    Args:
        state: Current workflow state with aggregated_insights

    Returns:
        Dictionary with quality_scores and retry_count fields

    """
    analysis_id = state["analysis_id"]
    aggregated_insights = state.get("aggregated_insights", {})
    retry_count = state.get("quality_gate_retry_count", 0)

    if not aggregated_insights:
        logger.warning(
            "quality_gate_skipped_no_insights",
            analysis_id=analysis_id,
        )
        # No insights to validate - skip gate
        return {
            "quality_scores": {},
            "quality_gate_retry_count": retry_count,
            "quality_gate_passed": True,
        }

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
            run_tree.metadata["retry_count"] = retry_count
            if run_tree.tags is not None:
                run_tree.tags.append("quality-gate")
    except Exception:  # noqa: BLE001 - LangSmith may not be available
        pass

    logger.info(
        "quality_gate_started",
        analysis_id=analysis_id,
        retry_count=retry_count,
        trace_id=trace_id,
    )

    try:
        # Create mock Run and Example for evaluators
        # The evaluators expect LangSmith Run/Example objects
        from langsmith.schemas import Example, Run

        # Prepare input (original content) and output (synthesized insights)
        input_content = state.get("raw_content", "")
        output_content = _format_insights_for_evaluation(aggregated_insights)

        # Create mock Run object with outputs
        mock_run = Run(
            id=str(analysis_id),
            name="synthesis",
            run_type="chain",
            inputs={"content": input_content},
            outputs={"insights": output_content},
        )

        # Create mock Example object with inputs
        mock_example = Example(
            id=str(analysis_id),
            inputs={"content": input_content},
            outputs={},  # No reference outputs for online evaluation
        )

        # Run evaluators for each aspect
        quality_scores = {}
        for aspect in QUALITY_ASPECTS:
            evaluator = create_quality_evaluator(aspect=aspect, judge_model="gpt-4o-mini")

            # Wrap evaluator call with timeout protection to prevent hanging
            try:
                async with asyncio.timeout(30):
                    result = await evaluator(mock_run, mock_example)
                    score = result.get("score", 0.0)
                    quality_scores[aspect] = {
                        "score": score,
                        "comment": result.get("comment", ""),
                    }
            except TimeoutError:
                # Timeout occurred - assign default passing score (fail open)
                logger.warning(
                    "quality_evaluator_timeout",
                    analysis_id=analysis_id,
                    aspect=aspect,
                    timeout_seconds=30,
                    message="evaluator timed out, using default passing score",
                )
                quality_scores[aspect] = {
                    "score": 0.7,  # Default passing score
                    "comment": "Evaluation timed out after 30 seconds",
                }

            logger.debug(
                "quality_aspect_evaluated",
                analysis_id=analysis_id,
                aspect=aspect,
                score=quality_scores[aspect]["score"],
                comment=quality_scores[aspect]["comment"],
            )

        # Calculate average quality score (guard against division by zero)
        avg_score = (
            sum(s["score"] for s in quality_scores.values()) / len(quality_scores)
            if quality_scores
            else 0.0
        )

        # Determine if gate passes
        gate_passed = avg_score >= QUALITY_THRESHOLD

        duration = time.time() - start_time

        logger.info(
            "quality_gate_evaluated",
            analysis_id=analysis_id,
            retry_count=retry_count,
            avg_quality_score=avg_score,
            threshold=QUALITY_THRESHOLD,
            gate_passed=gate_passed,
            individual_scores={aspect: s["score"] for aspect, s in quality_scores.items()},
            duration_seconds=duration,
            trace_id=trace_id,
        )

        # Emit SSE event for quality gate result
        from app.services.sse_helpers import emit_streaming_event

        await emit_streaming_event(
            "quality_gate",
            analysis_id=analysis_id,
            stage="quality_validation",
            status="passed" if gate_passed else "failed",
            avg_score=avg_score,
            threshold=QUALITY_THRESHOLD,
            retry_count=retry_count,
            scores=quality_scores,
        )

        # Return quality scores and gate status
        return {
            "quality_scores": quality_scores,
            "quality_gate_avg_score": avg_score,
            "quality_gate_passed": gate_passed,
            "quality_gate_retry_count": retry_count,
        }

    except Exception as e:
        duration = time.time() - start_time
        logger.error(
            "quality_gate_failed",
            analysis_id=analysis_id,
            retry_count=retry_count,
            error=str(e),
            error_type=type(e).__name__,
            duration_seconds=duration,
            trace_id=trace_id,
            exc_info=True,
        )

        # On error, pass the gate (fail open) to avoid blocking workflow
        # but log the failure for investigation
        return {
            "quality_scores": {},
            "quality_gate_avg_score": 0.0,
            "quality_gate_passed": True,  # Fail open
            "quality_gate_retry_count": retry_count,
            "quality_gate_error": str(e),
        }


def _format_insights_for_evaluation(aggregated_insights: dict) -> str:
    """Format aggregated insights for evaluation.

    Extracts key fields from aggregated insights dictionary and formats
    them as a coherent string for LLM evaluation.

    Args:
        aggregated_insights: Dictionary with synthesized insights

    Returns:
        Formatted string representation of insights

    """
    if not isinstance(aggregated_insights, dict):
        return str(aggregated_insights)

    parts = []

    # Extract executive summary
    exec_summary = aggregated_insights.get("executive_summary")
    if exec_summary:
        parts.append(f"Executive Summary:\n{exec_summary}")

    # Extract key findings
    key_findings = aggregated_insights.get("key_findings", [])
    if key_findings and isinstance(key_findings, list):
        findings_text = "\n".join(f"- {finding}" for finding in key_findings[:7])
        parts.append(f"\nKey Findings:\n{findings_text}")

    # Extract synthesis sections
    synthesis = aggregated_insights.get("synthesis", {})
    if synthesis and isinstance(synthesis, dict):
        for section, content in list(synthesis.items())[:5]:
            if content:
                parts.append(f"\n{section.replace('_', ' ').title()}:\n{content}")

    # Extract recommendations
    recommendations = aggregated_insights.get("recommendations", [])
    if recommendations and isinstance(recommendations, list):
        recs_text = "\n".join(f"- {rec}" for rec in recommendations[:5])
        parts.append(f"\nRecommendations:\n{recs_text}")

    if not parts:
        # Fallback: convert entire dict to string
        return str(aggregated_insights)[:2000]

    return "\n".join(parts)[:2000]  # Limit to 2000 chars


def should_retry_synthesis(state: AnalysisState) -> str:
    """Conditional edge function to determine if synthesis should retry.

    Args:
        state: Current workflow state with quality gate results

    Returns:
        "retry_synthesis" if quality gate failed and retries available,
        "continue" if gate passed or max retries reached

    """
    gate_passed = state.get("quality_gate_passed", True)
    retry_count = state.get("quality_gate_retry_count", 0)

    # If gate passed, continue to artifact generation
    if gate_passed:
        return "continue"

    # If max retries reached, continue anyway (fail open)
    if retry_count >= MAX_RETRY_ATTEMPTS:
        logger.warning(
            "quality_gate_max_retries_reached",
            analysis_id=state.get("analysis_id"),
            retry_count=retry_count,
            max_retries=MAX_RETRY_ATTEMPTS,
            avg_score=state.get("quality_gate_avg_score", 0.0),
            message="continuing to artifact generation despite low quality score",
        )
        return "continue"

    # Otherwise, retry synthesis
    logger.info(
        "quality_gate_triggering_retry",
        analysis_id=state.get("analysis_id"),
        retry_count=retry_count,
        avg_score=state.get("quality_gate_avg_score", 0.0),
    )
    return "retry_synthesis"
