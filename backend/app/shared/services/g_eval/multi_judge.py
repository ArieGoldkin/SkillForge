"""Multi-judge evaluation helper for quality gate integration.

This module provides convenience functions for running multi-judge G-Eval
evaluations in the quality gate workflow.

Issue #GAP5: Wire Langfuse multi-judge evaluators into quality gate.
"""

from __future__ import annotations

from typing import Any

from app.core.logging import get_logger
from app.shared.services.g_eval.langfuse_evaluators import create_g_eval_evaluator

logger = get_logger(__name__)

# Default quality aspects for quality gate evaluation
DEFAULT_QUALITY_ASPECTS = ["relevance", "depth", "coherence"]


async def run_multi_judge_evaluation(
    input_content: str,
    output_content: str,
    agent_type: str = "tech_comparator",
    aspects: list[str] | None = None,
    use_cache: bool = True,
) -> dict[str, dict[str, Any]]:
    """Run multi-judge G-Eval evaluation on content.

    This is a convenience wrapper for the quality gate that runs multiple
    G-Eval evaluators in parallel and returns structured scores.

    Args:
        input_content: Original input/content that generated the output
        output_content: Generated output to evaluate
        agent_type: Agent type for rubric selection
        aspects: List of aspects to evaluate (default: relevance, depth, coherence)
        use_cache: Whether to use G-Eval caching

    Returns:
        Dictionary mapping aspect -> {score, comment, metadata}

    Example:
        >>> scores = await run_multi_judge_evaluation(
        ...     input_content="Article about RAG systems...",
        ...     output_content="Analysis: RAG systems combine...",
        ...     agent_type="tech_comparator",
        ... )
        >>> print(scores["depth"]["score"])
        0.85

    """
    eval_aspects = aspects or DEFAULT_QUALITY_ASPECTS
    quality_scores: dict[str, dict[str, Any]] = {}

    # Run evaluations for each aspect
    for aspect in eval_aspects:
        try:
            # Create G-Eval evaluator for this criterion
            evaluator = create_g_eval_evaluator(
                criterion=aspect,
                agent_type=agent_type,
                use_cache=use_cache,
            )

            # Run evaluator with Langfuse experiment signature
            result = evaluator(
                input={"content": input_content},
                output=output_content,
                _expected_output=None,
            )

            # Extract score from Langfuse Evaluation object
            score_value = result.value if hasattr(result, "value") else 0.0
            score_comment = result.comment if hasattr(result, "comment") else ""
            score_metadata = result.metadata if hasattr(result, "metadata") else {}

            quality_scores[aspect] = {
                "score": score_value,
                "comment": score_comment,
                "metadata": score_metadata,
            }

            logger.debug(
                "multi_judge_aspect_evaluated",
                aspect=aspect,
                agent_type=agent_type,
                score=score_value,
            )

        except Exception as e:  # noqa: BLE001 - Graceful degradation for quality evaluation
            logger.warning(
                "multi_judge_evaluation_failed",
                aspect=aspect,
                agent_type=agent_type,
                error=str(e),
                error_type=type(e).__name__,
                exc_info=True,
            )
            # Return neutral score on error
            quality_scores[aspect] = {
                "score": 0.5,
                "comment": f"Evaluation error: {type(e).__name__}",
                "error": str(e),
            }

    return quality_scores


# Quality tier thresholds (align with quality_gate_node.py)
QUALITY_TIER_HIGH_THRESHOLD = 0.8
QUALITY_TIER_MEDIUM_THRESHOLD = 0.6


def calculate_weighted_score(
    quality_scores: dict[str, dict[str, Any]],
    weights: dict[str, float] | None = None,
) -> float:
    """Calculate weighted average from multi-judge scores.

    Args:
        quality_scores: Dictionary of aspect -> {score, ...}
        weights: Optional custom weights (defaults to equal weighting)

    Returns:
        Weighted average score (0.0-1.0)

    Example:
        >>> scores = {"relevance": {"score": 0.8}, "depth": {"score": 0.9}}
        >>> avg = calculate_weighted_score(scores, {"relevance": 0.6, "depth": 0.4})
        >>> print(avg)
        0.84

    """
    if not quality_scores:
        return 0.0

    # Default to equal weighting if not provided
    if weights is None:
        weights = {aspect: 1.0 / len(quality_scores) for aspect in quality_scores}

    # Calculate weighted sum and return directly
    return sum(
        quality_scores[aspect]["score"] * weights.get(aspect, 0.0)
        for aspect in quality_scores
        if aspect in weights
    )


def get_quality_tier(avg_score: float) -> str:
    """Get quality tier label from average score.

    Args:
        avg_score: Average quality score (0.0-1.0)

    Returns:
        Quality tier: "quality:high", "quality:medium", or "quality:low"

    """
    if avg_score >= QUALITY_TIER_HIGH_THRESHOLD:
        return "quality:high"
    if avg_score >= QUALITY_TIER_MEDIUM_THRESHOLD:
        return "quality:medium"
    return "quality:low"
