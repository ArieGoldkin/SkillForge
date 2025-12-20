#!/usr/bin/env python
r"""Run automated Langfuse experiments for CI/CD pipelines.

Issue #428 Phase 4.2: This script orchestrates running quality experiments
on Langfuse datasets using the ExperimentRunner. Designed for GitHub Actions
but works in any CI/CD environment.

Features:
- Runs experiments on Langfuse datasets
- Configurable experiment parameters via CLI args or env vars
- Outputs JSON results for programmatic parsing
- Includes Git metadata for experiment context
- Graceful error handling with detailed logging

Usage:
    # Run on default golden dataset
    poetry run python scripts/run_langfuse_experiments.py

    # Custom dataset and experiment name
    poetry run python scripts/run_langfuse_experiments.py \
        --dataset my-dataset \
        --experiment v2.0-quality-test \
        --max-parallel 10

    # Output results to file
    poetry run python scripts/run_langfuse_experiments.py \
        --output-file results.json

Environment Variables:
    LANGFUSE_PUBLIC_KEY     - Langfuse API public key (required)
    LANGFUSE_SECRET_KEY     - Langfuse API secret key (required)
    LANGFUSE_HOST           - Langfuse host URL (required)
    EXPERIMENT_DATASET      - Default dataset name
    EXPERIMENT_NAME         - Default experiment name
    EXPERIMENT_MAX_PARALLEL - Default max parallel evaluations
    GIT_COMMIT_SHA          - Git commit SHA for metadata
    GIT_BRANCH              - Git branch name for metadata
    GIT_COMMIT_MESSAGE      - Git commit message for metadata
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
from datetime import UTC, datetime
from pathlib import Path

# Add parent to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv

# Load environment variables before other imports
env_path = Path(__file__).parent.parent / ".env"
if env_path.exists():
    load_dotenv(env_path)

from app.core.langfuse_client import (  # noqa: E402
    LangfuseClient,
    LangfuseClientError,
    get_langfuse_api_client,
)
from app.core.logging import get_logger  # noqa: E402
from app.evaluation.experiment_runner import (  # noqa: E402
    ExperimentRunner,
    ExperimentSummary,
)

# Example evaluator using G-Eval (you can customize this)
from app.shared.services.g_eval.scorer import g_eval_score  # noqa: E402

logger = get_logger(__name__)

DEFAULT_DATASET = "golden-dataset"
DEFAULT_EXPERIMENT_PREFIX = "ci-experiment"
DEFAULT_MAX_PARALLEL = 10


async def quality_evaluator(item: dict) -> dict:
    """Evaluate quality using G-Eval LLM-as-Judge.

    This is the evaluator function passed to ExperimentRunner.
    It processes a single dataset item and returns scores.

    Args:
        item: Dataset item with 'input' and 'expected_output'

    Returns:
        Dict with 'output' and 'scores' keys

    """
    # Extract input and expected output from dataset item
    input_data = item.get("input", {})
    expected_output = item.get("expected_output", {})

    # For quality evaluation, we need the content and agent type
    content = input_data.get("content", "")
    agent_type = input_data.get("agent_type", "tech_comparator")

    # Truncate content to prevent token overflow
    content = content[:8000] if content else ""

    if not content:
        # No content to evaluate - return neutral score
        return {
            "output": {"status": "skipped", "reason": "no_content"},
            "scores": {"overall": 0.5},
        }

    # Run G-Eval scoring
    result = await g_eval_score(
        input_content=content,
        output=expected_output,
        agent_type=agent_type,
        trace_id=None,  # ExperimentRunner will provide trace_id
    )

    # Convert G-Eval result to experiment format
    return {
        "output": {
            "overall": result.overall,
            "confidence": result.confidence,
            "criteria": {
                name: {
                    "score": score.score,
                    "normalized": score.normalized,
                    "reasoning": score.reasoning,
                }
                for name, score in result.criteria_scores.items()
            },
        },
        "scores": {
            "overall": result.overall,
            "confidence": result.confidence,
            **{
                f"criteria_{name}": score.normalized
                for name, score in result.criteria_scores.items()
            },
        },
    }


async def run_experiment(
    client: LangfuseClient,
    dataset_name: str,
    experiment_name: str,
    max_parallel: int,
) -> ExperimentSummary:
    """Run a quality experiment on the specified dataset.

    Args:
        client: Configured LangfuseClient
        dataset_name: Name of the dataset in Langfuse
        experiment_name: Name for this experiment run
        max_parallel: Maximum parallel evaluations

    Returns:
        ExperimentSummary with results

    Raises:
        LangfuseClientError: If experiment fails

    """
    # Collect metadata from environment (CI/CD context)
    metadata = {
        "timestamp": datetime.now(UTC).isoformat(),
        "evaluator": "g_eval_quality",
        "max_parallel": max_parallel,
    }

    # Add Git metadata if available (from CI environment)
    if commit_sha := os.getenv("GIT_COMMIT_SHA"):
        metadata["git_commit"] = commit_sha
    if branch := os.getenv("GIT_BRANCH"):
        metadata["git_branch"] = branch
    if commit_msg := os.getenv("GIT_COMMIT_MESSAGE"):
        metadata["git_commit_message"] = commit_msg[:200]  # Truncate

    runner = ExperimentRunner(client)

    logger.info(
        "Starting experiment",
        dataset=dataset_name,
        experiment=experiment_name,
        max_parallel=max_parallel,
    )

    summary = await runner.run_experiment(
        dataset_name=dataset_name,
        experiment_name=experiment_name,
        evaluator_fn=quality_evaluator,
        max_parallel=max_parallel,
        description=f"Automated quality experiment run at {datetime.now(UTC).isoformat()}",
        metadata=metadata,
    )

    return summary


def print_summary(summary: ExperimentSummary) -> None:
    """Print experiment summary to console.

    Args:
        summary: ExperimentSummary to display

    """
    print("\n" + "=" * 70)
    print("EXPERIMENT RESULTS")
    print("=" * 70)
    print(f"Experiment: {summary.experiment_name}")
    print(f"Dataset: {summary.dataset_name}")
    print(f"Experiment ID: {summary.experiment_id or 'N/A'}")
    print()
    print(f"Total Items: {summary.total_items}")
    print(f"Successful: {summary.successful_runs}")
    print(f"Failed: {summary.failed_runs}")
    print(f"Success Rate: {summary.success_rate:.1%}")
    print()
    print(f"Duration: {summary.total_duration_ms / 1000:.2f}s")
    print(f"Throughput: {summary.items_per_second:.2f} items/sec")
    print()

    if summary.average_scores:
        print("Average Scores:")
        for name, value in summary.average_scores.items():
            print(f"  {name}: {value:.3f}")
    else:
        print("No scores available")

    if summary.errors:
        print()
        print(f"Errors ({len(summary.errors)}):")
        for i, error in enumerate(summary.errors[:5], 1):  # Show first 5
            print(f"  {i}. {error[:100]}...")
        if len(summary.errors) > 5:
            print(f"  ... and {len(summary.errors) - 5} more errors")

    print("=" * 70)


def summary_to_dict(summary: ExperimentSummary) -> dict:
    """Convert ExperimentSummary to JSON-serializable dict.

    Args:
        summary: ExperimentSummary to convert

    Returns:
        Dict with all summary data

    """
    return {
        "experiment_id": summary.experiment_id,
        "dataset_name": summary.dataset_name,
        "experiment_name": summary.experiment_name,
        "total_items": summary.total_items,
        "successful_runs": summary.successful_runs,
        "failed_runs": summary.failed_runs,
        "success_rate": summary.success_rate,
        "average_scores": summary.average_scores,
        "total_duration_ms": summary.total_duration_ms,
        "items_per_second": summary.items_per_second,
        "errors": summary.errors[:10],  # Limit to first 10 errors
        "timestamp": datetime.now(UTC).isoformat(),
    }


async def main() -> int:
    """Main entry point.

    Returns:
        Exit code (0 = success, 1 = failure)

    """
    parser = argparse.ArgumentParser(
        description="Run automated Langfuse experiments",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    parser.add_argument(
        "--dataset",
        type=str,
        default=os.getenv("EXPERIMENT_DATASET", DEFAULT_DATASET),
        help=f"Dataset name in Langfuse (default: {DEFAULT_DATASET})",
    )

    parser.add_argument(
        "--experiment",
        type=str,
        default=os.getenv("EXPERIMENT_NAME", DEFAULT_EXPERIMENT_PREFIX),
        help=f"Experiment name (default: {DEFAULT_EXPERIMENT_PREFIX})",
    )

    parser.add_argument(
        "--max-parallel",
        type=int,
        default=int(os.getenv("EXPERIMENT_MAX_PARALLEL", DEFAULT_MAX_PARALLEL)),
        help=f"Max parallel evaluations (default: {DEFAULT_MAX_PARALLEL})",
    )

    parser.add_argument(
        "--output-file",
        type=str,
        help="Output results to JSON file",
    )

    args = parser.parse_args()

    # Validate Langfuse configuration
    required_env = ["LANGFUSE_PUBLIC_KEY", "LANGFUSE_SECRET_KEY", "LANGFUSE_HOST"]
    missing = [var for var in required_env if not os.getenv(var)]

    if missing:
        logger.error(
            "Missing required environment variables",
            missing=missing,
        )
        print(f"\nERROR: Missing required environment variables: {', '.join(missing)}")
        print("\nRequired:")
        print("  LANGFUSE_PUBLIC_KEY")
        print("  LANGFUSE_SECRET_KEY")
        print("  LANGFUSE_HOST")
        return 1

    try:
        # Get Langfuse client
        client = get_langfuse_api_client()
        if not client:
            logger.error("Failed to initialize Langfuse client")
            print("\nERROR: Failed to initialize Langfuse client")
            print("Check that LANGFUSE_* environment variables are set correctly")
            return 1

        # Run experiment
        summary = await run_experiment(
            client=client,
            dataset_name=args.dataset,
            experiment_name=args.experiment,
            max_parallel=args.max_parallel,
        )

        # Print results to console
        print_summary(summary)

        # Write to file if requested
        if args.output_file:
            output_path = Path(args.output_file)
            results_dict = summary_to_dict(summary)

            output_path.write_text(json.dumps(results_dict, indent=2))
            print(f"\nResults written to: {output_path}")

        # Exit with error if too many failures
        if summary.success_rate < 0.5:
            logger.warning(
                "Experiment success rate below 50%",
                success_rate=summary.success_rate,
            )
            print(f"\nWARNING: Success rate ({summary.success_rate:.1%}) is below 50%")
            return 1

        return 0

    except LangfuseClientError as e:
        logger.exception("Langfuse client error")
        print(f"\nERROR: Langfuse client error: {e}")
        return 1

    except Exception as e:
        logger.exception("Unexpected error during experiment")
        print(f"\nERROR: Unexpected error: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
