"""Unit tests for regression detection module.

Tests cover:
- Regression detection (>5% performance drop)
- Improvement detection (>5% performance gain)
- Baseline comparison
- Markdown report generation
"""

import json
import pytest
from pathlib import Path

from app.evaluation.metrics.regression import (

@pytest.mark.unit
    RegressionReport,
    check_regression,
)


class TestRegressionChecker:
    """Tests for regression checking functionality."""

    def test_no_regression(self, tmp_path: Path):
        """Test no regression detected when metrics stable (±5%)."""
        baseline = {
            "results": {
                "easy": {
                    "recall_at_5": 0.80,
                    "mrr": 0.70,
                    "ndcg_at_5": 0.75,
                    "status": "pass",
                }
            }
        }
        current = {
            "results": {
                "easy": {
                    "recall_at_5": 0.81,
                    "mrr": 0.69,
                    "ndcg_at_5": 0.76,
                    "status": "pass",
                }
            }
        }

        baseline_path = tmp_path / "baseline.json"
        current_path = tmp_path / "current.json"
        baseline_path.write_text(json.dumps(baseline))
        current_path.write_text(json.dumps(current))

        report = check_regression(current_path, baseline_path, threshold=0.05)

        assert not report.has_regressions
        assert len(report.regressions) == 0
        assert report.threshold == 0.05
        assert not report.baseline_missing

    def test_detect_regression(self, tmp_path: Path):
        """Test regression detected when metrics drop >5%."""
        baseline = {
            "results": {
                "easy": {
                    "recall_at_5": 0.80,
                    "mrr": 0.70,
                    "ndcg_at_5": 0.75,
                    "status": "pass",
                }
            }
        }
        current = {
            "results": {
                "easy": {
                    "recall_at_5": 0.72,  # 10% drop
                    "mrr": 0.70,
                    "ndcg_at_5": 0.75,
                    "status": "pass",
                }
            }
        }

        baseline_path = tmp_path / "baseline.json"
        current_path = tmp_path / "current.json"
        baseline_path.write_text(json.dumps(baseline))
        current_path.write_text(json.dumps(current))

        report = check_regression(current_path, baseline_path, threshold=0.05)

        assert report.has_regressions
        assert len(report.regressions) == 1
        assert report.regressions[0]["metric_name"] == "recall_at_5"
        assert report.regressions[0]["difficulty"] == "easy"
        assert report.regressions[0]["baseline_value"] == 0.80
        assert report.regressions[0]["current_value"] == 0.72

    def test_detect_improvement(self, tmp_path: Path):
        """Test improvement detected when metrics increase >5%."""
        baseline = {
            "results": {
                "easy": {
                    "recall_at_5": 0.70,
                    "mrr": 0.60,
                    "ndcg_at_5": 0.65,
                    "status": "pass",
                }
            }
        }
        current = {
            "results": {
                "easy": {
                    "recall_at_5": 0.78,  # 11.4% improvement, delta=0.08 > 0.05
                    "mrr": 0.60,
                    "ndcg_at_5": 0.65,
                    "status": "pass",
                }
            }
        }

        baseline_path = tmp_path / "baseline.json"
        current_path = tmp_path / "current.json"
        baseline_path.write_text(json.dumps(baseline))
        current_path.write_text(json.dumps(current))

        report = check_regression(current_path, baseline_path, threshold=0.05)

        assert not report.has_regressions
        assert len(report.improvements) == 1
        assert report.improvements[0]["metric_name"] == "recall_at_5"
        assert report.improvements[0]["difficulty"] == "easy"

    def test_detect_mixed_results(self, tmp_path: Path):
        """Test mixed results (some regress, some improve)."""
        baseline = {
            "results": {
                "easy": {
                    "recall_at_5": 0.80,
                    "mrr": 0.70,
                    "ndcg_at_5": 0.75,
                    "status": "pass",
                }
            }
        }
        current = {
            "results": {
                "easy": {
                    "recall_at_5": 0.72,  # Regressed (delta=-0.08)
                    "mrr": 0.78,  # Improved (delta=0.08)
                    "ndcg_at_5": 0.75,
                    "status": "pass",
                }
            }
        }

        baseline_path = tmp_path / "baseline.json"
        current_path = tmp_path / "current.json"
        baseline_path.write_text(json.dumps(baseline))
        current_path.write_text(json.dumps(current))

        report = check_regression(current_path, baseline_path, threshold=0.05)

        assert report.has_regressions
        assert len(report.regressions) == 1
        assert len(report.improvements) == 1
        assert report.regressions[0]["metric_name"] == "recall_at_5"
        assert report.improvements[0]["metric_name"] == "mrr"

    def test_status_degradation(self, tmp_path: Path):
        """Test status degradation detection (PASS -> WARN -> FAIL)."""
        baseline = {
            "results": {
                "easy": {
                    "recall_at_5": 0.80,
                    "mrr": 0.70,
                    "ndcg_at_5": 0.75,
                    "status": "pass",
                }
            }
        }
        current = {
            "results": {
                "easy": {
                    "recall_at_5": 0.81,
                    "mrr": 0.71,
                    "ndcg_at_5": 0.76,
                    "status": "fail",  # Status degraded
                }
            }
        }

        baseline_path = tmp_path / "baseline.json"
        current_path = tmp_path / "current.json"
        baseline_path.write_text(json.dumps(baseline))
        current_path.write_text(json.dumps(current))

        report = check_regression(current_path, baseline_path, threshold=0.05)

        assert report.has_regressions  # Status degradation counts as regression
        assert len(report.status_changes) == 1
        assert report.status_changes[0]["difficulty"] == "easy"
        assert report.status_changes[0]["baseline_status"] == "pass"
        assert report.status_changes[0]["current_status"] == "fail"
        assert report.status_changes[0]["is_degradation"] is True

    def test_missing_baseline_handled(self, tmp_path: Path):
        """Test missing baseline file is handled gracefully."""
        current = {
            "results": {
                "easy": {
                    "recall_at_5": 0.80,
                    "mrr": 0.70,
                    "ndcg_at_5": 0.75,
                    "status": "pass",
                }
            }
        }

        baseline_path = tmp_path / "baseline.json"  # Does not exist
        current_path = tmp_path / "current.json"
        current_path.write_text(json.dumps(current))

        report = check_regression(current_path, baseline_path, threshold=0.05)

        assert not report.has_regressions
        assert report.baseline_missing
        assert report.comparison_error is None

    def test_missing_current_handled(self, tmp_path: Path):
        """Test missing current file is handled with error."""
        baseline = {
            "results": {
                "easy": {
                    "recall_at_5": 0.80,
                    "mrr": 0.70,
                    "ndcg_at_5": 0.75,
                    "status": "pass",
                }
            }
        }

        baseline_path = tmp_path / "baseline.json"
        current_path = tmp_path / "current.json"  # Does not exist
        baseline_path.write_text(json.dumps(baseline))

        report = check_regression(current_path, baseline_path, threshold=0.05)

        assert not report.has_regressions
        assert report.comparison_error is not None
        assert "not found" in report.comparison_error.lower()

    def test_threshold_configuration(self, tmp_path: Path):
        """Test configuring regression threshold (default=5%)."""
        baseline = {
            "results": {
                "easy": {
                    "recall_at_5": 0.80,
                    "mrr": 0.70,
                    "ndcg_at_5": 0.75,
                    "status": "pass",
                }
            }
        }
        current = {
            "results": {
                "easy": {
                    "recall_at_5": 0.73,  # 8.75% drop, delta=-0.07
                    "mrr": 0.70,
                    "ndcg_at_5": 0.75,
                    "status": "pass",
                }
            }
        }

        baseline_path = tmp_path / "baseline.json"
        current_path = tmp_path / "current.json"
        baseline_path.write_text(json.dumps(baseline))
        current_path.write_text(json.dumps(current))

        # With 10% threshold (0.10 absolute), should not detect regression
        report = check_regression(current_path, baseline_path, threshold=0.10)
        assert not report.has_regressions

        # With 5% threshold (0.05 absolute), should detect regression
        report = check_regression(current_path, baseline_path, threshold=0.05)
        assert report.has_regressions

    def test_multiple_difficulties(self, tmp_path: Path):
        """Test regression checking across multiple difficulties."""
        baseline = {
            "results": {
                "easy": {
                    "recall_at_5": 0.80,
                    "mrr": 0.70,
                    "ndcg_at_5": 0.75,
                    "status": "pass",
                },
                "hard": {
                    "recall_at_5": 0.60,
                    "mrr": 0.50,
                    "ndcg_at_5": 0.55,
                    "status": "pass",
                },
            }
        }
        current = {
            "results": {
                "easy": {
                    "recall_at_5": 0.86,  # Improved (delta=0.06 > 0.05)
                    "mrr": 0.76,  # Improved (delta=0.06 > 0.05)
                    "ndcg_at_5": 0.81,  # Improved (delta=0.06 > 0.05)
                    "status": "pass",
                },
                "hard": {
                    "recall_at_5": 0.54,  # Regressed (delta=-0.06 < -0.05)
                    "mrr": 0.50,
                    "ndcg_at_5": 0.55,
                    "status": "pass",
                },
            }
        }

        baseline_path = tmp_path / "baseline.json"
        current_path = tmp_path / "current.json"
        baseline_path.write_text(json.dumps(baseline))
        current_path.write_text(json.dumps(current))

        report = check_regression(current_path, baseline_path, threshold=0.05)

        assert report.has_regressions
        assert len(report.regressions) == 1
        assert report.regressions[0]["difficulty"] == "hard"
        assert len(report.improvements) == 3  # All three metrics in "easy" improved


class TestRegressionReport:
    """Tests for RegressionReport class."""

    def test_to_dict(self):
        """Test to_dict() serialization."""
        report = RegressionReport(
            has_regressions=True,
            regressions=[
                {
                    "difficulty": "easy",
                    "metric_name": "recall_at_5",
                    "baseline_value": 0.80,
                    "current_value": 0.72,
                    "delta": -0.08,
                    "delta_percent": -10.0,
                }
            ],
            improvements=[],
            status_changes=[],
            threshold=0.05,
        )

        d = report.to_dict()
        assert d["has_regressions"] is True
        assert len(d["regressions"]) == 1
        assert d["threshold"] == 0.05

    def test_to_json(self):
        """Test to_json() serialization."""
        report = RegressionReport(
            has_regressions=False,
            threshold=0.05,
        )

        json_str = report.to_json()
        parsed = json.loads(json_str)
        assert parsed["has_regressions"] is False

    def test_to_markdown_no_baseline(self):
        """Test markdown report when baseline is missing."""
        report = RegressionReport(
            has_regressions=False,
            threshold=0.05,
            baseline_missing=True,
        )

        markdown = report.to_markdown()
        assert "NO BASELINE" in markdown
        assert "first run" in markdown.lower()

    def test_to_markdown_with_regressions(self):
        """Test markdown report generation with regressions."""
        report = RegressionReport(
            has_regressions=True,
            regressions=[
                {
                    "difficulty": "easy",
                    "metric_name": "recall_at_5",
                    "baseline_value": 0.80,
                    "current_value": 0.72,
                    "delta": -0.08,
                    "delta_percent": -10.0,
                }
            ],
            improvements=[],
            status_changes=[],
            threshold=0.05,
        )

        markdown = report.to_markdown()
        assert "REGRESSIONS DETECTED" in markdown
        assert "recall_at_5" in markdown
        assert "0.800" in markdown or "0.80" in markdown
        assert "0.720" in markdown or "0.72" in markdown

    def test_to_markdown_with_improvements(self):
        """Test markdown report generation with improvements."""
        report = RegressionReport(
            has_regressions=False,
            regressions=[],
            improvements=[
                {
                    "difficulty": "easy",
                    "metric_name": "mrr",
                    "baseline_value": 0.70,
                    "current_value": 0.78,
                    "delta": 0.08,
                    "delta_percent": 11.4,
                }
            ],
            status_changes=[],
            threshold=0.05,
        )

        markdown = report.to_markdown()
        assert "NO REGRESSIONS" in markdown
        assert "Improvements" in markdown
        assert "mrr" in markdown

    def test_to_markdown_with_status_changes(self):
        """Test markdown report with status degradations."""
        report = RegressionReport(
            has_regressions=True,
            regressions=[],
            improvements=[],
            status_changes=[
                {
                    "difficulty": "easy",
                    "baseline_status": "pass",
                    "current_status": "fail",
                    "is_degradation": True,
                }
            ],
            threshold=0.05,
        )

        markdown = report.to_markdown()
        assert "Status Changes" in markdown
        assert "pass" in markdown
        assert "fail" in markdown

    def test_to_markdown_no_changes(self):
        """Test markdown report when no changes detected."""
        report = RegressionReport(
            has_regressions=False,
            regressions=[],
            improvements=[],
            status_changes=[],
            threshold=0.05,
        )

        markdown = report.to_markdown()
        assert "NO REGRESSIONS" in markdown
        assert "No significant" in markdown


class TestCIIntegration:
    """Tests for CI/CD integration."""

    def test_has_regressions_flag(self, tmp_path: Path):
        """Test has_regressions flag for CI failure detection."""
        baseline = {
            "results": {
                "easy": {
                    "recall_at_5": 0.80,
                    "mrr": 0.70,
                    "ndcg_at_5": 0.75,
                    "status": "pass",
                }
            }
        }
        current = {
            "results": {
                "easy": {
                    "recall_at_5": 0.72,  # Regression
                    "mrr": 0.70,
                    "ndcg_at_5": 0.75,
                    "status": "pass",
                }
            }
        }

        baseline_path = tmp_path / "baseline.json"
        current_path = tmp_path / "current.json"
        baseline_path.write_text(json.dumps(baseline))
        current_path.write_text(json.dumps(current))

        report = check_regression(current_path, baseline_path)

        # CI should fail when has_regressions is True
        assert report.has_regressions is True

    def test_no_regressions_passes(self, tmp_path: Path):
        """Test CI passes when no regression detected."""
        baseline = {
            "results": {
                "easy": {
                    "recall_at_5": 0.80,
                    "mrr": 0.70,
                    "ndcg_at_5": 0.75,
                    "status": "pass",
                }
            }
        }
        current = {
            "results": {
                "easy": {
                    "recall_at_5": 0.81,
                    "mrr": 0.71,
                    "ndcg_at_5": 0.76,
                    "status": "pass",
                }
            }
        }

        baseline_path = tmp_path / "baseline.json"
        current_path = tmp_path / "current.json"
        baseline_path.write_text(json.dumps(baseline))
        current_path.write_text(json.dumps(current))

        report = check_regression(current_path, baseline_path)

        # CI should pass when has_regressions is False
        assert report.has_regressions is False

    def test_improvement_does_not_fail_ci(self, tmp_path: Path):
        """Test CI passes when improvement detected (not regression)."""
        baseline = {
            "results": {
                "easy": {
                    "recall_at_5": 0.70,
                    "mrr": 0.60,
                    "ndcg_at_5": 0.65,
                    "status": "pass",
                }
            }
        }
        current = {
            "results": {
                "easy": {
                    "recall_at_5": 0.78,  # Improvement (delta=0.08 > 0.05)
                    "mrr": 0.68,  # Improvement (delta=0.08 > 0.05)
                    "ndcg_at_5": 0.73,  # Improvement (delta=0.08 > 0.05)
                    "status": "pass",
                }
            }
        }

        baseline_path = tmp_path / "baseline.json"
        current_path = tmp_path / "current.json"
        baseline_path.write_text(json.dumps(baseline))
        current_path.write_text(json.dumps(current))

        report = check_regression(current_path, baseline_path)

        # Improvements should not fail CI
        assert report.has_regressions is False
        assert len(report.improvements) == 3
