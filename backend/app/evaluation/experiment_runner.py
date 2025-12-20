"""CI/CD Experiment Runner for Langfuse-First Architecture.

Issue #428 Phase 4.1: This module provides automated experiment execution
for CI/CD pipelines. It orchestrates running experiments on Langfuse datasets,
logging results, and collecting comprehensive statistics.

Key Features:
1. Async/await pattern for efficient parallel execution
2. Configurable parallelism with semaphore-based throttling
3. Graceful error handling with partial failure support
4. Progress logging with structlog integration
5. Comprehensive summary statistics
6. Full Langfuse experiment API integration

Architecture:
    ExperimentRunner takes a LangfuseClient instance and coordinates:
    1. Fetching dataset items from Langfuse
    2. Running custom evaluator functions in parallel
    3. Logging results back to Langfuse experiments
    4. Collecting success/failure statistics

Example Usage:
    ```python
    from app.core.langfuse_client import get_langfuse_api_client
    from app.evaluation.experiment_runner import ExperimentRunner


    async def my_evaluator(item: dict) -> dict:
        # Run your evaluation logic here
        input_data = item.get("input", {})
        expected_output = item.get("expected_output", {})

        # Your evaluation logic
        actual_output = await run_model(input_data)
        score = compute_accuracy(actual_output, expected_output)

        return {"output": actual_output, "scores": {"accuracy": score}}


    client = get_langfuse_api_client()
    runner = ExperimentRunner(client)

    results = await runner.run_experiment(
        dataset_name="golden-dataset",
        experiment_name="v2.0-quality-test",
        evaluator_fn=my_evaluator,
        max_parallel=10,
    )

    print(f"Success rate: {results['success_rate']:.1%}")
    print(f"Average scores: {results['average_scores']}")
    ```

Integration with CI/CD:
    This runner is designed for automated testing in CI/CD pipelines:
    - Returns comprehensive statistics for pass/fail decisions
    - Gracefully handles partial failures (don't fail entire pipeline)
    - Logs all errors for debugging
    - Supports configurable parallelism for different environments

"""

from __future__ import annotations

import asyncio
import time
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from typing import Any
from uuid import uuid4

from app.core.langfuse_client import LangfuseClient, LangfuseClientError
from app.core.logging import get_logger

logger = get_logger(__name__)


@dataclass
class ExperimentRunResult:
    """Result of processing a single dataset item.

    Attributes:
        dataset_item_id: ID of the dataset item
        success: Whether the evaluation succeeded
        output: Model output (if successful)
        scores: Evaluation scores (if successful)
        error: Error message (if failed)
        duration_ms: Processing duration in milliseconds
        trace_id: Langfuse trace ID for this run

    """

    dataset_item_id: str
    success: bool
    trace_id: str
    duration_ms: float
    output: str | dict[str, Any] | None = None
    scores: dict[str, float] | None = None
    error: str | None = None


@dataclass
class ExperimentSummary:
    """Summary statistics for an experiment run.

    Attributes:
        experiment_id: Langfuse experiment ID
        dataset_name: Dataset that was tested
        experiment_name: Name of the experiment
        total_items: Total number of dataset items
        successful_runs: Number of successful evaluations
        failed_runs: Number of failed evaluations
        success_rate: Percentage of successful runs (0-1)
        average_scores: Average of all scores across successful runs
        total_duration_ms: Total processing time in milliseconds
        items_per_second: Processing throughput
        errors: List of error messages from failed runs

    """

    experiment_id: str | None
    dataset_name: str
    experiment_name: str
    total_items: int
    successful_runs: int
    failed_runs: int
    success_rate: float
    average_scores: dict[str, float]
    total_duration_ms: float
    items_per_second: float
    errors: list[str] = field(default_factory=list)


class ExperimentRunner:
    """Automated experiment runner for Langfuse datasets.

    This class orchestrates running experiments on Langfuse datasets with:
    - Parallel execution for efficiency
    - Graceful error handling
    - Progress logging
    - Result aggregation and statistics

    The runner fetches dataset items, applies a custom evaluator function
    to each item in parallel, and logs the results back to Langfuse.

    Example:
        >>> client = LangfuseClient.from_env()
        >>> runner = ExperimentRunner(client)
        >>> async def evaluator(item):
        ...     return {"output": "test", "scores": {"accuracy": 0.95}}
        >>> summary = await runner.run_experiment(
        ...     dataset_name="test-dataset",
        ...     experiment_name="v1.0-test",
        ...     evaluator_fn=evaluator,
        ... )

    """

    def __init__(self, langfuse_client: LangfuseClient) -> None:
        """Initialize the experiment runner.

        Args:
            langfuse_client: Configured Langfuse API client

        """
        self._client = langfuse_client
        self._logger = logger.bind(component="experiment_runner")

    async def run_experiment(
        self,
        dataset_name: str,
        experiment_name: str,
        evaluator_fn: Callable[[dict[str, Any]], Awaitable[dict[str, Any]]],
        *,
        max_parallel: int = 5,
        description: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> ExperimentSummary:
        """Run an experiment on a Langfuse dataset.

        This is the main entry point for running experiments. It:
        1. Verifies the dataset exists in Langfuse
        2. Creates an experiment record
        3. Fetches all dataset items
        4. Processes items in parallel using the evaluator function
        5. Logs results to Langfuse
        6. Returns comprehensive statistics

        Args:
            dataset_name: Name of the dataset in Langfuse
            experiment_name: Name for this experiment run
            evaluator_fn: Async function that evaluates a dataset item.
                         Must accept dict and return dict with 'output' and optional 'scores'.
            max_parallel: Maximum number of parallel evaluations (default: 5)
            description: Optional experiment description
            metadata: Optional experiment metadata

        Returns:
            ExperimentSummary with statistics and results

        Raises:
            LangfuseClientError: If dataset doesn't exist or client is unavailable

        Example:
            >>> async def my_evaluator(item: dict) -> dict:
            ...     input_data = item["input"]
            ...     result = await process(input_data)
            ...     return {"output": result, "scores": {"accuracy": 0.9}}
            >>> summary = await runner.run_experiment(
            ...     "golden-dataset",
            ...     "v2.0-test",
            ...     my_evaluator,
            ...     max_parallel=10,
            ... )

        """
        start_time = time.monotonic()

        self._logger.info(
            "experiment_starting",
            dataset=dataset_name,
            experiment=experiment_name,
            max_parallel=max_parallel,
        )

        # Step 1: Verify dataset exists
        dataset = await self._client.get_dataset(dataset_name)
        if dataset is None:
            msg = f"Dataset '{dataset_name}' not found in Langfuse"
            self._logger.error("dataset_not_found", dataset=dataset_name)
            raise LangfuseClientError(msg)

        # Step 2: Create experiment
        experiment_data = await self._client.create_experiment(
            name=experiment_name,
            dataset_name=dataset_name,
            description=description,
            metadata=metadata,
        )

        experiment_id = experiment_data.get("id") if experiment_data else None

        if experiment_id is None:
            self._logger.warning(
                "experiment_creation_failed",
                experiment=experiment_name,
                message="Continuing without experiment tracking",
            )

        # Step 3: Fetch all dataset items
        all_items = await self._fetch_all_dataset_items(dataset_name)

        if not all_items:
            self._logger.warning(
                "no_dataset_items",
                dataset=dataset_name,
                message="Dataset is empty, no items to process",
            )
            return ExperimentSummary(
                experiment_id=experiment_id,
                dataset_name=dataset_name,
                experiment_name=experiment_name,
                total_items=0,
                successful_runs=0,
                failed_runs=0,
                success_rate=0.0,
                average_scores={},
                total_duration_ms=0.0,
                items_per_second=0.0,
            )

        self._logger.info(
            "dataset_items_fetched",
            dataset=dataset_name,
            total_items=len(all_items),
        )

        # Step 4: Process items in parallel
        results = await self._process_items_parallel(
            items=all_items,
            evaluator_fn=evaluator_fn,
            max_parallel=max_parallel,
        )

        # Step 5: Log results to Langfuse (if experiment was created)
        if experiment_id:
            await self._log_results_to_langfuse(
                experiment_id=experiment_id,
                results=results,
            )

        # Step 6: Compute summary statistics
        total_duration = (time.monotonic() - start_time) * 1000  # ms
        summary = self._compute_summary(
            experiment_id=experiment_id,
            dataset_name=dataset_name,
            experiment_name=experiment_name,
            results=results,
            total_duration_ms=total_duration,
        )

        self._logger.info(
            "experiment_completed",
            experiment=experiment_name,
            total_items=summary.total_items,
            successful=summary.successful_runs,
            failed=summary.failed_runs,
            success_rate=f"{summary.success_rate:.1%}",
            duration_ms=round(summary.total_duration_ms, 2),
        )

        return summary

    async def _fetch_all_dataset_items(
        self,
        dataset_name: str,
        page_size: int = 100,
    ) -> list[dict[str, Any]]:
        """Fetch all items from a dataset with pagination.

        Args:
            dataset_name: Name of the dataset
            page_size: Items per page (default: 100)

        Returns:
            List of all dataset items

        """
        all_items: list[dict[str, Any]] = []
        page = 1

        while True:
            items = await self._client.get_dataset_items(
                dataset_name,
                limit=page_size,
                page=page,
            )

            if not items:
                break

            all_items.extend(items)

            self._logger.debug(
                "dataset_page_fetched",
                dataset=dataset_name,
                page=page,
                items_count=len(items),
                total_so_far=len(all_items),
            )

            # If we got fewer items than page_size, we're done
            if len(items) < page_size:
                break

            page += 1

        return all_items

    async def _process_items_parallel(
        self,
        items: list[dict[str, Any]],
        evaluator_fn: Callable[[dict[str, Any]], Awaitable[dict[str, Any]]],
        max_parallel: int,
    ) -> list[ExperimentRunResult]:
        """Process dataset items in parallel with throttling.

        Uses asyncio.Semaphore to limit concurrency and prevent overwhelming
        the system with too many parallel evaluations.

        Args:
            items: List of dataset items to process
            evaluator_fn: Async evaluator function
            max_parallel: Maximum concurrent evaluations

        Returns:
            List of ExperimentRunResult for all items

        """
        semaphore = asyncio.Semaphore(max_parallel)
        tasks = [self._process_single_item(item, evaluator_fn, semaphore) for item in items]

        self._logger.info(
            "processing_items",
            total_items=len(items),
            max_parallel=max_parallel,
        )

        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Handle any unexpected exceptions from gather
        processed_results: list[ExperimentRunResult] = []
        for i, result in enumerate(results):
            if isinstance(result, BaseException):
                # This shouldn't happen (we catch in _process_single_item),
                # but handle it gracefully just in case
                self._logger.error(
                    "unexpected_processing_error",
                    item_index=i,
                    error=str(result),
                )
                processed_results.append(
                    ExperimentRunResult(
                        dataset_item_id=items[i].get("id", f"unknown-{i}"),
                        success=False,
                        trace_id=str(uuid4()),
                        duration_ms=0.0,
                        error=f"Unexpected error: {result}",
                    )
                )
            elif isinstance(result, ExperimentRunResult):
                processed_results.append(result)
            else:
                # This case shouldn't happen but type checker needs it
                self._logger.error(
                    "unexpected_result_type",
                    item_index=i,
                    result_type=type(result).__name__,
                )

        return processed_results

    async def _process_single_item(
        self,
        item: dict[str, Any],
        evaluator_fn: Callable[[dict[str, Any]], Awaitable[dict[str, Any]]],
        semaphore: asyncio.Semaphore,
    ) -> ExperimentRunResult:
        """Process a single dataset item with semaphore throttling.

        Args:
            item: Dataset item to process
            evaluator_fn: Async evaluator function
            semaphore: Semaphore for throttling

        Returns:
            ExperimentRunResult with outcome

        """
        item_id = item.get("id", str(uuid4()))
        trace_id = str(uuid4())
        start_time = time.monotonic()

        async with semaphore:
            try:
                self._logger.debug("processing_item", item_id=item_id)

                # Call the evaluator function
                result = await evaluator_fn(item)

                duration_ms = (time.monotonic() - start_time) * 1000

                # Validate result format
                if not isinstance(result, dict):
                    msg = f"Evaluator must return dict, got {type(result)}"
                    raise TypeError(msg)

                output = result.get("output")
                scores = result.get("scores", {})

                self._logger.debug(
                    "item_processed_successfully",
                    item_id=item_id,
                    duration_ms=round(duration_ms, 2),
                    scores=scores,
                )

                return ExperimentRunResult(
                    dataset_item_id=item_id,
                    success=True,
                    trace_id=trace_id,
                    output=output,
                    scores=scores,
                    duration_ms=duration_ms,
                )

            except Exception as e:
                duration_ms = (time.monotonic() - start_time) * 1000

                self._logger.error(
                    "item_processing_failed",
                    item_id=item_id,
                    error=str(e),
                    error_type=type(e).__name__,
                    duration_ms=round(duration_ms, 2),
                )

                return ExperimentRunResult(
                    dataset_item_id=item_id,
                    success=False,
                    trace_id=trace_id,
                    error=str(e),
                    duration_ms=duration_ms,
                )

    async def _log_results_to_langfuse(
        self,
        experiment_id: str,
        results: list[ExperimentRunResult],
    ) -> None:
        """Log all experiment results to Langfuse.

        Logs both successful and failed runs. Failures in logging don't
        affect the overall experiment (we log errors but continue).

        Args:
            experiment_id: Langfuse experiment ID
            results: List of all experiment run results

        """
        self._logger.info(
            "logging_results_to_langfuse",
            experiment_id=experiment_id,
            total_results=len(results),
        )

        successful_logs = 0
        failed_logs = 0

        for result in results:
            # Only log successful evaluations to Langfuse
            # (Failed evaluations don't have valid output/scores)
            if not result.success:
                continue

            try:
                logged = await self._client.log_experiment_run(
                    experiment_id=experiment_id,
                    dataset_item_id=result.dataset_item_id,
                    trace_id=result.trace_id,
                    output=result.output or "",
                    scores=result.scores,
                )

                if logged:
                    successful_logs += 1
                else:
                    failed_logs += 1
                    self._logger.warning(
                        "failed_to_log_run",
                        item_id=result.dataset_item_id,
                        trace_id=result.trace_id,
                    )

            except Exception as e:
                failed_logs += 1
                self._logger.error(
                    "error_logging_run",
                    item_id=result.dataset_item_id,
                    error=str(e),
                )

        self._logger.info(
            "results_logged",
            experiment_id=experiment_id,
            successful=successful_logs,
            failed=failed_logs,
        )

    def _compute_summary(
        self,
        experiment_id: str | None,
        dataset_name: str,
        experiment_name: str,
        results: list[ExperimentRunResult],
        total_duration_ms: float,
    ) -> ExperimentSummary:
        """Compute summary statistics from experiment results.

        Args:
            experiment_id: Langfuse experiment ID (None if creation failed)
            dataset_name: Dataset name
            experiment_name: Experiment name
            results: List of all results
            total_duration_ms: Total processing time in ms

        Returns:
            ExperimentSummary with aggregated statistics

        """
        total_items = len(results)
        successful_runs = sum(1 for r in results if r.success)
        failed_runs = total_items - successful_runs
        success_rate = successful_runs / total_items if total_items > 0 else 0.0

        # Aggregate scores from successful runs
        score_sums: dict[str, float] = {}
        score_counts: dict[str, int] = {}

        for result in results:
            if result.success and result.scores:
                for score_name, score_value in result.scores.items():
                    score_sums[score_name] = score_sums.get(score_name, 0.0) + score_value
                    score_counts[score_name] = score_counts.get(score_name, 0) + 1

        average_scores = {name: score_sums[name] / score_counts[name] for name in score_sums}

        # Collect error messages
        errors = [r.error for r in results if r.error is not None]

        items_per_second = (
            total_items / (total_duration_ms / 1000) if total_duration_ms > 0 else 0.0
        )

        return ExperimentSummary(
            experiment_id=experiment_id,
            dataset_name=dataset_name,
            experiment_name=experiment_name,
            total_items=total_items,
            successful_runs=successful_runs,
            failed_runs=failed_runs,
            success_rate=success_rate,
            average_scores=average_scores,
            total_duration_ms=total_duration_ms,
            items_per_second=items_per_second,
            errors=errors,
        )
