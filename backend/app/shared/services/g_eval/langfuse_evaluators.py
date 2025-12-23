"""Langfuse-compatible evaluators for G-Eval integration.

This module provides evaluator functions that return proper Langfuse `Evaluation`
objects, enabling seamless integration with `langfuse.run_experiment()`.

Issue #428: Implements proper Langfuse SDK patterns for experiments.

The evaluators follow Langfuse's expected signature:
    def evaluator(*, input, output, expected_output=None, **kwargs) -> Evaluation

References:
- Langfuse Experiments SDK: https://langfuse.com/docs/evaluation/experiments
- G-Eval Paper: https://arxiv.org/abs/2303.16634

"""

from __future__ import annotations

import asyncio
import json
from typing import TYPE_CHECKING, Any

from app.core.logging import get_logger
from app.shared.services.g_eval.rubrics import get_agent_rubrics
from app.shared.services.g_eval.scorer import g_eval_score

if TYPE_CHECKING:
    from app.shared.services.g_eval.scorer import GEvalResult

logger = get_logger(__name__)

# Default criteria weights for overall score calculation
DEFAULT_CRITERIA_WEIGHTS = {
    "completeness": 0.25,
    "accuracy": 0.30,
    "coherence": 0.20,
    "depth": 0.25,
}


def _get_langfuse_evaluation_class():
    """Lazy import of Langfuse Evaluation to avoid import errors when not installed."""
    try:
        from langfuse import Evaluation

        return Evaluation
    except ImportError:
        logger.warning(
            "langfuse_evaluation_import_failed",
            message="Langfuse Evaluation class not available. Install langfuse>=3.0.0",
        )
        return None


def _run_async(coro):
    """Run async coroutine in sync context, handling existing event loops."""
    try:
        asyncio.get_running_loop()  # Check if loop exists
        # We're in an async context, run in thread pool
        import concurrent.futures

        with concurrent.futures.ThreadPoolExecutor() as pool:
            future = pool.submit(asyncio.run, coro)
            return future.result()
    except RuntimeError:
        # No running loop, safe to use asyncio.run
        return asyncio.run(coro)


def create_g_eval_evaluator(
    criterion: str,
    agent_type: str = "tech_comparator",
    use_cache: bool = True,
):
    """Create a criterion-specific G-Eval evaluator for Langfuse experiments.

    Creates an evaluator function compatible with `langfuse.run_experiment()`.
    The evaluator returns a Langfuse `Evaluation` object with the criterion score.

    Args:
        criterion: The evaluation criterion (completeness, accuracy, coherence, depth)
        agent_type: Agent type for rubric selection
        use_cache: Whether to use G-Eval caching

    Returns:
        Evaluator function compatible with Langfuse experiments

    Example:
        >>> accuracy_eval = create_g_eval_evaluator("accuracy", "security_auditor")
        >>> result = langfuse.run_experiment(
        ...     name="Security Audit",
        ...     data=dataset.items,
        ...     task=my_task,
        ...     evaluators=[accuracy_eval],
        ... )

    """
    evaluation_cls = _get_langfuse_evaluation_class()
    if evaluation_cls is None:
        msg = "Langfuse Evaluation class required. Install langfuse>=3.0.0"
        raise ImportError(msg)

    def evaluator(
        *,
        input: dict[str, Any] | str,
        output: Any,
        _expected_output: dict[str, Any] | str | None = None,
        **_kwargs: Any,
    ):
        """G-Eval criterion evaluator for Langfuse experiments.

        Args:
            input: The input content (from dataset item)
            output: The generated output to evaluate
            expected_output: Optional expected output for comparison
            **kwargs: Additional context from Langfuse

        Returns:
            Langfuse Evaluation object with criterion score

        """
        # Extract content from input
        if isinstance(input, dict):
            input_content = input.get("content", "") or json.dumps(input, default=str)
        else:
            input_content = str(input)

        # Convert output to string
        if isinstance(output, dict):
            output_str = json.dumps(output, indent=2, default=str)
        else:
            output_str = str(output) if output else ""

        # Run G-Eval scoring for this criterion only
        # Issue #428: submit_to_langfuse=False because we return Evaluation objects
        try:
            result: GEvalResult = _run_async(
                g_eval_score(
                    input_content=input_content,
                    output=output_str,
                    agent_type=agent_type,
                    criteria=[criterion],
                    use_cache=use_cache,
                    submit_to_langfuse=False,  # Evaluator returns Evaluation, Langfuse handles it
                )
            )

            # Get the criterion score
            criterion_score = result.criteria_scores.get(criterion)
            if criterion_score:
                return evaluation_cls(
                    name=f"g_eval_{criterion}",
                    value=criterion_score.normalized,
                    data_type="NUMERIC",
                    comment=criterion_score.reasoning[:500] if criterion_score.reasoning else None,
                    metadata={
                        "raw_score": criterion_score.score,
                        "confidence": criterion_score.confidence,
                        "agent_type": agent_type,
                        "criterion": criterion,
                    },
                )
            return evaluation_cls(
                name=f"g_eval_{criterion}",
                value=0.5,
                data_type="NUMERIC",
                comment=f"No score returned for {criterion}",
                metadata={"error": "missing_score", "agent_type": agent_type},
            )

        except Exception as e:
            logger.exception(
                "g_eval_evaluator_error",
                criterion=criterion,
                agent_type=agent_type,
                error=str(e),
            )
            return evaluation_cls(
                name=f"g_eval_{criterion}",
                value=None,
                data_type="NUMERIC",
                comment=f"Evaluation error: {e!s}",
                metadata={"error": str(e), "agent_type": agent_type},
            )

    # Set function name for Langfuse UI
    evaluator.__name__ = f"g_eval_{criterion}_evaluator"
    evaluator.__doc__ = f"G-Eval {criterion} evaluator for {agent_type}"

    return evaluator


def create_g_eval_overall_evaluator(
    agent_type: str = "tech_comparator",
    criteria: list[str] | None = None,
    use_cache: bool = True,
    use_self_consistency: bool = False,
):
    """Create an overall G-Eval evaluator for Langfuse experiments.

    Creates an evaluator that scores all criteria and returns weighted overall score.
    Compatible with `langfuse.run_experiment()`.

    Args:
        agent_type: Agent type for rubric selection
        criteria: List of criteria to evaluate (defaults to agent config)
        use_cache: Whether to use G-Eval caching
        use_self_consistency: Enable self-consistency voting for accuracy boost

    Returns:
        Evaluator function returning overall G-Eval score

    Example:
        >>> overall_eval = create_g_eval_overall_evaluator("implementation_planner")
        >>> result = langfuse.run_experiment(
        ...     name="Implementation Quality",
        ...     data=dataset.items,
        ...     task=my_task,
        ...     evaluators=[overall_eval],
        ... )

    """
    evaluation_cls = _get_langfuse_evaluation_class()
    if evaluation_cls is None:
        msg = "Langfuse Evaluation class required. Install langfuse>=3.0.0"
        raise ImportError(msg)

    # Get agent-specific configuration
    config = get_agent_rubrics(agent_type)
    eval_criteria = criteria or config.get(
        "criteria", ["completeness", "accuracy", "coherence", "depth"]
    )

    def evaluator(
        *,
        input: dict[str, Any] | str,
        output: Any,
        _expected_output: dict[str, Any] | str | None = None,
        **_kwargs: Any,
    ):
        """G-Eval overall evaluator for Langfuse experiments.

        Evaluates all criteria and returns weighted average score.

        Args:
            input: The input content (from dataset item)
            output: The generated output to evaluate
            expected_output: Optional expected output for comparison
            **kwargs: Additional context from Langfuse

        Returns:
            Langfuse Evaluation object with overall G-Eval score

        """
        # Extract content from input
        if isinstance(input, dict):
            input_content = input.get("content", "") or json.dumps(input, default=str)
        else:
            input_content = str(input)

        # Convert output to string
        if isinstance(output, dict):
            output_str = json.dumps(output, indent=2, default=str)
        else:
            output_str = str(output) if output else ""

        # Issue #428: submit_to_langfuse=False because we return Evaluation objects
        try:
            result: GEvalResult = _run_async(
                g_eval_score(
                    input_content=input_content,
                    output=output_str,
                    agent_type=agent_type,
                    criteria=eval_criteria,
                    use_cache=use_cache,
                    use_self_consistency=use_self_consistency,
                    submit_to_langfuse=False,  # Evaluator returns Evaluation, Langfuse handles it
                )
            )

            # Build metadata with all criterion scores
            metadata = {
                "agent_type": agent_type,
                "confidence": result.confidence,
                "criteria_evaluated": list(result.criteria_scores.keys()),
            }

            for criterion, score_obj in result.criteria_scores.items():
                metadata[f"{criterion}_score"] = score_obj.normalized
                metadata[f"{criterion}_raw"] = score_obj.score

            if result.voting_distribution:
                metadata["voting_distribution"] = result.voting_distribution

            # Build comment with score breakdown
            score_breakdown = ", ".join(
                f"{c}: {s.normalized:.2f}" for c, s in result.criteria_scores.items()
            )

            return evaluation_cls(
                name="g_eval_overall",
                value=result.overall,
                data_type="NUMERIC",
                comment=f"Weighted average: {score_breakdown}",
                metadata=metadata,
            )

        except Exception as e:
            logger.exception(
                "g_eval_overall_evaluator_error",
                agent_type=agent_type,
                criteria=eval_criteria,
                error=str(e),
            )
            return evaluation_cls(
                name="g_eval_overall",
                value=None,
                data_type="NUMERIC",
                comment=f"Evaluation error: {e!s}",
                metadata={"error": str(e), "agent_type": agent_type},
            )

    evaluator.__name__ = "g_eval_overall_evaluator"
    evaluator.__doc__ = f"G-Eval overall evaluator for {agent_type}"

    return evaluator


# ============================================================================
# Run-Level Evaluators (Aggregate Metrics)
# ============================================================================


def average_g_eval_score_evaluator(*, item_results: list, **_kwargs: Any):
    """Run-level evaluator that calculates average G-Eval score across all items.

    This evaluator aggregates the 'g_eval_overall' scores from all experiment items
    and returns the mean, providing an overall experiment quality metric.

    Args:
        item_results: List of ExperimentItemResult from Langfuse
        **kwargs: Additional context

    Returns:
        Langfuse Evaluation with average score

    Example:
        >>> result = langfuse.run_experiment(
        ...     name="Quality Experiment",
        ...     data=dataset.items,
        ...     task=my_task,
        ...     evaluators=[overall_eval],
        ...     run_evaluators=[average_g_eval_score_evaluator],
        ... )

    """
    evaluation_cls = _get_langfuse_evaluation_class()
    if evaluation_cls is None:
        return None

    # Extract g_eval_overall scores from all items
    overall_scores = []
    for item in item_results:
        for eval_obj in getattr(item, "evaluations", []):
            if eval_obj.name == "g_eval_overall" and eval_obj.value is not None:
                overall_scores.append(eval_obj.value)  # noqa: PERF401

    if not overall_scores:
        return evaluation_cls(
            name="avg_g_eval_overall",
            value=None,
            data_type="NUMERIC",
            comment="No g_eval_overall scores found",
            metadata={"total_items": len(item_results)},
        )

    avg = sum(overall_scores) / len(overall_scores)
    min_score = min(overall_scores)
    max_score = max(overall_scores)

    return evaluation_cls(
        name="avg_g_eval_overall",
        value=avg,
        data_type="NUMERIC",
        comment=(
            f"Average: {avg:.3f} (range: {min_score:.3f}-{max_score:.3f}, "
            f"n={len(overall_scores)})"
        ),
        metadata={
            "total_items": len(item_results),
            "scored_items": len(overall_scores),
            "min_score": min_score,
            "max_score": max_score,
            "std_dev": _calculate_std_dev(overall_scores),
        },
    )


def criterion_average_evaluator(criterion: str):
    """Create run-level evaluator that averages a specific criterion.

    Args:
        criterion: The G-Eval criterion to average (completeness, accuracy, etc.)

    Returns:
        Run-level evaluator function

    Example:
        >>> result = langfuse.run_experiment(
        ...     name="Accuracy Focus",
        ...     data=dataset.items,
        ...     task=my_task,
        ...     evaluators=[accuracy_eval],
        ...     run_evaluators=[criterion_average_evaluator("accuracy")],
        ... )

    """
    evaluation_cls = _get_langfuse_evaluation_class()

    def evaluator(*, item_results: list, **_kwargs: Any):
        if evaluation_cls is None:
            return None

        score_name = f"g_eval_{criterion}"
        scores = []

        for item in item_results:
            for eval_obj in getattr(item, "evaluations", []):
                if eval_obj.name == score_name and eval_obj.value is not None:
                    scores.append(eval_obj.value)  # noqa: PERF401

        if not scores:
            return evaluation_cls(
                name=f"avg_{score_name}",
                value=None,
                data_type="NUMERIC",
                comment=f"No {score_name} scores found",
            )

        avg = sum(scores) / len(scores)

        return evaluation_cls(
            name=f"avg_{score_name}",
            value=avg,
            data_type="NUMERIC",
            comment=f"Average {criterion}: {avg:.3f} (n={len(scores)})",
            metadata={
                "criterion": criterion,
                "scored_items": len(scores),
                "min": min(scores),
                "max": max(scores),
            },
        )

    evaluator.__name__ = f"avg_{criterion}_evaluator"
    return evaluator


def quality_threshold_evaluator(threshold: float = 0.6):
    """Run-level evaluator that counts items passing quality threshold.

    Useful for acceptance criteria: "X% of items must score above Y".

    Args:
        threshold: Minimum g_eval_overall score to pass (default: 0.6)

    Returns:
        Run-level evaluator function

    Example:
        >>> result = langfuse.run_experiment(
        ...     name="Quality Gate",
        ...     data=dataset.items,
        ...     task=my_task,
        ...     evaluators=[overall_eval],
        ...     run_evaluators=[quality_threshold_evaluator(0.7)],
        ... )

    """
    evaluation_cls = _get_langfuse_evaluation_class()

    def evaluator(*, item_results: list, **_kwargs: Any):
        if evaluation_cls is None:
            return None

        passing = 0
        total = 0

        for item in item_results:
            for eval_obj in getattr(item, "evaluations", []):
                if eval_obj.name == "g_eval_overall" and eval_obj.value is not None:
                    total += 1
                    if eval_obj.value >= threshold:
                        passing += 1

        if total == 0:
            return evaluation_cls(
                name="quality_pass_rate",
                value=None,
                data_type="NUMERIC",
                comment="No scores to evaluate",
            )

        pass_rate = passing / total

        return evaluation_cls(
            name="quality_pass_rate",
            value=pass_rate,
            data_type="NUMERIC",
            comment=f"{passing}/{total} items ({pass_rate:.1%}) passed threshold {threshold}",
            metadata={
                "threshold": threshold,
                "passing": passing,
                "failing": total - passing,
                "total": total,
            },
        )

    evaluator.__name__ = f"quality_threshold_{int(threshold * 100)}_evaluator"
    return evaluator


_MIN_SAMPLE_SIZE_FOR_STD_DEV = 2


def _calculate_std_dev(values: list[float]) -> float:
    """Calculate standard deviation of a list of values."""
    if len(values) < _MIN_SAMPLE_SIZE_FOR_STD_DEV:
        return 0.0
    mean = sum(values) / len(values)
    variance = sum((x - mean) ** 2 for x in values) / (len(values) - 1)
    return variance**0.5


# ============================================================================
# Pre-configured Evaluator Sets
# ============================================================================


def get_standard_evaluators(agent_type: str = "tech_comparator"):
    """Get standard set of G-Eval evaluators for an agent type.

    Returns evaluators for all agent-specific criteria plus overall score.
    Dynamically uses the agent's configured criteria from rubrics.

    Args:
        agent_type: Agent type for rubric selection

    Returns:
        List of evaluator functions

    Example:
        >>> evaluators = get_standard_evaluators("security_auditor")
        >>> result = langfuse.run_experiment(
        ...     name="Security Audit",
        ...     data=dataset.items,
        ...     task=my_task,
        ...     evaluators=evaluators,
        ... )

    """
    # Get agent-specific criteria from rubrics (not hardcoded)
    config = get_agent_rubrics(agent_type)
    criteria = config.get("criteria", ["completeness", "accuracy", "coherence", "depth"])

    evaluators = [create_g_eval_evaluator(criterion, agent_type) for criterion in criteria]
    evaluators.append(create_g_eval_overall_evaluator(agent_type))
    return evaluators


def get_standard_run_evaluators(
    quality_threshold: float = 0.6,
    agent_type: str = "tech_comparator",
):
    """Get standard set of run-level evaluators.

    Returns aggregation evaluators for experiment-wide metrics.
    Dynamically uses the agent's configured criteria from rubrics.

    Args:
        quality_threshold: Threshold for pass rate calculation
        agent_type: Agent type for rubric selection (determines which criteria to aggregate)

    Returns:
        List of run-level evaluator functions

    Example:
        >>> run_evals = get_standard_run_evaluators(0.7, "security_auditor")
        >>> result = langfuse.run_experiment(
        ...     name="Quality Check",
        ...     data=dataset.items,
        ...     task=my_task,
        ...     evaluators=evaluators,
        ...     run_evaluators=run_evals,
        ... )

    """
    # Get agent-specific criteria from rubrics (not hardcoded)
    config = get_agent_rubrics(agent_type)
    criteria = config.get("criteria", ["completeness", "accuracy", "coherence", "depth"])

    return [
        average_g_eval_score_evaluator,
        *[criterion_average_evaluator(criterion) for criterion in criteria],
        quality_threshold_evaluator(quality_threshold),
    ]
