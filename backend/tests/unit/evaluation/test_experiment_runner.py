"""Unit tests for ExperimentRunner (Issue #428).

Tests the CI/CD experiment automation module that orchestrates:
1. Fetching datasets from Langfuse
2. Running evaluator functions in parallel
3. Logging results back to Langfuse
4. Collecting comprehensive statistics

Test Coverage:
- Successful experiment runs with all items passing
- Partial failures (some items fail, others succeed)
- Empty datasets
- Dataset not found errors
- Experiment creation failures
- Parallel execution with configurable concurrency
- Result aggregation and statistics
- Error collection and reporting
"""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from app.core.langfuse_client import LangfuseClient, LangfuseClientError
from app.evaluation.experiment_runner import (
    ExperimentRunner,
    ExperimentRunResult,
    ExperimentSummary,
)


@pytest.fixture
def mock_langfuse_client() -> MagicMock:
    """Create a mock LangfuseClient for testing."""
    client = MagicMock(spec=LangfuseClient)

    # Default mock behaviors
    client.get_dataset = AsyncMock(return_value={"id": "dataset-123", "name": "test-dataset"})
    client.get_dataset_items = AsyncMock(return_value=[])
    client.create_experiment = AsyncMock(
        return_value={"id": "experiment-456", "name": "test-experiment"}
    )
    client.log_experiment_run = AsyncMock(return_value=True)

    return client


@pytest.fixture
def sample_dataset_items() -> list[dict[str, Any]]:
    """Create sample dataset items for testing."""
    return [
        {
            "id": "item-1",
            "input": {"query": "What is Python?"},
            "expected_output": "A programming language",
        },
        {
            "id": "item-2",
            "input": {"query": "What is FastAPI?"},
            "expected_output": "A web framework",
        },
        {
            "id": "item-3",
            "input": {"query": "What is asyncio?"},
            "expected_output": "Async programming library",
        },
    ]


@pytest.fixture
async def successful_evaluator() -> Any:
    """Create a successful evaluator function."""

    async def evaluator(item: dict[str, Any]) -> dict[str, Any]:
        """Return successful evaluation result."""
        return {
            "output": f"Answer to: {item['input']['query']}",
            "scores": {"accuracy": 0.95, "relevance": 0.88},
        }

    return evaluator


@pytest.fixture
async def failing_evaluator() -> Any:
    """Create an evaluator that always fails."""

    async def evaluator(item: dict[str, Any]) -> dict[str, Any]:
        """Raise an evaluation exception."""
        raise ValueError("Evaluation failed")

    return evaluator


@pytest.mark.asyncio
class TestExperimentRunner:
    """Test suite for ExperimentRunner."""

    async def test_run_experiment_success(
        self,
        mock_langfuse_client: MagicMock,
        sample_dataset_items: list[dict[str, Any]],
        successful_evaluator: Any,
    ) -> None:
        """Test successful experiment run with all items passing."""
        # Setup mock to return dataset items
        mock_langfuse_client.get_dataset_items.return_value = sample_dataset_items

        runner = ExperimentRunner(mock_langfuse_client)

        # Run experiment
        summary = await runner.run_experiment(
            dataset_name="test-dataset",
            experiment_name="test-experiment",
            evaluator_fn=successful_evaluator,
            max_parallel=2,
        )

        # Verify summary
        assert isinstance(summary, ExperimentSummary)
        assert summary.dataset_name == "test-dataset"
        assert summary.experiment_name == "test-experiment"
        assert summary.total_items == 3
        assert summary.successful_runs == 3
        assert summary.failed_runs == 0
        assert summary.success_rate == 1.0
        assert "accuracy" in summary.average_scores
        assert "relevance" in summary.average_scores
        assert summary.average_scores["accuracy"] == pytest.approx(0.95)
        assert summary.average_scores["relevance"] == pytest.approx(0.88)

        # Verify Langfuse API calls
        mock_langfuse_client.get_dataset.assert_called_once_with("test-dataset")
        mock_langfuse_client.create_experiment.assert_called_once()
        assert mock_langfuse_client.log_experiment_run.call_count == 3

    async def test_run_experiment_partial_failure(
        self,
        mock_langfuse_client: MagicMock,
        sample_dataset_items: list[dict[str, Any]],
    ) -> None:
        """Test experiment run with some items failing."""
        mock_langfuse_client.get_dataset_items.return_value = sample_dataset_items

        call_count = 0

        async def partial_failing_evaluator(item: dict[str, Any]) -> dict[str, Any]:
            """Fail on every other item for testing."""
            nonlocal call_count
            call_count += 1

            if call_count % 2 == 0:
                msg = f"Failed on item {call_count}"
                raise ValueError(msg)

            return {
                "output": f"Success on item {call_count}",
                "scores": {"accuracy": 0.9},
            }

        runner = ExperimentRunner(mock_langfuse_client)

        summary = await runner.run_experiment(
            dataset_name="test-dataset",
            experiment_name="partial-failure-test",
            evaluator_fn=partial_failing_evaluator,
            max_parallel=1,
        )

        # Verify partial success
        assert summary.total_items == 3
        assert summary.successful_runs == 2  # Items 1 and 3 succeed
        assert summary.failed_runs == 1  # Item 2 fails
        assert summary.success_rate == pytest.approx(2 / 3)
        assert len(summary.errors) == 1
        assert "Failed on item 2" in summary.errors[0]

        # Only successful runs should be logged
        assert mock_langfuse_client.log_experiment_run.call_count == 2

    async def test_run_experiment_all_failures(
        self,
        mock_langfuse_client: MagicMock,
        sample_dataset_items: list[dict[str, Any]],
        failing_evaluator: Any,
    ) -> None:
        """Test experiment run where all items fail."""
        mock_langfuse_client.get_dataset_items.return_value = sample_dataset_items

        runner = ExperimentRunner(mock_langfuse_client)

        summary = await runner.run_experiment(
            dataset_name="test-dataset",
            experiment_name="all-failures-test",
            evaluator_fn=failing_evaluator,
            max_parallel=2,
        )

        # Verify all failures
        assert summary.total_items == 3
        assert summary.successful_runs == 0
        assert summary.failed_runs == 3
        assert summary.success_rate == 0.0
        assert len(summary.errors) == 3
        assert all("Evaluation failed" in error for error in summary.errors)

        # No successful runs to log
        mock_langfuse_client.log_experiment_run.assert_not_called()

    async def test_run_experiment_empty_dataset(
        self,
        mock_langfuse_client: MagicMock,
    ) -> None:
        """Test experiment run on empty dataset."""
        mock_langfuse_client.get_dataset_items.return_value = []

        async def dummy_evaluator(item: dict[str, Any]) -> dict[str, Any]:
            return {"output": "test", "scores": {}}

        runner = ExperimentRunner(mock_langfuse_client)

        summary = await runner.run_experiment(
            dataset_name="empty-dataset",
            experiment_name="empty-test",
            evaluator_fn=dummy_evaluator,
        )

        # Verify empty results
        assert summary.total_items == 0
        assert summary.successful_runs == 0
        assert summary.failed_runs == 0
        assert summary.success_rate == 0.0
        assert summary.average_scores == {}

    async def test_run_experiment_dataset_not_found(
        self,
        mock_langfuse_client: MagicMock,
    ) -> None:
        """Test experiment run when dataset doesn't exist."""
        mock_langfuse_client.get_dataset.return_value = None

        async def dummy_evaluator(item: dict[str, Any]) -> dict[str, Any]:
            return {"output": "test", "scores": {}}

        runner = ExperimentRunner(mock_langfuse_client)

        # Should raise LangfuseClientError
        with pytest.raises(LangfuseClientError, match="not found"):
            await runner.run_experiment(
                dataset_name="nonexistent-dataset",
                experiment_name="test",
                evaluator_fn=dummy_evaluator,
            )

    async def test_run_experiment_creation_failure(
        self,
        mock_langfuse_client: MagicMock,
        sample_dataset_items: list[dict[str, Any]],
        successful_evaluator: Any,
    ) -> None:
        """Test experiment run when experiment creation fails."""
        mock_langfuse_client.get_dataset_items.return_value = sample_dataset_items
        mock_langfuse_client.create_experiment.return_value = None  # Creation fails

        runner = ExperimentRunner(mock_langfuse_client)

        # Should continue without experiment tracking
        summary = await runner.run_experiment(
            dataset_name="test-dataset",
            experiment_name="test-experiment",
            evaluator_fn=successful_evaluator,
        )

        # Verify it still processes items
        assert summary.total_items == 3
        assert summary.successful_runs == 3
        assert summary.experiment_id is None  # No experiment ID

    async def test_run_experiment_parallel_execution(
        self,
        mock_langfuse_client: MagicMock,
        successful_evaluator: Any,
    ) -> None:
        """Test parallel execution respects max_parallel limit."""
        # Create 10 items
        items = [{"id": f"item-{i}", "input": {"query": f"Query {i}"}} for i in range(10)]
        mock_langfuse_client.get_dataset_items.return_value = items

        runner = ExperimentRunner(mock_langfuse_client)

        summary = await runner.run_experiment(
            dataset_name="test-dataset",
            experiment_name="parallel-test",
            evaluator_fn=successful_evaluator,
            max_parallel=3,  # Limit to 3 parallel executions
        )

        # Verify all items were processed
        assert summary.total_items == 10
        assert summary.successful_runs == 10
        assert summary.items_per_second > 0

    async def test_run_experiment_with_metadata(
        self,
        mock_langfuse_client: MagicMock,
        sample_dataset_items: list[dict[str, Any]],
        successful_evaluator: Any,
    ) -> None:
        """Test experiment run with description and metadata."""
        mock_langfuse_client.get_dataset_items.return_value = sample_dataset_items

        runner = ExperimentRunner(mock_langfuse_client)

        description = "Test experiment with metadata"
        metadata = {"version": "2.0", "environment": "test"}

        await runner.run_experiment(
            dataset_name="test-dataset",
            experiment_name="metadata-test",
            evaluator_fn=successful_evaluator,
            description=description,
            metadata=metadata,
        )

        # Verify experiment was created with metadata
        create_call = mock_langfuse_client.create_experiment.call_args
        assert create_call.kwargs["name"] == "metadata-test"
        assert create_call.kwargs["dataset_name"] == "test-dataset"
        assert create_call.kwargs["description"] == description
        assert create_call.kwargs["metadata"] == metadata

    async def test_run_experiment_score_aggregation(
        self,
        mock_langfuse_client: MagicMock,
        sample_dataset_items: list[dict[str, Any]],
    ) -> None:
        """Test score aggregation across multiple items."""
        mock_langfuse_client.get_dataset_items.return_value = sample_dataset_items

        item_scores = [
            {"accuracy": 0.9, "relevance": 0.8},
            {"accuracy": 0.95, "relevance": 0.85},
            {"accuracy": 0.85, "relevance": 0.9},
        ]

        call_count = 0

        async def varying_scores_evaluator(item: dict[str, Any]) -> dict[str, Any]:
            """Return varying scores for testing aggregation."""
            nonlocal call_count
            scores = item_scores[call_count]
            call_count += 1

            return {"output": "test", "scores": scores}

        runner = ExperimentRunner(mock_langfuse_client)

        summary = await runner.run_experiment(
            dataset_name="test-dataset",
            experiment_name="score-aggregation-test",
            evaluator_fn=varying_scores_evaluator,
        )

        # Verify score averages
        assert summary.average_scores["accuracy"] == pytest.approx(0.9)
        assert summary.average_scores["relevance"] == pytest.approx(0.85)

    async def test_run_experiment_pagination(
        self,
        mock_langfuse_client: MagicMock,
        successful_evaluator: Any,
    ) -> None:
        """Test pagination when fetching dataset items."""
        # Create enough items to trigger pagination (page_size is 100)
        # Page 1: 100 items (triggers next page fetch)
        # Page 2: 50 items (stops pagination since < page_size)
        page1_items = [{"id": f"item-{i}", "input": {"query": f"Query {i}"}} for i in range(100)]
        page2_items = [
            {"id": f"item-{i}", "input": {"query": f"Query {i}"}} for i in range(100, 150)
        ]

        # Mock paginated responses
        async def paginated_get_items(
            dataset_name: str, limit: int = 100, page: int = 1
        ) -> list[dict[str, Any]]:
            if page == 1:
                return page1_items
            elif page == 2:
                return page2_items
            return []

        mock_langfuse_client.get_dataset_items.side_effect = paginated_get_items

        runner = ExperimentRunner(mock_langfuse_client)

        summary = await runner.run_experiment(
            dataset_name="test-dataset",
            experiment_name="pagination-test",
            evaluator_fn=successful_evaluator,
        )

        # Verify all items from both pages were processed
        assert summary.total_items == 150
        assert summary.successful_runs == 150

    async def test_run_experiment_logging_failure_continues(
        self,
        mock_langfuse_client: MagicMock,
        sample_dataset_items: list[dict[str, Any]],
        successful_evaluator: Any,
    ) -> None:
        """Test that logging failures don't stop experiment execution."""
        mock_langfuse_client.get_dataset_items.return_value = sample_dataset_items

        # Make logging fail for some items
        log_call_count = 0

        async def failing_log(*args: Any, **kwargs: Any) -> bool:
            nonlocal log_call_count
            log_call_count += 1
            if log_call_count == 2:
                msg = "Logging failed"
                raise RuntimeError(msg)
            return True

        mock_langfuse_client.log_experiment_run.side_effect = failing_log

        runner = ExperimentRunner(mock_langfuse_client)

        # Should complete despite logging failure
        summary = await runner.run_experiment(
            dataset_name="test-dataset",
            experiment_name="logging-failure-test",
            evaluator_fn=successful_evaluator,
        )

        # Verify execution completed
        assert summary.total_items == 3
        assert summary.successful_runs == 3

    async def test_experiment_run_result_success_property(self) -> None:
        """Test ExperimentRunResult.success property."""
        # Successful result
        success_result = ExperimentRunResult(
            dataset_item_id="item-1",
            success=True,
            trace_id=str(uuid4()),
            duration_ms=100.0,
            output="test output",
            scores={"accuracy": 0.9},
        )
        assert success_result.success is True

        # Failed result
        failed_result = ExperimentRunResult(
            dataset_item_id="item-2",
            success=False,
            trace_id=str(uuid4()),
            duration_ms=50.0,
            error="Test error",
        )
        assert failed_result.success is False

    async def test_experiment_summary_success_rate_calculation(self) -> None:
        """Test ExperimentSummary success_rate calculation."""
        # 100% success
        summary_full = ExperimentSummary(
            experiment_id="exp-1",
            dataset_name="test",
            experiment_name="test-exp",
            total_items=10,
            successful_runs=10,
            failed_runs=0,
            success_rate=1.0,
            average_scores={},
            total_duration_ms=1000.0,
            items_per_second=10.0,
        )
        assert summary_full.success_rate == 1.0

        # 50% success
        summary_half = ExperimentSummary(
            experiment_id="exp-2",
            dataset_name="test",
            experiment_name="test-exp",
            total_items=10,
            successful_runs=5,
            failed_runs=5,
            success_rate=0.5,
            average_scores={},
            total_duration_ms=1000.0,
            items_per_second=10.0,
        )
        assert summary_half.success_rate == 0.5

        # 0% success
        summary_zero = ExperimentSummary(
            experiment_id="exp-3",
            dataset_name="test",
            experiment_name="test-exp",
            total_items=10,
            successful_runs=0,
            failed_runs=10,
            success_rate=0.0,
            average_scores={},
            total_duration_ms=1000.0,
            items_per_second=10.0,
        )
        assert summary_zero.success_rate == 0.0

    async def test_run_experiment_evaluator_type_error(
        self,
        mock_langfuse_client: MagicMock,
        sample_dataset_items: list[dict[str, Any]],
    ) -> None:
        """Test handling of evaluator returning wrong type."""
        mock_langfuse_client.get_dataset_items.return_value = sample_dataset_items

        async def bad_evaluator(item: dict[str, Any]) -> Any:
            """Return wrong type to test error handling."""
            return "not a dict"  # Should return dict

        runner = ExperimentRunner(mock_langfuse_client)

        summary = await runner.run_experiment(
            dataset_name="test-dataset",
            experiment_name="type-error-test",
            evaluator_fn=bad_evaluator,
        )

        # Should handle gracefully as failures
        assert summary.total_items == 3
        assert summary.successful_runs == 0
        assert summary.failed_runs == 3
        assert all("must return dict" in error for error in summary.errors)
