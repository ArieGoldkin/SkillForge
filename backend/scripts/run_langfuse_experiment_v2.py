#!/usr/bin/env python
"""Run Langfuse dataset experiment using CORRECT SDK patterns (v3).

Issue #428: Refactored to use proper Langfuse SDK `run_experiment()` API.

This script implements the recommended Langfuse patterns (Dec 2025):
1. Uses `langfuse.run_experiment()` for automatic iteration and tracing
2. Returns proper `Evaluation` objects from evaluator functions
3. Supports run-level evaluators for aggregate metrics
4. Integrates with G-Eval scoring via Langfuse-compatible adapters

Key improvements over v1/v2:
- No manual `for item in items:` loop - SDK handles iteration
- Evaluators return `Evaluation` objects (not custom classes)
- Run-level aggregation (average scores, pass rates)
- Proper experiment UI integration in Langfuse dashboard
- Structured output via `result.format()`

Usage:
    # Run a quick experiment with 3 examples
    poetry run python scripts/run_langfuse_experiment_v2.py --quick

    # Run full experiment with all examples
    poetry run python scripts/run_langfuse_experiment_v2.py --full

    # Run with specific agent type
    poetry run python scripts/run_langfuse_experiment_v2.py --full --agent-type security_auditor

    # Dry run (show what would happen)
    poetry run python scripts/run_langfuse_experiment_v2.py --dry-run

    # Legacy mode (uses old item.run() pattern for comparison)
    poetry run python scripts/run_langfuse_experiment_v2.py --quick --legacy

Environment:
    LANGFUSE_PUBLIC_KEY, LANGFUSE_SECRET_KEY, LANGFUSE_HOST, LANGFUSE_ENABLED
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

# Add parent to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv

# Load environment variables before other imports
env_path = Path(__file__).parent.parent / ".env"
if env_path.exists():
    load_dotenv(env_path)

from app.core.logging import get_logger  # noqa: E402

logger = get_logger(__name__)

# Issue #428: Use the dataset created by sync_golden_dataset_to_langfuse.py
# which includes full artifact content (not just summaries)
DATASET_NAME = "skillforge_golden_analyses_v1_prod"
EXPERIMENT_NAME_PREFIX = "g_eval_quality"


def check_langfuse_enabled() -> bool:
    """Check if Langfuse is enabled and configured."""
    if os.getenv("LANGFUSE_ENABLED", "false").lower() != "true":
        print("ERROR: LANGFUSE_ENABLED must be 'true' to run experiment")
        return False

    if not os.getenv("LANGFUSE_PUBLIC_KEY") or not os.getenv("LANGFUSE_SECRET_KEY"):
        print("ERROR: LANGFUSE_PUBLIC_KEY and LANGFUSE_SECRET_KEY must be set")
        return False

    return True


def create_task_function(agent_type: str):
    """Create the task function for experiment execution.

    The task function processes a single dataset item and returns output
    for evaluation. In our case, we use the expected_output as the "output"
    since we're evaluating existing artifacts.

    Args:
        agent_type: Agent type for context

    Returns:
        Task function compatible with langfuse.run_experiment()

    """

    def task(*, item, **kwargs) -> dict[str, Any]:
        """Process a single dataset item.

        For golden dataset evaluation, we're evaluating existing artifacts,
        so we return the expected_output (artifact content) as the output.

        Args:
            item: Langfuse ExperimentItem with input/expected_output
            **kwargs: Additional context from Langfuse

        Returns:
            The output to be evaluated

        """
        # For golden dataset: the expected_output contains the artifact content
        # that was already generated - we're evaluating its quality
        expected = item.expected_output if hasattr(item, "expected_output") else {}

        if isinstance(expected, dict):
            return expected
        else:
            return {"content": str(expected)}

    task.__name__ = f"golden_artifact_task_{agent_type}"
    return task


def run_experiment_modern(
    max_examples: int | None = None,
    dry_run: bool = False,
    experiment_name: str | None = None,
    agent_type: str = "tech_comparator",
    quality_threshold: float = 0.6,
) -> dict[str, Any]:
    """Run G-Eval experiment using MODERN Langfuse SDK patterns.

    Uses `langfuse.run_experiment()` API for proper integration with
    Langfuse Experiments UI and automatic score aggregation.

    Args:
        max_examples: Limit number of examples (None = all)
        dry_run: If True, just show what would run
        experiment_name: Custom experiment name
        agent_type: Agent type for G-Eval rubrics
        quality_threshold: Threshold for pass rate calculation

    Returns:
        Dict with experiment results

    """
    if not check_langfuse_enabled():
        return {"status": "error", "message": "Langfuse not enabled"}

    try:
        from langfuse import Langfuse

        from app.shared.services.g_eval import (
            create_g_eval_overall_evaluator,
            get_standard_run_evaluators,
        )

        # Initialize Langfuse client
        langfuse = Langfuse(
            public_key=os.getenv("LANGFUSE_PUBLIC_KEY"),
            secret_key=os.getenv("LANGFUSE_SECRET_KEY"),
            host=os.getenv("LANGFUSE_HOST", "http://localhost:3000"),
        )

        # Fetch dataset
        print(f"\nFetching dataset: {DATASET_NAME}...")
        dataset = langfuse.get_dataset(DATASET_NAME)
        all_items = list(dataset.items)

        # Apply limit if specified
        items_to_evaluate = all_items[:max_examples] if max_examples else all_items

        exp_name = (
            experiment_name or f"{EXPERIMENT_NAME_PREFIX}_v3_{int(datetime.now().timestamp())}"
        )

        print(f"\n{'=' * 70}")
        print("G-EVAL EXPERIMENT (Modern SDK Pattern)")
        print("=" * 70)
        print(f"  Dataset:     {DATASET_NAME}")
        print(f"  Items:       {len(items_to_evaluate)} / {len(all_items)}")
        print(f"  Experiment:  {exp_name}")
        print(f"  Agent Type:  {agent_type}")
        print(f"  Threshold:   {quality_threshold}")
        print("=" * 70)

        if dry_run:
            print(f"\n[DRY RUN] Would evaluate {len(items_to_evaluate)} items")
            print("  Pattern: langfuse.run_experiment() with Evaluation objects")
            print("  Evaluators: g_eval_overall")
            print("  Run Evaluators: avg_score, avg_criteria, pass_rate")
            print("\nSample items:")
            for i, item in enumerate(items_to_evaluate[:3]):
                inp = item.input if hasattr(item, "input") else {}
                print(f"  {i + 1}. {inp.get('title', 'N/A')[:50]}...")
            return {"status": "dry_run", "example_count": len(items_to_evaluate)}

        # Create evaluators using new Langfuse-compatible adapters
        # Issue #428: These return proper Evaluation objects
        overall_evaluator = create_g_eval_overall_evaluator(
            agent_type=agent_type,
            use_cache=True,
        )

        # Run-level evaluators for aggregate metrics
        run_evaluators = get_standard_run_evaluators(quality_threshold)

        print(f"\nRunning experiment with {len(items_to_evaluate)} items...")
        print("  Using langfuse.run_experiment() API")
        print("  Evaluators: g_eval_overall")
        print(f"  Run Evaluators: {len(run_evaluators)} aggregate metrics")

        # Create task function
        task_fn = create_task_function(agent_type)

        # Run experiment using MODERN SDK pattern
        # This is the KEY FIX from Issue #428
        result = langfuse.run_experiment(
            name=exp_name,
            description=f"G-Eval quality evaluation for {agent_type} agent artifacts",
            data=items_to_evaluate,
            task=task_fn,
            evaluators=[overall_evaluator],
            run_evaluators=run_evaluators,
            metadata={
                "agent_type": agent_type,
                "quality_threshold": quality_threshold,
                "dataset_name": DATASET_NAME,
                "sdk_pattern": "run_experiment_v3",
            },
        )

        # Flush to ensure all data is sent
        langfuse.flush()

        # Print results
        print(f"\n{'=' * 70}")
        print("EXPERIMENT COMPLETE")
        print("=" * 70)

        # Try to get formatted results
        try:
            formatted = result.format()
            print(formatted)
        except Exception as format_err:
            logger.warning("result_format_failed", error=str(format_err))
            print(f"  Experiment: {exp_name}")
            print(f"  Items processed: {len(items_to_evaluate)}")

        # Extract aggregate metrics from run evaluations
        run_evals = getattr(result, "run_evaluations", [])
        metrics = {}
        for eval_obj in run_evals:
            if hasattr(eval_obj, "name") and hasattr(eval_obj, "value"):
                metrics[eval_obj.name] = eval_obj.value
                print(
                    f"  {eval_obj.name}: {eval_obj.value:.3f}"
                    if eval_obj.value
                    else f"  {eval_obj.name}: N/A"
                )

        print(f"\n  View in Langfuse: {os.getenv('LANGFUSE_HOST', 'http://localhost:3000')}")
        print(f"  Path: /datasets/{DATASET_NAME}/experiments")

        return {
            "status": "success",
            "experiment_name": exp_name,
            "example_count": len(items_to_evaluate),
            "metrics": metrics,
            "sdk_pattern": "run_experiment_v3",
        }

    except ImportError as e:
        print(f"ERROR: Missing dependency - {e}")
        print("Run: poetry add langfuse")
        return {"status": "error", "message": str(e)}
    except Exception as e:
        logger.exception("experiment_failed")
        print(f"ERROR: {e}")
        return {"status": "error", "message": str(e)}


def run_experiment_legacy(
    max_examples: int | None = None,
    dry_run: bool = False,
    experiment_name: str | None = None,
) -> dict[str, Any]:
    """Run experiment using LEGACY item.run() pattern.

    Preserved for comparison and backward compatibility.
    Use --legacy flag to invoke this mode.

    Args:
        max_examples: Limit number of examples
        dry_run: If True, just show what would run
        experiment_name: Custom experiment name

    Returns:
        Dict with experiment results

    """
    if not check_langfuse_enabled():
        return {"status": "error", "message": "Langfuse not enabled"}

    try:
        from langfuse import Langfuse

        from app.shared.services.g_eval.scorer import g_eval_score

        langfuse = Langfuse(
            public_key=os.getenv("LANGFUSE_PUBLIC_KEY"),
            secret_key=os.getenv("LANGFUSE_SECRET_KEY"),
            host=os.getenv("LANGFUSE_HOST", "http://localhost:3000"),
        )

        print(f"\nFetching dataset: {DATASET_NAME}...")
        lf_dataset = langfuse.get_dataset(DATASET_NAME)
        all_items = list(lf_dataset.items)
        items_to_evaluate = all_items[:max_examples] if max_examples else all_items

        exp_name = (
            experiment_name or f"{EXPERIMENT_NAME_PREFIX}_legacy_{int(datetime.now().timestamp())}"
        )

        print(f"\n{'=' * 70}")
        print("G-EVAL EXPERIMENT (Legacy item.run() Pattern)")
        print("=" * 70)
        print("  WARNING: Using legacy pattern - consider using --modern instead")
        print(f"  Dataset: {DATASET_NAME}")
        print(f"  Items: {len(items_to_evaluate)}")
        print(f"  Experiment: {exp_name}")
        print("=" * 70)

        if dry_run:
            print(f"\n[DRY RUN] Would evaluate {len(items_to_evaluate)} items using legacy pattern")
            return {"status": "dry_run", "example_count": len(items_to_evaluate)}

        import asyncio

        results = []
        total_score = 0.0
        successful = 0

        for i, item in enumerate(items_to_evaluate):
            print(f"\n[{i + 1}/{len(items_to_evaluate)}] Evaluating item: {item.id[:20]}...")

            inputs = item.input if isinstance(item.input, dict) else {}
            expected_output = item.expected_output if item.expected_output else {}
            input_content = inputs.get("content", "")[:8000]
            agent_type = inputs.get("agent_type", "tech_comparator")

            try:
                with item.run(
                    run_name=exp_name,
                    run_metadata={"agent_type": agent_type, "pattern": "legacy"},
                ) as root_span:
                    # Run G-Eval
                    g_eval_result = asyncio.run(
                        g_eval_score(
                            input_content=input_content,
                            output=expected_output,
                            agent_type=agent_type,
                        )
                    )

                    print(f"  Score: {g_eval_result.overall:.2f}")

                    # Score the trace
                    for criterion, score_obj in g_eval_result.criteria_scores.items():
                        root_span.score_trace(
                            name=f"g_eval_{criterion}",
                            value=score_obj.normalized,
                            comment=score_obj.reasoning[:200] if score_obj.reasoning else None,
                        )

                    root_span.score_trace(
                        name="g_eval_overall",
                        value=g_eval_result.overall,
                        comment=f"Legacy pattern - {len(g_eval_result.criteria_scores)} criteria",
                    )

                    total_score += g_eval_result.overall
                    successful += 1
                    results.append(
                        {
                            "item_id": item.id,
                            "overall": g_eval_result.overall,
                        }
                    )

            except Exception as e:
                logger.exception(f"Error evaluating item {item.id}")
                print(f"  ERROR: {e}")
                results.append({"item_id": item.id, "error": str(e)})

        langfuse.flush()

        avg_score = total_score / successful if successful > 0 else 0

        print(f"\n{'=' * 70}")
        print("EXPERIMENT COMPLETE (Legacy)")
        print("=" * 70)
        print(f"  Evaluated: {successful}/{len(items_to_evaluate)}")
        print(f"  Average: {avg_score:.3f}")
        print("\n  NOTE: Run with --modern for better Langfuse integration")

        return {
            "status": "success",
            "experiment_name": exp_name,
            "example_count": len(items_to_evaluate),
            "successful_count": successful,
            "average_score": avg_score,
            "sdk_pattern": "legacy_item_run",
        }

    except Exception as e:
        logger.exception("legacy_experiment_failed")
        return {"status": "error", "message": str(e)}


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Run Langfuse dataset experiment with G-Eval (v3 - proper SDK patterns)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Quick test (3 items, modern pattern)
  poetry run python scripts/run_langfuse_experiment_v2.py --quick

  # Full experiment
  poetry run python scripts/run_langfuse_experiment_v2.py --full

  # With specific agent type
  poetry run python scripts/run_langfuse_experiment_v2.py --full --agent-type security_auditor

  # Legacy pattern (for comparison)
  poetry run python scripts/run_langfuse_experiment_v2.py --quick --legacy

  # Dry run
  poetry run python scripts/run_langfuse_experiment_v2.py --full --dry-run
""",
    )

    parser.add_argument(
        "--quick",
        action="store_true",
        help="Run quick experiment with 3 examples",
    )
    parser.add_argument(
        "--full",
        action="store_true",
        help="Run full experiment with all examples",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would happen without running",
    )
    parser.add_argument(
        "--legacy",
        action="store_true",
        help="Use legacy item.run() pattern instead of run_experiment()",
    )
    parser.add_argument(
        "--max-examples",
        type=int,
        help="Maximum examples to evaluate",
    )
    parser.add_argument(
        "--experiment-name",
        type=str,
        help="Custom experiment name",
    )
    parser.add_argument(
        "--agent-type",
        type=str,
        default="tech_comparator",
        help="Agent type for G-Eval rubrics (default: tech_comparator)",
    )
    parser.add_argument(
        "--quality-threshold",
        type=float,
        default=0.6,
        help="Quality threshold for pass rate (default: 0.6)",
    )

    args = parser.parse_args()

    # Determine max examples
    if args.quick:
        max_examples = args.max_examples or 3
    elif args.full:
        max_examples = args.max_examples  # None means all
    else:
        # Default: show help
        parser.print_help()
        print("\n" + "=" * 70)
        print("TIP: Use --quick for a fast test or --full for complete evaluation")
        print("=" * 70)
        return

    # Run experiment
    if args.legacy:
        result = run_experiment_legacy(
            max_examples=max_examples,
            dry_run=args.dry_run,
            experiment_name=args.experiment_name,
        )
    else:
        result = run_experiment_modern(
            max_examples=max_examples,
            dry_run=args.dry_run,
            experiment_name=args.experiment_name,
            agent_type=args.agent_type,
            quality_threshold=args.quality_threshold,
        )

    # Print final status
    print(f"\nResult: {result['status']}")
    if result["status"] == "success":
        print(f"  SDK Pattern: {result.get('sdk_pattern', 'unknown')}")
        if "metrics" in result:
            print(f"  Metrics: {json.dumps(result['metrics'], indent=4, default=str)}")


if __name__ == "__main__":
    main()
