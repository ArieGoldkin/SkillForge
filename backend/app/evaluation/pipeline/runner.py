"""Evaluation pipeline runner for CI/CD integration.

This module provides the main evaluation pipeline that:
1. Loads golden datasets by difficulty
2. Runs retrieval evaluation for each difficulty level
3. Checks metrics against thresholds
4. Generates pass/fail reports for CI/CD

Usage:
    ```python
    runner = EvaluationRunner(db_session, embedding_service)
    result = await runner.run_all()

    # Check if evaluation passed
    if result.overall_status != ThresholdStatus.PASS:
        print(f"Evaluation failed: {result.to_markdown()}")
        sys.exit(1)
    ```
"""

from __future__ import annotations

import json
import math
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Any

from app.core.logging import get_logger
from app.evaluation.pipeline.thresholds import (
    THRESHOLDS,
    Difficulty,
    ThresholdStatus,
    get_threshold,
)
from app.schemas.search import SearchMode

if TYPE_CHECKING:
    from collections.abc import Sequence

    from sqlalchemy.ext.asyncio import AsyncSession

    from app.services.embeddings.service import EmbeddingService
    from app.services.search.search_service import SearchService

logger = get_logger(__name__)


@dataclass
class EvaluationResult:
    """Results from evaluating a single difficulty level.

    Attributes:
        difficulty: Difficulty level evaluated
        recall_at_5: Measured Recall@5 (0-1)
        mrr: Measured Mean Reciprocal Rank (0-1)
        ndcg_at_5: Measured NDCG@5 (0-1)
        examples_evaluated: Total examples in dataset
        examples_passed: Examples that met thresholds
        failed_example_ids: IDs of examples that failed
        execution_time_seconds: Time to evaluate this difficulty
        status: Overall threshold status (PASS/WARN/FAIL)

    """

    difficulty: Difficulty
    recall_at_5: float
    mrr: float
    ndcg_at_5: float
    examples_evaluated: int
    examples_passed: int
    failed_example_ids: list[str]
    execution_time_seconds: float
    status: ThresholdStatus = ThresholdStatus.FAIL

    def __post_init__(self) -> None:
        """Compute status based on metrics and thresholds."""
        config = get_threshold(self.difficulty)
        self.status = config.overall_status(self.recall_at_5, self.mrr, self.ndcg_at_5)

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "difficulty": self.difficulty.value,
            "recall_at_5": self.recall_at_5,
            "mrr": self.mrr,
            "ndcg_at_5": self.ndcg_at_5,
            "examples_evaluated": self.examples_evaluated,
            "examples_passed": self.examples_passed,
            "failed_example_ids": self.failed_example_ids,
            "execution_time_seconds": self.execution_time_seconds,
            "status": self.status.value,
        }


@dataclass
class PipelineResult:
    """Results from full evaluation pipeline run.

    Attributes:
        results: Per-difficulty evaluation results
        total_examples: Total examples evaluated across all difficulties
        total_passed: Total examples that passed thresholds
        overall_status: Worst status across all difficulties (FAIL > WARN > PASS)
        execution_time_seconds: Total execution time
        timestamp: ISO timestamp of evaluation run

    """

    results: dict[Difficulty, EvaluationResult]
    total_examples: int
    total_passed: int
    overall_status: ThresholdStatus
    execution_time_seconds: float
    timestamp: str = field(
        default_factory=lambda: time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    )

    def to_json(self) -> str:
        """Serialize to JSON format.

        Returns:
            JSON string suitable for CI artifacts. Includes overall_status, metrics,
            execution_time_seconds, and per-difficulty results.
        """
        return json.dumps(
            {
                "overall_status": self.overall_status.value,
                "total_examples": self.total_examples,
                "total_passed": self.total_passed,
                "execution_time_seconds": self.execution_time_seconds,
                "timestamp": self.timestamp,
                "results": {diff.value: result.to_dict() for diff, result in self.results.items()},
            },
            indent=2,
        )

    def to_markdown(self) -> str:
        """Generate markdown report for PR comments.

        Returns:
            Formatted markdown table with results. Includes overall status,
            pass rate, execution time, and per-difficulty metrics table.
        """
        lines = [
            "# Evaluation Pipeline Results",
            "",
            f"**Overall Status**: {self._status_emoji(self.overall_status)} {self.overall_status.value.upper()}",
            f"**Total Examples**: {self.total_passed}/{self.total_examples} passed ({self._pass_rate():.1f}%)",
            f"**Execution Time**: {self.execution_time_seconds:.1f}s",
            f"**Timestamp**: {self.timestamp}",
            "",
            "## Results by Difficulty",
            "",
            "| Difficulty | Recall@5 | MRR | NDCG@5 | Examples | Passed | Status |",
            "|------------|----------|-----|--------|----------|--------|--------|",
        ]

        for difficulty in Difficulty:
            if difficulty in self.results:
                result = self.results[difficulty]
                config = THRESHOLDS[difficulty]
                lines.append(
                    f"| {difficulty.value:10} | "
                    f"{result.recall_at_5:.3f} (≥{config.recall_at_5:.2f}) | "
                    f"{result.mrr:.3f} (≥{config.mrr:.2f}) | "
                    f"{result.ndcg_at_5:.3f} (≥{config.ndcg_at_5:.2f}) | "
                    f"{result.examples_evaluated:3} | "
                    f"{result.examples_passed:3} | "
                    f"{self._status_emoji(result.status)} {result.status.value.upper()} |"
                )

        # Add failed examples if any
        failed_examples = []
        for result in self.results.values():
            if result.failed_example_ids:
                failed_examples.extend(
                    [(result.difficulty.value, ex_id) for ex_id in result.failed_example_ids]
                )

        if failed_examples:
            lines.extend(
                [
                    "",
                    "## Failed Examples",
                    "",
                    "| Difficulty | Example ID |",
                    "|------------|------------|",
                ]
            )
            for diff, ex_id in failed_examples:
                lines.append(f"| {diff} | {ex_id} |")

        return "\n".join(lines)

    def _status_emoji(self, status: ThresholdStatus) -> str:
        """Get emoji for status."""
        return {"pass": "✅", "warn": "⚠️", "fail": "❌"}[status.value]

    def _pass_rate(self) -> float:
        """Calculate overall pass rate percentage."""
        if self.total_examples == 0:
            return 0.0
        return (self.total_passed / self.total_examples) * 100


class EvaluationRunner:
    """Run evaluation pipeline across all difficulty levels.

    This class coordinates:
    - Loading evaluation datasets
    - Running retrieval for each query
    - Computing metrics
    - Checking thresholds
    - Generating reports
    """

    def __init__(
        self,
        session: AsyncSession,
        embedding_service: EmbeddingService,
        search_service: SearchService | None = None,
    ) -> None:
        """Initialize evaluation runner.

        Args:
            session: Database session for retrieval
            embedding_service: Service for generating query embeddings
            search_service: Optional search service (created if not provided)

        """
        self.session = session
        self.embedding_service = embedding_service

        if search_service is None:
            from app.services.search.search_service import SearchService

            search_service = SearchService(
                session=session,
                embedding_service=embedding_service,
            )

        self.search_service = search_service
        self._queries: list[dict[str, Any]] = []

    async def run_all(
        self,
        difficulties: list[Difficulty] | None = None,
    ) -> PipelineResult:
        """Run evaluation pipeline for all or specified difficulties.

        Args:
            difficulties: List of difficulties to evaluate (default: all)

        Returns:
            PipelineResult with aggregated metrics and status.
        """
        start_time = time.time()

        if difficulties is None:
            difficulties = list(Difficulty)

        results: dict[Difficulty, EvaluationResult] = {}
        total_examples = 0
        total_passed = 0
        worst_status = ThresholdStatus.PASS

        for difficulty in difficulties:
            logger.info(f"Evaluating difficulty: {difficulty.value}")
            result = await self._run_difficulty(difficulty)
            results[difficulty] = result

            total_examples += result.examples_evaluated
            total_passed += result.examples_passed

            # Track worst status
            if result.status == ThresholdStatus.FAIL:
                worst_status = ThresholdStatus.FAIL
            elif result.status == ThresholdStatus.WARN and worst_status != ThresholdStatus.FAIL:
                worst_status = ThresholdStatus.WARN

        execution_time = time.time() - start_time

        pipeline_result = PipelineResult(
            results=results,
            total_examples=total_examples,
            total_passed=total_passed,
            overall_status=worst_status,
            execution_time_seconds=execution_time,
        )

        logger.info(
            "Pipeline completed",
            status=worst_status.value,
            total_examples=total_examples,
            total_passed=total_passed,
            execution_time=f"{execution_time:.1f}s",
        )

        return pipeline_result

    async def _run_difficulty(self, difficulty: Difficulty) -> EvaluationResult:
        """Run evaluation for a single difficulty level.

        Loads examples from the configured queries, runs retrieval,
        and computes IR metrics (Recall@5, MRR, NDCG@5).

        Args:
            difficulty: Difficulty level to evaluate

        Returns:
            EvaluationResult with metrics and status

        """
        start_time = time.time()

        # Filter queries by difficulty
        queries = [q for q in self._queries if q.get("difficulty") == difficulty.value]

        if not queries:
            logger.warning(f"No queries found for difficulty: {difficulty.value}")
            config = get_threshold(difficulty)
            return EvaluationResult(
                difficulty=difficulty,
                recall_at_5=config.recall_at_5,  # Return threshold as "no data"
                mrr=config.mrr,
                ndcg_at_5=config.ndcg_at_5,
                examples_evaluated=0,
                examples_passed=0,
                failed_example_ids=[],
                execution_time_seconds=time.time() - start_time,
            )

        # Compute metrics for each query
        recalls: list[float] = []
        mrrs: list[float] = []
        ndcgs: list[float] = []
        failed_ids: list[str] = []
        passed_count = 0

        for query in queries:
            query_id = query.get("id", "unknown")
            query_text = query.get("query", "")
            expected_chunks = query.get("expected_chunks", [])
            min_score = query.get("min_score")

            try:
                # Run retrieval
                results = await self.search_service.search(
                    query=query_text,
                    top_k=5,
                    mode=SearchMode.HYBRID,
                )

                # Extract section IDs from path metadata for matching
                # Path is stored as ["doc_id", "section_id"], e.g., ["fastapi-auth", "fastapi-auth/intro"]
                # We use path[1] (section_id) to match against expected_chunks
                retrieved_ids = []
                for r in results:
                    if r.metadata.path and len(r.metadata.path) > 1:
                        retrieved_ids.append(r.metadata.path[1])
                    else:
                        # Fallback to chunk_id if path not available
                        retrieved_ids.append(r.chunk_id)

                # Compute metrics
                metrics = self._compute_metrics(retrieved_ids, expected_chunks, k=5)
                recalls.append(metrics["recall"])
                mrrs.append(metrics["mrr"])
                ndcgs.append(metrics["ndcg"])

                # Check if query passed (based on min_score if provided)
                query_passed = True
                if min_score is not None and results and results[0].score < min_score:
                    query_passed = False

                # Also check recall - must have at least one hit
                if metrics["recall"] == 0 and expected_chunks:
                    query_passed = False

                if query_passed:
                    passed_count += 1
                else:
                    failed_ids.append(query_id)

            except Exception as e:
                logger.error(f"Error evaluating query {query_id}: {e}")
                recalls.append(0.0)
                mrrs.append(0.0)
                ndcgs.append(0.0)
                failed_ids.append(query_id)

        # Aggregate metrics
        mean_recall = sum(recalls) / len(recalls) if recalls else 0.0
        mean_mrr = sum(mrrs) / len(mrrs) if mrrs else 0.0
        mean_ndcg = sum(ndcgs) / len(ndcgs) if ndcgs else 0.0

        result = EvaluationResult(
            difficulty=difficulty,
            recall_at_5=mean_recall,
            mrr=mean_mrr,
            ndcg_at_5=mean_ndcg,
            examples_evaluated=len(queries),
            examples_passed=passed_count,
            failed_example_ids=failed_ids,
            execution_time_seconds=time.time() - start_time,
        )

        logger.info(
            f"Evaluated {difficulty.value}",
            examples=len(queries),
            passed=passed_count,
            recall=f"{mean_recall:.3f}",
            mrr=f"{mean_mrr:.3f}",
            ndcg=f"{mean_ndcg:.3f}",
            status=result.status.value,
        )

        return result

    def _compute_metrics(
        self,
        retrieved_ids: Sequence[str],
        expected_ids: Sequence[str],
        k: int = 5,
    ) -> dict[str, float]:
        """Compute IR metrics for a single query.

        Args:
            retrieved_ids: Ordered list of retrieved chunk IDs
            expected_ids: Set of relevant chunk IDs (ground truth)
            k: Number of top results to consider

        Returns:
            Dict with recall, mrr, ndcg values

        """
        expected_set = set(expected_ids)
        top_k = list(retrieved_ids[:k])

        # Recall@k = |relevant ∩ retrieved@k| / |relevant|
        if not expected_set:
            recall = 1.0  # No expected = trivially satisfied
        else:
            hits = sum(1 for doc_id in top_k if doc_id in expected_set)
            recall = hits / len(expected_set)

        # MRR = 1 / rank_of_first_relevant
        mrr = 0.0
        for i, doc_id in enumerate(retrieved_ids, start=1):
            if doc_id in expected_set:
                mrr = 1.0 / i
                break

        # NDCG@k = DCG@k / IDCG@k (binary relevance)
        dcg = sum(
            1.0 / math.log2(i + 2) for i, doc_id in enumerate(top_k) if doc_id in expected_set
        )
        ideal_count = min(len(expected_set), k)
        idcg = sum(1.0 / math.log2(i + 2) for i in range(ideal_count))
        ndcg = dcg / idcg if idcg > 0 else (1.0 if dcg == 0 else 0.0)

        return {"recall": recall, "mrr": mrr, "ndcg": ndcg}

    async def run_from_fixtures(
        self,
        fixtures_dir: Path,
        difficulties: list[Difficulty] | None = None,
    ) -> PipelineResult:
        """Run evaluation using fixture files.

        Loads queries from queries.json in the fixtures directory and
        runs evaluation against the database.

        Args:
            fixtures_dir: Directory containing queries.json
            difficulties: List of difficulties to evaluate (default: all)

        Returns:
            PipelineResult with aggregated metrics

        """
        queries_path = fixtures_dir / "queries.json"
        if not queries_path.exists():
            msg = f"Queries file not found: {queries_path}"
            raise FileNotFoundError(msg)

        with queries_path.open() as f:
            data = json.load(f)

        # Extract queries (handle both flat list and wrapped format)
        if isinstance(data, dict) and "queries" in data:
            self._queries = data["queries"]
        elif isinstance(data, list):
            self._queries = data
        else:
            msg = "Invalid queries.json format"
            raise ValueError(msg)

        logger.info(f"Loaded {len(self._queries)} queries from {queries_path}")

        return await self.run_all(difficulties)
