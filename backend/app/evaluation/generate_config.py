"""Generate optimal model configuration from experiment results.

This module analyzes experiment results from Langfuse and generates
an optimal model configuration for SkillForge's multi-task LLM pipeline.

Usage:
    # From experiment results file
    python -m app.evaluation.generate_config --input results.json

    # Fetch from Langfuse project
    python -m app.evaluation.generate_config --project skillforge-eval

    # Use hypotheses (no experiments required)
    python -m app.evaluation.generate_config --hypotheses
"""

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from app.core.logging import get_logger
from app.core.model_registry import (
    MODEL_REGISTRY,
    TASK_MODEL_HYPOTHESES,
    ModelInfo,
    get_model_info,
)

logger = get_logger(__name__)


@dataclass
class ModelSelection:
    """Model selection with reasoning."""

    model_id: str
    model_info: ModelInfo
    score: float
    rationale: str


@dataclass
class TaskConfig:
    """Configuration for a specific task type."""

    task_type: str
    primary_model: str
    fallback_model: str
    rationale: str
    metrics: dict[str, float]


def analyze_experiment_results(results: dict[str, Any]) -> dict[str, TaskConfig]:
    """Analyze experiment results and generate task configs.

    Args:
        results: Experiment results dictionary from run_experiments.py

    Returns:
        Dictionary mapping task_type to TaskConfig

    """
    configs = {}

    for task_type, task_results in results.get("tasks", {}).items():
        if task_results.get("status") != "completed":
            logger.warning(f"Skipping {task_type}: experiments not completed")
            continue

        winners = task_results.get("winner_by_metric", {})
        experiments = task_results.get("experiments", [])

        # Find best model by combined score
        model_scores: dict[str, float] = {}

        for exp in experiments:
            model_id = exp.get("model_id")
            if not model_id:
                continue

            metrics = exp.get("metrics", {})

            # Calculate weighted score
            # Higher weight for correctness, then cost, then latency
            correctness_keys = [
                "supervisor_correctness",
                "agent_correctness",
                "synthesis_correctness",
                "accuracy",
            ]
            correctness = 0.0
            for key in correctness_keys:
                if key in metrics:
                    correctness = metrics[key]
                    break

            cost_score = metrics.get("cost_usd", 0.0)
            latency_score = metrics.get("latency_ms", 0.0)

            # Normalize and weight (60% correctness, 25% cost, 15% latency)
            # Lower cost and latency are better, so invert them
            weighted = (
                0.60 * correctness
                + 0.25 * (1.0 - min(cost_score / 0.01, 1.0))  # Normalize to $0.01 max
                + 0.15 * (1.0 - min(latency_score / 10000, 1.0))  # Normalize to 10s max
            )

            model_scores[model_id] = weighted

        if not model_scores:
            logger.warning(f"No model scores for {task_type}")
            continue

        # Sort by score (descending)
        sorted_models = sorted(model_scores.items(), key=lambda x: x[1], reverse=True)

        # Primary is highest score, fallback is second highest (or cheapest if only one)
        primary_model = sorted_models[0][0]
        if len(sorted_models) > 1:
            fallback_model = sorted_models[1][0]
        else:
            # Find cheapest model in registry
            cheapest = min(
                MODEL_REGISTRY.items(),
                key=lambda x: x[1].input_cost_per_1m + x[1].output_cost_per_1m,
            )
            fallback_model = cheapest[0]

        # Get metrics for primary model
        primary_metrics = {}
        for exp in experiments:
            if exp.get("model_id") == primary_model:
                primary_metrics = exp.get("metrics", {})
                break

        # Build rationale
        primary_info = get_model_info(primary_model)
        fallback_info = get_model_info(fallback_model)

        rationale_parts = [
            f"Selected {primary_info.display_name if primary_info else primary_model} based on:",
            f"  - Combined score: {model_scores[primary_model]:.3f}",
        ]

        if primary_metrics:
            for key, value in primary_metrics.items():
                if isinstance(value, float):
                    rationale_parts.append(f"  - {key}: {value:.4f}")

        rationale_parts.append(
            f"Fallback: {fallback_info.display_name if fallback_info else fallback_model}"
        )

        configs[task_type] = TaskConfig(
            task_type=task_type,
            primary_model=primary_model,
            fallback_model=fallback_model,
            rationale="\n".join(rationale_parts),
            metrics=primary_metrics,
        )

    return configs


def generate_from_hypotheses() -> dict[str, TaskConfig]:
    """Generate config from pre-defined hypotheses (no experiments needed).

    Uses TASK_MODEL_HYPOTHESES from model_registry as starting point.

    Returns:
        Dictionary mapping task_type to TaskConfig

    """
    configs = {}

    for task_type, candidates in TASK_MODEL_HYPOTHESES.items():
        if not candidates:
            continue

        # Use first candidate as primary, second as fallback
        primary_model = candidates[0]
        fallback_model = candidates[1] if len(candidates) > 1 else candidates[0]

        primary_info = get_model_info(primary_model)
        fallback_info = get_model_info(fallback_model)

        rationale = (
            f"Hypothesis-based selection (not validated):\n"
            f"  - Primary: {primary_info.display_name if primary_info else primary_model}\n"
            f"  - Fallback: {fallback_info.display_name if fallback_info else fallback_model}\n"
            f"  - Rationale: {_hypothesis_rationale(task_type)}"
        )

        configs[task_type] = TaskConfig(
            task_type=task_type,
            primary_model=primary_model,
            fallback_model=fallback_model,
            rationale=rationale,
            metrics={},
        )

    return configs


def _hypothesis_rationale(task_type: str) -> str:
    """Get rationale for task type hypothesis."""
    rationales = {
        "supervisor": "Fast routing requires low latency; Gemini Flash offers best speed/cost",
        "agent": "Analysis quality needs strong reasoning; balanced models like GPT-4o-mini",
        "synthesis": "Aggregation benefits from longer context; Claude excels at coherent summaries",
    }
    return rationales.get(task_type, "No specific rationale")


def generate_config_file(
    configs: dict[str, TaskConfig],
    output_path: str,
) -> None:
    """Generate Python config file from task configs.

    Args:
        configs: Task configurations
        output_path: Path to write config file

    """
    lines = [
        '"""Auto-generated model configuration from LLM benchmark experiments.',
        "",
        f"Generated: {datetime.now().isoformat()}",
        "",
        "This file contains optimal model selections based on evaluation metrics.",
        "Edit this file to customize model routing for your use case.",
        '"""',
        "",
        "from __future__ import annotations",
        "",
        "# Task-specific model assignments",
        "# Format: task_type -> (primary_model, fallback_model)",
        "TASK_MODELS = {",
    ]

    for task_type, config in configs.items():
        lines.append(f'    "{task_type}": ("{config.primary_model}", "{config.fallback_model}"),')

    lines.extend(
        [
            "}",
            "",
            "",
            "def get_model_for_task(task_type: str, use_fallback: bool = False) -> str:",
            '    """Get optimal model for a task type.',
            "",
            "    Args:",
            "        task_type: Type of task (supervisor, agent, synthesis)",
            "        use_fallback: If True, return fallback model instead of primary",
            "",
            "    Returns:",
            "        Model identifier string",
            '    """',
            "    primary, fallback = TASK_MODELS.get(task_type, (None, None))",
            "    if use_fallback:",
            "        return fallback",
            "    return primary",
            "",
            "",
            "# Selection rationale (for documentation)",
            "SELECTION_RATIONALE = {",
        ]
    )

    for task_type, config in configs.items():
        # Escape the rationale for Python string
        escaped = config.rationale.replace('"', '\\"').replace("\n", "\\n")
        lines.append(f'    "{task_type}": "{escaped}",')

    lines.extend(
        [
            "}",
            "",
        ]
    )

    # Write file
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text("\n".join(lines))

    logger.info(f"Config file written to: {output_path}")


def generate_json_config(configs: dict[str, TaskConfig]) -> dict[str, Any]:
    """Generate JSON representation of config.

    Args:
        configs: Task configurations

    Returns:
        JSON-serializable dictionary

    """
    return {
        "generated_at": datetime.now().isoformat(),
        "tasks": {
            task_type: {
                "primary_model": config.primary_model,
                "fallback_model": config.fallback_model,
                "rationale": config.rationale,
                "metrics": config.metrics,
            }
            for task_type, config in configs.items()
        },
    }


def main():
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Generate model configuration from experiment results",
    )

    parser.add_argument(
        "--input",
        type=str,
        help="Path to experiment results JSON file",
    )
    parser.add_argument(
        "--project",
        type=str,
        help="Langfuse project name to fetch results from",
    )
    parser.add_argument(
        "--hypotheses",
        action="store_true",
        help="Use pre-defined hypotheses (no experiments needed)",
    )
    parser.add_argument(
        "--output-py",
        type=str,
        default="app/core/task_model_config.py",
        help="Output path for Python config file",
    )
    parser.add_argument(
        "--output-json",
        type=str,
        help="Output path for JSON config file (optional)",
    )

    args = parser.parse_args()

    if args.hypotheses:
        print("Generating config from hypotheses...")
        configs = generate_from_hypotheses()
    elif args.input:
        print(f"Generating config from: {args.input}")
        with open(args.input) as f:
            results = json.load(f)
        configs = analyze_experiment_results(results)
    elif args.project:
        print(f"Fetching results from Langfuse project: {args.project}")
        # TODO: Implement Langfuse API fetch
        print("ERROR: Langfuse fetch not yet implemented. Use --input with results JSON.")
        return
    else:
        parser.print_help()
        return

    if not configs:
        print("ERROR: No configurations generated")
        return

    # Print summary
    print("\n" + "=" * 60)
    print("MODEL CONFIGURATION")
    print("=" * 60)

    for task_type, config in configs.items():
        print(f"\n{task_type.upper()}:")
        print(f"  Primary: {config.primary_model}")
        print(f"  Fallback: {config.fallback_model}")
        print(f"  Rationale: {config.rationale.split(chr(10))[0]}")

    # Generate outputs
    generate_config_file(configs, args.output_py)
    print(f"\nPython config written to: {args.output_py}")

    if args.output_json:
        json_config = generate_json_config(configs)
        with open(args.output_json, "w") as f:
            json.dump(json_config, f, indent=2)
        print(f"JSON config written to: {args.output_json}")


if __name__ == "__main__":
    main()
