"""Latency evaluator for LLM benchmarking.

This module provides evaluators that measure response time metrics:
- Time to first token (TTFT) for streaming responses
- Total response time (end-to-end)
- Percentile latencies (p50, p95, p99)

All evaluators are compatible with Langfuse's evaluate() method.
"""

from typing import Any

from app.evaluation.types import EvalExample, EvalRun


def latency_evaluator(run: EvalRun, _example: EvalExample) -> dict[str, Any]:
    """Evaluate response latency.

    Measures total execution time from the Langfuse run object.
    This captures end-to-end latency including all API calls, retries, and processing.

    Args:
        run: Langfuse run with timing information
        example: Golden example (not used for latency)

    Returns:
        Dictionary with:
            - key: "latency_ms"
            - score: Inverse of latency (lower latency = higher score)
            - comment: Latency in milliseconds

    """
    # Extract timing from run
    if not run.start_time or not run.end_time:
        return {
            "key": "latency_ms",
            "score": 0.0,
            "comment": "No timing data available",
        }

    # Calculate latency in milliseconds
    duration = run.end_time - run.start_time
    latency_ms = duration.total_seconds() * 1000

    # Score is inverse of latency (lower is better)
    # Normalize to 0-1 range assuming 10s is worst case
    max_latency_ms = 10000
    score = max(0.0, 1.0 - (latency_ms / max_latency_ms))

    return {
        "key": "latency_ms",
        "score": score,
        "comment": f"{latency_ms:.0f}ms",
    }


def ttft_evaluator(run: EvalRun, _example: EvalExample) -> dict[str, Any]:
    """Evaluate time to first token (for streaming responses).

    Measures how quickly the first token is returned for streaming LLM calls.
    This is important for perceived responsiveness in interactive applications.

    Args:
        run: Langfuse run with streaming timing information
        example: Golden example (not used)

    Returns:
        Dictionary with:
            - key: "ttft_ms"
            - score: Inverse of TTFT (lower = higher score)
            - comment: TTFT in milliseconds

    """
    # Extract TTFT from run metadata if available
    # This requires instrumentation in the target function to track first token time
    metadata = run.extra or {}
    ttft_ms = metadata.get("ttft_ms")

    if ttft_ms is None:
        return {
            "key": "ttft_ms",
            "score": 0.0,
            "comment": "No TTFT data available",
        }

    # Score is inverse of TTFT (lower is better)
    # Normalize to 0-1 range assuming 5s is worst case
    max_ttft_ms = 5000
    score = max(0.0, 1.0 - (ttft_ms / max_ttft_ms))

    return {
        "key": "ttft_ms",
        "score": score,
        "comment": f"{ttft_ms:.0f}ms",
    }
