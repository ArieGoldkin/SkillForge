"""CLI script for running LLM benchmark experiments.

This script provides a command-line interface for running A/B experiments
across different LLM models and generating recommendations.

Usage:
    # Run all experiments
    python -m app.evaluation.run_experiments --all

    # Run specific task type
    python -m app.evaluation.run_experiments --task supervisor

    # Compare specific models
    python -m app.evaluation.run_experiments --task agent --models gpt-4o-mini,gemini-2.5-flash

    # Dry run (validate setup without API calls)
    python -m app.evaluation.run_experiments --dry-run
"""

from __future__ import annotations

import argparse
import asyncio
import json
from datetime import datetime
from pathlib import Path
from typing import Any

from app.core.logging import get_logger
from app.core.model_registry import MODEL_REGISTRY
from app.evaluation import LLMBenchmark
from app.evaluation.datasets import list_datasets, load_dataset

logger = get_logger(__name__)

# Default models to test for each task
# Multi-provider support: supervisor_route now accepts model_id parameter
# for runtime model switching across OpenAI, Anthropic, Google, and xAI
DEFAULT_MODELS = {
    "supervisor": ["gpt-4o-mini", "gpt-4o", "gemini-2.5-flash", "claude-haiku-3-5-20241022"],
    "agent": [
        "gpt-4o-mini",
        "gpt-4o",
    ],  # Agent analysis still uses env var (TODO: add model_id support)
    "synthesis": [
        "gpt-4o-mini",
        "gpt-4o",
    ],  # Synthesis still uses env var (TODO: add model_id support)
}

# Dataset mappings
TASK_DATASETS = {
    "supervisor": "supervisor_golden_v1",
    "agent": "agent_analysis_golden_v1",
    "synthesis": "synthesis_golden_v1",
}


async def run_task_experiments(
    benchmark: LLMBenchmark,
    task_type: str,
    model_ids: list[str] | None = None,
    dry_run: bool = False,
    local_mode: bool = True,
) -> dict[str, Any]:
    """Run experiments for a specific task type.

    Args:
        benchmark: LLMBenchmark instance
        task_type: Type of task (supervisor, agent, synthesis)
        model_ids: Optional list of models to test (uses defaults if None)
        dry_run: If True, validate setup without making API calls

    Returns:
        Dictionary with experiment results and recommendations

    """
    models = model_ids or DEFAULT_MODELS.get(task_type, [])
    dataset_name = TASK_DATASETS.get(task_type)

    if not dataset_name:
        raise ValueError(f"No dataset configured for task type: {task_type}")

    logger.info(
        "experiment_batch_starting",
        task_type=task_type,
        models=models,
        dataset=dataset_name,
    )

    if dry_run:
        # Validate configuration without making API calls
        dataset = load_dataset(dataset_name)
        print(f"\n[DRY RUN] Task: {task_type}")
        print(f"  Dataset: {dataset_name} ({len(dataset)} examples)")
        print(f"  Models to test: {models}")
        print("  Evaluators: correctness, latency, cost")

        # Validate all models exist in registry
        for model_id in models:
            if model_id not in MODEL_REGISTRY:
                print(f"  WARNING: Model '{model_id}' not in registry!")
            else:
                info = MODEL_REGISTRY[model_id]
                print(
                    f"  {model_id}: ${info.input_cost_per_1m}/1M input, ${info.output_cost_per_1m}/1M output"
                )

        return {
            "task_type": task_type,
            "status": "dry_run",
            "models": models,
            "dataset_size": len(dataset),
        }

    # Run comparison
    try:
        comparison = await benchmark.compare_models(
            task_type=task_type,
            model_ids=models,
            dataset_name=dataset_name,
        )

        return {
            "task_type": task_type,
            "status": "completed",
            "winner_by_metric": comparison.winner_by_metric,
            "recommendation": comparison.recommendation,
            "cost_savings": comparison.cost_savings,
            "experiments": [
                {
                    "model_id": exp.model_id,
                    "metrics": exp.metrics,
                    "run_count": exp.run_count,
                }
                for exp in comparison.experiments
            ],
        }

    except Exception as e:
        logger.error("experiment_batch_failed", task_type=task_type, error=str(e))
        return {
            "task_type": task_type,
            "status": "failed",
            "error": str(e),
        }


async def run_all_experiments(
    dry_run: bool = False,
    output_path: str | None = None,
    local_mode: bool = True,
) -> dict[str, Any]:
    """Run experiments for all task types.

    Args:
        dry_run: If True, validate setup without making API calls
        output_path: Optional path to save results JSON
        local_mode: If True, run locally without LangSmith dataset sync

    Returns:
        Dictionary with all results and recommendations

    """
    benchmark = LLMBenchmark(project_name="skillforge-eval", local_mode=local_mode)

    results = {
        "timestamp": datetime.now().isoformat(),
        "mode": "dry_run" if dry_run else "live",
        "tasks": {},
        "recommendations": {},
    }

    # Run experiments for each task type
    for task_type in ["supervisor", "agent", "synthesis"]:
        print(f"\n{'=' * 60}")
        print(f"Running experiments for: {task_type.upper()}")
        print("=" * 60)

        task_results = await run_task_experiments(
            benchmark=benchmark,
            task_type=task_type,
            dry_run=dry_run,
        )

        results["tasks"][task_type] = task_results

        if task_results.get("status") == "completed":
            results["recommendations"][task_type] = task_results.get("recommendation")

    # Generate summary
    if not dry_run:
        print("\n" + "=" * 60)
        print("EXPERIMENT SUMMARY")
        print("=" * 60)

        for task_type, task_results in results["tasks"].items():
            if task_results.get("status") == "completed":
                print(f"\n{task_type.upper()}:")
                print(f"  Recommendation: {task_results.get('recommendation')}")
                print("  Winners by metric:")
                for metric, winner in task_results.get("winner_by_metric", {}).items():
                    print(f"    - {metric}: {winner}")
            else:
                print(f"\n{task_type.upper()}: {task_results.get('status')}")

    # Save results if output path provided
    if output_path:
        output_file = Path(output_path)
        output_file.parent.mkdir(parents=True, exist_ok=True)
        with open(output_file, "w") as f:
            json.dump(results, f, indent=2, default=str)
        print(f"\nResults saved to: {output_path}")

    return results


def generate_model_config(results: dict[str, Any]) -> dict[str, str]:
    """Generate model configuration from experiment results.

    Args:
        results: Experiment results dictionary

    Returns:
        Dictionary mapping task type to recommended model

    """
    config = {}

    for task_type, task_results in results.get("tasks", {}).items():
        if task_results.get("status") == "completed":
            # Get winner by accuracy metric (or first available winner)
            winners = task_results.get("winner_by_metric", {})
            accuracy_winner = winners.get("accuracy")
            correctness_winner = (
                winners.get("supervisor_correctness")
                or winners.get("agent_correctness")
                or winners.get("synthesis_correctness")
            )

            # Prefer correctness metric, then accuracy, then first winner
            recommended_model = (
                correctness_winner or accuracy_winner or next(iter(winners.values()), None)
            )

            if recommended_model:
                config[task_type] = recommended_model

    return config


async def main():
    """Main entry point for CLI."""
    parser = argparse.ArgumentParser(
        description="Run LLM benchmark experiments for SkillForge",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python -m app.evaluation.run_experiments --all
  python -m app.evaluation.run_experiments --task supervisor
  python -m app.evaluation.run_experiments --task agent --models gpt-4o-mini,gemini-2.5-flash
  python -m app.evaluation.run_experiments --dry-run
        """,
    )

    parser.add_argument(
        "--all",
        action="store_true",
        help="Run experiments for all task types",
    )
    parser.add_argument(
        "--task",
        choices=["supervisor", "agent", "synthesis"],
        help="Run experiments for specific task type",
    )
    parser.add_argument(
        "--models",
        type=str,
        help="Comma-separated list of model IDs to test",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Validate setup without making API calls",
    )
    parser.add_argument(
        "--local",
        action="store_true",
        default=True,
        help="Run locally without LangSmith dataset sync (default: True)",
    )
    parser.add_argument(
        "--langsmith",
        action="store_true",
        help="Use LangSmith for dataset sync and evaluation (requires write permissions)",
    )
    parser.add_argument(
        "--output",
        type=str,
        help="Path to save results JSON",
    )
    parser.add_argument(
        "--list-models",
        action="store_true",
        help="List available models and exit",
    )
    parser.add_argument(
        "--list-datasets",
        action="store_true",
        help="List available datasets and exit",
    )

    args = parser.parse_args()

    # Handle list commands
    if args.list_models:
        print("Available models:")
        for name, info in sorted(MODEL_REGISTRY.items()):
            print(
                f"  {name}: {info.display_name} (${info.input_cost_per_1m}/1M in, ${info.output_cost_per_1m}/1M out)"
            )
        return

    if args.list_datasets:
        print("Available datasets:")
        for dataset_name in list_datasets():
            dataset = load_dataset(dataset_name)
            print(f"  {dataset_name}: {len(dataset)} examples")
        return

    # Determine local mode
    local_mode = not args.langsmith

    # Run experiments
    if args.all:
        results = await run_all_experiments(
            dry_run=args.dry_run,
            output_path=args.output,
            local_mode=local_mode,
        )

        if not args.dry_run and results.get("recommendations"):
            print("\n" + "=" * 60)
            print("GENERATED MODEL CONFIG")
            print("=" * 60)
            config = generate_model_config(results)
            print(json.dumps(config, indent=2))

    elif args.task:
        benchmark = LLMBenchmark(project_name="skillforge-eval", local_mode=local_mode)
        models = args.models.split(",") if args.models else None

        results = await run_task_experiments(
            benchmark=benchmark,
            task_type=args.task,
            model_ids=models,
            dry_run=args.dry_run,
            local_mode=local_mode,
        )

        print("\nResults:")
        print(json.dumps(results, indent=2, default=str))

    else:
        parser.print_help()


if __name__ == "__main__":
    asyncio.run(main())
