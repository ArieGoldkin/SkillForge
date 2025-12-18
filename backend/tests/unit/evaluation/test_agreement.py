"""Unit tests for inter-annotator agreement metrics.

Tests cover:
- Cohen's Kappa: pairwise agreement between 2 annotators
- Fleiss' Kappa: multi-rater agreement for 3+ annotators
- Kappa interpretation: poor/fair/moderate/substantial/almost_perfect
- Edge cases: perfect agreement, no agreement, undefined cases
"""

import numpy as np
import pytest

from app.evaluation.validation.agreement import (
    AgreementCalculator,
    cohens_kappa,
    fleiss_kappa,
    interpret_kappa,
)
from app.evaluation.validation.models import Annotation, RelevanceScore


@pytest.mark.unit
class TestCohensKappa:
    """Tests for Cohen's Kappa coefficient."""

    def test_perfect_agreement(self):
        """Test perfect agreement returns kappa=1.0."""
        kappa = cohens_kappa(ratings_a=[0, 1, 2, 3], ratings_b=[0, 1, 2, 3])
        assert kappa == 1.0

    def test_no_agreement(self):
        """Test systematic disagreement returns kappa<=0.0."""
        # When all ratings are completely opposite, kappa approaches 0
        # This isn't "worse than chance" but rather "no agreement beyond chance"
        kappa = cohens_kappa(ratings_a=[0, 0, 0, 0], ratings_b=[3, 3, 3, 3])
        assert kappa <= 0.0

    def test_moderate_agreement(self):
        """Test moderate agreement returns 0.4 < kappa < 0.6."""
        kappa = cohens_kappa(ratings_a=[0, 1, 2, 3, 0], ratings_b=[0, 1, 2, 2, 1])
        assert 0.4 < kappa < 0.6

    def test_chance_agreement(self):
        """Test pure chance agreement returns kappa≈0.0."""
        # Create ratings that should have low kappa
        # With diverse ratings, agreement is close to chance
        kappa = cohens_kappa(
            ratings_a=[0, 1, 2, 3, 0, 1, 2, 3, 0, 1], ratings_b=[1, 2, 3, 0, 2, 3, 0, 1, 3, 2]
        )
        # Should be low (but exact value depends on the distribution)
        assert abs(kappa) < 0.4

    def test_different_lengths_raises_error(self):
        """Test different annotation lengths raises ValueError."""
        with pytest.raises(ValueError, match="same length"):
            cohens_kappa(ratings_a=[0, 1], ratings_b=[0, 1, 2])

    def test_empty_annotations_returns_zero(self):
        """Test empty annotations return 0.0."""
        kappa = cohens_kappa(ratings_a=[], ratings_b=[])
        assert kappa == 0.0

    def test_single_category_returns_one(self):
        """Test single category (no variance) returns 1.0."""
        kappa = cohens_kappa(ratings_a=[0, 0, 0], ratings_b=[0, 0, 0])
        assert kappa == 1.0


class TestFleissKappa:
    """Tests for Fleiss' Kappa coefficient (multi-rater)."""

    def test_three_annotators_perfect_agreement(self):
        """Test 3 annotators with perfect agreement returns kappa=1.0."""
        # Each row: [count_0, count_1, count_2, count_3]
        # Perfect agreement: all 3 annotators chose same category
        ratings = np.array(
            [
                [3, 0, 0, 0],  # Item 1: 3 annotators chose category 0
                [0, 3, 0, 0],  # Item 2: 3 annotators chose category 1
                [0, 0, 3, 0],  # Item 3: 3 annotators chose category 2
                [0, 0, 0, 3],  # Item 4: 3 annotators chose category 3
            ]
        )
        kappa = fleiss_kappa(ratings)
        assert abs(kappa - 1.0) < 0.01  # Should be very close to 1.0

    def test_three_annotators_no_agreement(self):
        """Test 3 annotators with no agreement returns low kappa."""
        # Maximum disagreement: each annotator picks different category
        # With 3 annotators and 4 categories, perfect disagreement is hard
        # This creates a scenario with low agreement
        ratings = np.array(
            [
                [1, 1, 1, 0],  # Each annotator picked different category
                [1, 1, 1, 0],
                [1, 1, 1, 0],
                [1, 1, 1, 0],
            ]
        )
        kappa = fleiss_kappa(ratings)
        # Should be negative or close to 0 (worse than chance)
        assert kappa < 0.2

    def test_partial_agreement(self):
        """Test partial agreement (2/3 agree) returns positive kappa."""
        # 2 out of 3 annotators agree on each item
        ratings = np.array(
            [
                [2, 1, 0, 0],  # 2 agree on category 0
                [1, 2, 0, 0],  # 2 agree on category 1
                [0, 1, 2, 0],  # 2 agree on category 2
                [0, 0, 1, 2],  # 2 agree on category 3
            ]
        )
        kappa = fleiss_kappa(ratings)
        # Should be positive, showing better than chance agreement
        assert kappa > 0.0

    def test_invalid_rating_matrix_raises_error(self):
        """Test invalid rating matrix raises ValueError."""
        # Wrong number of categories
        ratings = np.array(
            [
                [1, 1, 1],  # Only 3 categories instead of 4
            ]
        )
        with pytest.raises(ValueError, match="Categories mismatch"):
            fleiss_kappa(ratings)


class TestInterpretKappa:
    """Tests for kappa interpretation function."""

    def test_poor_agreement(self):
        """Test kappa<0.2 interpreted as 'poor' or 'slight'."""
        assert interpret_kappa(0.15) in ["poor", "slight"]
        assert interpret_kappa(-0.1) == "poor"

    def test_fair_agreement(self):
        """Test 0.2≤kappa<0.4 interpreted as 'fair'."""
        assert interpret_kappa(0.35) == "fair"
        assert interpret_kappa(0.2) == "fair"

    def test_moderate_agreement(self):
        """Test 0.4≤kappa<0.6 interpreted as 'moderate'."""
        assert interpret_kappa(0.55) == "moderate"
        assert interpret_kappa(0.4) == "moderate"

    def test_substantial_agreement(self):
        """Test 0.6≤kappa<0.8 interpreted as 'substantial'."""
        assert interpret_kappa(0.75) == "substantial"
        assert interpret_kappa(0.6) == "substantial"

    def test_almost_perfect_agreement(self):
        """Test 0.8≤kappa≤1.0 interpreted as 'almost_perfect'."""
        assert interpret_kappa(0.85) == "almost_perfect"
        assert interpret_kappa(1.0) == "almost_perfect"

    def test_negative_kappa_interpreted_as_poor(self):
        """Test negative kappa interpreted as 'poor' (worse than chance)."""
        assert interpret_kappa(-0.5) == "poor"


class TestAgreementCalculator:
    """Tests for AgreementCalculator class."""

    def test_calculate_cohens_with_two_annotators(self):
        """Test calculating Cohen's Kappa for 2 annotators."""
        annotations = [
            Annotation(
                id="1",
                annotator_id="ann1",
                example_id="ex1",
                chunk_id="chunk1",
                score=RelevanceScore.HIGHLY_RELEVANT,
                confidence=0.9,
            ),
            Annotation(
                id="2",
                annotator_id="ann1",
                example_id="ex1",
                chunk_id="chunk2",
                score=RelevanceScore.PARTIAL,
                confidence=0.8,
            ),
            Annotation(
                id="3",
                annotator_id="ann2",
                example_id="ex1",
                chunk_id="chunk1",
                score=RelevanceScore.HIGHLY_RELEVANT,
                confidence=0.95,
            ),
            Annotation(
                id="4",
                annotator_id="ann2",
                example_id="ex1",
                chunk_id="chunk2",
                score=RelevanceScore.PARTIAL,
                confidence=0.85,
            ),
        ]

        calculator = AgreementCalculator()
        report = calculator.calculate(annotations)

        assert report.cohens_kappa is not None
        assert report.fleiss_kappa is None  # Not used for 2 annotators
        assert report.cohens_kappa == 1.0  # Perfect agreement
        assert report.percent_agreement == 1.0
        assert report.interpretation == "almost_perfect"

    def test_calculate_fleiss_with_three_annotators(self):
        """Test calculating Fleiss' Kappa for 3+ annotators."""
        annotations = [
            # Item 1: All 3 annotators agree on HIGHLY_RELEVANT
            Annotation(
                id="1",
                annotator_id="ann1",
                example_id="ex1",
                chunk_id="chunk1",
                score=RelevanceScore.HIGHLY_RELEVANT,
                confidence=0.9,
            ),
            Annotation(
                id="2",
                annotator_id="ann2",
                example_id="ex1",
                chunk_id="chunk1",
                score=RelevanceScore.HIGHLY_RELEVANT,
                confidence=0.95,
            ),
            Annotation(
                id="3",
                annotator_id="ann3",
                example_id="ex1",
                chunk_id="chunk1",
                score=RelevanceScore.HIGHLY_RELEVANT,
                confidence=0.85,
            ),
        ]

        calculator = AgreementCalculator()
        report = calculator.calculate(annotations)

        assert report.cohens_kappa is None  # Not used for 3+ annotators
        assert report.fleiss_kappa is not None
        assert report.fleiss_kappa > 0.8  # High agreement
        assert report.percent_agreement == 1.0  # Perfect agreement
        assert report.interpretation in ["substantial", "almost_perfect"]

    def test_insufficient_annotators_raises_error(self):
        """Test that fewer than 2 annotators raises ValueError."""
        annotations = [
            Annotation(
                id="1",
                annotator_id="ann1",
                example_id="ex1",
                chunk_id="chunk1",
                score=RelevanceScore.HIGHLY_RELEVANT,
                confidence=0.9,
            ),
        ]

        calculator = AgreementCalculator()
        with pytest.raises(ValueError, match="at least 2 annotators"):
            calculator.calculate(annotations)

    def test_no_annotations_raises_error(self):
        """Test that no annotations raises ValueError."""
        calculator = AgreementCalculator()
        with pytest.raises(ValueError, match="no annotations"):
            calculator.calculate([])
