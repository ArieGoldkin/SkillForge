"""Metrics tracking for LLM technique performance."""

import time
from dataclasses import dataclass, field
from typing import Literal

from app.core.logging import get_logger

logger = get_logger(__name__)


@dataclass
class TechniqueMetrics:
    """Metrics for a single analysis run."""

    analysis_id: str
    technique: str
    variant: Literal["control", "treatment"]

    # Performance
    latency_ms: float = 0
    token_count_input: int = 0
    token_count_output: int = 0

    # Caching
    cache_hit: bool = False
    cache_level: str | None = None  # "l1_exact", "l2_redis", "l3_prompt"

    # Few-Shot Prompting metrics
    example_retrieval_ms: float = 0  # Time to retrieve examples from vector DB
    num_examples_used: int = 0  # Number of examples injected into prompt

    # Quality (populated later via feedback)
    quality_score: float | None = None

    # Cost
    estimated_cost_usd: float = 0

    # Timestamps
    started_at: float = field(default_factory=time.time)
    completed_at: float | None = None


class MetricsCollector:
    """Collect and report technique metrics."""

    def __init__(self):
        """Initialize MetricsCollector with empty metrics list."""
        self._metrics: list[TechniqueMetrics] = []

    def record(self, metrics: TechniqueMetrics) -> None:
        """Record metrics for an analysis."""
        metrics.completed_at = time.time()
        self._metrics.append(metrics)

        logger.info(
            "technique_metrics_recorded",
            analysis_id=metrics.analysis_id,
            technique=metrics.technique,
            variant=metrics.variant,
            latency_ms=metrics.latency_ms,
            cache_hit=metrics.cache_hit,
            estimated_cost_usd=metrics.estimated_cost_usd,
        )

    def get_summary(self, technique: str) -> dict:
        """Get summary statistics for a technique."""
        technique_metrics = [m for m in self._metrics if m.technique == technique]

        if not technique_metrics:
            return {}

        control = [m for m in technique_metrics if m.variant == "control"]
        treatment = [m for m in technique_metrics if m.variant == "treatment"]

        return {
            "technique": technique,
            "control_count": len(control),
            "treatment_count": len(treatment),
            "control_avg_latency": sum(m.latency_ms for m in control) / len(control)
            if control
            else 0,
            "treatment_avg_latency": sum(m.latency_ms for m in treatment) / len(treatment)
            if treatment
            else 0,
            "treatment_cache_hit_rate": sum(1 for m in treatment if m.cache_hit) / len(treatment)
            if treatment
            else 0,
        }


# Global collector instance
metrics_collector = MetricsCollector()
