"""Auto-generated model configuration from LLM benchmark experiments.

Generated: 2025-12-09T19:25:52
Last Updated: 2025-12-09T19:25:52 (supervisor validated)

This file contains optimal model selections based on evaluation metrics.
Edit this file to customize model routing for your use case.

VALIDATION STATUS:
  - supervisor: ✓ VALIDATED (20 examples, 4 providers, Dec 9 2025)
  - agent_analysis: ○ HYPOTHESIS (pending validation)
  - synthesis: ○ HYPOTHESIS (pending validation)
  - tutoring: ○ HYPOTHESIS (pending validation)
  - code_analysis: ○ HYPOTHESIS (pending validation)
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

ValidationStatus = Literal["validated", "hypothesis"]


@dataclass(frozen=True)
class TaskModelConfig:
    """Configuration for a task's model selection with validation metadata."""

    primary: str
    fallback: str
    status: ValidationStatus
    correctness: float | None = None  # Validation metric (0.0-1.0)
    cost_per_call: float | None = None  # Average cost in USD
    latency_p50_ms: float | None = None  # Median latency in milliseconds


# Task-specific model assignments with validation metadata
# SUPERVISOR: Validated via multi-provider benchmark (Dec 9, 2025)
#   Winner: gemini-2.5-flash with 48.7% correctness
#   Cost savings: up to 97% vs alternatives
#   Trade-off: Higher latency (6.2s vs 2s for gpt-4o)
TASK_MODELS: dict[str, TaskModelConfig] = {
    # ✓ VALIDATED: Benchmark showed gemini-2.5-flash wins on correctness + cost
    "supervisor": TaskModelConfig(
        primary="gemini-2.5-flash",
        fallback="gpt-4o-mini",  # Best latency alternative
        status="validated",
        correctness=0.487,  # 48.7% Jaccard similarity
        cost_per_call=0.00011,  # $0.11 per 1000 calls
        latency_p50_ms=6167,  # 6.2 seconds median
    ),
    # ○ HYPOTHESIS: Pending validation
    "agent_analysis": TaskModelConfig(
        primary="gpt-5-mini",
        fallback="claude-sonnet-4-20250514",
        status="hypothesis",
    ),
    # ○ HYPOTHESIS: Pending validation
    "synthesis": TaskModelConfig(
        primary="claude-sonnet-4-20250514",
        fallback="gpt-5",
        status="hypothesis",
    ),
    # ○ HYPOTHESIS: Pending validation
    "tutoring": TaskModelConfig(
        primary="claude-sonnet-4-20250514",
        fallback="gpt-5",
        status="hypothesis",
    ),
    # ○ HYPOTHESIS: Pending validation
    "code_analysis": TaskModelConfig(
        primary="claude-sonnet-4-20250514",
        fallback="gpt-5",
        status="hypothesis",
    ),
}

# Legacy dict format for backwards compatibility
TASK_MODELS_LEGACY = {
    task: (config.primary, config.fallback) for task, config in TASK_MODELS.items()
}


def get_model_for_task(task_type: str, use_fallback: bool = False) -> str | None:
    """Get optimal model for a task type.

    Args:
        task_type: Type of task (supervisor, agent_analysis, synthesis, etc.)
        use_fallback: If True, return fallback model instead of primary

    Returns:
        Model identifier string, or None if task type not found
    """
    config = TASK_MODELS.get(task_type)
    if not config:
        return None
    return config.fallback if use_fallback else config.primary


def get_task_config(task_type: str) -> TaskModelConfig | None:
    """Get full configuration for a task type including validation metadata.

    Args:
        task_type: Type of task

    Returns:
        TaskModelConfig with primary, fallback, status, and metrics
    """
    return TASK_MODELS.get(task_type)


def is_validated(task_type: str) -> bool:
    """Check if a task's model selection has been validated via benchmark.

    Args:
        task_type: Type of task

    Returns:
        True if validated, False if hypothesis-based
    """
    config = TASK_MODELS.get(task_type)
    return config.status == "validated" if config else False


# Selection rationale (for documentation)
SELECTION_RATIONALE = {
    "supervisor": """✓ VALIDATED via multi-provider benchmark (Dec 9, 2025):
  - Primary: Gemini 2.5 Flash
  - Fallback: GPT-4o-mini (best latency alternative)
  - Benchmark: 20 examples, 4 providers (OpenAI, Google, Anthropic)
  - Results:
    • gemini-2.5-flash: 48.7% correctness, $0.002 cost, 6.2s latency
    • gpt-4o-mini: 46.7% correctness, $0.008 cost, 2.0s latency
    • claude-haiku: 45.6% correctness, $0.013 cost, 2.7s latency
    • gpt-4o: 45.2% correctness, $0.069 cost, 1.9s latency
  - Trade-off: Higher latency (3x) but 75-97% cost savings
  - Rationale: Supervisor routing prioritizes correctness over speed;
               the 2% accuracy gain justifies the latency increase""",
    "agent_analysis": """○ HYPOTHESIS (pending validation):
  - Primary: GPT-5 Mini
  - Fallback: Claude Sonnet 4
  - Rationale: Balanced model for domain-specific analysis""",
    "synthesis": """○ HYPOTHESIS (pending validation):
  - Primary: Claude Sonnet 4
  - Fallback: GPT-5
  - Rationale: Claude excels at coherent multi-source synthesis""",
    "tutoring": """○ HYPOTHESIS (pending validation):
  - Primary: Claude Sonnet 4
  - Fallback: GPT-5
  - Rationale: Claude's teaching style suits tutoring dialogues""",
    "code_analysis": """○ HYPOTHESIS (pending validation):
  - Primary: Claude Sonnet 4
  - Fallback: GPT-5
  - Rationale: Claude leads SWE-bench (72.5%), best for code analysis""",
}


# =============================================================================
# BENCHMARK RESULTS ARCHIVE (December 2025)
# =============================================================================
# Raw results from multi-provider supervisor benchmark
# Run: 2025-12-09T19:21:19 to 2025-12-09T19:25:52
# Dataset: supervisor_golden_v1 (20 examples)
# =============================================================================

SUPERVISOR_BENCHMARK_RESULTS = {
    "timestamp": "2025-12-09T19:25:52",
    "dataset": "supervisor_golden_v1",
    "example_count": 20,
    "winner_by_metric": {
        "supervisor_correctness": "gemini-2.5-flash",
        "cost_total": "gemini-2.5-flash",
        "cost_avg": "gemini-2.5-flash",
        "latency_ms": "gpt-4o",
        "latency_p50": "gpt-4o",
        "latency_p95": "gpt-4o-mini",
    },
    "models": {
        "gpt-4o-mini": {
            "correctness": 0.467,
            "cost_total": 0.0084,
            "cost_avg": 0.00042,
            "latency_p50_ms": 2041,
            "latency_p95_ms": 2717,
        },
        "gpt-4o": {
            "correctness": 0.452,
            "cost_total": 0.0693,
            "cost_avg": 0.00346,
            "latency_p50_ms": 1887,
            "latency_p95_ms": 4153,
        },
        "gemini-2.5-flash": {
            "correctness": 0.487,
            "cost_total": 0.0021,
            "cost_avg": 0.00011,
            "latency_p50_ms": 6167,
            "latency_p95_ms": 19457,
        },
        "claude-haiku-3-5-20241022": {
            "correctness": 0.456,
            "cost_total": 0.0126,
            "cost_avg": 0.00063,
            "latency_p50_ms": 2724,
            "latency_p95_ms": 3882,
        },
    },
    "cost_savings_vs_winner": {
        "gpt-4o-mini": 74.9,
        "gpt-4o": 97.0,
        "claude-haiku": 83.3,
    },
    "recommendation": (
        "gemini-2.5-flash for supervisor task. "
        "Won 3/7 metrics (correctness, cost_total, cost_avg). "
        "Trade-off: 3x higher latency but 75-97% cost savings."
    ),
}
