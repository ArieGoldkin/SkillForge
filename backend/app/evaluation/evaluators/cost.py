"""Cost evaluator for LLM benchmarking.

This module provides evaluators that measure API cost metrics:
- Token usage (input and output)
- Estimated cost based on model pricing
- Cost per correct answer (cost-effectiveness)

All evaluators are compatible with Langfuse's evaluate() method.
"""

from typing import Any

from app.core.model_registry import get_model_info
from app.evaluation.types import Example, Run


def cost_evaluator(run: Run, example: Example) -> dict[str, Any]:
    """Evaluate API cost based on token usage.

    Calculates the estimated cost of the LLM call using token counts
    and model pricing from the model registry.

    Args:
        run: Langfuse run with token usage information
        example: Golden example (not used for cost)

    Returns:
        Dictionary with:
            - key: "cost_usd"
            - score: Inverse of cost (lower cost = higher score)
            - comment: Cost in USD and token breakdown

    """
    # Extract token usage from run
    # Langfuse tracks usage in run.outputs or run.extra
    usage = {}
    if hasattr(run, "outputs") and run.outputs:
        usage = run.outputs.get("usage", {})
    if not usage and hasattr(run, "extra") and run.extra:
        usage = run.extra.get("usage", {})

    input_tokens = usage.get("input_tokens", 0) or usage.get("prompt_tokens", 0)
    output_tokens = usage.get("output_tokens", 0) or usage.get("completion_tokens", 0)

    if not input_tokens and not output_tokens:
        return {
            "key": "cost_usd",
            "score": 0.0,
            "comment": "No token usage data available",
        }

    # Get model info from run metadata
    metadata = run.extra or {}
    model_id = metadata.get("model_id", "unknown")

    model_info = get_model_info(model_id)
    if not model_info:
        return {
            "key": "cost_usd",
            "score": 0.0,
            "comment": f"Model '{model_id}' not found in registry",
        }

    # Calculate cost
    cost_usd = model_info.estimate_cost(input_tokens, output_tokens)

    # Score is inverse of cost (lower is better)
    # Normalize to 0-1 range assuming $0.10 is worst case
    max_cost = 0.10
    score = max(0.0, 1.0 - (cost_usd / max_cost))

    return {
        "key": "cost_usd",
        "score": score,
        "comment": f"${cost_usd:.6f} ({input_tokens} in + {output_tokens} out tokens)",
    }


def cost_per_correct_evaluator(run: Run, example: Example) -> dict[str, Any]:
    """Evaluate cost-effectiveness (cost per correct answer).

    Combines cost and correctness to measure how cost-effective a model is.
    Lower cost per correct answer is better.

    Args:
        run: Langfuse run with cost and correctness data
        example: Golden example for correctness evaluation

    Returns:
        Dictionary with:
            - key: "cost_per_correct"
            - score: Correctness / cost ratio
            - comment: Cost-effectiveness metric

    """
    # Get cost from run
    cost_result = cost_evaluator(run, example)
    cost_usd = 0.0

    # Parse cost from comment
    if "comment" in cost_result:
        comment = cost_result["comment"]
        if "$" in comment:
            try:
                cost_str = comment.split("$")[1].split()[0]
                cost_usd = float(cost_str)
            except (IndexError, ValueError):
                pass

    # Get correctness from run feedback if available
    correctness = 0.0
    if hasattr(run, "feedback") and run.feedback:
        for feedback in run.feedback:
            if feedback.key in {
                "supervisor_correctness",
                "agent_correctness",
                "synthesis_correctness",
            }:
                correctness = feedback.score or 0.0
                break

    if cost_usd == 0.0:
        return {
            "key": "cost_per_correct",
            "score": 0.0,
            "comment": "No cost data available",
        }

    # Calculate cost-effectiveness (lower is better)
    # If correctness is 0, cost per correct is infinite (worst case)
    if correctness == 0.0:
        cost_per_correct = float("inf")
        score = 0.0
    else:
        cost_per_correct = cost_usd / correctness
        # Normalize score (assuming $0.10 per correct is worst case)
        max_cost_per_correct = 0.10
        score = max(0.0, 1.0 - (cost_per_correct / max_cost_per_correct))

    return {
        "key": "cost_per_correct",
        "score": score,
        "comment": f"${cost_per_correct:.6f} per correct (correctness={correctness:.2f})",
    }
