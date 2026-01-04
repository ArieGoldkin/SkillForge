"""Unit tests for evaluation pipeline runner module.

Tests cover:
- EvaluationResult: status calculation, serialization
- PipelineResult: JSON/Markdown export, overall status aggregation
- Edge cases: empty results, all failures, mixed results
"""

import json

import pytest

from app.evaluation.pipeline.runner import (
    EvaluationResult,
    EvaluationRunner,
    PipelineResult,
)
from app.evaluation.pipeline.thresholds import Difficulty, ThresholdStatus


@pytest.mark.unit
class TestEvaluationResult:
    """Tests for EvaluationResult dataclass."""

    def test_status_calculated_on_init_pass(self):
        """Test status is automatically calculated as PASS when metrics meet thresholds."""
        # Trivial difficulty: recall>=0.95, mrr>=0.90, ndcg>=0.92
        result = EvaluationResult(
            difficulty=Difficulty.TRIVIAL,
            recall_at_5=0.96,
            mrr=0.91,
            ndcg_at_5=0.93,
            examples_evaluated=10,
            examples_passed=10,
            failed_example_ids=[],
            execution_time_seconds=1.5,
        )
        assert result.status == ThresholdStatus.PASS

    def test_status_calculated_on_init_warn(self):
        """Test status is WARN when metrics in warning margin (5% below threshold)."""
        # Easy difficulty: recall>=0.85, mrr>=0.80, ndcg>=0.82
        # Warning margin: 0.80 <= recall < 0.85
        result = EvaluationResult(
            difficulty=Difficulty.EASY,
            recall_at_5=0.82,  # In warning margin
            mrr=0.81,
            ndcg_at_5=0.83,
            examples_evaluated=10,
            examples_passed=8,
            failed_example_ids=["q1", "q2"],
            execution_time_seconds=2.0,
        )
        assert result.status == ThresholdStatus.WARN

    def test_status_calculated_on_init_fail(self):
        """Test status is FAIL when any metric below warning margin."""
        # Medium difficulty: recall>=0.75, mrr>=0.70, ndcg>=0.72
        result = EvaluationResult(
            difficulty=Difficulty.MEDIUM,
            recall_at_5=0.65,  # Below 0.75 - 0.05 = 0.70
            mrr=0.72,
            ndcg_at_5=0.74,
            examples_evaluated=10,
            examples_passed=5,
            failed_example_ids=["q1", "q2", "q3", "q4", "q5"],
            execution_time_seconds=2.5,
        )
        assert result.status == ThresholdStatus.FAIL

    def test_to_dict_serialization(self):
        """Test to_dict() converts result to serializable dictionary."""
        result = EvaluationResult(
            difficulty=Difficulty.HARD,
            recall_at_5=0.67,
            mrr=0.62,
            ndcg_at_5=0.64,
            examples_evaluated=8,
            examples_passed=6,
            failed_example_ids=["q7", "q8"],
            execution_time_seconds=3.2,
        )

        data = result.to_dict()

        assert data == {
            "difficulty": "hard",
            "recall_at_5": 0.67,
            "mrr": 0.62,
            "ndcg_at_5": 0.64,
            "examples_evaluated": 8,
            "examples_passed": 6,
            "failed_example_ids": ["q7", "q8"],
            "execution_time_seconds": 3.2,
            "status": "pass",
        }

    def test_adversarial_difficulty_thresholds(self):
        """Test adversarial difficulty has lower thresholds."""
        # Adversarial: recall>=0.50, mrr>=0.45, ndcg>=0.48
        result = EvaluationResult(
            difficulty=Difficulty.ADVERSARIAL,
            recall_at_5=0.52,
            mrr=0.47,
            ndcg_at_5=0.50,
            examples_evaluated=20,
            examples_passed=12,
            failed_example_ids=["adv1", "adv2", "adv3", "adv4", "adv5", "adv6", "adv7", "adv8"],
            execution_time_seconds=5.0,
        )
        assert result.status == ThresholdStatus.PASS


class TestPipelineResult:
    """Tests for PipelineResult dataclass."""

    def test_to_json_format(self):
        """Test to_json() produces valid JSON with expected structure."""
        result1 = EvaluationResult(
            difficulty=Difficulty.EASY,
            recall_at_5=0.86,
            mrr=0.81,
            ndcg_at_5=0.83,
            examples_evaluated=10,
            examples_passed=9,
            failed_example_ids=["q5"],
            execution_time_seconds=2.0,
        )
        result2 = EvaluationResult(
            difficulty=Difficulty.MEDIUM,
            recall_at_5=0.76,
            mrr=0.71,
            ndcg_at_5=0.73,
            examples_evaluated=10,
            examples_passed=8,
            failed_example_ids=["q3", "q7"],
            execution_time_seconds=2.5,
        )

        pipeline = PipelineResult(
            results={Difficulty.EASY: result1, Difficulty.MEDIUM: result2},
            total_examples=20,
            total_passed=17,
            overall_status=ThresholdStatus.PASS,
            execution_time_seconds=4.5,
            timestamp="2025-12-11T10:00:00Z",
        )

        json_str = pipeline.to_json()
        data = json.loads(json_str)

        assert data["overall_status"] == "pass"
        assert data["total_examples"] == 20
        assert data["total_passed"] == 17
        assert data["execution_time_seconds"] == 4.5
        assert data["timestamp"] == "2025-12-11T10:00:00Z"
        assert "easy" in data["results"]
        assert "medium" in data["results"]
        assert data["results"]["easy"]["recall_at_5"] == 0.86
        assert data["results"]["medium"]["examples_passed"] == 8

    def test_to_markdown_structure(self):
        """Test to_markdown() generates properly formatted markdown table."""
        result = EvaluationResult(
            difficulty=Difficulty.TRIVIAL,
            recall_at_5=0.96,
            mrr=0.91,
            ndcg_at_5=0.93,
            examples_evaluated=5,
            examples_passed=5,
            failed_example_ids=[],
            execution_time_seconds=1.0,
        )

        pipeline = PipelineResult(
            results={Difficulty.TRIVIAL: result},
            total_examples=5,
            total_passed=5,
            overall_status=ThresholdStatus.PASS,
            execution_time_seconds=1.0,
            timestamp="2025-12-11T10:00:00Z",
        )

        markdown = pipeline.to_markdown()

        # Check structure
        assert "# Evaluation Pipeline Results" in markdown
        assert "**Overall Status**: ✅ PASS" in markdown
        assert "**Total Examples**: 5/5 passed (100.0%)" in markdown
        assert "**Execution Time**: 1.0s" in markdown
        assert "**Timestamp**: 2025-12-11T10:00:00Z" in markdown
        assert "## Results by Difficulty" in markdown
        assert "| Difficulty | Recall@5 | MRR | NDCG@5 | Examples | Passed | Status |" in markdown
        assert "trivial" in markdown.lower()

    def test_to_markdown_with_failed_examples(self):
        """Test markdown includes failed examples section when present."""
        result = EvaluationResult(
            difficulty=Difficulty.HARD,
            recall_at_5=0.60,
            mrr=0.55,
            ndcg_at_5=0.58,
            examples_evaluated=10,
            examples_passed=6,
            failed_example_ids=["q1", "q4", "q7", "q9"],
            execution_time_seconds=3.0,
        )

        pipeline = PipelineResult(
            results={Difficulty.HARD: result},
            total_examples=10,
            total_passed=6,
            overall_status=ThresholdStatus.FAIL,
            execution_time_seconds=3.0,
        )

        markdown = pipeline.to_markdown()

        assert "## Failed Examples" in markdown
        assert "| Difficulty | Example ID |" in markdown
        assert "| hard | q1 |" in markdown
        assert "| hard | q4 |" in markdown
        assert "| hard | q7 |" in markdown
        assert "| hard | q9 |" in markdown

    def test_overall_status_fail_if_any_fail(self):
        """Test overall status is FAIL if any difficulty FAILS."""
        result_pass = EvaluationResult(
            difficulty=Difficulty.EASY,
            recall_at_5=0.86,
            mrr=0.81,
            ndcg_at_5=0.83,
            examples_evaluated=10,
            examples_passed=9,
            failed_example_ids=["q5"],
            execution_time_seconds=2.0,
        )
        result_fail = EvaluationResult(
            difficulty=Difficulty.MEDIUM,
            recall_at_5=0.60,  # Below threshold
            mrr=0.71,
            ndcg_at_5=0.73,
            examples_evaluated=10,
            examples_passed=5,
            failed_example_ids=["q1", "q2", "q3", "q4", "q5"],
            execution_time_seconds=2.5,
        )

        pipeline = PipelineResult(
            results={Difficulty.EASY: result_pass, Difficulty.MEDIUM: result_fail},
            total_examples=20,
            total_passed=14,
            overall_status=ThresholdStatus.FAIL,  # Worst status
            execution_time_seconds=4.5,
        )

        assert pipeline.overall_status == ThresholdStatus.FAIL

    def test_overall_status_warn_if_any_warn_no_fail(self):
        """Test overall status is WARN if any difficulty WARNS and none FAIL."""
        result_pass = EvaluationResult(
            difficulty=Difficulty.EASY,
            recall_at_5=0.86,
            mrr=0.81,
            ndcg_at_5=0.83,
            examples_evaluated=10,
            examples_passed=9,
            failed_example_ids=["q5"],
            execution_time_seconds=2.0,
        )
        result_warn = EvaluationResult(
            difficulty=Difficulty.MEDIUM,
            recall_at_5=0.72,  # In warning margin (0.70-0.75)
            mrr=0.71,
            ndcg_at_5=0.73,
            examples_evaluated=10,
            examples_passed=7,
            failed_example_ids=["q2", "q4", "q9"],
            execution_time_seconds=2.5,
        )

        pipeline = PipelineResult(
            results={Difficulty.EASY: result_pass, Difficulty.MEDIUM: result_warn},
            total_examples=20,
            total_passed=16,
            overall_status=ThresholdStatus.WARN,  # Worst status
            execution_time_seconds=4.5,
        )

        assert pipeline.overall_status == ThresholdStatus.WARN

    def test_overall_status_pass_if_all_pass(self):
        """Test overall status is PASS if all difficulties PASS."""
        result1 = EvaluationResult(
            difficulty=Difficulty.EASY,
            recall_at_5=0.86,
            mrr=0.81,
            ndcg_at_5=0.83,
            examples_evaluated=10,
            examples_passed=9,
            failed_example_ids=["q5"],
            execution_time_seconds=2.0,
        )
        result2 = EvaluationResult(
            difficulty=Difficulty.MEDIUM,
            recall_at_5=0.76,
            mrr=0.71,
            ndcg_at_5=0.73,
            examples_evaluated=10,
            examples_passed=8,
            failed_example_ids=["q3", "q7"],
            execution_time_seconds=2.5,
        )

        pipeline = PipelineResult(
            results={Difficulty.EASY: result1, Difficulty.MEDIUM: result2},
            total_examples=20,
            total_passed=17,
            overall_status=ThresholdStatus.PASS,
            execution_time_seconds=4.5,
        )

        assert pipeline.overall_status == ThresholdStatus.PASS

    def test_pass_rate_calculation(self):
        """Test _pass_rate() helper calculates correct percentage."""
        result = EvaluationResult(
            difficulty=Difficulty.EASY,
            recall_at_5=0.86,
            mrr=0.81,
            ndcg_at_5=0.83,
            examples_evaluated=10,
            examples_passed=8,
            failed_example_ids=["q3", "q7"],
            execution_time_seconds=2.0,
        )

        pipeline = PipelineResult(
            results={Difficulty.EASY: result},
            total_examples=10,
            total_passed=8,
            overall_status=ThresholdStatus.PASS,
            execution_time_seconds=2.0,
        )

        assert pipeline._pass_rate() == 80.0

    def test_pass_rate_zero_examples(self):
        """Test _pass_rate() returns 0.0 when no examples evaluated."""
        pipeline = PipelineResult(
            results={},
            total_examples=0,
            total_passed=0,
            overall_status=ThresholdStatus.PASS,
            execution_time_seconds=0.0,
        )

        assert pipeline._pass_rate() == 0.0

    def test_status_emoji_mapping(self):
        """Test _status_emoji() returns correct emoji for each status."""
        pipeline = PipelineResult(
            results={},
            total_examples=0,
            total_passed=0,
            overall_status=ThresholdStatus.PASS,
            execution_time_seconds=0.0,
        )

        assert pipeline._status_emoji(ThresholdStatus.PASS) == "✅"
        assert pipeline._status_emoji(ThresholdStatus.WARN) == "⚠️"
        assert pipeline._status_emoji(ThresholdStatus.FAIL) == "❌"


class TestPipelineRunner:
    """Tests for EvaluationRunner class.

    Tests the core runner functionality including metrics computation,
    fixtures loading, and threshold checking.
    """

    def test_compute_metrics_perfect_recall(self):
        """Test _compute_metrics with perfect recall (all expected found in top-k)."""
        from unittest.mock import MagicMock

        runner = MagicMock()
        runner._compute_metrics = EvaluationRunner._compute_metrics.__get__(runner)

        retrieved = ["doc1", "doc2", "doc3", "doc4", "doc5"]
        expected = ["doc1", "doc3"]

        metrics = runner._compute_metrics(retrieved, expected, k=5)

        assert metrics["recall"] == 1.0  # 2/2 found
        assert metrics["mrr"] == 1.0  # First relevant at position 1
        assert metrics["ndcg"] > 0.8  # High NDCG since relevant docs are at top

    def test_compute_metrics_partial_recall(self):
        """Test _compute_metrics with partial recall."""
        from unittest.mock import MagicMock

        runner = MagicMock()
        runner._compute_metrics = EvaluationRunner._compute_metrics.__get__(runner)

        retrieved = ["doc1", "doc2", "doc3", "doc4", "doc5"]
        expected = ["doc3", "doc6", "doc7", "doc8"]

        metrics = runner._compute_metrics(retrieved, expected, k=5)

        assert metrics["recall"] == 0.25  # 1/4 found
        assert metrics["mrr"] == 1 / 3  # First relevant at position 3
        assert metrics["ndcg"] < 0.5  # Low NDCG since only 1 hit

    def test_compute_metrics_no_hits(self):
        """Test _compute_metrics with no relevant documents found."""
        from unittest.mock import MagicMock

        runner = MagicMock()
        runner._compute_metrics = EvaluationRunner._compute_metrics.__get__(runner)

        retrieved = ["doc1", "doc2", "doc3", "doc4", "doc5"]
        expected = ["doc10", "doc11"]

        metrics = runner._compute_metrics(retrieved, expected, k=5)

        assert metrics["recall"] == 0.0
        assert metrics["mrr"] == 0.0
        assert metrics["ndcg"] == 0.0

    def test_compute_metrics_empty_expected(self):
        """Test _compute_metrics with no expected documents (trivially satisfied)."""
        from unittest.mock import MagicMock

        runner = MagicMock()
        runner._compute_metrics = EvaluationRunner._compute_metrics.__get__(runner)

        retrieved = ["doc1", "doc2", "doc3"]
        expected: list[str] = []

        metrics = runner._compute_metrics(retrieved, expected, k=5)

        assert metrics["recall"] == 1.0  # Trivially satisfied
        assert metrics["mrr"] == 0.0  # No relevant docs to find
        assert metrics["ndcg"] == 1.0  # Perfect NDCG (no relevant docs)

    def test_run_from_fixtures_loads_queries(self, tmp_path):
        """Test run_from_fixtures correctly loads queries.json."""
        import asyncio
        from unittest.mock import AsyncMock, MagicMock

        # Create mock queries file
        queries_file = tmp_path / "queries.json"
        queries_data = {
            "version": "1.0",
            "queries": [
                {
                    "id": "q1",
                    "query": "test query",
                    "difficulty": "easy",
                    "expected_chunks": ["chunk1"],
                    "min_score": 0.5,
                }
            ],
        }
        queries_file.write_text(json.dumps(queries_data))

        # Create mock runner
        mock_session = MagicMock()
        mock_embedding_service = MagicMock()
        mock_search_service = MagicMock()
        mock_search_service.search = AsyncMock(return_value=[])

        runner = EvaluationRunner(
            session=mock_session,
            embedding_service=mock_embedding_service,
            search_service=mock_search_service,
        )

        # Run with mocked search (will return empty results)
        async def run_test():
            return await runner.run_from_fixtures(
                fixtures_dir=tmp_path,
                difficulties=[Difficulty.EASY],
            )

        result = asyncio.get_event_loop().run_until_complete(run_test())

        assert len(runner._queries) == 1
        assert runner._queries[0]["id"] == "q1"
        assert Difficulty.EASY in result.results

    def test_run_from_fixtures_missing_file_raises(self, tmp_path):
        """Test run_from_fixtures raises FileNotFoundError for missing queries.json."""
        import asyncio
        from unittest.mock import MagicMock

        mock_session = MagicMock()
        mock_embedding_service = MagicMock()
        mock_search_service = MagicMock()

        runner = EvaluationRunner(
            session=mock_session,
            embedding_service=mock_embedding_service,
            search_service=mock_search_service,
        )

        async def run_test():
            await runner.run_from_fixtures(fixtures_dir=tmp_path)

        with pytest.raises(FileNotFoundError):
            asyncio.get_event_loop().run_until_complete(run_test())

    def test_runner_init_with_raw_mode_flags(self):
        """Test EvaluationRunner correctly stores use_hyde and use_rerank flags."""
        from unittest.mock import MagicMock

        mock_session = MagicMock()
        mock_embedding_service = MagicMock()
        mock_embedding_service.model = "test-model"
        mock_embedding_service.expected_dimensions = 768
        mock_search_service = MagicMock()

        # Test with all flags disabled (raw mode)
        runner = EvaluationRunner(
            session=mock_session,
            embedding_service=mock_embedding_service,
            search_service=mock_search_service,
            use_hyde=False,
            use_rerank=False,
            max_parallel=10,
        )

        assert runner.use_hyde is False
        assert runner.use_rerank is False
        assert runner.max_parallel == 10

    def test_runner_init_defaults_to_full_mode(self):
        """Test EvaluationRunner defaults to full HyDE and reranking enabled."""
        from unittest.mock import MagicMock

        mock_session = MagicMock()
        mock_embedding_service = MagicMock()
        mock_embedding_service.model = "test-model"
        mock_embedding_service.expected_dimensions = 768
        mock_search_service = MagicMock()

        runner = EvaluationRunner(
            session=mock_session,
            embedding_service=mock_embedding_service,
            search_service=mock_search_service,
        )

        assert runner.use_hyde is True
        assert runner.use_rerank is True
        assert runner.max_parallel == 1  # Sequential by default

    def test_runner_max_parallel_clamped_to_minimum(self):
        """Test max_parallel is clamped to at least 1."""
        from unittest.mock import MagicMock

        mock_session = MagicMock()
        mock_embedding_service = MagicMock()
        mock_embedding_service.model = "test-model"
        mock_embedding_service.expected_dimensions = 768
        mock_search_service = MagicMock()

        runner = EvaluationRunner(
            session=mock_session,
            embedding_service=mock_embedding_service,
            search_service=mock_search_service,
            max_parallel=0,  # Invalid value
        )

        assert runner.max_parallel == 1  # Should be clamped to 1

        runner = EvaluationRunner(
            session=mock_session,
            embedding_service=mock_embedding_service,
            search_service=mock_search_service,
            max_parallel=-5,  # Negative value
        )

        assert runner.max_parallel == 1  # Should be clamped to 1
