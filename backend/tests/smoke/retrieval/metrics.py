"""Information Retrieval metrics for smoke tests.

Computes standard IR metrics to evaluate retrieval quality:
- Recall@k: Fraction of relevant documents retrieved in top-k
- MRR (Mean Reciprocal Rank): Average of 1/rank for first relevant result
- NDCG@k: Normalized Discounted Cumulative Gain
- Precision@k: Fraction of top-k results that are relevant
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Sequence


@dataclass
class RetrievalMetrics:
    """Container for computed retrieval metrics."""

    recall_at_k: float
    mrr: float
    ndcg_at_k: float
    precision_at_k: float
    hit_rate: float
    k: int
    retrieved_count: int
    relevant_count: int
    hits: list[str] = field(default_factory=list)
    misses: list[str] = field(default_factory=list)

    def passes_thresholds(
        self,
        min_recall: float | None = None,
        min_mrr: float | None = None,
        min_ndcg: float | None = None,
    ) -> bool:
        """Check if metrics meet minimum thresholds.

        Args:
            min_recall: Minimum acceptable Recall@k.
            min_mrr: Minimum acceptable MRR.
            min_ndcg: Minimum acceptable NDCG@k.

        Returns:
            True if all specified thresholds are met.

        """
        if min_recall is not None and self.recall_at_k < min_recall:
            return False
        if min_mrr is not None and self.mrr < min_mrr:
            return False
        return not (min_ndcg is not None and self.ndcg_at_k < min_ndcg)

    def summary(self) -> str:
        """Generate human-readable summary.

        Returns:
            Formatted string with all metrics.

        """
        return (
            f"Recall@{self.k}: {self.recall_at_k:.3f} | "
            f"MRR: {self.mrr:.3f} | "
            f"NDCG@{self.k}: {self.ndcg_at_k:.3f} | "
            f"Precision@{self.k}: {self.precision_at_k:.3f} | "
            f"Hits: {len(self.hits)}/{self.relevant_count}"
        )


class MetricsCalculator:
    """Calculate information retrieval metrics for search results."""

    def __init__(self, k: int = 5) -> None:
        """Initialize calculator with default k value.

        Args:
            k: Number of top results to consider for @k metrics.

        """
        self.k = k

    def compute(
        self,
        retrieved_ids: Sequence[str],
        expected_ids: Sequence[str],
        k: int | None = None,
    ) -> RetrievalMetrics:
        """Compute all retrieval metrics.

        Args:
            retrieved_ids: Ordered list of retrieved document/chunk IDs.
            expected_ids: Set of relevant document/chunk IDs (ground truth).
            k: Override default k value for this computation.

        Returns:
            RetrievalMetrics containing all computed values.

        """
        k = k or self.k
        expected_set = set(expected_ids)
        top_k = list(retrieved_ids[:k])

        # Compute individual metrics
        recall = self._recall_at_k(top_k, expected_set)
        mrr = self._mrr(retrieved_ids, expected_set)
        ndcg = self._ndcg_at_k(top_k, expected_set, k)
        precision = self._precision_at_k(top_k, expected_set)
        hit_rate = self._hit_rate(top_k, expected_set)

        # Track hits and misses
        hits = [rid for rid in top_k if rid in expected_set]
        misses = [eid for eid in expected_ids if eid not in set(top_k)]

        return RetrievalMetrics(
            recall_at_k=recall,
            mrr=mrr,
            ndcg_at_k=ndcg,
            precision_at_k=precision,
            hit_rate=hit_rate,
            k=k,
            retrieved_count=len(top_k),
            relevant_count=len(expected_ids),
            hits=hits,
            misses=misses,
        )

    def _recall_at_k(self, top_k: list[str], expected: set[str]) -> float:
        """Compute Recall@k.

        Recall@k = |relevant ∩ retrieved@k| / |relevant|

        Args:
            top_k: Top k retrieved document IDs.
            expected: Set of relevant document IDs.

        Returns:
            Recall value between 0 and 1.

        """
        if not expected:
            return 1.0  # No expected = trivially satisfied

        hits = sum(1 for doc_id in top_k if doc_id in expected)
        return hits / len(expected)

    def _precision_at_k(self, top_k: list[str], expected: set[str]) -> float:
        """Compute Precision@k.

        Precision@k = |relevant ∩ retrieved@k| / k

        Args:
            top_k: Top k retrieved document IDs.
            expected: Set of relevant document IDs.

        Returns:
            Precision value between 0 and 1.

        """
        if not top_k:
            return 0.0

        hits = sum(1 for doc_id in top_k if doc_id in expected)
        return hits / len(top_k)

    def _mrr(self, retrieved: Sequence[str], expected: set[str]) -> float:
        """Compute Mean Reciprocal Rank.

        MRR = 1 / rank_of_first_relevant

        Args:
            retrieved: Full ordered list of retrieved IDs.
            expected: Set of relevant document IDs.

        Returns:
            MRR value between 0 and 1.

        """
        for i, doc_id in enumerate(retrieved, start=1):
            if doc_id in expected:
                return 1.0 / i
        return 0.0

    def _ndcg_at_k(self, top_k: list[str], expected: set[str], k: int) -> float:
        """Compute Normalized Discounted Cumulative Gain at k.

        NDCG@k = DCG@k / IDCG@k

        Uses binary relevance (1 if relevant, 0 otherwise).

        Args:
            top_k: Top k retrieved document IDs.
            expected: Set of relevant document IDs.
            k: Number of results to consider.

        Returns:
            NDCG value between 0 and 1.

        """
        # Compute DCG (binary relevance)
        dcg = self._dcg(top_k, expected)

        # Compute ideal DCG (all relevant docs at top)
        ideal_count = min(len(expected), k)
        ideal_order = ["relevant"] * ideal_count
        idcg = self._dcg(ideal_order, {"relevant"})

        if idcg == 0:
            return 1.0 if dcg == 0 else 0.0

        return dcg / idcg

    def _dcg(self, ranked_items: Sequence[str], expected: set[str]) -> float:
        """Compute Discounted Cumulative Gain.

        DCG = Σ rel_i / log2(i + 1)

        Args:
            ranked_items: Ordered list of item IDs.
            expected: Set of relevant item IDs.

        Returns:
            DCG score.

        """
        dcg = 0.0
        for i, item_id in enumerate(ranked_items, start=1):
            if item_id in expected:
                # Binary relevance: 1 if relevant, 0 otherwise
                dcg += 1.0 / math.log2(i + 1)
        return dcg

    def _hit_rate(self, top_k: list[str], expected: set[str]) -> float:
        """Compute hit rate (any relevant doc in top-k).

        Args:
            top_k: Top k retrieved document IDs.
            expected: Set of relevant document IDs.

        Returns:
            1.0 if any hit, 0.0 otherwise.

        """
        return 1.0 if any(doc_id in expected for doc_id in top_k) else 0.0


@dataclass
class AggregateMetrics:
    """Aggregated metrics across multiple queries."""

    mean_recall: float
    mean_mrr: float
    mean_ndcg: float
    mean_precision: float
    mean_hit_rate: float
    query_count: int
    passed_count: int
    failed_count: int
    failed_queries: list[str] = field(default_factory=list)

    def summary(self) -> str:
        """Generate human-readable summary.

        Returns:
            Formatted string with aggregate metrics.

        """
        pass_rate = self.passed_count / self.query_count * 100 if self.query_count else 0
        return (
            f"Queries: {self.query_count} | "
            f"Passed: {self.passed_count} ({pass_rate:.1f}%) | "
            f"Mean Recall: {self.mean_recall:.3f} | "
            f"Mean MRR: {self.mean_mrr:.3f} | "
            f"Mean NDCG: {self.mean_ndcg:.3f}"
        )


def aggregate_metrics(
    results: list[tuple[str, RetrievalMetrics, bool]],
) -> AggregateMetrics:
    """Aggregate metrics across multiple queries.

    Args:
        results: List of (query_id, metrics, passed) tuples.

    Returns:
        AggregateMetrics with means and pass/fail counts.

    """
    if not results:
        return AggregateMetrics(
            mean_recall=0.0,
            mean_mrr=0.0,
            mean_ndcg=0.0,
            mean_precision=0.0,
            mean_hit_rate=0.0,
            query_count=0,
            passed_count=0,
            failed_count=0,
        )

    recalls = [m.recall_at_k for _, m, _ in results]
    mrrs = [m.mrr for _, m, _ in results]
    ndcgs = [m.ndcg_at_k for _, m, _ in results]
    precisions = [m.precision_at_k for _, m, _ in results]
    hit_rates = [m.hit_rate for _, m, _ in results]

    passed = [qid for qid, _, p in results if p]
    failed = [qid for qid, _, p in results if not p]

    return AggregateMetrics(
        mean_recall=sum(recalls) / len(recalls),
        mean_mrr=sum(mrrs) / len(mrrs),
        mean_ndcg=sum(ndcgs) / len(ndcgs),
        mean_precision=sum(precisions) / len(precisions),
        mean_hit_rate=sum(hit_rates) / len(hit_rates),
        query_count=len(results),
        passed_count=len(passed),
        failed_count=len(failed),
        failed_queries=failed,
    )
