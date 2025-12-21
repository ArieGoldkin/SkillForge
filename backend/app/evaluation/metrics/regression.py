"""Regression detection for evaluation metrics.

This module compares current evaluation results against a baseline to detect:
- Performance regressions (metrics decreased significantly)
- Performance improvements (metrics increased)
- Status changes (PASS -> FAIL, etc.)

Used in CI/CD to prevent merging PRs that degrade retrieval quality.

Usage:
    ```python
    report = check_regression(
        current_path=Path("results/current.json"),
        baseline_path=Path("results/baseline.json"),
        threshold=0.05,  # 5% regression tolerance
    )

    if report.has_regressions:
        print(report.to_markdown())
        sys.exit(1)
    ```
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from app.core.logging import get_logger
from app.evaluation.pipeline.thresholds import Difficulty

if TYPE_CHECKING:
    from pathlib import Path

logger = get_logger(__name__)


@dataclass
class MetricChange:
    """Details of a metric change between baseline and current.

    Attributes:
        difficulty: Difficulty level
        metric_name: Name of metric (recall_at_5, mrr, ndcg_at_5)
        baseline_value: Baseline metric value
        current_value: Current metric value
        delta: Change in metric (current - baseline)
        delta_percent: Percentage change
        is_regression: True if metric decreased beyond threshold
        is_improvement: True if metric increased beyond threshold

    """

    difficulty: str
    metric_name: str
    baseline_value: float
    current_value: float
    delta: float
    delta_percent: float
    is_regression: bool
    is_improvement: bool


@dataclass
class StatusChange:
    """Details of a status change between baseline and current.

    Attributes:
        difficulty: Difficulty level
        baseline_status: Baseline threshold status
        current_status: Current threshold status
        is_degradation: True if status worsened (PASS->WARN, PASS->FAIL, WARN->FAIL)

    """

    difficulty: str
    baseline_status: str
    current_status: str
    is_degradation: bool


@dataclass
class RegressionReport:
    """Report of regression analysis results.

    Attributes:
        has_regressions: True if any regressions detected
        regressions: List of metric regressions
        improvements: List of metric improvements
        status_changes: List of status changes
        threshold: Regression detection threshold (e.g., 0.05 = 5%)
        baseline_missing: True if baseline file not found
        comparison_error: Error message if comparison failed

    """

    has_regressions: bool
    regressions: list[dict[str, Any]] = field(default_factory=list)
    improvements: list[dict[str, Any]] = field(default_factory=list)
    status_changes: list[dict[str, Any]] = field(default_factory=list)
    threshold: float = 0.05
    baseline_missing: bool = False
    comparison_error: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "has_regressions": self.has_regressions,
            "regressions": self.regressions,
            "improvements": self.improvements,
            "status_changes": self.status_changes,
            "threshold": self.threshold,
            "baseline_missing": self.baseline_missing,
            "comparison_error": self.comparison_error,
        }

    def to_json(self) -> str:
        """Serialize to JSON format."""
        return json.dumps(self.to_dict(), indent=2)

    def to_markdown(self) -> str:
        """Generate markdown report for PR comments.

        Returns:
            Formatted markdown report showing regressions and improvements.
            Output includes status header, regressions table, and improvements table.
        """
        lines = [
            "# Regression Analysis",
            "",
        ]

        # Status header
        if self.baseline_missing:
            lines.extend(
                [
                    "**Status**: ⚠️ NO BASELINE (first run)",
                    "",
                    "No baseline results found for comparison. This evaluation will establish the baseline.",
                    "",
                ]
            )
            return "\n".join(lines)

        if self.comparison_error:
            lines.extend(
                [
                    "**Status**: ❌ COMPARISON ERROR",
                    "",
                    f"Error: {self.comparison_error}",
                    "",
                ]
            )
            return "\n".join(lines)

        status_emoji = "❌" if self.has_regressions else "✅"
        status_text = "REGRESSIONS DETECTED" if self.has_regressions else "NO REGRESSIONS"
        lines.extend(
            [
                f"**Status**: {status_emoji} {status_text}",
                f"**Threshold**: {self.threshold * 100:.1f}% change tolerance",
                "",
            ]
        )

        # Status changes
        if self.status_changes:
            degradations = [sc for sc in self.status_changes if sc.get("is_degradation")]
            if degradations:
                lines.extend(
                    [
                        f"## Status Changes ({len(degradations)} degradations)",
                        "",
                        "| Difficulty | Baseline | Current |",
                        "|------------|----------|---------|",
                    ]
                )
                for change in degradations:
                    lines.append(
                        f"| {change['difficulty']} | "
                        f"{change['baseline_status']} | "
                        f"{change['current_status']} |"
                    )
                lines.append("")

        # Regressions
        if self.regressions:
            lines.extend(
                [
                    f"## Regressions ({len(self.regressions)})",
                    "",
                    "| Difficulty | Metric | Baseline | Current | Change |",
                    "|------------|--------|----------|---------|--------|",
                ]
            )
            for reg in self.regressions:
                lines.append(
                    f"| {reg['difficulty']:10} | "
                    f"{reg['metric_name']:10} | "
                    f"{reg['baseline_value']:.3f} | "
                    f"{reg['current_value']:.3f} | "
                    f"{reg['delta_percent']:+.1f}% |"
                )
            lines.append("")

        # Improvements
        if self.improvements:
            lines.extend(
                [
                    f"## Improvements ({len(self.improvements)})",
                    "",
                    "| Difficulty | Metric | Baseline | Current | Change |",
                    "|------------|--------|----------|---------|--------|",
                ]
            )
            for imp in self.improvements:
                lines.append(
                    f"| {imp['difficulty']:10} | "
                    f"{imp['metric_name']:10} | "
                    f"{imp['baseline_value']:.3f} | "
                    f"{imp['current_value']:.3f} | "
                    f"{imp['delta_percent']:+.1f}% |"
                )
            lines.append("")

        # No changes
        if not self.regressions and not self.improvements and not self.status_changes:
            lines.extend(
                [
                    "No significant metric changes detected.",
                    "",
                ]
            )

        return "\n".join(lines)


def check_regression(
    current_path: Path,
    baseline_path: Path,
    threshold: float = 0.05,
) -> RegressionReport:
    """Check for regressions by comparing current results to baseline.

    Args:
        current_path: Path to current evaluation results JSON
        baseline_path: Path to baseline evaluation results JSON
        threshold: Minimum change to consider regression/improvement (default 0.05 = 5%)

    Returns:
        RegressionReport with detected regressions and improvements.
    """
    logger.info(
        "Checking for regressions",
        current=str(current_path),
        baseline=str(baseline_path),
        threshold=threshold,
    )

    # Check if baseline exists
    if not baseline_path.exists():
        logger.warning("Baseline file not found", path=str(baseline_path))
        return RegressionReport(
            has_regressions=False,
            threshold=threshold,
            baseline_missing=True,
        )

    # Check if current exists
    if not current_path.exists():
        logger.error("Current results file not found", path=str(current_path))
        return RegressionReport(
            has_regressions=False,
            threshold=threshold,
            comparison_error=f"Current results file not found: {current_path}",
        )

    # Load results
    try:
        with open(baseline_path) as f:
            baseline = json.load(f)
        with open(current_path) as f:
            current = json.load(f)
    except json.JSONDecodeError as e:
        logger.error("Failed to parse JSON", error=str(e))
        return RegressionReport(
            has_regressions=False,
            threshold=threshold,
            comparison_error=f"Failed to parse JSON: {e}",
        )

    # Compare metrics
    regressions: list[dict[str, Any]] = []
    improvements: list[dict[str, Any]] = []
    status_changes: list[dict[str, Any]] = []

    baseline_results = baseline.get("results", {})
    current_results = current.get("results", {})

    # Metrics to compare
    metrics = ["recall_at_5", "mrr", "ndcg_at_5"]

    for difficulty_str in Difficulty.__members__.values():
        difficulty = difficulty_str.value

        if difficulty not in baseline_results or difficulty not in current_results:
            continue

        baseline_diff = baseline_results[difficulty]
        current_diff = current_results[difficulty]

        # Compare metrics
        for metric in metrics:
            baseline_value = baseline_diff.get(metric, 0.0)
            current_value = current_diff.get(metric, 0.0)

            if baseline_value == 0.0:
                continue

            delta = current_value - baseline_value
            delta_percent = (delta / baseline_value) * 100

            change = {
                "difficulty": difficulty,
                "metric_name": metric,
                "baseline_value": baseline_value,
                "current_value": current_value,
                "delta": delta,
                "delta_percent": delta_percent,
            }

            # Check if regression (negative change beyond threshold)
            if delta < -threshold:
                regressions.append({**change, "is_regression": True})
            # Check if improvement (positive change beyond threshold)
            elif delta > threshold:
                improvements.append({**change, "is_improvement": True})

        # Compare status
        baseline_status = baseline_diff.get("status", "unknown")
        current_status = current_diff.get("status", "unknown")

        if baseline_status != current_status:
            is_degradation = _is_status_degradation(baseline_status, current_status)
            status_changes.append(
                {
                    "difficulty": difficulty,
                    "baseline_status": baseline_status,
                    "current_status": current_status,
                    "is_degradation": is_degradation,
                }
            )

    has_regressions = bool(regressions) or any(sc.get("is_degradation") for sc in status_changes)

    logger.info(
        "Regression check complete",
        regressions=len(regressions),
        improvements=len(improvements),
        status_changes=len(status_changes),
        has_regressions=has_regressions,
    )

    return RegressionReport(
        has_regressions=has_regressions,
        regressions=regressions,
        improvements=improvements,
        status_changes=status_changes,
        threshold=threshold,
    )


def _is_status_degradation(baseline: str, current: str) -> bool:
    """Check if status change represents a degradation.

    Degradation: PASS -> WARN, PASS -> FAIL, WARN -> FAIL

    Args:
        baseline: Baseline status string
        current: Current status string

    Returns:
        True if status degraded

    """
    status_order = {"pass": 0, "warn": 1, "fail": 2}

    baseline_rank = status_order.get(baseline.lower(), 2)
    current_rank = status_order.get(current.lower(), 2)

    return current_rank > baseline_rank
