"""Example usage of ExperimentRunner for CI/CD automation.

This script demonstrates how to use the ExperimentRunner to run automated
experiments on Langfuse datasets. This is useful for:

1. CI/CD pipelines - Automated testing on golden datasets
2. A/B testing - Compare different model versions
3. Regression testing - Ensure quality doesn't degrade
4. Benchmarking - Measure performance improvements

Issue #428: Part of Langfuse-First Architecture migration.
"""

from __future__ import annotations

import asyncio
from typing import Any

from app.core.langfuse_client import get_langfuse_api_client
from app.core.logging import get_logger
from app.evaluation.experiment_runner import ExperimentRunner

logger = get_logger(__name__)


async def example_quality_evaluator(item: dict[str, Any]) -> dict[str, Any]:
    """Example evaluator that measures output quality.

    In a real implementation, this would:
    1. Extract input from dataset item
    2. Run your model/system on the input
    3. Evaluate the output quality
    4. Return scores and output

    Args:
        item: Dataset item with "input" and optionally "expected_output"

    Returns:
        Dict with "output" and "scores" keys

    """
    # Simulate processing time
    await asyncio.sleep(0.1)

    # In real implementation, you would:
    # input_data = item.get("input", {})
    # expected = item.get("expected_output", {})
    # actual_output = await your_model.generate(input_data)
    # scores = await evaluate_quality(actual_output, expected)

    # For this example, return dummy scores
    return {
        "output": f"Processed: {item.get('id', 'unknown')}",
        "scores": {
            "accuracy": 0.92,
            "relevance": 0.88,
            "completeness": 0.85,
        },
    }


async def run_baseline_experiment() -> None:
    """Run a baseline experiment for demonstration.

    This is a minimal example showing how to:
    1. Get the Langfuse client
    2. Create an ExperimentRunner
    3. Run an experiment on a dataset
    4. Review the results

    """
    logger.info("example_experiment_starting", experiment_type="baseline")

    # Step 1: Get Langfuse client
    client = get_langfuse_api_client()
    if not client:
        logger.error(
            "langfuse_not_configured",
            message="Set LANGFUSE_ENABLED=true and provide API keys",
        )
        return

    # Step 2: Create runner
    runner = ExperimentRunner(client)

    # Step 3: Run experiment
    try:
        summary = await runner.run_experiment(
            dataset_name="golden-dataset",  # Your dataset name in Langfuse
            experiment_name="baseline-v1.0",  # Name for this experiment run
            evaluator_fn=example_quality_evaluator,
            max_parallel=5,  # Process 5 items concurrently
            description="Baseline quality evaluation",
            metadata={
                "version": "1.0",
                "model": "gpt-4o-mini",
                "environment": "development",
            },
        )

        # Step 4: Review results
        logger.info(
            "experiment_summary",
            experiment_id=summary.experiment_id,
            total_items=summary.total_items,
            successful=summary.successful_runs,
            failed=summary.failed_runs,
            success_rate=f"{summary.success_rate:.1%}",
            average_scores=summary.average_scores,
            duration_sec=round(summary.total_duration_ms / 1000, 2),
            throughput=f"{summary.items_per_second:.1f} items/sec",
        )

        # Check if experiment meets quality thresholds
        if summary.success_rate < 0.95:
            logger.warning(
                "quality_threshold_not_met",
                success_rate=summary.success_rate,
                threshold=0.95,
                message="Consider investigating failed items",
            )

        # Check average scores
        avg_accuracy = summary.average_scores.get("accuracy", 0.0)
        if avg_accuracy < 0.9:
            logger.warning(
                "accuracy_threshold_not_met",
                avg_accuracy=avg_accuracy,
                threshold=0.9,
            )

    except Exception:
        logger.exception("experiment_failed")
        raise


async def run_ab_comparison() -> None:
    """Run A/B comparison between two model versions.

    This demonstrates how to run multiple experiments and compare results.

    """
    logger.info("ab_comparison_starting")

    client = get_langfuse_api_client()
    if not client:
        return

    runner = ExperimentRunner(client)

    # Define two evaluators (simulating different model versions)
    async def model_a_evaluator(item: dict[str, Any]) -> dict[str, Any]:
        await asyncio.sleep(0.08)  # Faster but less accurate
        return {
            "output": f"Model A: {item.get('id')}",
            "scores": {"accuracy": 0.85},
        }

    async def model_b_evaluator(item: dict[str, Any]) -> dict[str, Any]:
        await asyncio.sleep(0.12)  # Slower but more accurate
        return {
            "output": f"Model B: {item.get('id')}",
            "scores": {"accuracy": 0.92},
        }

    # Run both experiments
    summary_a = await runner.run_experiment(
        dataset_name="golden-dataset",
        experiment_name="model-a-comparison",
        evaluator_fn=model_a_evaluator,
        metadata={"model": "A", "version": "1.0"},
    )

    summary_b = await runner.run_experiment(
        dataset_name="golden-dataset",
        experiment_name="model-b-comparison",
        evaluator_fn=model_b_evaluator,
        metadata={"model": "B", "version": "2.0"},
    )

    # Compare results
    logger.info(
        "ab_comparison_results",
        model_a_accuracy=summary_a.average_scores.get("accuracy", 0),
        model_a_throughput=summary_a.items_per_second,
        model_b_accuracy=summary_b.average_scores.get("accuracy", 0),
        model_b_throughput=summary_b.items_per_second,
    )


async def main() -> None:
    """Run example experiments."""
    # Run baseline experiment
    await run_baseline_experiment()

    # Uncomment to run A/B comparison
    # await run_ab_comparison()


if __name__ == "__main__":
    # Run with: poetry run python -m app.evaluation.example_experiment
    asyncio.run(main())
