"""Hybrid evaluator that supports multiple evaluation backends.

This module provides a unified interface for quality evaluation that can:
- Use local G-Eval (PRIMARY, default, self-contained)
- Use Langfuse evaluators (COMPLEMENTARY, opt-in, with observability)
- Use both simultaneously (HYBRID, for comparison and validation)

The hybrid evaluator automatically falls back to local G-Eval when Langfuse
API is unavailable, ensuring evaluation reliability.

Configuration via environment variable:
- EVALUATOR_BACKEND="local" (default) - Use local G-Eval only
- EVALUATOR_BACKEND="langfuse" - Use Langfuse with fallback to local
- EVALUATOR_BACKEND="both" - Run both evaluators and log comparison

Issue #381: Langfuse LLM-as-Judge Evaluators
"""

from __future__ import annotations

from typing import Any

from app.core.logging import get_logger
from app.evaluation.types import Example, Run

logger = get_logger(__name__)


class HybridEvaluator:
    """Hybrid evaluator supporting multiple backends.

    This evaluator wraps both local G-Eval and Langfuse evaluators,
    providing a unified interface with configurable backend selection
    and automatic fallback handling.

    Backends:
    - "local": Local G-Eval only (default, self-contained, fast)
    - "langfuse": Langfuse with fallback to local (observability, cost tracking)
    - "both": Run both and compare (validation, A/B testing)

    The evaluator handles Run/Example objects (Langfuse format) and
    returns scores in the same format as the quality evaluators.
    """

    def __init__(
        self,
        aspect: str,
        backend: str = "local",
        judge_model: str | None = None,
    ):
        """Initialize hybrid evaluator.

        Args:
            aspect: Quality aspect to evaluate (relevance, depth, coherence)
            backend: Backend to use (local, langfuse, both)
            judge_model: Optional model override for Langfuse

        """
        self.aspect = aspect
        self.backend = backend
        self.judge_model = judge_model

        # Validate backend
        if backend not in ["local", "langfuse", "both"]:
            msg = f"Invalid backend: {backend}. Must be one of: local, langfuse, both"
            raise ValueError(msg)

        # Validate aspect
        if aspect not in ["relevance", "depth", "coherence", "overall"]:
            msg = f"Invalid aspect: {aspect}. Must be one of: relevance, depth, coherence, overall"
            raise ValueError(msg)

    async def evaluate(self, run: Run, example: Example) -> dict[str, Any]:
        """Evaluate output quality using configured backend.

        Args:
            run: Langfuse run with outputs
            example: Example with inputs and reference outputs

        Returns:
            Dictionary with:
                - key: "quality_{aspect}"
                - score: Normalized score (0.0-1.0)
                - comment: Evaluation comment/reasoning

        """
        if self.backend == "local":
            return await self._evaluate_local(run, example)

        elif self.backend == "langfuse":
            return await self._evaluate_langfuse_with_fallback(run, example)

        elif self.backend == "both":
            return await self._evaluate_both(run, example)

        # Should never reach here due to __init__ validation
        msg = f"Unknown backend: {self.backend}"
        raise ValueError(msg)

    async def _evaluate_local(self, run: Run, example: Example) -> dict[str, Any]:
        """Evaluate using local G-Eval only.

        Args:
            run: Langfuse run
            example: Example data

        Returns:
            Evaluation result dictionary

        """
        from app.evaluation.evaluators.quality import create_quality_evaluator

        logger.debug(
            "hybrid_evaluator_using_local",
            aspect=self.aspect,
            backend="local",
        )

        evaluator = create_quality_evaluator(aspect=self.aspect, judge_model=self.judge_model)
        return await evaluator(run, example)

    async def _evaluate_langfuse_with_fallback(self, run: Run, example: Example) -> dict[str, Any]:
        """Evaluate using Langfuse with automatic fallback to local.

        Args:
            run: Langfuse run
            example: Example data

        Returns:
            Evaluation result dictionary

        """
        from app.evaluation.evaluators.quality import _extract_evaluable_content
        from app.shared.services.evaluators.langfuse_evaluators import (
            create_langfuse_evaluator,
        )

        try:
            logger.debug(
                "hybrid_evaluator_using_langfuse",
                aspect=self.aspect,
                backend="langfuse",
            )

            # Extract content for evaluation
            input_content = _extract_evaluable_content(example.inputs)
            output_content = _extract_evaluable_content(run.outputs)

            # Get trace_id from run
            trace_id = str(run.trace_id) if run.trace_id else None

            # Create Langfuse evaluator
            evaluator = create_langfuse_evaluator(criterion=self.aspect, model=self.judge_model)

            # Run Langfuse evaluation
            score = await evaluator.evaluate(
                trace_id=trace_id,
                input_content=input_content,
                output_content=output_content,
                criterion=self.aspect,
            )

            return {
                "key": f"quality_{self.aspect}",
                "score": score,
                "comment": f"Langfuse evaluation: {score:.2f}",
            }

        except Exception as e:
            # Fallback to local G-Eval on any error
            logger.warning(
                "hybrid_evaluator_langfuse_failed_fallback_to_local",
                aspect=self.aspect,
                error=str(e),
                error_type=type(e).__name__,
            )

            return await self._evaluate_local(run, example)

    async def _evaluate_both(self, run: Run, example: Example) -> dict[str, Any]:
        """Evaluate using both local and Langfuse for comparison.

        This mode runs both evaluators and logs the comparison for analysis.
        The local score is used for gate decisions (as primary).

        Args:
            run: Langfuse run
            example: Example data

        Returns:
            Evaluation result dictionary (uses local score for gate)

        """
        import asyncio

        from app.evaluation.evaluators.quality import _extract_evaluable_content
        from app.shared.services.evaluators.langfuse_evaluators import (
            create_langfuse_evaluator,
        )

        logger.debug(
            "hybrid_evaluator_using_both",
            aspect=self.aspect,
            backend="both",
        )

        # Run local evaluator
        local_task = self._evaluate_local(run, example)

        # Prepare Langfuse evaluator
        input_content = _extract_evaluable_content(example.inputs)
        output_content = _extract_evaluable_content(run.outputs)
        trace_id = str(run.trace_id) if run.trace_id else None

        async def langfuse_eval_wrapper() -> dict[str, Any]:
            """Wrapper for Langfuse evaluation with error handling."""
            try:
                evaluator = create_langfuse_evaluator(criterion=self.aspect, model=self.judge_model)
                score = await evaluator.evaluate(
                    trace_id=trace_id,
                    input_content=input_content,
                    output_content=output_content,
                    criterion=self.aspect,
                )
                return {
                    "key": f"quality_{self.aspect}",
                    "score": score,
                    "comment": f"Langfuse: {score:.2f}",
                }
            except Exception as e:
                logger.warning(
                    "hybrid_evaluator_langfuse_failed_in_both_mode",
                    aspect=self.aspect,
                    error=str(e),
                )
                return {
                    "key": f"quality_{self.aspect}",
                    "score": 0.0,
                    "comment": f"Langfuse failed: {e!s}",
                }

        langfuse_task = langfuse_eval_wrapper()

        # Run both evaluators in parallel
        local_result, langfuse_result = await asyncio.gather(local_task, langfuse_task)

        # Compare scores
        local_score = local_result.get("score", 0.0)
        langfuse_score = langfuse_result.get("score", 0.0)
        score_diff = abs(local_score - langfuse_score)

        logger.info(
            "hybrid_evaluator_comparison",
            aspect=self.aspect,
            local_score=local_score,
            langfuse_score=langfuse_score,
            score_diff=score_diff,
            agreement_level="high" if score_diff < 0.1 else "medium" if score_diff < 0.2 else "low",
        )

        # Return local result (primary) with comparison metadata
        local_result["comment"] = (
            f"Local: {local_score:.2f}, Langfuse: {langfuse_score:.2f}, Diff: {score_diff:.2f}"
        )

        return local_result


def create_hybrid_evaluator(
    aspect: str,
    backend: str | None = None,
    judge_model: str | None = None,
) -> HybridEvaluator:
    """Create a hybrid evaluator with configurable backend.

    Args:
        aspect: Quality aspect to evaluate (relevance, depth, coherence, overall)
        backend: Backend to use (local, langfuse, both) - defaults to settings.EVALUATOR_BACKEND
        judge_model: Optional model override

    Returns:
        HybridEvaluator instance

    Example:
        >>> evaluator = create_hybrid_evaluator("relevance", backend="langfuse")
        >>> result = await evaluator.evaluate(run, example)

    """
    # Get backend from settings if not provided
    if backend is None:
        from app.core.config import get_settings

        settings = get_settings()
        backend = getattr(settings, "EVALUATOR_BACKEND", "local")

    return HybridEvaluator(aspect=aspect, backend=backend, judge_model=judge_model)
