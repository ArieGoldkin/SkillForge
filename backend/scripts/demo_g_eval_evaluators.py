#!/usr/bin/env python
"""Demonstrate G-Eval LLM-as-a-Judge evaluators for Langfuse.

This script shows how to use the G-Eval evaluators with Langfuse experiments.
It demonstrates both item-level and run-level evaluators.

Usage:
    # Dry run (show evaluator configuration)
    poetry run python scripts/demo_g_eval_evaluators.py --dry-run

    # Run a quick test with 3 examples
    poetry run python scripts/demo_g_eval_evaluators.py --quick

    # Run full evaluation
    poetry run python scripts/demo_g_eval_evaluators.py --full

Environment:
    LANGFUSE_ENABLED=true
    LANGFUSE_PUBLIC_KEY=<your-key>
    LANGFUSE_SECRET_KEY=<your-key>
    LANGFUSE_HOST=http://localhost:3000
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from dotenv import load_dotenv

# Load environment variables
env_path = Path(__file__).parent.parent / ".env"
if env_path.exists():
    load_dotenv(env_path)

# Add app to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.core.logging import get_logger
from app.shared.services.g_eval import (
    get_standard_evaluators,
    get_standard_run_evaluators,
)

logger = get_logger(__name__)


def show_evaluator_info(agent_type: str = "tech_comparator") -> None:
    """Show information about configured evaluators."""
    print("=" * 70)
    print("G-Eval LLM-as-a-Judge Evaluators for Langfuse")
    print("=" * 70)
    print()

    print(f"Agent Type: {agent_type}")
    print()

    print("ITEM-LEVEL EVALUATORS (score individual artifacts)")
    print("-" * 70)

    # Get standard evaluators for this agent
    evaluators = get_standard_evaluators(agent_type)

    print(f"Total evaluators: {len(evaluators)}")
    print()

    for i, evaluator in enumerate(evaluators, 1):
        name = getattr(evaluator, "__name__", "unknown")
        doc = getattr(evaluator, "__doc__", "No description")
        print(f"{i}. {name}")
        if doc:
            print(f"   {doc.strip()}")
        print()

    print()
    print("RUN-LEVEL EVALUATORS (aggregate metrics across all items)")
    print("-" * 70)

    # Get standard run-level evaluators
    run_evaluators = get_standard_run_evaluators(quality_threshold=0.6, agent_type=agent_type)

    print(f"Total run evaluators: {len(run_evaluators)}")
    print()

    for i, evaluator in enumerate(run_evaluators, 1):
        name = getattr(evaluator, "__name__", "unknown")
        doc = getattr(evaluator, "__doc__", "No description")
        print(f"{i}. {name}")
        if doc:
            print(f"   {doc.strip()[:100]}...")
        print()

    print()
    print("SCORE CONFIGS IN LANGFUSE")
    print("-" * 70)

    # Try to fetch score configs
    try:
        import os

        import httpx

        public_key = os.getenv("LANGFUSE_PUBLIC_KEY")
        secret_key = os.getenv("LANGFUSE_SECRET_KEY")
        host = os.getenv("LANGFUSE_HOST", "http://localhost:3000")

        if public_key and secret_key:
            resp = httpx.get(f"{host}/api/public/score-configs", auth=(public_key, secret_key))
            configs = resp.json()

            g_eval_configs = [c for c in configs.get("data", []) if c["name"].startswith("g_eval_")]

            print(f"G-Eval score configs: {len(g_eval_configs)}")
            print()

            for config in g_eval_configs:
                print(f"  - {config['name']}: {config['dataType']}")
                if "minValue" in config:
                    print(
                        f"    Range: {config.get('minValue', 'N/A')} - {config.get('maxValue', 'N/A')}"
                    )
                if "description" in config:
                    print(f"    {config['description']}")
                print()

        else:
            print("  ⚠ LANGFUSE_PUBLIC_KEY or LANGFUSE_SECRET_KEY not set")
            print("  Cannot fetch score configs from Langfuse API")

    except Exception as e:
        print(f"  ⚠ Error fetching score configs: {e}")

    print()
    print("=" * 70)
    print()


def run_demo_experiment(
    max_examples: int | None = None,
    agent_type: str = "tech_comparator",
) -> None:
    """Run a demo experiment using the evaluators.

    Args:
        max_examples: Limit number of examples (None = all)
        agent_type: Agent type for G-Eval rubrics

    """
    print("=" * 70)
    print("Running Demo G-Eval Experiment")
    print("=" * 70)
    print()

    try:
        from langfuse import Langfuse

        langfuse = Langfuse()

        # Fetch dataset
        dataset_name = "skillforge_golden_analyses_v1_prod"
        print(f"1. Fetching dataset: {dataset_name}")

        dataset = langfuse.get_dataset(dataset_name)
        items = list(dataset.items)

        if not items:
            print(f"   ⚠ No items found in dataset '{dataset_name}'")
            print("   Run: poetry run python scripts/sync_golden_dataset_to_langfuse.py")
            return

        print(f"   ✓ Found {len(items)} items")

        if max_examples:
            items = items[:max_examples]
            print(f"   Using first {max_examples} items")

        print()

        # Create task function (just returns expected output for golden dataset)
        def task(*, item, **kwargs):
            """Task function for evaluating existing artifacts."""
            expected = item.expected_output if hasattr(item, "expected_output") else {}
            return expected if isinstance(expected, dict) else {"content": str(expected)}

        # Get evaluators
        print(f"2. Creating evaluators for agent type: {agent_type}")
        evaluators = get_standard_evaluators(agent_type)
        run_evaluators = get_standard_run_evaluators(quality_threshold=0.6, agent_type=agent_type)

        print(f"   ✓ {len(evaluators)} item-level evaluators")
        print(f"   ✓ {len(run_evaluators)} run-level evaluators")
        print()

        # Run experiment
        print("3. Running experiment...")
        print(f"   This will evaluate {len(items)} artifacts")
        print(f"   Each artifact scored on {len(evaluators)} criteria")
        print()

        experiment_name = f"g_eval_demo_{agent_type}"

        result = langfuse.run_experiment(
            name=experiment_name,
            data=items,
            task=task,
            evaluators=evaluators,
            run_evaluators=run_evaluators,
        )

        print()
        print("=" * 70)
        print("Experiment Results")
        print("=" * 70)
        print()

        # Print formatted results
        print(result.format())

        print()
        print("View detailed results in Langfuse UI:")
        import os

        host = os.getenv("LANGFUSE_HOST", "http://localhost:3000")
        print(f"  {host}/project/skillforge/experiments")
        print()

    except ImportError:
        print("⚠ Langfuse SDK not installed")
        print("  Install: poetry add langfuse")
        return

    except Exception as e:
        logger.exception("experiment_failed", error=str(e))
        print(f"⚠ Experiment failed: {e}")
        return


def main() -> int:
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Demonstrate G-Eval LLM-as-a-Judge evaluators",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show evaluator configuration without running experiment",
    )

    parser.add_argument(
        "--quick",
        action="store_true",
        help="Run quick test with 3 examples",
    )

    parser.add_argument(
        "--full",
        action="store_true",
        help="Run full evaluation with all examples",
    )

    parser.add_argument(
        "--agent-type",
        type=str,
        default="tech_comparator",
        choices=[
            "tech_comparator",
            "security_auditor",
            "implementation_planner",
            "integration_analyst",
            "performance_profiler",
            "code_reviewer",
            "documentation_specialist",
            "test_strategist",
        ],
        help="Agent type for G-Eval rubrics",
    )

    args = parser.parse_args()

    # Show evaluator info
    show_evaluator_info(args.agent_type)

    # Run experiment if requested
    if args.quick:
        print()
        run_demo_experiment(max_examples=3, agent_type=args.agent_type)
    elif args.full:
        print()
        run_demo_experiment(max_examples=None, agent_type=args.agent_type)
    elif not args.dry_run:
        print()
        print("ℹ Use --quick or --full to run experiment")
        print("  Or --dry-run to just show configuration")

    return 0


if __name__ == "__main__":
    sys.exit(main())
