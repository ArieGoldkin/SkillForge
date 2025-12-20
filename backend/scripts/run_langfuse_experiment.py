#!/usr/bin/env python
"""Run a Langfuse dataset experiment with G-Eval scoring.

This script:
1. Creates/updates a Langfuse dataset from golden data
2. Runs an experiment with G-Eval LLM-as-Judge scoring
3. Submits results to Langfuse for visualization

Issue #418: Part of Langfuse Phase 2 integration.

Usage:
    # Create dataset only (no experiment)
    poetry run python scripts/run_langfuse_experiment.py --create-dataset

    # Run a quick experiment with 3 examples
    poetry run python scripts/run_langfuse_experiment.py --quick

    # Run full experiment
    poetry run python scripts/run_langfuse_experiment.py --full

    # Dry run (show what would happen)
    poetry run python scripts/run_langfuse_experiment.py --dry-run

Environment:
    LANGFUSE_PUBLIC_KEY, LANGFUSE_SECRET_KEY, LANGFUSE_HOST
"""

from __future__ import annotations

import argparse
import asyncio
import sys
from datetime import datetime
from pathlib import Path

# Add parent to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv

# Load environment variables before other imports
env_path = Path(__file__).parent.parent / ".env"
if env_path.exists():
    load_dotenv(env_path)

from app.core.langfuse_config import get_langfuse_client  # noqa: E402
from app.core.logging import get_logger  # noqa: E402
from app.evaluation.datasets import load_dataset  # noqa: E402
from app.shared.services.g_eval.scorer import g_eval_score  # noqa: E402

logger = get_logger(__name__)

DATASET_NAME = "skillforge-golden-analysis"
EXPERIMENT_PREFIX = "g_eval_quality_v1"


async def create_langfuse_dataset(dry_run: bool = False) -> dict:
    """Create or update a Langfuse dataset from golden data.

    Args:
        dry_run: If True, just show what would be created

    Returns:
        Dict with creation results

    """
    # Load golden dataset
    dataset = load_dataset("golden/agent_analysis")

    if dry_run:
        print(f"\n[DRY RUN] Would create Langfuse dataset '{DATASET_NAME}'")
        print(f"  Examples: {len(dataset)}")
        for i, example in enumerate(dataset[:3]):
            print(f"  Example {i + 1}: {example.get('id', 'N/A')[:40]}...")
        return {"status": "dry_run", "example_count": len(dataset)}

    langfuse = get_langfuse_client()
    if not langfuse:
        print("ERROR: Langfuse client not available. Check LANGFUSE_* env vars.")
        return {"status": "error", "message": "Langfuse client not initialized"}

    # Create or get existing dataset
    print(f"\nCreating/updating Langfuse dataset: {DATASET_NAME}")

    try:
        lf_dataset = langfuse.create_dataset(
            name=DATASET_NAME,
            description="SkillForge golden dataset for agent analysis quality evaluation",
            metadata={
                "source": "golden/agent_analysis",
                "created_at": datetime.now().isoformat(),
                "version": "1.0",
            },
        )
        print(f"  Dataset created/found: {lf_dataset.name}")

        # Add items from golden dataset
        items_created = 0
        for example in dataset:
            example_id = example.get("id", f"example_{items_created}")
            inputs = example.get("inputs", {})
            expected_output = example.get("outputs", {})

            langfuse.create_dataset_item(
                dataset_name=DATASET_NAME,
                input=inputs,
                expected_output=expected_output,
                metadata={
                    "original_id": example_id,
                    "agent_type": inputs.get("agent_type", "unknown"),
                },
            )
            items_created += 1
            print(f"  Added item {items_created}: {example_id[:40]}...")

        print(f"\n  Total items created: {items_created}")

        return {
            "status": "success",
            "dataset_name": DATASET_NAME,
            "items_created": items_created,
        }

    except Exception as e:
        logger.exception("Failed to create Langfuse dataset")
        return {"status": "error", "message": str(e)}


async def run_experiment(
    max_examples: int | None = None,
    dry_run: bool = False,
) -> dict:
    """Run G-Eval experiment on golden dataset with Langfuse tracking.

    G-Eval scores are automatically submitted to Langfuse via
    _submit_g_eval_scores_to_langfuse() inside g_eval_score().

    Args:
        max_examples: Limit number of examples (None = all)
        dry_run: If True, just show what would run

    Returns:
        Dict with experiment results

    """
    import uuid

    # Load golden dataset
    dataset = load_dataset("golden/agent_analysis")
    if max_examples:
        dataset = dataset[:max_examples]

    print(f"\n{'=' * 60}")
    print(f"G-EVAL EXPERIMENT: {len(dataset)} examples")
    print("=" * 60)

    if dry_run:
        print(f"\n[DRY RUN] Would evaluate {len(dataset)} examples")
        print("  Criteria: completeness, accuracy, coherence, depth")
        print("  Scoring: G-Eval LLM-as-Judge")
        print("  Results: Auto-submitted to Langfuse")
        return {"status": "dry_run", "example_count": len(dataset)}

    langfuse = get_langfuse_client()
    if not langfuse:
        print("WARNING: Langfuse client not available. Scores won't be tracked.")
    else:
        print("Langfuse client connected - scores will be tracked")

    results = []
    total_score = 0.0

    for i, example in enumerate(dataset):
        example_id = example.get("id", f"example_{i}")
        inputs = example.get("inputs", {})
        expected_output = example.get("outputs", {})

        # Extract content for evaluation
        input_content = inputs.get("content", "")[:8000]
        agent_type = inputs.get("agent_type", "tech_comparator")

        print(f"\n[{i + 1}/{len(dataset)}] Evaluating: {example_id[:40]}...")
        print(f"  Agent type: {agent_type}")
        print(f"  Input length: {len(input_content)} chars")

        try:
            # Generate a trace ID for this evaluation
            # G-Eval will auto-submit scores to Langfuse with this trace_id
            trace_id = str(uuid.uuid4())

            # Run G-Eval scoring (auto-submits to Langfuse)
            g_eval_result = await g_eval_score(
                input_content=input_content,
                output=expected_output,
                agent_type=agent_type,
                trace_id=trace_id,
            )

            print(f"  Overall score: {g_eval_result.overall:.2f}")
            print(f"  Confidence: {g_eval_result.confidence:.2f}")

            # Log individual criteria scores
            for criterion, score_obj in g_eval_result.criteria_scores.items():
                print(f"    - {criterion}: {score_obj.score}/5 ({score_obj.normalized:.2f})")

            total_score += g_eval_result.overall

            results.append(
                {
                    "example_id": example_id,
                    "agent_type": agent_type,
                    "overall": g_eval_result.overall,
                    "confidence": g_eval_result.confidence,
                    "trace_id": trace_id,
                    "criteria": {
                        k: {"score": v.score, "normalized": v.normalized}
                        for k, v in g_eval_result.criteria_scores.items()
                    },
                }
            )

        except Exception as e:
            logger.exception(f"Error evaluating example {example_id}")
            results.append(
                {
                    "example_id": example_id,
                    "error": str(e),
                }
            )

    # Summary
    print(f"\n{'=' * 60}")
    print("EXPERIMENT SUMMARY")
    print("=" * 60)

    successful = [r for r in results if "overall" in r]
    if successful:
        avg_score = total_score / len(successful)
        print(f"  Evaluated: {len(successful)}/{len(dataset)} examples")
        print(f"  Average overall score: {avg_score:.2f}")
        print(
            f"  Score range: {min(r['overall'] for r in successful):.2f} - {max(r['overall'] for r in successful):.2f}"
        )
    else:
        print("  No successful evaluations")

    # Flush Langfuse
    if langfuse:
        langfuse.flush()
        print("\n  Results flushed to Langfuse")

    return {
        "status": "success",
        "example_count": len(dataset),
        "successful_count": len(successful),
        "average_score": avg_score if successful else 0,
        "results": results,
    }


async def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Run Langfuse dataset experiment with G-Eval",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    parser.add_argument(
        "--create-dataset",
        action="store_true",
        help="Create Langfuse dataset from golden data (no experiment)",
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
        "--max-examples",
        type=int,
        help="Maximum examples to evaluate",
    )

    args = parser.parse_args()

    if args.create_dataset:
        result = await create_langfuse_dataset(dry_run=args.dry_run)
        print(f"\nResult: {result}")

    elif args.quick:
        result = await run_experiment(
            max_examples=3,
            dry_run=args.dry_run,
        )
        print(f"\nResult: {result['status']}")

    elif args.full:
        result = await run_experiment(
            max_examples=args.max_examples,
            dry_run=args.dry_run,
        )
        print(f"\nResult: {result['status']}")

    else:
        parser.print_help()
        print("\nExamples:")
        print("  poetry run python scripts/run_langfuse_experiment.py --create-dataset")
        print("  poetry run python scripts/run_langfuse_experiment.py --quick")
        print("  poetry run python scripts/run_langfuse_experiment.py --full --max-examples 5")


if __name__ == "__main__":
    asyncio.run(main())
