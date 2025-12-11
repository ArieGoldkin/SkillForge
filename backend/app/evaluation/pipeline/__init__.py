"""CI/CD evaluation pipeline for quality gates and regression detection.

This package provides the core evaluation pipeline infrastructure:
- Threshold-based quality gates (PASS/WARN/FAIL)
- Difficulty-specific evaluation metrics
- Regression detection against baselines
- CI/CD integration utilities

Main Components:
- thresholds: Quality gate thresholds per difficulty level
- runner: Pipeline execution and result aggregation
- metrics.regression: Baseline comparison and regression detection

Usage:
    ```python
    from app.evaluation.pipeline import EvaluationRunner, check_regression
    from app.evaluation.pipeline.thresholds import Difficulty, ThresholdStatus

    # Run evaluation
    runner = EvaluationRunner(session, embedding_service)
    result = await runner.run_all()

    # Check for regressions
    regression_report = check_regression(
        current_path=Path("results/current.json"), baseline_path=Path("results/baseline.json")
    )
    ```
"""

from app.evaluation.pipeline.runner import (
    EvaluationResult,
    EvaluationRunner,
    PipelineResult,
)
from app.evaluation.pipeline.thresholds import (
    THRESHOLDS,
    Difficulty,
    ThresholdConfig,
    ThresholdStatus,
    get_threshold,
)

__all__ = [
    # Thresholds
    "Difficulty",
    "ThresholdStatus",
    "ThresholdConfig",
    "THRESHOLDS",
    "get_threshold",
    # Runner
    "EvaluationRunner",
    "EvaluationResult",
    "PipelineResult",
]
