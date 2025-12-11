"""Unit tests for evaluation thresholds module.

Tests cover:
- ThresholdConfig: recall/MRR/NDCG threshold checking with pass/warn/fail
- Threshold validation: ensure thresholds decrease with difficulty
- Edge cases: missing metrics, invalid difficulty levels
"""

import pytest

from app.evaluation.pipeline.thresholds import (
    Difficulty,
    ThresholdConfig,
    ThresholdStatus,
    THRESHOLDS,
    get_threshold,
)


class TestThresholdConfig:
    """Tests for ThresholdConfig class."""

    def test_check_recall_pass(self):
        """Test recall check returns PASS when above threshold."""
        config = ThresholdConfig(recall_at_5=0.85, mrr=0.80, ndcg_at_5=0.82)
        status = config.check_recall(0.86)
        assert status == ThresholdStatus.PASS

    def test_check_recall_warn(self):
        """Test recall check returns WARN when within warning margin (5%)."""
        config = ThresholdConfig(recall_at_5=0.85, mrr=0.80, ndcg_at_5=0.82)
        # 0.83 is within margin (0.85 - 0.05 = 0.80 <= 0.83 < 0.85)
        status = config.check_recall(0.83)
        assert status == ThresholdStatus.WARN

    def test_check_recall_fail(self):
        """Test recall check returns FAIL when below threshold."""
        config = ThresholdConfig(recall_at_5=0.85, mrr=0.80, ndcg_at_5=0.82)
        # 0.78 is below warning margin (< 0.80)
        status = config.check_recall(0.78)
        assert status == ThresholdStatus.FAIL

    def test_check_mrr_pass(self):
        """Test MRR check returns PASS when above threshold."""
        config = ThresholdConfig(recall_at_5=0.85, mrr=0.80, ndcg_at_5=0.82)
        status = config.check_mrr(0.82)
        assert status == ThresholdStatus.PASS

    def test_check_mrr_warn(self):
        """Test MRR check returns WARN when within warning margin."""
        config = ThresholdConfig(recall_at_5=0.85, mrr=0.80, ndcg_at_5=0.82)
        status = config.check_mrr(0.78)
        assert status == ThresholdStatus.WARN

    def test_check_mrr_fail(self):
        """Test MRR check returns FAIL when below threshold."""
        config = ThresholdConfig(recall_at_5=0.85, mrr=0.80, ndcg_at_5=0.82)
        status = config.check_mrr(0.72)
        assert status == ThresholdStatus.FAIL

    def test_check_ndcg_pass(self):
        """Test NDCG@5 check returns PASS when above threshold."""
        config = ThresholdConfig(recall_at_5=0.85, mrr=0.80, ndcg_at_5=0.82)
        status = config.check_ndcg(0.85)
        assert status == ThresholdStatus.PASS

    def test_check_ndcg_warn(self):
        """Test NDCG@5 check returns WARN when within warning margin."""
        config = ThresholdConfig(recall_at_5=0.85, mrr=0.80, ndcg_at_5=0.82)
        status = config.check_ndcg(0.79)
        assert status == ThresholdStatus.WARN

    def test_check_ndcg_fail(self):
        """Test NDCG@5 check returns FAIL when below threshold."""
        config = ThresholdConfig(recall_at_5=0.85, mrr=0.80, ndcg_at_5=0.82)
        status = config.check_ndcg(0.74)
        assert status == ThresholdStatus.FAIL

    def test_check_all(self):
        """Test check_all returns tuple of all statuses."""
        config = ThresholdConfig(recall_at_5=0.85, mrr=0.80, ndcg_at_5=0.82)
        # All pass
        statuses = config.check_all(recall=0.90, mrr=0.85, ndcg=0.88)
        assert statuses == (
            ThresholdStatus.PASS,
            ThresholdStatus.PASS,
            ThresholdStatus.PASS,
        )

        # Mixed results
        statuses = config.check_all(recall=0.83, mrr=0.78, ndcg=0.70)
        assert statuses == (
            ThresholdStatus.WARN,
            ThresholdStatus.WARN,
            ThresholdStatus.FAIL,
        )

    def test_overall_status_all_pass(self):
        """Test overall_status returns PASS when all metrics pass."""
        config = ThresholdConfig(recall_at_5=0.85, mrr=0.80, ndcg_at_5=0.82)
        status = config.overall_status(recall=0.90, mrr=0.85, ndcg=0.88)
        assert status == ThresholdStatus.PASS

    def test_overall_status_any_warn(self):
        """Test overall_status returns WARN when any metric warns."""
        config = ThresholdConfig(recall_at_5=0.85, mrr=0.80, ndcg_at_5=0.82)
        status = config.overall_status(recall=0.90, mrr=0.78, ndcg=0.88)
        assert status == ThresholdStatus.WARN

    def test_overall_status_any_fail(self):
        """Test overall_status returns FAIL when any metric fails."""
        config = ThresholdConfig(recall_at_5=0.85, mrr=0.80, ndcg_at_5=0.82)
        status = config.overall_status(recall=0.90, mrr=0.85, ndcg=0.70)
        assert status == ThresholdStatus.FAIL

    def test_custom_warning_margin(self):
        """Test custom warning margin configuration."""
        config = ThresholdConfig(
            recall_at_5=0.85, mrr=0.80, ndcg_at_5=0.82, warning_margin=0.10
        )
        # 0.77 would be WARN with 10% margin (0.85 - 0.10 = 0.75 <= 0.77 < 0.85)
        status = config.check_recall(0.77)
        assert status == ThresholdStatus.WARN


class TestThresholdValidation:
    """Tests for threshold configuration validation."""

    def test_all_difficulties_have_thresholds(self):
        """Test all difficulty levels have threshold definitions."""
        difficulties = [
            Difficulty.TRIVIAL,
            Difficulty.EASY,
            Difficulty.MEDIUM,
            Difficulty.HARD,
            Difficulty.ADVERSARIAL,
        ]
        for difficulty in difficulties:
            assert difficulty in THRESHOLDS

    def test_thresholds_decrease_with_difficulty(self):
        """Test thresholds decrease monotonically as difficulty increases."""
        # Recall@5: should decrease from trivial to adversarial
        recall_thresholds = [
            THRESHOLDS[Difficulty.TRIVIAL].recall_at_5,
            THRESHOLDS[Difficulty.EASY].recall_at_5,
            THRESHOLDS[Difficulty.MEDIUM].recall_at_5,
            THRESHOLDS[Difficulty.HARD].recall_at_5,
            THRESHOLDS[Difficulty.ADVERSARIAL].recall_at_5,
        ]
        assert recall_thresholds == sorted(recall_thresholds, reverse=True)

        # MRR: should decrease from trivial to adversarial
        mrr_thresholds = [
            THRESHOLDS[Difficulty.TRIVIAL].mrr,
            THRESHOLDS[Difficulty.EASY].mrr,
            THRESHOLDS[Difficulty.MEDIUM].mrr,
            THRESHOLDS[Difficulty.HARD].mrr,
            THRESHOLDS[Difficulty.ADVERSARIAL].mrr,
        ]
        assert mrr_thresholds == sorted(mrr_thresholds, reverse=True)

        # NDCG@5: should decrease from trivial to adversarial
        ndcg_thresholds = [
            THRESHOLDS[Difficulty.TRIVIAL].ndcg_at_5,
            THRESHOLDS[Difficulty.EASY].ndcg_at_5,
            THRESHOLDS[Difficulty.MEDIUM].ndcg_at_5,
            THRESHOLDS[Difficulty.HARD].ndcg_at_5,
            THRESHOLDS[Difficulty.ADVERSARIAL].ndcg_at_5,
        ]
        assert ndcg_thresholds == sorted(ndcg_thresholds, reverse=True)

    def test_threshold_ranges_valid(self):
        """Test all thresholds are between 0.0 and 1.0."""
        for difficulty, config in THRESHOLDS.items():
            assert 0.0 <= config.recall_at_5 <= 1.0, (
                f"{difficulty.value}.recall_at_5={config.recall_at_5} outside [0.0, 1.0]"
            )
            assert 0.0 <= config.mrr <= 1.0, (
                f"{difficulty.value}.mrr={config.mrr} outside [0.0, 1.0]"
            )
            assert 0.0 <= config.ndcg_at_5 <= 1.0, (
                f"{difficulty.value}.ndcg_at_5={config.ndcg_at_5} outside [0.0, 1.0]"
            )


class TestGetThreshold:
    """Tests for get_threshold() function."""

    def test_get_threshold_with_enum(self):
        """Test get_threshold with Difficulty enum."""
        config = get_threshold(Difficulty.EASY)
        assert isinstance(config, ThresholdConfig)
        assert config.recall_at_5 == 0.85

    def test_get_threshold_with_string(self):
        """Test get_threshold with string difficulty."""
        config = get_threshold("easy")
        assert isinstance(config, ThresholdConfig)
        assert config.recall_at_5 == 0.85

    def test_invalid_difficulty_raises_error(self):
        """Test invalid difficulty level raises ValueError."""
        with pytest.raises(ValueError, match="Invalid difficulty"):
            get_threshold("invalid")

    def test_all_difficulties_accessible(self):
        """Test all difficulties can be retrieved."""
        for difficulty in Difficulty:
            config = get_threshold(difficulty)
            assert isinstance(config, ThresholdConfig)


class TestThresholdStatus:
    """Tests for threshold status checking logic."""

    def test_pass_status_calculation(self):
        """Test PASS status when all metrics above threshold."""
        config = get_threshold(Difficulty.EASY)
        status = config.overall_status(recall=0.90, mrr=0.85, ndcg=0.88)
        assert status == ThresholdStatus.PASS

    def test_warn_status_calculation(self):
        """Test WARN status when any metric in warning margin."""
        config = get_threshold(Difficulty.EASY)
        # recall_at_5=0.85, warn if >= 0.80
        status = config.overall_status(recall=0.83, mrr=0.85, ndcg=0.88)
        assert status == ThresholdStatus.WARN

    def test_fail_status_calculation(self):
        """Test FAIL status when any metric below threshold."""
        config = get_threshold(Difficulty.EASY)
        # recall_at_5=0.85, fail if < 0.80
        status = config.overall_status(recall=0.75, mrr=0.85, ndcg=0.88)
        assert status == ThresholdStatus.FAIL

    def test_edge_case_exact_threshold(self):
        """Test exact threshold value returns PASS."""
        config = ThresholdConfig(recall_at_5=0.85, mrr=0.80, ndcg_at_5=0.82)
        status = config.check_recall(0.85)
        assert status == ThresholdStatus.PASS

    def test_edge_case_exact_warning_boundary(self):
        """Test exact warning boundary returns WARN."""
        config = ThresholdConfig(recall_at_5=0.85, mrr=0.80, ndcg_at_5=0.82)
        # Exactly at warning boundary (0.85 - 0.05 = 0.80)
        status = config.check_recall(0.80)
        assert status == ThresholdStatus.WARN
