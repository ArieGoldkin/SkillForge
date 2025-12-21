"""Threshold configuration for evaluation quality gates.

This module defines quality thresholds for retrieval evaluation metrics across
different difficulty levels. Thresholds are used in CI/CD pipelines to:
- Pass/Warn/Fail PRs based on evaluation results
- Detect regressions in retrieval quality
- Enforce minimum quality standards

Difficulty-Specific Thresholds:
- trivial: 95% recall, 0.90 MRR, 0.92 NDCG
- easy: 85% recall, 0.80 MRR, 0.82 NDCG
- medium: 75% recall, 0.70 MRR, 0.72 NDCG
- hard: 65% recall, 0.60 MRR, 0.62 NDCG
- adversarial: 50% recall, 0.45 MRR, 0.48 NDCG

Warning Margin: 5% below threshold triggers warning (not failure)
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class ThresholdStatus(str, Enum):
    """Status from threshold check.

    PASS: Metrics exceed thresholds
    WARN: Metrics in warning margin (threshold - warning_margin)
    FAIL: Metrics below warning margin
    """

    PASS = "pass"  # noqa: S105
    WARN = "warn"
    FAIL = "fail"


class Difficulty(str, Enum):
    """Difficulty levels for evaluation queries.

    Maps to metadata.difficulty in evaluation datasets v2.0.
    """

    TRIVIAL = "trivial"
    EASY = "easy"
    MEDIUM = "medium"
    HARD = "hard"
    ADVERSARIAL = "adversarial"


@dataclass
class ThresholdConfig:
    """Threshold configuration for a single difficulty level.

    Attributes:
        recall_at_5: Minimum acceptable Recall@5 (0-1)
        mrr: Minimum acceptable Mean Reciprocal Rank (0-1)
        ndcg_at_5: Minimum acceptable NDCG@5 (0-1)
        warning_margin: Distance below threshold that triggers warning (default 0.05)

    Example:
        ```python
        config = ThresholdConfig(recall_at_5=0.85, mrr=0.80, ndcg_at_5=0.82)
        status = config.check_recall(0.83)  # Returns WARN (85% - 5% = 80% < 83%)
        status = config.check_recall(0.86)  # Returns PASS (>= 85%)
        status = config.check_recall(0.78)  # Returns FAIL (< 80%)
        ```

    """

    recall_at_5: float
    mrr: float
    ndcg_at_5: float
    warning_margin: float = 0.05

    def check_recall(self, value: float) -> ThresholdStatus:
        """Check Recall@5 against threshold.

        Args:
            value: Measured Recall@5 value (0-1)

        Returns:
            PASS if value >= threshold
            WARN if value >= threshold - warning_margin
            FAIL otherwise

        """
        if value >= self.recall_at_5:
            return ThresholdStatus.PASS
        if value >= self.recall_at_5 - self.warning_margin:
            return ThresholdStatus.WARN
        return ThresholdStatus.FAIL

    def check_mrr(self, value: float) -> ThresholdStatus:
        """Check MRR against threshold.

        Args:
            value: Measured MRR value (0-1)

        Returns:
            PASS if value >= threshold
            WARN if value >= threshold - warning_margin
            FAIL otherwise

        """
        if value >= self.mrr:
            return ThresholdStatus.PASS
        if value >= self.mrr - self.warning_margin:
            return ThresholdStatus.WARN
        return ThresholdStatus.FAIL

    def check_ndcg(self, value: float) -> ThresholdStatus:
        """Check NDCG@5 against threshold.

        Args:
            value: Measured NDCG@5 value (0-1)

        Returns:
            PASS if value >= threshold
            WARN if value >= threshold - warning_margin
            FAIL otherwise

        """
        if value >= self.ndcg_at_5:
            return ThresholdStatus.PASS
        if value >= self.ndcg_at_5 - self.warning_margin:
            return ThresholdStatus.WARN
        return ThresholdStatus.FAIL

    def check_all(
        self, recall: float, mrr: float, ndcg: float
    ) -> tuple[ThresholdStatus, ThresholdStatus, ThresholdStatus]:
        """Check all metrics against thresholds.

        Args:
            recall: Measured Recall@5 value
            mrr: Measured MRR value
            ndcg: Measured NDCG@5 value

        Returns:
            Tuple of (recall_status, mrr_status, ndcg_status)

        """
        return (
            self.check_recall(recall),
            self.check_mrr(mrr),
            self.check_ndcg(ndcg),
        )

    def overall_status(self, recall: float, mrr: float, ndcg: float) -> ThresholdStatus:
        """Determine overall threshold status from all metrics.

        Returns FAIL if any metric fails, WARN if any warns, else PASS.

        Args:
            recall: Measured Recall@5 value
            mrr: Measured MRR value
            ndcg: Measured NDCG@5 value

        Returns:
            Worst status among all metrics (FAIL > WARN > PASS)

        """
        statuses = self.check_all(recall, mrr, ndcg)
        if ThresholdStatus.FAIL in statuses:
            return ThresholdStatus.FAIL
        if ThresholdStatus.WARN in statuses:
            return ThresholdStatus.WARN
        return ThresholdStatus.PASS


# Per-difficulty threshold configurations
# Based on Sprint 12 spec and retrieval smoke test calibration
THRESHOLDS: dict[Difficulty, ThresholdConfig] = {
    Difficulty.TRIVIAL: ThresholdConfig(
        recall_at_5=0.95,
        mrr=0.90,
        ndcg_at_5=0.92,
    ),
    Difficulty.EASY: ThresholdConfig(
        recall_at_5=0.85,
        mrr=0.80,
        ndcg_at_5=0.82,
    ),
    Difficulty.MEDIUM: ThresholdConfig(
        recall_at_5=0.75,
        mrr=0.70,
        ndcg_at_5=0.72,
    ),
    Difficulty.HARD: ThresholdConfig(
        recall_at_5=0.65,
        mrr=0.60,
        ndcg_at_5=0.62,
    ),
    Difficulty.ADVERSARIAL: ThresholdConfig(
        recall_at_5=0.50,
        mrr=0.45,
        ndcg_at_5=0.48,
    ),
}


def get_threshold(difficulty: Difficulty | str) -> ThresholdConfig:
    """Get threshold configuration for a difficulty level.

    Args:
        difficulty: Difficulty enum or string value

    Returns:
        ThresholdConfig for the difficulty level

    Raises:
        ValueError: If difficulty is not recognized

    """
    if isinstance(difficulty, str):
        try:
            difficulty = Difficulty(difficulty)
        except ValueError as e:
            msg = (
                f"Invalid difficulty: {difficulty}. Must be one of: {[d.value for d in Difficulty]}"
            )
            raise ValueError(msg) from e

    if difficulty not in THRESHOLDS:
        msg = f"No threshold configured for difficulty: {difficulty}"
        raise ValueError(msg)

    return THRESHOLDS[difficulty]
