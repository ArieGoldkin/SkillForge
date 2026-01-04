#!/usr/bin/env python
"""Unified dataset experiment runner for all Langfuse golden datasets.

Issue #570: Run experiments on all golden datasets with proper evaluators.

This script implements three evaluation modes:
1. VALIDATE (default, free): Check dataset structure only
2. QUALITY ($0.50-2.00): LLM-as-judge evaluation via real G-Eval
3. SYSTEM ($5-20): Full workflow evaluation (future)

The script uses real G-Eval from app.shared.services.g_eval, NOT fake heuristics.

Usage:
    # Validate dataset structure (free, fast, CI default)
    poetry run python scripts/run_dataset_experiments.py --dataset supervisor --mode validate

    # Quality evaluation with LLM-as-judge (costs money)
    poetry run python scripts/run_dataset_experiments.py --dataset synthesis --mode quality

    # Run all datasets with baseline export
    poetry run python scripts/run_dataset_experiments.py --all --baseline --mode quality

    # Dry run (show what would happen)
    poetry run python scripts/run_dataset_experiments.py --all --dry-run

    # Compare against baseline (for CI)
    poetry run python scripts/run_dataset_experiments.py --all --compare-baseline

Environment variables required:
    LANGFUSE_ENABLED=true
    LANGFUSE_PUBLIC_KEY=<your-key>
    LANGFUSE_SECRET_KEY=<your-key>
    LANGFUSE_HOST=<your-host>  # Optional, defaults to http://localhost:3000
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import UTC, datetime
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

# =============================================================================
# DATASET REGISTRY - Maps CLI name to Langfuse dataset and evaluation config
# =============================================================================

DATASET_REGISTRY = {
    "supervisor": {
        "langfuse_name": "supervisor_routing_golden_v1_prod",
        "description": "Supervisor routing decisions",
        "evaluator_type": "routing",
        "agent_type": None,  # Routing doesn't need agent-specific G-Eval
        "expected_items": 20,
    },
    "agent_analysis": {
        "langfuse_name": "agent_analysis_golden_v1_prod",
        "description": "Agent analysis quality",
        "evaluator_type": "g_eval",
        "agent_type": "tech_comparator",  # For G-Eval rubric
        "expected_items": 9,
    },
    "synthesis": {
        "langfuse_name": "synthesis_golden_v1_prod",
        "description": "Synthesis quality",
        "evaluator_type": "g_eval",
        "agent_type": "synthesizer",  # For G-Eval rubric
        "expected_items": 5,
    },
    "golden_analyses": {
        "langfuse_name": "skillforge_golden_analyses_v1_prod",
        "description": "Full golden analyses",
        "evaluator_type": "g_eval",
        "agent_type": "tech_comparator",  # For G-Eval rubric
        "expected_items": 98,
    },
    "adversarial": {
        "langfuse_name": "adversarial_safety_v1_prod",
        "description": "Adversarial/safety testing",
        "evaluator_type": "structural",  # Structural validation only
        "agent_type": None,
        "expected_items": 31,
    },
    "edge_cases": {
        "langfuse_name": "edge_cases_boundary_v1_prod",
        "description": "Edge case/boundary testing",
        "evaluator_type": "structural",  # Structural validation only
        "agent_type": None,
        "expected_items": 40,
    },
}

# Baseline thresholds for CI pass/fail
DEFAULT_THRESHOLDS = {
    "min_avg_score": 0.60,
    "min_pass_rate": 0.70,
}

BASELINE_DIR = Path(__file__).parent / "baseline_scores"


def check_langfuse_enabled() -> bool:
    """Check if Langfuse is enabled and configured."""
    if os.getenv("LANGFUSE_ENABLED", "false").lower() != "true":
        print("ERROR: LANGFUSE_ENABLED must be 'true' to run experiment")
        return False

    if not os.getenv("LANGFUSE_PUBLIC_KEY") or not os.getenv("LANGFUSE_SECRET_KEY"):
        print("ERROR: LANGFUSE_PUBLIC_KEY and LANGFUSE_SECRET_KEY must be set")
        return False

    return True


# =============================================================================
# STRUCTURAL VALIDATORS - Dataset structure checks (Mode: validate)
# =============================================================================

# Required fields for each dataset type (must match Langfuse upload format)
STRUCTURAL_REQUIREMENTS = {
    "adversarial": {
        # Uploaded via format_adversarial_item: content, content_type, attack_type
        "input": ["content", "content_type"],  # attack_type from metadata, may not exist
        "expected_output": ["behavior"],
    },
    "edge_cases": {
        # Uploaded via format_edge_cases_item: content, content_type, edge_case_type
        "input": ["content", "content_type"],  # edge_case_type from metadata
        "expected_output": ["behavior"],
    },
    "routing": {
        # Uploaded via format_supervisor_item
        "input": ["content", "content_type"],
        "expected_output": ["expected_agents"],
    },
    "synthesis": {
        # Uploaded via format_synthesis_item - DIFFERENT STRUCTURE
        "input": ["agent_findings"],  # No content/content_type!
        "expected_output": [],  # Flexible
    },
    "agent_analysis": {
        # Uploaded via format_agent_analysis_item
        "input": ["content", "content_type", "agent_type"],
        "expected_output": [],  # Primary/expected_response structure varies
    },
    "golden": {
        # Default for golden_analyses
        "input": ["content", "content_type"],
        "expected_output": [],  # Flexible structure
    },
}


def create_structural_validator(dataset_type: str):
    """Create validator that checks dataset item structure.

    This is a FREE evaluator (no LLM calls) that verifies:
    1. Required input fields are present
    2. Required expected_output fields are present
    3. Primary content field is non-empty

    Args:
        dataset_type: Type of dataset (adversarial, edge_cases, routing, golden, synthesis)

    Returns:
        Langfuse-compatible evaluator function
    """
    from langfuse import Evaluation

    requirements = STRUCTURAL_REQUIREMENTS.get(dataset_type, STRUCTURAL_REQUIREMENTS["golden"])

    def structural_validator(*, input, output, expected_output, **_kwargs) -> Evaluation:
        """Validate dataset item has required structure."""
        violations = []

        # Check input fields
        if isinstance(input, dict):
            for field in requirements["input"]:
                if field not in input:
                    violations.append(f"Missing input.{field}")
                elif not input.get(field):
                    violations.append(f"Empty input.{field}")
        else:
            violations.append("Input is not a dict")

        # Check expected_output fields
        if isinstance(expected_output, dict):
            for field in requirements["expected_output"]:
                if field not in expected_output:
                    violations.append(f"Missing expected_output.{field}")
        elif requirements["expected_output"]:
            violations.append("expected_output is not a dict")

        # Check primary content is meaningful (field depends on dataset type)
        if isinstance(input, dict):
            # Use the first required input field as the "content" field
            primary_field = requirements["input"][0] if requirements["input"] else "content"
            content = input.get(primary_field, "")

            # For complex fields like agent_findings (list), check if non-empty
            if isinstance(content, list):
                if len(content) == 0:
                    violations.append(f"Empty {primary_field} list")
            elif isinstance(content, str):
                if len(content.strip()) < 10:
                    violations.append(f"{primary_field} too short (<10 chars)")
            elif not content:
                violations.append(f"Empty {primary_field}")

        score = 1.0 if not violations else 0.0

        return Evaluation(
            name="structural_validity",
            value=score,
            comment=f"Violations: {violations}" if violations else "Structure valid",
        )

    structural_validator.__name__ = f"structural_validator_{dataset_type}"
    return structural_validator


# =============================================================================
# ROUTING EVALUATOR - Supervisor accuracy (Mode: validate + quality)
# =============================================================================


def create_routing_accuracy_evaluator():
    """Create evaluator for supervisor routing accuracy.

    This evaluator checks if the supervisor correctly selected agents.
    Uses Jaccard similarity for partial credit.
    """
    from langfuse import Evaluation

    def routing_accuracy(*, output, expected_output, **_kwargs) -> Evaluation:
        """Evaluate if supervisor correctly selected agents."""
        expected_agents = set(expected_output.get("expected_agents", []))
        predicted_agents = set(output.get("selected_agents", output.get("expected_agents", [])))

        # Exact match
        exact_match = expected_agents == predicted_agents

        # Jaccard similarity for partial credit
        if expected_agents or predicted_agents:
            intersection = expected_agents & predicted_agents
            union = expected_agents | predicted_agents
            jaccard = len(intersection) / len(union) if union else 1.0
        else:
            jaccard = 1.0

        score = 1.0 if exact_match else jaccard

        return Evaluation(
            name="routing_accuracy",
            value=score,
            comment=f"Expected: {sorted(expected_agents)}, Got: {sorted(predicted_agents)}",
        )

    return routing_accuracy


# =============================================================================
# EVALUATOR FACTORY - Get evaluators based on mode and dataset type
# =============================================================================


def get_evaluators_for_dataset(
    evaluator_type: str,
    agent_type: str | None = None,
    mode: str = "validate",
    dataset_name: str | None = None,
) -> list:
    """Get evaluators for a dataset based on mode.

    Args:
        evaluator_type: Type from DATASET_REGISTRY (routing, g_eval, structural)
        agent_type: Agent type for G-Eval rubric selection
        mode: Evaluation mode (validate, quality, system)
        dataset_name: Name of the dataset (for dataset-specific structural validators)

    Returns:
        List of evaluator functions
    """
    # Determine the correct structural validator type
    def get_structural_type() -> str:
        """Get the structural requirements key for this dataset."""
        if dataset_name in STRUCTURAL_REQUIREMENTS:
            return dataset_name
        if evaluator_type == "structural":
            return "adversarial"  # Default for structural type
        return "golden"

    # Mode: validate - structural validators only (FREE)
    if mode == "validate":
        if evaluator_type == "routing":
            return [create_routing_accuracy_evaluator()]
        else:
            return [create_structural_validator(get_structural_type())]

    # Mode: quality - real G-Eval LLM-as-judge (COSTS MONEY)
    if mode == "quality":
        if evaluator_type == "routing":
            return [create_routing_accuracy_evaluator()]
        elif evaluator_type == "structural":
            # Structural datasets (adversarial, edge_cases) use structural validators even in quality mode
            return [create_structural_validator(get_structural_type())]
        else:
            # Import real G-Eval for quality evaluation
            from app.shared.services.g_eval.langfuse_evaluators import (
                create_g_eval_overall_evaluator,
            )

            return [create_g_eval_overall_evaluator(agent_type or "tech_comparator")]

    # Mode: system - full workflow evaluation (COSTS MORE, future implementation)
    if mode == "system":
        raise NotImplementedError("System mode not yet implemented. Use validate or quality.")

    # Default fallback
    return [create_structural_validator("golden")]


def get_run_evaluators_for_mode(mode: str, threshold: float = 0.6) -> list:
    """Get run-level evaluators based on mode.

    Args:
        mode: Evaluation mode
        threshold: Pass rate threshold

    Returns:
        List of run-level evaluator functions
    """
    from langfuse import Evaluation

    def avg_score(*, item_results, **_kwargs) -> Evaluation:
        """Calculate average score across all items."""
        scores = [
            e.value
            for result in item_results
            for e in (result.evaluations if hasattr(result, "evaluations") else [])
            if hasattr(e, "value") and e.value is not None
        ]
        avg = sum(scores) / len(scores) if scores else 0.0
        return Evaluation(name="avg_score", value=avg, comment=f"Average: {avg:.3f}")

    def pass_rate(*, item_results, **_kwargs) -> Evaluation:
        """Calculate pass rate (% of items above threshold)."""
        scores = [
            e.value
            for result in item_results
            for e in (result.evaluations if hasattr(result, "evaluations") else [])
            if hasattr(e, "value") and e.value is not None
        ]
        passed = sum(1 for s in scores if s >= threshold)
        rate = passed / len(scores) if scores else 0.0
        return Evaluation(name="pass_rate", value=rate, comment=f"Pass rate: {rate:.1%}")

    def std_deviation(*, item_results, **_kwargs) -> Evaluation:
        """Calculate standard deviation of scores."""
        scores = [
            e.value
            for result in item_results
            for e in (result.evaluations if hasattr(result, "evaluations") else [])
            if hasattr(e, "value") and e.value is not None
        ]
        if len(scores) < 2:
            return Evaluation(name="std_deviation", value=0.0, comment="Not enough scores")
        mean = sum(scores) / len(scores)
        variance = sum((s - mean) ** 2 for s in scores) / len(scores)
        std = variance**0.5
        return Evaluation(name="std_deviation", value=std, comment=f"Std dev: {std:.3f}")

    return [avg_score, pass_rate, std_deviation]


# =============================================================================
# TASK FUNCTIONS - Process dataset items
# =============================================================================


def create_task_function(dataset_name: str, mode: str = "validate"):
    """Create task function for a dataset.

    For validate/quality modes: Return expected_output as output
    (evaluating the quality of our golden data)

    For system mode: Actually run the workflow and return real output
    (evaluating our system's ability to produce correct outputs)

    Args:
        dataset_name: Name of the dataset
        mode: Evaluation mode

    Returns:
        Task function compatible with langfuse.run_experiment()
    """

    def task(*, item, **_kwargs) -> dict[str, Any]:
        """Process a single dataset item."""
        # For validate/quality modes: return expected_output as "output"
        # This evaluates the quality of our golden data
        expected = item.expected_output if hasattr(item, "expected_output") else {}
        if isinstance(expected, dict):
            return expected
        return {"content": str(expected)}

    task.__name__ = f"golden_task_{dataset_name}_{mode}"
    return task


# =============================================================================
# EXPERIMENT RUNNER
# =============================================================================


def run_experiment(  # noqa: PLR0911, PLR0912 - Complex but clear flow
    dataset_name: str,
    *,
    run_name: str | None = None,
    mode: str = "validate",
    dry_run: bool = False,
    save_baseline: bool = False,
) -> dict[str, Any]:
    """Run experiment on a single dataset.

    Args:
        dataset_name: Key from DATASET_REGISTRY
        run_name: Custom experiment run name
        mode: Evaluation mode (validate, quality, system)
        dry_run: If True, show what would run without running
        save_baseline: If True, save results to baseline file

    Returns:
        Dict with experiment results
    """
    if dataset_name not in DATASET_REGISTRY:
        return {"status": "error", "message": f"Unknown dataset: {dataset_name}"}

    config = DATASET_REGISTRY[dataset_name]
    langfuse_name = str(config["langfuse_name"])
    evaluator_type = str(config["evaluator_type"])
    agent_type = config.get("agent_type")

    if not check_langfuse_enabled():
        return {"status": "error", "message": "Langfuse not enabled"}

    try:
        from langfuse import Langfuse

        # Initialize Langfuse client
        langfuse = Langfuse(
            public_key=os.getenv("LANGFUSE_PUBLIC_KEY"),
            secret_key=os.getenv("LANGFUSE_SECRET_KEY"),
            host=os.getenv("LANGFUSE_HOST", "http://localhost:3000"),
        )

        # Fetch dataset
        print(f"\nFetching dataset: {langfuse_name}...")
        try:
            dataset = langfuse.get_dataset(langfuse_name)
            items = list(dataset.items)
        except Exception as e:
            return {
                "status": "error",
                "message": f"Dataset not found: {langfuse_name}. Run upload script first. Error: {e}",
            }

        # Build run name with mode
        exp_name = (
            run_name
            or f"{dataset_name}_{mode}_{datetime.now(UTC).strftime('%Y%m%d_%H%M%S')}"
        )

        # Calculate estimated cost
        cost_estimate = "$0" if mode == "validate" else f"~${len(items) * 0.02:.2f}" if mode == "quality" else "N/A"

        print(f"\n{'=' * 70}")
        print(f"EXPERIMENT: {dataset_name}")
        print("=" * 70)
        print(f"  Dataset:     {langfuse_name}")
        print(f"  Items:       {len(items)} / {config['expected_items']} expected")
        print(f"  Mode:        {mode.upper()}")
        print(f"  Evaluator:   {evaluator_type}")
        if agent_type:
            print(f"  Agent Type:  {agent_type}")
        print(f"  Est. Cost:   {cost_estimate}")
        print(f"  Run Name:    {exp_name}")
        print("=" * 70)

        if dry_run:
            print(f"\n[DRY RUN] Would evaluate {len(items)} items in {mode} mode")
            return {"status": "dry_run", "dataset": dataset_name, "items": len(items), "mode": mode}

        if not items:
            return {"status": "error", "message": f"No items in dataset {langfuse_name}"}

        # Get evaluators based on mode
        evaluators = get_evaluators_for_dataset(evaluator_type, agent_type, mode, dataset_name)
        run_evaluators = get_run_evaluators_for_mode(mode)

        # Create task function
        task_fn = create_task_function(dataset_name, mode)

        # Run experiment using modern SDK pattern
        print(f"\nRunning experiment with {len(evaluators)} evaluator(s) in {mode} mode...")
        result = langfuse.run_experiment(
            name=exp_name,
            description=f"{mode.upper()} experiment for {config['description']}",
            data=items,
            task=task_fn,
            evaluators=evaluators,
            run_evaluators=run_evaluators,
            metadata={
                "dataset_name": dataset_name,
                "evaluator_type": evaluator_type,
                "agent_type": agent_type,
                "mode": mode,
                "sdk_pattern": "run_experiment_v3",
                "created_at": datetime.now(UTC).isoformat(),
            },
        )

        # Flush to ensure all data is sent
        langfuse.flush()

        # Extract metrics - FIX: Handle 0.0 values correctly (truthiness bug)
        metrics = {}
        try:
            run_evals = getattr(result, "run_evaluations", [])
            for eval_obj in run_evals:
                if hasattr(eval_obj, "name") and hasattr(eval_obj, "value"):
                    # FIX: Use `is not None` instead of truthy check
                    # 0.0 is a valid score, not None
                    metrics[eval_obj.name] = (
                        round(eval_obj.value, 4) if eval_obj.value is not None else None
                    )
        except Exception as e:
            logger.debug("metrics_extraction_failed", error=str(e))

        # Print results
        print(f"\n{'=' * 70}")
        print("RESULTS")
        print("=" * 70)
        for name, value in metrics.items():
            if value is not None:
                print(f"  {name}: {value:.4f}")
            else:
                print(f"  {name}: N/A")

        # Determine CI status (handle None values gracefully)
        ci_status = "PASS"
        avg_score = metrics.get("avg_score")
        pass_rate = metrics.get("pass_rate")
        if avg_score is not None and avg_score < DEFAULT_THRESHOLDS["min_avg_score"]:
            ci_status = "FAIL"
        if pass_rate is not None and pass_rate < DEFAULT_THRESHOLDS["min_pass_rate"]:
            ci_status = "FAIL"
        # If we have no metrics, can't determine pass/fail
        if avg_score is None and pass_rate is None:
            ci_status = "UNKNOWN"

        print(f"\n  CI Status: {ci_status}")
        print(
            f"  View: {os.getenv('LANGFUSE_HOST', 'http://localhost:3000')}/datasets/{langfuse_name}"
        )

        # Build result
        experiment_result = {
            "status": "success",
            "dataset": dataset_name,
            "langfuse_name": langfuse_name,
            "run_name": exp_name,
            "mode": mode,
            "created_at": datetime.now(UTC).isoformat(),
            "items_evaluated": len(items),
            "metrics": metrics,
            "thresholds": DEFAULT_THRESHOLDS,
            "ci_status": ci_status,
        }

        # Save baseline if requested
        if save_baseline:
            save_baseline_result(dataset_name, experiment_result)

        return experiment_result

    except ImportError as e:
        return {"status": "error", "message": f"Missing dependency: {e}"}
    except Exception as e:
        logger.exception("experiment_failed")
        return {"status": "error", "message": str(e)}


def save_baseline_result(dataset_name: str, result: dict[str, Any]) -> None:
    """Save experiment result as baseline."""
    BASELINE_DIR.mkdir(parents=True, exist_ok=True)
    baseline_file = BASELINE_DIR / f"{dataset_name}_baseline.json"

    with baseline_file.open("w") as f:
        json.dump(result, f, indent=2, default=str)

    print(f"\n  Baseline saved: {baseline_file}")


def load_baseline(dataset_name: str) -> dict[str, Any] | None:
    """Load baseline result for comparison."""
    baseline_file = BASELINE_DIR / f"{dataset_name}_baseline.json"
    if baseline_file.exists():
        with baseline_file.open() as f:
            return json.load(f)
    return None


def compare_with_baseline(dataset_name: str, current: dict[str, Any]) -> dict[str, Any]:
    """Compare current results with baseline."""
    baseline = load_baseline(dataset_name)
    if not baseline:
        return {"status": "no_baseline", "message": f"No baseline found for {dataset_name}"}

    regressions: list[dict[str, Any]] = []
    improvements: list[dict[str, Any]] = []
    comparison: dict[str, Any] = {
        "dataset": dataset_name,
        "baseline_run": baseline.get("run_name"),
        "current_run": current.get("run_name"),
        "regressions": regressions,
        "improvements": improvements,
    }

    baseline_metrics = baseline.get("metrics", {})
    current_metrics = current.get("metrics", {})

    for metric, baseline_value in baseline_metrics.items():
        current_value = current_metrics.get(metric)
        if baseline_value is None or current_value is None:
            continue

        diff = current_value - baseline_value
        if diff < -0.05:  # 5% regression threshold
            regressions.append(
                {
                    "metric": metric,
                    "baseline": baseline_value,
                    "current": current_value,
                    "diff": diff,
                }
            )
        elif diff > 0.05:  # 5% improvement threshold
            improvements.append(
                {
                    "metric": metric,
                    "baseline": baseline_value,
                    "current": current_value,
                    "diff": diff,
                }
            )

    comparison["status"] = "FAIL" if comparison["regressions"] else "PASS"
    return comparison


# =============================================================================
# CLI
# =============================================================================


def main() -> int:
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Run Langfuse dataset experiments (Issue #570)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    # Validate dataset structure (free, fast)
    poetry run python scripts/run_dataset_experiments.py --dataset supervisor --mode validate

    # Quality evaluation with LLM-as-judge
    poetry run python scripts/run_dataset_experiments.py --dataset synthesis --mode quality

    # Run all datasets with baseline export
    poetry run python scripts/run_dataset_experiments.py --all --baseline --mode quality

    # Dry run
    poetry run python scripts/run_dataset_experiments.py --all --dry-run

    # Compare with baseline (for CI)
    poetry run python scripts/run_dataset_experiments.py --all --compare-baseline

Evaluation Modes:
    validate  - Check dataset structure only ($0, milliseconds)
    quality   - LLM-as-judge via real G-Eval (~$0.50-2.00 per run)
    system    - Full workflow evaluation (~$5-20 per run) [NOT YET IMPLEMENTED]

Available datasets:
    - supervisor: Supervisor routing decisions (20 items)
    - agent_analysis: Agent analysis quality (9 items)
    - synthesis: Synthesis quality (5 items)
    - golden_analyses: Full golden analyses (98 items)
    - adversarial: Adversarial/safety testing (31 items)
    - edge_cases: Edge case/boundary testing (40 items)
""",
    )

    parser.add_argument(
        "--dataset",
        type=str,
        choices=list(DATASET_REGISTRY.keys()),
        help="Run experiment on specific dataset",
    )

    parser.add_argument(
        "--all",
        action="store_true",
        help="Run experiments on all datasets",
    )

    parser.add_argument(
        "--mode",
        type=str,
        choices=["validate", "quality", "system"],
        default="validate",
        help="Evaluation mode: validate (free), quality (LLM-as-judge), system (full workflow)",
    )

    parser.add_argument(
        "--baseline",
        action="store_true",
        help="Save results as baseline for future comparison",
    )

    parser.add_argument(
        "--compare-baseline",
        action="store_true",
        help="Compare results against saved baseline",
    )

    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would run without running",
    )

    parser.add_argument(
        "--run-name",
        type=str,
        help="Custom experiment run name",
    )

    args = parser.parse_args()

    # Determine which datasets to run
    if args.all:
        datasets = list(DATASET_REGISTRY.keys())
    elif args.dataset:
        datasets = [args.dataset]
    else:
        parser.print_help()
        print("\n" + "=" * 70)
        print("TIP: Use --dataset <name> or --all to run experiments")
        print("=" * 70)
        return 0

    # Print mode information
    print(f"\n{'#' * 70}")
    print(f"# EVALUATION MODE: {args.mode.upper()}")
    if args.mode == "validate":
        print("# Cost: $0 (structural validation only)")
    elif args.mode == "quality":
        print("# Cost: ~$0.50-2.00 (LLM-as-judge via real G-Eval)")
    elif args.mode == "system":
        print("# Cost: ~$5-20 (full workflow evaluation)")
    print("#" * 70)

    # Run experiments
    results = {}
    all_pass = True

    for dataset_name in datasets:
        print(f"\n{'#' * 70}")
        print(f"# DATASET: {dataset_name}")
        print("#" * 70)

        result = run_experiment(
            dataset_name,
            run_name=args.run_name,
            mode=args.mode,
            dry_run=args.dry_run,
            save_baseline=args.baseline,
        )

        results[dataset_name] = result

        if result.get("status") == "error":
            print(f"\nERROR: {result.get('message')}")
            all_pass = False
        elif result.get("ci_status") == "FAIL":
            all_pass = False

        # Compare with baseline if requested
        if args.compare_baseline and result.get("status") == "success":
            comparison = compare_with_baseline(dataset_name, result)
            print(f"\n  Baseline Comparison: {comparison.get('status')}")
            if comparison.get("regressions"):
                print("  Regressions:")
                for reg in comparison["regressions"]:
                    print(f"    - {reg['metric']}: {reg['baseline']:.4f} → {reg['current']:.4f}")
                all_pass = False

    # Summary
    print(f"\n{'=' * 70}")
    print("SUMMARY")
    print("=" * 70)
    print(f"  Mode: {args.mode.upper()}")
    for dataset_name, result in results.items():
        status = result.get("status", "unknown")
        ci = result.get("ci_status", "N/A")
        print(f"  {dataset_name}: {status} (CI: {ci})")

    print(f"\n  Overall: {'PASS' if all_pass else 'FAIL'}")

    return 0 if all_pass else 1


if __name__ == "__main__":
    sys.exit(main())
