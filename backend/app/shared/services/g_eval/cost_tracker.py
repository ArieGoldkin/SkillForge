"""Token and cost tracking for G-Eval LLM-as-Judge scoring.

This module provides a singleton cost tracker that monitors token usage
and calculates costs across G-Eval evaluation sessions.

Features:
- Track input, output, and cached tokens per evaluation
- Calculate costs based on model-specific pricing
- Session-level and per-evaluation cost summaries
- Singleton pattern for global tracking across evaluations

Pricing (as of Dec 2025):
- Gemini 3 Flash: $0.50/1M input, $3.00/1M output, $0.125/1M cached
- Gemini 2.5 Flash: $0.30/1M input, $2.50/1M output, $0.075/1M cached
- Gemini 2.0 Flash: $0.10/1M input, $0.40/1M output, $0.025/1M cached
- Claude Sonnet 4: $3.00/1M input, $15.00/1M output, $0.30/1M cached
- Claude Haiku 4.5: $1.00/1M input, $5.00/1M output, $0.10/1M cached
- Claude Haiku 3.5: $0.80/1M input, $4.00/1M output, $0.08/1M cached
- GPT-5 Mini: $0.25/1M input, $2.00/1M output
- GPT-4o: $2.50/1M input, $10.00/1M output
- GPT-4o-mini: $0.15/1M input, $0.60/1M output
- DeepSeek V3: $0.14/1M input, $0.28/1M output, $0.014/1M cached

Usage:
    tracker = GEvalCostTracker.get_instance()
    tracker.record_usage("eval-1", "gemini-2.0-flash", 1000, 500, 200)
    summary = tracker.get_session_summary()
"""

from __future__ import annotations

from dataclasses import dataclass, field
from threading import Lock
from typing import ClassVar

from app.core.logging import get_logger

logger = get_logger(__name__)

# ============================================================================
# Pricing Configuration
# ============================================================================

# Prices in USD per 1M tokens (as of Dec 2025)
MODEL_PRICING = {
    # Google Gemini
    "gemini-3-flash": {"input": 0.50, "output": 3.00, "cached": 0.125},
    "gemini-2.5-flash": {"input": 0.30, "output": 2.50, "cached": 0.075},
    "gemini-2.0-flash": {"input": 0.10, "output": 0.40, "cached": 0.025},
    # Anthropic Claude
    "claude-sonnet-4": {"input": 3.00, "output": 15.00, "cached": 0.30},
    "claude-haiku-4.5": {"input": 1.00, "output": 5.00, "cached": 0.10},
    "claude-haiku-3.5": {"input": 0.80, "output": 4.00, "cached": 0.08},
    # OpenAI GPT
    "gpt-5-mini": {"input": 0.25, "output": 2.00, "cached": 0.0},
    "gpt-4o": {"input": 2.50, "output": 10.00, "cached": 0.0},
    "gpt-4o-mini": {"input": 0.15, "output": 0.60, "cached": 0.0},
    # DeepSeek
    "deepseek-v3": {"input": 0.14, "output": 0.28, "cached": 0.014},
    # Default fallback
    "default": {"input": 1.00, "output": 5.00, "cached": 0.10},
}


def _normalize_model_name(model: str) -> str:
    """Normalize model name to match pricing keys.

    Args:
        model: Raw model identifier (e.g., "gemini-2.0-flash-002")

    Returns:
        Normalized key for pricing lookup (e.g., "gemini-2.0-flash")

    """
    model_lower = model.lower().strip()

    # Match against pricing keys
    for pricing_key in MODEL_PRICING:
        if pricing_key in model_lower:
            return pricing_key

    logger.warning(
        "cost_tracker_unknown_model",
        model=model,
        msg="Using default pricing - model not in pricing table",
    )
    return "default"


# ============================================================================
# Data Classes
# ============================================================================


@dataclass
class EvaluationCost:
    """Cost tracking for a single evaluation."""

    eval_id: str
    model: str
    input_tokens: int
    output_tokens: int
    cached_tokens: int
    input_cost: float
    output_cost: float
    cached_cost: float
    total_cost: float

    @property
    def total_tokens(self) -> int:
        """Total tokens used (input + output + cached)."""
        return self.input_tokens + self.output_tokens + self.cached_tokens


@dataclass
class SessionSummary:
    """Summary of all costs in a session."""

    total_evaluations: int
    total_input_tokens: int
    total_output_tokens: int
    total_cached_tokens: int
    total_cost: float
    by_model: dict[str, EvaluationCost] = field(default_factory=dict)
    by_variant: dict[str, EvaluationCost] = field(default_factory=dict)

    @property
    def total_tokens(self) -> int:
        """Total tokens across all evaluations."""
        return self.total_input_tokens + self.total_output_tokens + self.total_cached_tokens

    @property
    def avg_tokens_per_eval(self) -> float:
        """Average tokens per evaluation."""
        return self.total_tokens / self.total_evaluations if self.total_evaluations > 0 else 0.0

    @property
    def avg_cost_per_eval(self) -> float:
        """Average cost per evaluation."""
        return self.total_cost / self.total_evaluations if self.total_evaluations > 0 else 0.0


# ============================================================================
# Cost Tracker
# ============================================================================


class GEvalCostTracker:
    """Singleton cost tracker for G-Eval evaluations.

    Thread-safe singleton that tracks token usage and costs across
    all G-Eval scoring operations in a session.

    Example:
        tracker = GEvalCostTracker.get_instance()

        # Record usage after LLM call
        tracker.record_usage(
            eval_id="eval-1",
            model="gemini-2.0-flash",
            input_tokens=1000,
            output_tokens=500,
            cached_tokens=200,
        )

        # Get summary
        summary = tracker.get_session_summary()
        print(f"Total cost: ${summary.total_cost:.4f}")

    """

    _instance: ClassVar[GEvalCostTracker | None] = None
    _lock: ClassVar[Lock] = Lock()

    def __init__(self) -> None:
        """Initialize cost tracker (use get_instance() instead)."""
        self._evaluations: dict[str, EvaluationCost] = {}
        self._by_variant: dict[str, list[str]] = {}  # variant -> list of eval_ids
        self._instance_lock = Lock()

    @classmethod
    def get_instance(cls) -> GEvalCostTracker:
        """Get singleton instance (thread-safe)."""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
                    logger.info("cost_tracker_initialized")
        # At this point _instance is guaranteed to be set
        assert cls._instance is not None  # noqa: S101 - Type checker hint
        return cls._instance

    @classmethod
    def reset_instance(cls) -> None:
        """Reset singleton instance (mainly for testing)."""
        with cls._lock:
            cls._instance = None
            logger.info("cost_tracker_reset")

    def record_usage(  # noqa: PLR0913 - Need all params for comprehensive tracking
        self,
        eval_id: str,
        model: str,
        input_tokens: int,
        output_tokens: int,
        cached_tokens: int = 0,
        variant: str | None = None,
    ) -> EvaluationCost:
        """Record token usage for an evaluation.

        Args:
            eval_id: Unique evaluation identifier
            model: Model name used for evaluation
            input_tokens: Number of input tokens
            output_tokens: Number of output tokens
            cached_tokens: Number of cached/prompt-cached tokens
            variant: Optional variant name (e.g., "control", "few_shot", "cot")

        Returns:
            EvaluationCost with calculated costs

        """
        # Normalize model name and get pricing
        normalized_model = _normalize_model_name(model)
        pricing = MODEL_PRICING.get(normalized_model, MODEL_PRICING["default"])

        # Calculate costs (prices are per 1M tokens)
        input_cost = (input_tokens / 1_000_000) * pricing["input"]
        output_cost = (output_tokens / 1_000_000) * pricing["output"]
        cached_cost = (cached_tokens / 1_000_000) * pricing["cached"]
        total_cost = input_cost + output_cost + cached_cost

        cost = EvaluationCost(
            eval_id=eval_id,
            model=normalized_model,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            cached_tokens=cached_tokens,
            input_cost=input_cost,
            output_cost=output_cost,
            cached_cost=cached_cost,
            total_cost=total_cost,
        )

        # Thread-safe update
        with self._instance_lock:
            self._evaluations[eval_id] = cost

            # Track by variant
            if variant:
                if variant not in self._by_variant:
                    self._by_variant[variant] = []
                self._by_variant[variant].append(eval_id)

        logger.info(
            "cost_tracker_recorded",
            eval_id=eval_id,
            model=normalized_model,
            variant=variant,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            cached_tokens=cached_tokens,
            total_cost=total_cost,
        )

        return cost

    def get_evaluation_cost(self, eval_id: str) -> EvaluationCost | None:
        """Get cost for a specific evaluation."""
        return self._evaluations.get(eval_id)

    def get_variant_summary(self, variant: str) -> SessionSummary | None:
        """Get cost summary for a specific variant.

        Args:
            variant: Variant name (e.g., "control", "few_shot", "cot")

        Returns:
            SessionSummary for the variant, or None if no evaluations recorded

        """
        eval_ids = self._by_variant.get(variant, [])
        if not eval_ids:
            return None

        evals = [self._evaluations[eid] for eid in eval_ids if eid in self._evaluations]
        if not evals:
            return None

        return SessionSummary(
            total_evaluations=len(evals),
            total_input_tokens=sum(e.input_tokens for e in evals),
            total_output_tokens=sum(e.output_tokens for e in evals),
            total_cached_tokens=sum(e.cached_tokens for e in evals),
            total_cost=sum(e.total_cost for e in evals),
            by_variant={variant: evals[0]},  # Representative cost
        )

    def get_session_summary(self) -> SessionSummary:
        """Get cost summary for entire session.

        Returns:
            SessionSummary with aggregated costs across all evaluations

        """
        if not self._evaluations:
            return SessionSummary(
                total_evaluations=0,
                total_input_tokens=0,
                total_output_tokens=0,
                total_cached_tokens=0,
                total_cost=0.0,
            )

        evals = list(self._evaluations.values())

        # Aggregate by model
        by_model: dict[str, list[EvaluationCost]] = {}
        for cost in evals:
            if cost.model not in by_model:
                by_model[cost.model] = []
            by_model[cost.model].append(cost)

        # Create representative costs per model
        by_model_summary = {}
        for model, model_costs in by_model.items():
            by_model_summary[model] = EvaluationCost(
                eval_id=f"{model}_aggregate",
                model=model,
                input_tokens=sum(c.input_tokens for c in model_costs),
                output_tokens=sum(c.output_tokens for c in model_costs),
                cached_tokens=sum(c.cached_tokens for c in model_costs),
                input_cost=sum(c.input_cost for c in model_costs),
                output_cost=sum(c.output_cost for c in model_costs),
                cached_cost=sum(c.cached_cost for c in model_costs),
                total_cost=sum(c.total_cost for c in model_costs),
            )

        # Aggregate by variant
        by_variant_summary = {}
        for variant, eval_ids in self._by_variant.items():
            variant_costs = [self._evaluations[eid] for eid in eval_ids if eid in self._evaluations]
            if variant_costs:
                by_variant_summary[variant] = EvaluationCost(
                    eval_id=f"{variant}_aggregate",
                    model=variant_costs[0].model,  # Representative model
                    input_tokens=sum(c.input_tokens for c in variant_costs),
                    output_tokens=sum(c.output_tokens for c in variant_costs),
                    cached_tokens=sum(c.cached_tokens for c in variant_costs),
                    input_cost=sum(c.input_cost for c in variant_costs),
                    output_cost=sum(c.output_cost for c in variant_costs),
                    cached_cost=sum(c.cached_cost for c in variant_costs),
                    total_cost=sum(c.total_cost for c in variant_costs),
                )

        return SessionSummary(
            total_evaluations=len(evals),
            total_input_tokens=sum(e.input_tokens for e in evals),
            total_output_tokens=sum(e.output_tokens for e in evals),
            total_cached_tokens=sum(e.cached_tokens for e in evals),
            total_cost=sum(e.total_cost for e in evals),
            by_model=by_model_summary,
            by_variant=by_variant_summary,
        )

    def reset(self) -> None:
        """Reset all tracked costs (for new session)."""
        with self._instance_lock:
            self._evaluations.clear()
            self._by_variant.clear()
        logger.info("cost_tracker_session_reset")
