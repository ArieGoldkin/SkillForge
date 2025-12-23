"""Quality gate node for validating synthesized insights.

This node runs after aggregation/synthesis to validate the quality of
generated insights using LLM-as-judge evaluators. If quality scores fall
below threshold, it triggers a retry (up to 2 attempts).

Issue #301: Add quality validation gate to ensure high-quality artifacts.
"""

import asyncio
import time
from typing import Any

from app.core.logging import get_logger
from app.core.tracing import get_current_trace_id, update_current_trace
from app.domains.analysis.workflows.state import AnalysisState
from app.domains.analysis.workflows.state_accessors import (
    get_aggregated_insights,
    get_quality_scores,
)
from app.domains.analysis.workflows.state_types import AggregatedInsights
from app.evaluation.evaluators.quality import create_quality_evaluator

logger = get_logger(__name__)

# Quality gate configuration
QUALITY_THRESHOLD = 0.7  # Minimum AVERAGE score (0-1) to pass gate
MAX_RETRY_ATTEMPTS = 2  # Maximum retry attempts (0-indexed, so 0, 1, 2 = 3 total attempts)

# CRITICAL: Minimum thresholds for individual aspects
# If ANY aspect falls below its minimum, gate FAILS regardless of average
ASPECT_MINIMUMS = {
    "relevance": 0.5,  # MUST be at least 0.5 - content must be relevant!
    "depth": 0.4,  # Some depth required
    "coherence": 0.4,  # Basic coherence required
}

# Issue #299-304: Coverage-adjusted thresholds
# When content has limited data (low coverage_score), we adjust thresholds
# to reward honest partial analysis over hallucinated full analysis
COVERAGE_TRIGGER_BELOW: float = 0.5  # coverage_score < this -> use adjusted thresholds
COVERAGE_ADJUSTED_THRESHOLD: float = 0.55  # Lower average requirement
COVERAGE_ADJUSTED_MINIMUMS: dict[str, float] = {
    "relevance": 0.4,  # Still need some relevance
    "depth": 0.3,  # Expect less depth with limited data
    "coherence": 0.4,  # Coherence should still be maintained
}

# Aspects to evaluate
QUALITY_ASPECTS = ["relevance", "depth", "coherence"]

# Issue #413: Quality tier thresholds for auto-tagging
QUALITY_TIER_HIGH_THRESHOLD = 0.8  # avg_score >= this -> "quality:high"
QUALITY_TIER_MEDIUM_THRESHOLD = 0.6  # avg_score >= this -> "quality:medium", else "quality:low"


async def quality_gate_node(state: AnalysisState) -> dict[str, object]:  # noqa: PLR0912, PLR0915
    """Quality gate validation node.

    Evaluates synthesized insights using LLM-as-judge evaluators for:
    - Relevance: How relevant are the insights to the input content?
    - Depth: How thorough and detailed is the analysis?
    - Coherence: How well-structured and clear are the insights?

    If average quality score < 0.7 threshold, triggers retry (up to 2 attempts).
    Quality scores are added to state for observability.

    Note: LangGraph automatically traces this node. We update runtime metadata
    via update_current_trace() but don't add a separate tracing decorator.

    Args:
        state: Current workflow state with aggregated_insights

    Returns:
        Dictionary with quality_scores and retry_count fields

    """
    # Issue #441: Skip if workflow is aborting
    from app.domains.analysis.workflows.utils.abort_helpers import check_should_abort

    abort_result = check_should_abort(state)
    if abort_result is None:
        return {}

    analysis_id = state["analysis_id"]
    aggregated_insights = get_aggregated_insights(state)
    retry_count = state.get("quality_gate_retry_count", 0)

    # Issue #442: Track quality warnings for fail-open transparency
    quality_warnings: list[str] = []

    # Start timing at the very beginning
    start_time = time.time()

    if not aggregated_insights:
        logger.warning(
            "quality_gate_skipped_no_insights",
            analysis_id=analysis_id,
        )
        # No insights to validate - skip gate
        # Still submit latency for skipped evaluation
        from app.core.langfuse_service import get_langfuse_service

        langfuse_service = get_langfuse_service()
        if langfuse_service and langfuse_service.sdk_client:
            try:
                latency_seconds = time.time() - start_time
                trace_id = get_current_trace_id()
                if trace_id:
                    langfuse_service.sdk_client.create_score(
                        trace_id=str(trace_id),
                        name="latency_seconds",
                        value=latency_seconds,
                        data_type="NUMERIC",
                        comment=f"Quality gate skipped (no insights) in {latency_seconds:.2f}s",
                    )
                    langfuse_service.sdk_client.flush()
            except Exception as e:  # noqa: BLE001 - Graceful degradation
                logger.debug("latency_score_failed_no_insights", error=str(e))

        return {
            "quality_scores": {},
            "quality_gate_retry_count": retry_count,
            "quality_gate_passed": True,
            "quality_warnings": [],
        }

    # Update Langfuse trace metadata
    update_current_trace(
        metadata={
            "analysis_id": str(analysis_id),
            "retry_count": retry_count,
        },
        tags=["quality-gate"],
        session_id=f"analysis-{analysis_id}",
        user_id="anonymous",
    )
    trace_id = get_current_trace_id()

    logger.info(
        "quality_gate_started",
        analysis_id=analysis_id,
        retry_count=retry_count,
        trace_id=trace_id,
    )

    try:
        # Create mock Run and Example for evaluators
        # The evaluators expect Langfuse Run/Example objects
        from datetime import UTC, datetime
        from uuid import UUID, uuid4

        from app.evaluation.types import Example, Run

        # Prepare input (original content) and output (synthesized insights)
        input_content = state.get("raw_content", "")
        output_content = _format_insights_for_evaluation(aggregated_insights)

        # Convert analysis_id to UUID if it's a string
        try:
            run_uuid = UUID(analysis_id) if isinstance(analysis_id, str) else analysis_id
        except (ValueError, TypeError):
            # If analysis_id is not a valid UUID, generate a new one for the mock run
            run_uuid = uuid4()
            logger.warning(
                "quality_gate_invalid_analysis_id",
                analysis_id=analysis_id,
                using_generated_uuid=str(run_uuid),
            )

        # Generate trace_id if not available
        trace_uuid = UUID(trace_id) if trace_id else uuid4()

        # Create mock Run object with all required fields
        # Langfuse Run requires: id, name, start_time, run_type, trace_id
        mock_run = Run(
            id=run_uuid,
            name="synthesis",
            run_type="chain",
            start_time=datetime.now(UTC),
            trace_id=trace_uuid,
            inputs={"content": input_content},
            outputs={"insights": output_content},
        )

        # Create mock Example object with inputs
        mock_example = Example(
            id=run_uuid,
            inputs={"content": input_content},
            outputs={},  # No reference outputs for online evaluation
        )

        # Run evaluators for each aspect
        quality_scores = {}
        for aspect in QUALITY_ASPECTS:
            evaluator = create_quality_evaluator(aspect=aspect)

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
                # Issue #442: Timeout - use neutral score (0.5) and track warning
                warning_msg = f"Evaluation timed out for {aspect}"
                quality_warnings.append(warning_msg)
                logger.warning(
                    "quality_evaluator_timeout",
                    analysis_id=analysis_id,
                    aspect=aspect,
                    timeout_seconds=30,
                    message=warning_msg,
                )
                quality_scores[aspect] = {
                    "score": 0.5,  # Neutral score - reflects uncertainty
                    "comment": "Evaluation timed out after 30 seconds",
                    "timeout": True,
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

        # Issue #299-304: Determine effective thresholds based on coverage score
        # For content with limited data, use adjusted thresholds
        coverage_score_raw = aggregated_insights.get("coverage_score", 1.0)
        coverage_score = (
            float(coverage_score_raw) if isinstance(coverage_score_raw, (int, float)) else 1.0
        )
        use_adjusted_thresholds = coverage_score < COVERAGE_TRIGGER_BELOW

        if use_adjusted_thresholds:
            effective_threshold = COVERAGE_ADJUSTED_THRESHOLD
            effective_minimums: dict[str, float] = dict(COVERAGE_ADJUSTED_MINIMUMS)
            logger.info(
                "quality_gate_using_adjusted_thresholds",
                analysis_id=analysis_id,
                coverage_score=coverage_score,
                trigger_below=COVERAGE_TRIGGER_BELOW,
                effective_threshold=effective_threshold,
                effective_minimums=effective_minimums,
            )
        else:
            effective_threshold = QUALITY_THRESHOLD
            effective_minimums = dict(ASPECT_MINIMUMS)

        # Check individual aspect minimums (relevance MUST be above threshold!)
        failed_aspects: list[str] = []
        for aspect, minimum in effective_minimums.items():
            if aspect in quality_scores:
                aspect_score = quality_scores[aspect]["score"]
                if aspect_score < minimum:
                    failed_aspects.append(f"{aspect}={aspect_score:.2f}<{minimum}")
                    logger.warning(
                        "quality_aspect_below_minimum",
                        analysis_id=analysis_id,
                        aspect=aspect,
                        score=aspect_score,
                        minimum=minimum,
                        using_adjusted=use_adjusted_thresholds,
                    )

        # Determine if gate passes: BOTH average AND individual minimums must pass
        gate_passed = avg_score >= effective_threshold and len(failed_aspects) == 0

        duration = time.time() - start_time

        logger.info(
            "quality_gate_evaluated",
            analysis_id=analysis_id,
            retry_count=retry_count,
            avg_quality_score=avg_score,
            threshold=effective_threshold,
            gate_passed=gate_passed,
            failed_aspects=failed_aspects if failed_aspects else None,
            individual_scores={aspect: s["score"] for aspect, s in quality_scores.items()},
            aspect_minimums=effective_minimums,
            # Issue #299-304: Include coverage-aware context
            coverage_score=coverage_score,
            using_adjusted_thresholds=use_adjusted_thresholds,
            duration_seconds=duration,
            trace_id=trace_id,
        )

        # Emit SSE event for quality gate result
        from app.shared.services.messaging.sse_helpers import emit_error_event, emit_streaming_event

        if gate_passed:
            # Gate passed - emit progress event with complete status
            await emit_streaming_event(
                "progress",
                analysis_id=analysis_id,
                stage="quality_validation",
                status="complete",
                avg_score=avg_score,
                threshold=effective_threshold,
                retry_count=retry_count,
                scores=quality_scores,
                gate_passed=True,
            )
        else:
            # Gate failed - emit error event
            error_message = (
                f"Quality gate failed - average score {avg_score:.2f} below threshold "
                f"{effective_threshold:.2f}"
            )
            if failed_aspects:
                error_message += f". Failed aspects: {', '.join(failed_aspects)}"

            await emit_error_event(
                analysis_id=analysis_id,
                stage="quality_validation",
                error=error_message,
                error_code="QUALITY_GATE_FAILED",
                avg_score=avg_score,
                threshold=effective_threshold,
                retry_count=retry_count,
                scores=quality_scores,
                gate_passed=False,
                failed_aspects=failed_aspects if failed_aspects else None,
            )

        # Submit quality scores to Langfuse for analytics
        # Issue #432: Submit G-Eval scores using direct Langfuse SDK API
        from app.core.langfuse_service import get_langfuse_service

        langfuse_service = get_langfuse_service()
        if langfuse_service and langfuse_service.sdk_client and trace_id:
            try:
                sdk_client = langfuse_service.sdk_client

                # Submit individual criterion scores
                for aspect, score_data in quality_scores.items():
                    reasoning = score_data.get("comment", "")
                    # Truncate comment to 200 chars max for readability
                    comment = reasoning[:200] if reasoning else None

                    sdk_client.create_score(
                        trace_id=str(trace_id),
                        name=f"g_eval_{aspect}",
                        value=score_data["score"],
                        data_type="NUMERIC",
                        comment=comment,
                    )

                # Submit overall average score
                sdk_client.create_score(
                    trace_id=str(trace_id),
                    name="g_eval_overall",
                    value=avg_score,
                    data_type="NUMERIC",
                    comment=(
                        f"Gate {'passed' if gate_passed else 'failed'} "
                        f"(threshold: {effective_threshold})"
                    ),
                )

                # Flush to ensure scores are sent immediately
                sdk_client.flush()

                logger.info(
                    "g_eval_scores_submitted_to_langfuse",
                    analysis_id=analysis_id,
                    trace_id=trace_id,
                    aspect_count=len(quality_scores),
                    avg_score=avg_score,
                    gate_passed=gate_passed,
                )

            except Exception as e:  # noqa: BLE001 - Graceful degradation for observability
                logger.warning(
                    "g_eval_score_submission_failed",
                    analysis_id=analysis_id,
                    trace_id=trace_id,
                    error=str(e),
                    error_type=type(e).__name__,
                    message="Failed to submit G-Eval scores to Langfuse, continuing anyway",
                    exc_info=True,
                )
        else:
            logger.debug(
                "g_eval_scores_not_submitted",
                analysis_id=analysis_id,
                trace_id=trace_id,
                langfuse_available=bool(langfuse_service),
                sdk_client_available=bool(langfuse_service and langfuse_service.sdk_client),
                message="Langfuse not available - G-Eval scores not submitted",
            )

        # Issue #413: Quality-based auto-tagging for trace classification
        # Tag traces with quality tier for filtering/analytics in Langfuse
        quality_tier = (
            "quality:high"
            if avg_score >= QUALITY_TIER_HIGH_THRESHOLD
            else "quality:medium"
            if avg_score >= QUALITY_TIER_MEDIUM_THRESHOLD
            else "quality:low"
        )
        quality_tags = [quality_tier, f"gate:{'passed' if gate_passed else 'failed'}"]
        if use_adjusted_thresholds:
            quality_tags.append("coverage:limited")
        if failed_aspects:
            quality_tags.append("aspects:failed")

        update_current_trace(tags=quality_tags)

        logger.info(
            "quality_gate_auto_tagged",
            analysis_id=analysis_id,
            quality_tier=quality_tier,
            tags=quality_tags,
            trace_id=trace_id,
        )

        # Submit latency metric to Langfuse
        if langfuse_service and langfuse_service.sdk_client and trace_id:
            try:
                latency_seconds = time.time() - start_time
                langfuse_service.sdk_client.create_score(
                    trace_id=str(trace_id),
                    name="latency_seconds",
                    value=latency_seconds,
                    data_type="NUMERIC",
                    comment=f"Quality gate evaluation took {latency_seconds:.2f}s",
                )
                langfuse_service.sdk_client.flush()

                logger.debug(
                    "quality_gate_latency_submitted",
                    analysis_id=analysis_id,
                    latency_seconds=latency_seconds,
                    trace_id=trace_id,
                )
            except Exception as e:  # noqa: BLE001 - Graceful degradation
                logger.warning(
                    "latency_score_submission_failed",
                    analysis_id=analysis_id,
                    error=str(e),
                    exc_info=True,
                )

        # Return quality scores and gate status
        return {
            "quality_scores": quality_scores,
            "quality_gate_avg_score": avg_score,
            "quality_gate_passed": gate_passed,
            "quality_gate_retry_count": retry_count,
            "quality_warnings": quality_warnings,
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

        # Submit latency metric even on error
        from app.core.langfuse_service import get_langfuse_service

        langfuse_service = get_langfuse_service()
        if langfuse_service and langfuse_service.sdk_client:
            try:
                current_trace_id = trace_id if trace_id else get_current_trace_id()
                if current_trace_id:
                    langfuse_service.sdk_client.create_score(
                        trace_id=str(current_trace_id),
                        name="latency_seconds",
                        value=duration,
                        data_type="NUMERIC",
                        comment=(
                            f"Quality gate evaluation failed after {duration:.2f}s: "
                            f"{type(e).__name__}"
                        ),
                    )
                    langfuse_service.sdk_client.flush()
            except Exception as score_error:  # noqa: BLE001 - Graceful degradation
                logger.debug("latency_score_failed_on_error", error=str(score_error))

        # Issue #442: On error, pass gate (fail open) but track warning
        # This ensures workflow continues while providing transparency
        error_warning = f"Quality evaluation failed: {type(e).__name__}: {e!s}"
        return {
            "quality_scores": {},
            "quality_gate_avg_score": 0.0,
            "quality_gate_passed": True,  # Fail open
            "quality_gate_retry_count": retry_count,
            "quality_gate_error": str(e),
            "quality_warnings": [error_warning],
        }


def _format_insights_for_evaluation(aggregated_insights: AggregatedInsights) -> str:
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
    synthesis: dict[str, Any] = aggregated_insights.get("synthesis", {})  # type: ignore[assignment]
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
        # Issue #299-304: Increased from 2000 to 8000 to preserve depth for evaluation
        # Fallback: convert entire dict to string
        return str(aggregated_insights)[:8000]

    # Issue #299-304: Increased limit from 2000 to 8000 chars to preserve analytical depth
    # The G-Eval evaluator needs sufficient content to properly assess depth and coherence.
    # Previous 2000 char limit was causing over-truncation, resulting in low depth scores.
    return "\n".join(parts)[:8000]


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

    # If max retries reached, FAIL (fail-closed, not fail-open)
    # This prevents shipping garbage artifacts
    if retry_count >= MAX_RETRY_ATTEMPTS:
        analysis_id = state.get("analysis_id")
        avg_score = state.get("quality_gate_avg_score", 0.0)
        quality_scores = get_quality_scores(state)

        logger.error(
            "quality_gate_max_retries_exhausted",
            analysis_id=analysis_id,
            retry_count=retry_count,
            max_retries=MAX_RETRY_ATTEMPTS,
            avg_score=avg_score,
            quality_scores={k: v.get("score") for k, v in quality_scores.items()},  # type: ignore[attr-defined]
            message="FAILING analysis - quality too low after max retries",
        )

        # Return "fail" to trigger workflow failure instead of shipping garbage
        return "fail"

    # Otherwise, retry synthesis
    logger.info(
        "quality_gate_triggering_retry",
        analysis_id=state.get("analysis_id"),
        retry_count=retry_count,
        avg_score=state.get("quality_gate_avg_score", 0.0),
    )
    return "retry_synthesis"
