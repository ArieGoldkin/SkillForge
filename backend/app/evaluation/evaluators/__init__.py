"""LLM output evaluators for benchmarking.

This module provides evaluators compatible with Langfuse's evaluate() method:
- Correctness: Task-specific accuracy metrics
- Quality: LLM-as-judge scoring for relevance, depth, accuracy, coherence
- Latency: Time-to-first-token and total response time
- Cost: Token counting and cost estimation
"""

from app.evaluation.evaluators.correctness import (
    agent_correctness_evaluator,
    supervisor_correctness_evaluator,
    supervisor_coverage_evaluator,
    supervisor_precision_evaluator,
    synthesis_correctness_evaluator,
)
from app.evaluation.evaluators.cost import cost_evaluator, cost_per_correct_evaluator
from app.evaluation.evaluators.latency import latency_evaluator, ttft_evaluator
from app.evaluation.evaluators.quality import (
    accuracy_evaluator,
    coherence_evaluator,
    create_quality_evaluator,
    depth_evaluator,
    overall_quality_evaluator,
    relevance_evaluator,
)

__all__ = [
    # Correctness evaluators
    "supervisor_correctness_evaluator",
    "supervisor_coverage_evaluator",
    "supervisor_precision_evaluator",
    "agent_correctness_evaluator",
    "synthesis_correctness_evaluator",
    # Quality evaluators
    "create_quality_evaluator",
    "relevance_evaluator",
    "depth_evaluator",
    "accuracy_evaluator",
    "coherence_evaluator",
    "overall_quality_evaluator",
    # Performance evaluators
    "latency_evaluator",
    "ttft_evaluator",
    "cost_evaluator",
    "cost_per_correct_evaluator",
]
