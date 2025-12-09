"""LLM Benchmark Runner for SkillForge Evaluation Framework.

This module provides tools for benchmarking different LLM models (GPT-4o-mini, Claude Sonnet 4,
Gemini Flash, Grok-3-mini) across three task types:
1. Supervisor routing - selecting which agents to run
2. Agent analysis - generating structured analysis outputs
3. Synthesis - aggregating multiple agent findings

The benchmark uses LangSmith's evaluate() method to run experiments on golden datasets
and compare model performance across accuracy, latency, and cost metrics.

Example:
    ```python
    from app.evaluation.llm_benchmark import LLMBenchmark
    from app.evaluation.evaluators import (
        supervisor_correctness_evaluator,
        latency_evaluator,
        cost_evaluator,
    )

    benchmark = LLMBenchmark(project_name="skillforge-eval")

    # Run single experiment
    results = await benchmark.run_experiment(
        task_type="supervisor",
        model_id="gemini-2.5-flash",
        dataset_name="supervisor_golden_v1",
        evaluators=[
            supervisor_correctness_evaluator,
            latency_evaluator,
            cost_evaluator,
        ],
        experiment_prefix="supervisor_baseline",
    )

    # Compare multiple models
    comparison = await benchmark.compare_models(
        task_type="supervisor",
        model_ids=["gemini-2.5-flash", "gpt-4o-mini", "claude-sonnet-4-20250514"],
        dataset_name="supervisor_golden_v1",
    )
    print(f"Winner by accuracy: {comparison.winner_by_metric['accuracy']}")
    ```
"""

from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Callable, Literal

from langsmith import Client
from langsmith.schemas import Example, Run

from app.core.config import settings
from app.core.logging import get_logger
from app.core.model_factory import get_chat_model
from app.core.model_registry import MODEL_REGISTRY, get_model_info
from app.evaluation.datasets import load_dataset
from app.workflows.nodes.supervisor import supervisor_route
from app.workflows.nodes.agents.tech_comparator_node import tech_comparator_node
from app.workflows.state import AnalysisState
from app.workflows.tasks.aggregate_findings import aggregate_findings

logger = get_logger(__name__)

# Type aliases for task types
TaskType = Literal["supervisor", "agent", "synthesis"]


@dataclass
class ExperimentResults:
    """Results from a single experiment run.

    Attributes:
        experiment_id: LangSmith experiment ID
        model_id: Model identifier used in experiment
        task_type: Type of task (supervisor, agent, synthesis)
        metrics: Dictionary of metric_name -> value (accuracy, latency_p50, cost_total, etc.)
        run_count: Number of examples evaluated
        timestamp: When experiment was run
        dataset_name: Name of dataset used
    """

    experiment_id: str
    model_id: str
    task_type: str
    metrics: dict[str, float]
    run_count: int
    timestamp: datetime
    dataset_name: str = ""


@dataclass
class ComparisonResults:
    """Results from comparing multiple models.

    Attributes:
        experiments: List of individual experiment results
        winner_by_metric: Dictionary mapping metric_name -> winning model_id
        recommendation: Human-readable recommendation based on all metrics
        task_type: Type of task compared
    """

    experiments: list[ExperimentResults]
    winner_by_metric: dict[str, str]
    recommendation: str
    task_type: str
    cost_savings: dict[str, float] = field(default_factory=dict)


class LLMBenchmark:
    """Benchmark runner for comparing LLM models across tasks.

    This class integrates with LangSmith to run evaluation experiments
    on golden datasets and compare model performance.

    Attributes:
        client: LangSmith client for running experiments
        project_name: LangSmith project name for tracking experiments
        local_mode: If True, run evaluations locally without LangSmith dataset sync
    """

    def __init__(self, project_name: str = "skillforge-eval", local_mode: bool = False):
        """Initialize benchmark runner.

        Args:
            project_name: LangSmith project name for experiment tracking
            local_mode: If True, run evaluations locally without LangSmith dataset sync
        """
        self.client = Client()
        self.project_name = project_name
        self.local_mode = local_mode
        logger.info("benchmark_initialized", project=project_name, local_mode=local_mode)

    async def run_experiment(
        self,
        task_type: TaskType,
        model_id: str,
        dataset_name: str,
        evaluators: list[Callable],
        experiment_prefix: str | None = None,
    ) -> ExperimentResults:
        """Run evaluation experiment on a dataset.

        Args:
            task_type: Type of task to benchmark (supervisor, agent, synthesis)
            model_id: Model identifier from model registry
            dataset_name: Name of dataset to load from datasets/ directory
            evaluators: List of evaluator functions for metrics
            experiment_prefix: Optional prefix for experiment name

        Returns:
            ExperimentResults with metrics, run count, and metadata

        Raises:
            ValueError: If model_id not in registry or dataset not found
            RuntimeError: If experiment execution fails

        Example:
            ```python
            results = await benchmark.run_experiment(
                task_type="supervisor",
                model_id="gemini-2.5-flash",
                dataset_name="supervisor_golden_v1",
                evaluators=[
                    supervisor_correctness_evaluator,
                    latency_evaluator,
                    cost_evaluator,
                ],
            )
            ```
        """
        # Validate model exists in registry
        model_info = get_model_info(model_id)
        if not model_info:
            msg = f"Model '{model_id}' not found in registry"
            raise ValueError(msg)

        # Create experiment name
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        prefix = experiment_prefix or task_type
        experiment_name = f"{prefix}_{model_id}_{timestamp}"

        logger.info(
            "experiment_starting",
            experiment_name=experiment_name,
            model_id=model_id,
            task_type=task_type,
            dataset_name=dataset_name,
        )

        # Load dataset
        try:
            dataset = load_dataset(dataset_name)
        except FileNotFoundError as e:
            logger.error("dataset_not_found", dataset_name=dataset_name)
            raise ValueError(f"Dataset '{dataset_name}' not found") from e

        # Get target function for task type
        target_fn = self._get_target_function(task_type, model_id)

        # Run experiment
        start_time = time.time()

        if self.local_mode:
            # Local mode: run evaluations without LangSmith dataset sync
            metrics = await self._run_local_experiment(
                target_fn=target_fn,
                dataset=dataset,
                evaluators=evaluators,
                model_id=model_id,
                model_info=model_info,
                task_type=task_type,
            )
        else:
            # LangSmith mode: sync dataset and run via evaluate()
            try:
                # Create dataset in LangSmith if it doesn't exist
                ls_dataset_name = f"{dataset_name}_{task_type}"
                try:
                    ls_dataset = self.client.read_dataset(dataset_name=ls_dataset_name)
                except Exception:  # noqa: BLE001
                    # Dataset doesn't exist, create it
                    ls_dataset = self.client.create_dataset(
                        dataset_name=ls_dataset_name,
                        description=f"Golden dataset for {task_type} task evaluation",
                    )
                    # Upload examples
                    for example in dataset:
                        self.client.create_example(
                            dataset_id=ls_dataset.id,
                            inputs=example.get("inputs", {}),
                            outputs=example.get("outputs", {}),
                            metadata=example.get("metadata", {}),
                        )

                # Run evaluation
                experiment_results = await asyncio.get_event_loop().run_in_executor(
                    None,
                    lambda: self.client.evaluate(
                        target_fn,
                        data=ls_dataset_name,
                        evaluators=evaluators,
                        experiment_prefix=experiment_name,
                        max_concurrency=3,  # Limit concurrent API calls
                        metadata={
                            "model_id": model_id,
                            "task_type": task_type,
                            "provider": model_info.provider,
                            "cost_per_1m_input": model_info.input_cost_per_1m,
                            "cost_per_1m_output": model_info.output_cost_per_1m,
                        },
                    ),
                )
                metrics = self._extract_metrics(experiment_results)

            except Exception as e:
                duration = time.time() - start_time
                logger.error(
                    "experiment_failed",
                    experiment_name=experiment_name,
                    error=str(e),
                    duration_seconds=duration,
                    exc_info=True,
                )
                raise RuntimeError(f"Experiment failed: {e}") from e

        duration = time.time() - start_time

        # Create result object
        result = ExperimentResults(
            experiment_id=experiment_name,
            model_id=model_id,
            task_type=task_type,
            metrics=metrics,
            run_count=len(dataset),
            timestamp=datetime.now(),
            dataset_name=dataset_name,
        )

        logger.info(
            "experiment_complete",
            experiment_name=experiment_name,
            model_id=model_id,
            task_type=task_type,
            metrics=metrics,
            run_count=len(dataset),
            duration_seconds=duration,
        )

        return result

    async def compare_models(
        self,
        task_type: TaskType,
        model_ids: list[str],
        dataset_name: str,
    ) -> ComparisonResults:
        """Run A/B comparison across multiple models.

        This method runs experiments for each model and compares their performance
        across all metrics to determine the best model for the task.

        Args:
            task_type: Type of task to benchmark (supervisor, agent, synthesis)
            model_ids: List of model identifiers to compare
            dataset_name: Name of dataset to use for comparison

        Returns:
            ComparisonResults with winner by metric and recommendation

        Example:
            ```python
            comparison = await benchmark.compare_models(
                task_type="supervisor",
                model_ids=["gemini-2.5-flash", "gpt-4o-mini", "claude-sonnet-4-20250514"],
                dataset_name="supervisor_golden_v1",
            )
            print(comparison.recommendation)
            ```
        """
        logger.info(
            "comparison_starting",
            task_type=task_type,
            model_count=len(model_ids),
            dataset_name=dataset_name,
        )

        # Get default evaluators for task type
        evaluators = self._get_default_evaluators(task_type)

        # Run experiments for each model
        experiments: list[ExperimentResults] = []
        for model_id in model_ids:
            try:
                result = await self.run_experiment(
                    task_type=task_type,
                    model_id=model_id,
                    dataset_name=dataset_name,
                    evaluators=evaluators,
                    experiment_prefix=f"compare_{task_type}",
                )
                experiments.append(result)
            except Exception as e:
                logger.error(
                    "model_experiment_failed",
                    model_id=model_id,
                    task_type=task_type,
                    error=str(e),
                )
                # Continue with other models
                continue

        if not experiments:
            msg = "All experiments failed"
            raise RuntimeError(msg)

        # Determine winners by metric
        winner_by_metric = self._find_winners_by_metric(experiments)

        # Calculate cost savings
        cost_savings = self._calculate_cost_savings(experiments)

        # Generate recommendation
        recommendation = self._generate_recommendation(
            experiments, winner_by_metric, task_type, cost_savings
        )

        result = ComparisonResults(
            experiments=experiments,
            winner_by_metric=winner_by_metric,
            recommendation=recommendation,
            task_type=task_type,
            cost_savings=cost_savings,
        )

        logger.info(
            "comparison_complete",
            task_type=task_type,
            winner_by_metric=winner_by_metric,
            recommendation=recommendation,
            cost_savings=cost_savings,
        )

        return result

    def _get_target_function(self, task_type: TaskType, model_id: str) -> Callable:
        """Get target function for specific task type.

        The target function wraps the actual task logic and handles
        model configuration for benchmarking.

        Args:
            task_type: Type of task (supervisor, agent, synthesis)
            model_id: Model identifier to use

        Returns:
            Async callable that takes inputs dict and returns outputs dict
        """
        if task_type == "supervisor":
            return self._create_supervisor_target(model_id)
        elif task_type == "agent":
            return self._create_agent_target(model_id)
        elif task_type == "synthesis":
            return self._create_synthesis_target(model_id)
        else:
            msg = f"Unknown task type: {task_type}"
            raise ValueError(msg)

    def _create_supervisor_target(self, model_id: str) -> Callable:
        """Create target function for supervisor routing task.

        Args:
            model_id: Model to use for supervisor

        Returns:
            Callable that invokes supervisor with given model
        """
        # Capture model_id in closure - supervisor_route now accepts model_id parameter

        async def supervisor_target(inputs: dict[str, Any]) -> dict[str, Any]:
            """Invoke supervisor routing logic.

            Args:
                inputs: Dict with 'content' and 'content_type' keys

            Returns:
                Dict with 'selected_agents' list
            """
            content = inputs.get("content", "")
            content_type = inputs.get("content_type", "article")
            analysis_id = inputs.get("analysis_id", "benchmark")

            # Invoke supervisor with runtime model selection
            result = await supervisor_route(content, content_type, analysis_id, model_id=model_id)

            # Extract agent selection
            supervisor_decision = result.get("supervisor_decision", {})
            selected_agents = supervisor_decision.get("agents", [])

            return {
                "selected_agents": selected_agents,
                "confidence": supervisor_decision.get("confidence", 0.0),
                "reasoning": supervisor_decision.get("reasoning", ""),
            }

        return supervisor_target

    def _create_agent_target(self, model_id: str) -> Callable:
        """Create target function for agent analysis task.

        Args:
            model_id: Model to use for agent

        Returns:
            Callable that invokes agent with given model
        """

        async def agent_target(inputs: dict[str, Any]) -> dict[str, Any]:
            """Invoke agent analysis logic.

            Args:
                inputs: Dict with 'content', 'agent_type', and 'content_type' keys

            Returns:
                Dict with agent analysis output
            """
            content = inputs.get("content", "")
            agent_type = inputs.get("agent_type", "tech_comparator")
            content_type = inputs.get("content_type", "article")

            # Build minimal state for agent
            state: AnalysisState = {
                "analysis_id": "benchmark",
                "url": "https://example.com",
                "content_type": content_type,
                "skill_level": "intermediate",
                "raw_content": content,
                "extraction_metadata": {},
                "supervisor_decision": {"agents": [agent_type]},
            }

            # Configure model
            original_model = settings.LLM_MODEL
            try:
                settings.LLM_MODEL = model_id

                # Invoke agent (use tech_comparator as example)
                # In real implementation, would route to correct agent based on agent_type
                result = await tech_comparator_node(state)

                # Extract findings
                agent_findings = result.get("agent_findings", [])
                finding = agent_findings[0] if agent_findings else {}

                return {
                    "findings": finding.get("findings", []),
                    "confidence": finding.get("confidence", 0.0),
                }
            finally:
                settings.LLM_MODEL = original_model

        return agent_target

    def _create_synthesis_target(self, model_id: str) -> Callable:
        """Create target function for synthesis/aggregation task.

        Args:
            model_id: Model to use for synthesis

        Returns:
            Callable that invokes synthesis with given model
        """

        async def synthesis_target(inputs: dict[str, Any]) -> dict[str, Any]:
            """Invoke synthesis/aggregation logic.

            Args:
                inputs: Dict with 'agent_findings' list

            Returns:
                Dict with aggregated insights
            """
            agent_findings = inputs.get("agent_findings", [])

            # Build minimal state
            state: AnalysisState = {
                "analysis_id": "benchmark",
                "url": "https://example.com",
                "content_type": "article",
                "skill_level": "intermediate",
                "raw_content": "",
                "extraction_metadata": {},
                "agent_findings": agent_findings,
            }

            # Configure model
            original_model = settings.LLM_MODEL
            try:
                settings.LLM_MODEL = model_id

                # Invoke aggregation
                result = await aggregate_findings(state)

                # Extract insights
                aggregated = result.get("aggregated_insights", {})

                return {
                    "summary": aggregated.get("summary", ""),
                    "key_points": aggregated.get("key_points", []),
                    "coverage_score": aggregated.get("coverage_score", 0.0),
                }
            finally:
                settings.LLM_MODEL = original_model

        return synthesis_target

    def _get_default_evaluators(self, task_type: TaskType) -> list[Callable]:
        """Get default evaluators for a task type.

        Args:
            task_type: Type of task

        Returns:
            List of evaluator callables
        """
        # Import evaluators dynamically to avoid circular imports
        from app.evaluation.evaluators import (
            cost_evaluator,
            latency_evaluator,
        )

        # Base evaluators for all tasks
        evaluators: list[Callable] = [
            latency_evaluator,
            cost_evaluator,
        ]

        # Add task-specific correctness evaluators when available
        try:
            if task_type == "supervisor":
                from app.evaluation.evaluators import supervisor_correctness_evaluator

                evaluators.append(supervisor_correctness_evaluator)
            elif task_type == "agent":
                from app.evaluation.evaluators import agent_correctness_evaluator

                evaluators.append(agent_correctness_evaluator)
            elif task_type == "synthesis":
                from app.evaluation.evaluators import synthesis_correctness_evaluator

                evaluators.append(synthesis_correctness_evaluator)
        except ImportError:
            logger.warning(
                "correctness_evaluator_not_found",
                task_type=task_type,
                message="Using only latency and cost evaluators",
            )

        return evaluators

    def _extract_metrics(self, experiment_results: Any) -> dict[str, float]:
        """Extract metrics from LangSmith experiment results.

        Args:
            experiment_results: Results object from client.evaluate()

        Returns:
            Dictionary of metric_name -> value
        """
        metrics: dict[str, float] = {}

        # LangSmith returns aggregate statistics
        # Extract key metrics (exact structure depends on LangSmith version)
        try:
            # Get aggregate scores if available
            if hasattr(experiment_results, "aggregate_scores"):
                for metric_name, metric_value in experiment_results.aggregate_scores.items():
                    if isinstance(metric_value, (int, float)):
                        metrics[metric_name] = float(metric_value)

            # Calculate averages from individual runs if needed
            if hasattr(experiment_results, "results"):
                # Aggregate metrics from runs
                latencies = []
                costs = []

                for run in experiment_results.results:
                    if hasattr(run, "execution_time"):
                        latencies.append(run.execution_time)
                    if hasattr(run, "cost"):
                        costs.append(run.cost)

                if latencies:
                    metrics["latency_p50"] = sorted(latencies)[len(latencies) // 2]
                    metrics["latency_avg"] = sum(latencies) / len(latencies)

                if costs:
                    metrics["cost_total"] = sum(costs)
                    metrics["cost_avg"] = sum(costs) / len(costs)

        except Exception as e:
            logger.warning("metrics_extraction_failed", error=str(e))

        return metrics

    async def _run_local_experiment(
        self,
        target_fn: Callable,
        dataset: list[dict[str, Any]],
        evaluators: list[Callable],
        model_id: str,
        model_info: Any,
        task_type: str,
    ) -> dict[str, float]:
        """Run experiment locally without LangSmith dataset sync.

        This mode runs the target function on each example and collects
        metrics using simplified evaluators.

        Args:
            target_fn: Target function to evaluate
            dataset: List of examples from golden dataset
            evaluators: List of evaluator functions
            model_id: Model identifier
            model_info: Model info from registry
            task_type: Type of task

        Returns:
            Dictionary of aggregated metrics
        """
        from uuid import uuid4
        from langsmith.schemas import Run as LSRun, Example as LSExample

        all_scores: dict[str, list[float]] = {}
        latencies: list[float] = []
        total_cost = 0.0

        logger.info(
            "local_experiment_starting",
            model_id=model_id,
            task_type=task_type,
            example_count=len(dataset),
        )

        for i, example in enumerate(dataset):
            inputs = example.get("inputs", {})
            reference_outputs = example.get("outputs", {})

            # Run target function and measure latency
            example_start = time.time()
            try:
                # Check if target_fn is async
                if asyncio.iscoroutinefunction(target_fn):
                    outputs = await target_fn(inputs)
                else:
                    outputs = target_fn(inputs)
            except Exception as e:
                logger.warning(
                    "local_example_failed",
                    example_index=i,
                    error=str(e),
                )
                continue

            example_latency = (time.time() - example_start) * 1000  # ms
            latencies.append(example_latency)

            # Estimate cost based on approximate token counts
            # Rough estimation: 4 chars = 1 token
            input_chars = len(str(inputs))
            output_chars = len(str(outputs))
            input_tokens = input_chars // 4
            output_tokens = output_chars // 4
            example_cost = model_info.estimate_cost(input_tokens, output_tokens)
            total_cost += example_cost

            # Create mock Run and Example for evaluators
            run_id = uuid4()
            example_id = uuid4()

            mock_run = LSRun(
                id=run_id,
                name=f"local_{task_type}_{i}",
                run_type="chain",
                inputs=inputs,
                outputs=outputs,
                start_time=datetime.now(),
                end_time=datetime.now(),
                extra={"model_id": model_id},
                trace_id=run_id,
            )

            mock_example = LSExample(
                id=example_id,
                dataset_id=example_id,
                inputs=inputs,
                outputs=reference_outputs,
            )

            # Run evaluators
            for evaluator in evaluators:
                try:
                    # Check evaluator signature
                    import inspect
                    sig = inspect.signature(evaluator)
                    params = list(sig.parameters.keys())

                    if "run" in params and "example" in params:
                        # LangSmith-style evaluator
                        result = evaluator(mock_run, mock_example)
                    elif len(params) >= 3:
                        # Simple (inputs, outputs, reference_outputs) style
                        result = evaluator(inputs, outputs, reference_outputs)
                    else:
                        continue

                    # Handle async evaluators
                    if asyncio.iscoroutine(result):
                        result = await result

                    # Extract score
                    if isinstance(result, dict) and "score" in result:
                        key = result.get("key", "unknown")
                        score = result["score"]
                        if key not in all_scores:
                            all_scores[key] = []
                        all_scores[key].append(float(score))

                except Exception as e:
                    logger.warning(
                        "evaluator_failed",
                        evaluator=evaluator.__name__,
                        error=str(e),
                    )

            if (i + 1) % 5 == 0:
                logger.info(
                    "local_experiment_progress",
                    completed=i + 1,
                    total=len(dataset),
                )

        # Aggregate metrics
        metrics: dict[str, float] = {}

        # Add evaluator scores (averaged)
        for key, scores in all_scores.items():
            if scores:
                metrics[key] = sum(scores) / len(scores)

        # Add latency metrics
        if latencies:
            sorted_latencies = sorted(latencies)
            metrics["latency_ms"] = sum(latencies) / len(latencies)
            metrics["latency_p50"] = sorted_latencies[len(sorted_latencies) // 2]
            metrics["latency_p95"] = sorted_latencies[int(len(sorted_latencies) * 0.95)]

        # Add cost metrics
        metrics["cost_total"] = total_cost
        metrics["cost_avg"] = total_cost / len(dataset) if dataset else 0

        logger.info(
            "local_experiment_complete",
            model_id=model_id,
            task_type=task_type,
            metrics=metrics,
        )

        return metrics

    def _find_winners_by_metric(
        self, experiments: list[ExperimentResults]
    ) -> dict[str, str]:
        """Find winning model for each metric.

        Args:
            experiments: List of experiment results

        Returns:
            Dictionary mapping metric_name -> winning model_id
        """
        winners: dict[str, str] = {}

        # Get all metric names
        all_metrics = set()
        for exp in experiments:
            all_metrics.update(exp.metrics.keys())

        # For each metric, find best model
        for metric_name in all_metrics:
            # Determine if higher or lower is better
            lower_is_better = metric_name.startswith(("latency", "cost"))

            best_value = None
            best_model = None

            for exp in experiments:
                if metric_name not in exp.metrics:
                    continue

                value = exp.metrics[metric_name]

                if best_value is None:
                    best_value = value
                    best_model = exp.model_id
                elif lower_is_better and value < best_value:
                    best_value = value
                    best_model = exp.model_id
                elif not lower_is_better and value > best_value:
                    best_value = value
                    best_model = exp.model_id

            if best_model:
                winners[metric_name] = best_model

        return winners

    def _calculate_cost_savings(
        self, experiments: list[ExperimentResults]
    ) -> dict[str, float]:
        """Calculate cost savings between models.

        Args:
            experiments: List of experiment results

        Returns:
            Dictionary with cost comparison metrics
        """
        cost_savings = {}

        # Find model with lowest cost
        costs = {
            exp.model_id: exp.metrics.get("cost_total", float("inf"))
            for exp in experiments
            if "cost_total" in exp.metrics
        }

        if len(costs) < 2:
            return {}

        min_cost_model = min(costs, key=costs.get)  # type: ignore[arg-type]
        min_cost = costs[min_cost_model]

        # Calculate savings vs each model
        for model_id, cost in costs.items():
            if model_id != min_cost_model:
                savings_pct = ((cost - min_cost) / cost) * 100
                cost_savings[f"{model_id}_vs_{min_cost_model}"] = savings_pct

        return cost_savings

    def _generate_recommendation(
        self,
        experiments: list[ExperimentResults],
        winners: dict[str, str],
        task_type: str,
        cost_savings: dict[str, float],
    ) -> str:
        """Generate human-readable recommendation.

        Args:
            experiments: List of experiment results
            winners: Dictionary of winners by metric
            task_type: Type of task
            cost_savings: Cost savings percentages

        Returns:
            Recommendation string
        """
        # Count wins per model
        win_counts: dict[str, int] = {}
        for winner in winners.values():
            win_counts[winner] = win_counts.get(winner, 0) + 1

        # Find overall winner (most metrics won)
        overall_winner = max(win_counts, key=win_counts.get) if win_counts else None  # type: ignore[arg-type]

        if not overall_winner:
            return "Insufficient data to make recommendation"

        # Get model info
        model_info = MODEL_REGISTRY.get(overall_winner)
        if not model_info:
            return f"Recommended: {overall_winner} (won {win_counts[overall_winner]} metrics)"

        # Build recommendation
        rec_parts = [
            f"Recommended for {task_type}: {model_info.display_name} ({overall_winner})",
            f"Won {win_counts[overall_winner]}/{len(winners)} metrics tested",
        ]

        # Add cost info
        accuracy_winner = winners.get("accuracy")
        cost_winner = winners.get("cost_total")

        if cost_winner and cost_winner != overall_winner:
            # Overall winner is not cheapest
            rec_parts.append(
                f"Note: {cost_winner} is cheaper but {overall_winner} offers better overall performance"
            )
        elif accuracy_winner and accuracy_winner == overall_winner:
            rec_parts.append("Best accuracy with competitive cost")

        # Add specific cost savings
        if cost_savings:
            max_savings_key = max(cost_savings, key=cost_savings.get)  # type: ignore[arg-type]
            max_savings = cost_savings[max_savings_key]
            rec_parts.append(f"Up to {max_savings:.1f}% cost savings vs alternatives")

        return ". ".join(rec_parts)
