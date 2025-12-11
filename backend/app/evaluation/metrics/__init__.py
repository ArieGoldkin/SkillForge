"""Evaluation metrics and analysis tools.

This package provides metric calculation and analysis utilities:
- Information retrieval metrics (Recall, MRR, NDCG)
- Regression detection
- Baseline comparison

Main Components:
- regression: Regression detection and baseline comparison

Usage:
    ```python
    from app.evaluation.metrics import check_regression, RegressionReport

    report = check_regression(
        current_path=Path("results/current.json"),
        baseline_path=Path("results/baseline.json"),
        threshold=0.05,
    )
    ```
"""

from app.evaluation.metrics.regression import (
    MetricChange,
    RegressionReport,
    StatusChange,
    check_regression,
)

__all__ = [
    "check_regression",
    "RegressionReport",
    "MetricChange",
    "StatusChange",
]
