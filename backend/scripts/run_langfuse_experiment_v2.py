#!/usr/bin/env python
"""Run Langfuse dataset experiment using CORRECT SDK patterns.

This script uses the proper Langfuse SDK patterns for dataset experiments:
1. Fetch dataset with langfuse.get_dataset()
2. Use item.run() context manager to create proper traces
3. Link scores to dataset items properly
4. Use G-Eval scoring from app.shared.services.g_eval.scorer

Key improvements over v1:
- Uses item.run() context manager for proper trace linking
- No random trace IDs - traces are automatically linked to dataset items
- Uses real Langfuse SDK methods, not fabricated API endpoints
- Scores appear under Datasets > Runs in Langfuse UI

Usage:
    # Create dataset only (no experiment)
    poetry run python scripts/run_langfuse_experiment_v2.py --create-dataset

    # Run a quick experiment with 3 examples
    poetry run python scripts/run_langfuse_experiment_v2.py --quick

    # Run full experiment
    poetry run python scripts/run_langfuse_experiment_v2.py --full

    # Dry run (show what would happen)
    poetry run python scripts/run_langfuse_experiment_v2.py --dry-run

Environment:
    LANGFUSE_PUBLIC_KEY, LANGFUSE_SECRET_KEY, LANGFUSE_HOST, LANGFUSE_ENABLED
"""

from __future__ import annotations

import argparse
import asyncio
import json
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

from app.core.logging import get_logger  # noqa: E402
from app.evaluation.datasets import load_dataset  # noqa: E402
from app.shared.services.g_eval.scorer import g_eval_score  # noqa: E402

logger = get_logger(__name__)

DATASET_NAME = "skillforge-golden-analysis"
EXPERIMENT_NAME_PREFIX = "g_eval_quality"


async def create_langfuse_dataset(dry_run: bool = False) -> dict:
    """Create or update a Langfuse dataset from golden data.

    Uses the correct SDK pattern:
    - langfuse.create_dataset() to create dataset
    - langfuse.create_dataset_item() to add items

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

    try:
        import os

        from langfuse import Langfuse

        # Create Langfuse client using SDK
        langfuse = Langfuse(
            public_key=os.getenv("LANGFUSE_PUBLIC_KEY"),
            secret_key=os.getenv("LANGFUSE_SECRET_KEY"),
            host=os.getenv("LANGFUSE_HOST", "http://localhost:3000"),
        )

        print(f"\nCreating/updating Langfuse dataset: {DATASET_NAME}")

        # Create dataset (idempotent - won't fail if exists)
        langfuse.create_dataset(
            name=DATASET_NAME,
            description="SkillForge golden dataset for agent analysis quality evaluation",
            metadata={
                "source": "golden/agent_analysis",
                "created_at": datetime.now().isoformat(),
                "version": "2.0",
            },
        )
        print(f"  Dataset created/found: {DATASET_NAME}")

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
            if items_created <= 3 or items_created % 10 == 0:
                print(f"  Added item {items_created}: {example_id[:40]}...")

        # Flush to ensure items are sent
        langfuse.flush()

        print(f"\n  Total items created: {items_created}")

        return {
            "status": "success",
            "dataset_name": DATASET_NAME,
            "items_created": items_created,
        }

    except ImportError:
        print("ERROR: Langfuse package not installed. Run: poetry add langfuse")
        return {"status": "error", "message": "Langfuse not installed"}
    except Exception as e:
        logger.exception("Failed to create Langfuse dataset")
        return {"status": "error", "message": str(e)}


async def run_experiment(
    max_examples: int | None = None,
    dry_run: bool = False,
    experiment_name: str | None = None,
) -> dict:
    """Run G-Eval experiment using CORRECT Langfuse SDK patterns.

    Uses item.run() context manager to properly link traces to dataset items.
    This is the recommended pattern from Langfuse documentation.

    Args:
        max_examples: Limit number of examples (None = all)
        dry_run: If True, just show what would run
        experiment_name: Custom experiment name (default: g_eval_quality_v{timestamp})

    Returns:
        Dict with experiment results

    """
    import os

    # Check if Langfuse is enabled
    if os.getenv("LANGFUSE_ENABLED", "false").lower() != "true":
        print("ERROR: LANGFUSE_ENABLED must be 'true' to run experiment")
        return {"status": "error", "message": "Langfuse not enabled"}

    try:
        from langfuse import Langfuse

        # Create Langfuse client
        langfuse = Langfuse(
            public_key=os.getenv("LANGFUSE_PUBLIC_KEY"),
            secret_key=os.getenv("LANGFUSE_SECRET_KEY"),
            host=os.getenv("LANGFUSE_HOST", "http://localhost:3000"),
        )

        # Fetch dataset from Langfuse
        print(f"\nFetching dataset: {DATASET_NAME}...")
        lf_dataset = langfuse.get_dataset(DATASET_NAME)

        # Get all items
        all_items = list(lf_dataset.items)
        items_to_evaluate = all_items[:max_examples] if max_examples else all_items

        print(f"\n{'=' * 60}")
        print(f"G-EVAL EXPERIMENT: {len(items_to_evaluate)} examples")
        print(f"Dataset: {DATASET_NAME}")
        print(
            f"Experiment: {experiment_name or f'{EXPERIMENT_NAME_PREFIX}_v{int(datetime.now().timestamp())}'}"
        )
        print("=" * 60)

        if dry_run:
            print(f"\n[DRY RUN] Would evaluate {len(items_to_evaluate)} examples")
            print("  Criteria: completeness, accuracy, coherence, depth")
            print("  Scoring: G-Eval LLM-as-Judge")
            print("  Results: Linked to dataset items via item.run()")
            print("\nExample items:")
            for i, item in enumerate(items_to_evaluate[:3]):
                print(f"  {i + 1}. ID: {item.id}")
                print(f"     Agent: {item.input.get('agent_type', 'unknown')}")
            return {"status": "dry_run", "example_count": len(items_to_evaluate)}

        # Run experiment with item.run() context manager
        exp_name = experiment_name or f"{EXPERIMENT_NAME_PREFIX}_v{int(datetime.now().timestamp())}"
        results = []
        total_score = 0.0
        successful_count = 0

        for i, item in enumerate(items_to_evaluate):
            print(f"\n[{i + 1}/{len(items_to_evaluate)}] Evaluating item: {item.id}")

            # Extract inputs
            inputs = item.input if isinstance(item.input, dict) else {}
            expected_output = item.expected_output if item.expected_output else {}
            input_content = inputs.get("content", "")[:8000]
            agent_type = inputs.get("agent_type", "tech_comparator")

            print(f"  Agent type: {agent_type}")
            print(f"  Input length: {len(input_content)} chars")

            try:
                # Use item.run() context manager to create proper trace
                # This is the CORRECT pattern from Langfuse docs (Dec 2025)
                # Returns root_span for trace-level operations
                with item.run(
                    run_name=exp_name,
                    run_metadata={"agent_type": agent_type},
                ) as root_span:
                    # Run G-Eval scoring
                    g_eval_result = await g_eval_score(
                        input_content=input_content,
                        output=expected_output,
                        agent_type=agent_type,
                        trace_id=None,  # Will use current trace from context
                    )

                    print(f"  Overall score: {g_eval_result.overall:.2f}")
                    print(f"  Confidence: {g_eval_result.confidence:.2f}")

                    # Log individual criteria scores
                    for criterion, score_obj in g_eval_result.criteria_scores.items():
                        print(
                            f"    - {criterion}: {score_obj.score}/5 ({score_obj.normalized:.2f})"
                        )

                    # Use score_trace() to score the TRACE (appears in dataset runs)
                    # This is different from score() which only scores the observation
                    for criterion, score_obj in g_eval_result.criteria_scores.items():
                        root_span.score_trace(
                            name=f"g_eval_{criterion}",
                            value=score_obj.normalized,
                            comment=score_obj.reasoning[:200] if score_obj.reasoning else None,
                        )

                    # Overall score on the trace
                    root_span.score_trace(
                        name="g_eval_overall",
                        value=g_eval_result.overall,
                        comment=f"Weighted average across {len(g_eval_result.criteria_scores)} criteria",
                    )

                    total_score += g_eval_result.overall
                    successful_count += 1

                    results.append(
                        {
                            "item_id": item.id,
                            "agent_type": agent_type,
                            "overall": g_eval_result.overall,
                            "confidence": g_eval_result.confidence,
                            "criteria": {
                                k: {"score": v.score, "normalized": v.normalized}
                                for k, v in g_eval_result.criteria_scores.items()
                            },
                        }
                    )

            except Exception as e:
                logger.exception(f"Error evaluating item {item.id}")
                print(f"  ERROR: {e}")
                results.append(
                    {
                        "item_id": item.id,
                        "error": str(e),
                    }
                )

        # Summary
        print(f"\n{'=' * 60}")
        print("EXPERIMENT SUMMARY")
        print("=" * 60)

        if successful_count > 0:
            avg_score = total_score / successful_count
            successful_results = [r for r in results if "overall" in r]
            print(f"  Evaluated: {successful_count}/{len(items_to_evaluate)} examples")
            print(f"  Average overall score: {avg_score:.2f}")
            print(
                f"  Score range: {min(r['overall'] for r in successful_results):.2f} - "
                f"{max(r['overall'] for r in successful_results):.2f}"
            )
        else:
            avg_score = 0
            print("  No successful evaluations")

        # Flush Langfuse to send all data
        print("\n  Flushing results to Langfuse...")
        langfuse.flush()
        print("  ✓ Results sent to Langfuse")

        print("\n  View results in Langfuse UI:")
        print(f"  {os.getenv('LANGFUSE_HOST', 'http://localhost:3000')}/datasets/{DATASET_NAME}")

        return {
            "status": "success",
            "experiment_name": exp_name,
            "example_count": len(items_to_evaluate),
            "successful_count": successful_count,
            "average_score": avg_score,
            "results": results,
        }

    except ImportError:
        print("ERROR: Langfuse package not installed. Run: poetry add langfuse")
        return {"status": "error", "message": "Langfuse not installed"}
    except Exception as e:
        logger.exception("Experiment failed")
        return {"status": "error", "message": str(e)}


async def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Run Langfuse dataset experiment with G-Eval (v2 - correct SDK patterns)",
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
    parser.add_argument(
        "--experiment-name",
        type=str,
        help="Custom experiment name (default: g_eval_quality_v{timestamp})",
    )

    args = parser.parse_args()

    if args.create_dataset:
        result = await create_langfuse_dataset(dry_run=args.dry_run)
        print(f"\nResult: {json.dumps(result, indent=2)}")

    elif args.quick:
        result = await run_experiment(
            max_examples=3,
            dry_run=args.dry_run,
            experiment_name=args.experiment_name,
        )
        print(f"\nResult: {result['status']}")
        if result["status"] == "success":
            print(f"  Experiment: {result['experiment_name']}")
            print(f"  Success rate: {result['successful_count']}/{result['example_count']}")
            print(f"  Average score: {result['average_score']:.2f}")

    elif args.full:
        result = await run_experiment(
            max_examples=args.max_examples,
            dry_run=args.dry_run,
            experiment_name=args.experiment_name,
        )
        print(f"\nResult: {result['status']}")
        if result["status"] == "success":
            print(f"  Experiment: {result['experiment_name']}")
            print(f"  Success rate: {result['successful_count']}/{result['example_count']}")
            print(f"  Average score: {result['average_score']:.2f}")

    else:
        parser.print_help()
        print("\nExamples:")
        print("  poetry run python scripts/run_langfuse_experiment_v2.py --create-dataset")
        print("  poetry run python scripts/run_langfuse_experiment_v2.py --quick")
        print("  poetry run python scripts/run_langfuse_experiment_v2.py --full --max-examples 5")
        print(
            "  poetry run python scripts/run_langfuse_experiment_v2.py --full --experiment-name 'my-test'"
        )


if __name__ == "__main__":
    asyncio.run(main())
