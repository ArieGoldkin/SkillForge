"""LLM Evaluation Framework for SkillForge.

This module provides tools for benchmarking LLM models across different tasks
using golden datasets and automated evaluators integrated with Langfuse.

Key components:
- Golden datasets: Curated examples with expected outputs for supervisor, agent, and synthesis tasks
- Benchmark runner: Executes A/B experiments across multiple models
- Evaluators: Correctness, quality (LLM-as-judge), latency, and cost metrics
- Config generator: Produces optimal model configuration from experiment results
- Experiment runner: CI/CD automation for Langfuse experiments (Issue #428)
"""

from app.evaluation.experiment_runner import (
    ExperimentRunner,
    ExperimentRunResult,
    ExperimentSummary,
)
from app.evaluation.llm_benchmark import LLMBenchmark

__all__ = [
    "ExperimentRunResult",
    "ExperimentRunner",
    "ExperimentSummary",
    "LLMBenchmark",
]
