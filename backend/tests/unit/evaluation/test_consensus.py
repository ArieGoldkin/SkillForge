"""Unit tests for consensus algorithm module.

Tests cover:
- 2/3 majority rule for inclusion/exclusion
- High variance triggering manual review
- Insufficient annotators handling
- Edge cases: ties, unanimous decisions, missing data
"""

import pytest

from app.evaluation.validation.consensus import ConsensusAlgorithm, batch_consensus
from app.evaluation.validation.models import Annotation, RelevanceScore


class TestConsensusAlgorithm:
    """Tests for consensus decision-making algorithm."""

    def test_unanimous_include_high_confidence(self):
        """Test unanimous include (all ≥2) has high confidence and low variance."""
        algorithm = ConsensusAlgorithm(
            variance_threshold=1.0, include_threshold=2.0, min_annotators=2
        )

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

        result = algorithm.compute_consensus("ex1", "chunk1", annotations)

        assert result.final_decision == "include"
        assert result.mean_score == 3.0
        assert result.variance == 0.0  # All same score
        assert result.confidence > 0.8  # High confidence
        assert not result.requires_expert_review

    def test_unanimous_exclude_high_confidence(self):
        """Test unanimous exclude (all ≤1) has high confidence."""
        algorithm = ConsensusAlgorithm()

        annotations = [
            Annotation(
                id="1",
                annotator_id="ann1",
                example_id="ex1",
                chunk_id="chunk1",
                score=RelevanceScore.IRRELEVANT,
                confidence=0.9,
            ),
            Annotation(
                id="2",
                annotator_id="ann2",
                example_id="ex1",
                chunk_id="chunk1",
                score=RelevanceScore.IRRELEVANT,
                confidence=0.95,
            ),
        ]

        result = algorithm.compute_consensus("ex1", "chunk1", annotations)

        assert result.final_decision == "exclude"
        assert result.mean_score == 0.0
        assert result.variance == 0.0
        assert result.confidence > 0.8
        assert not result.requires_expert_review

    def test_high_variance_triggers_review(self):
        """Test high variance (>1.0) triggers REVIEW decision."""
        algorithm = ConsensusAlgorithm(variance_threshold=1.0)

        annotations = [
            Annotation(
                id="1",
                annotator_id="ann1",
                example_id="ex1",
                chunk_id="chunk1",
                score=RelevanceScore.IRRELEVANT,
                confidence=0.8,
            ),
            Annotation(
                id="2",
                annotator_id="ann2",
                example_id="ex1",
                chunk_id="chunk1",
                score=RelevanceScore.HIGHLY_RELEVANT,
                confidence=0.8,
            ),
        ]

        result = algorithm.compute_consensus("ex1", "chunk1", annotations)

        assert result.final_decision == "review"
        assert result.variance > 1.0  # High variance
        assert result.requires_expert_review
        assert result.confidence < 0.8  # Lower confidence due to disagreement

    def test_majority_include(self):
        """Test 2/3 annotators rating ≥2 results in INCLUDE decision."""
        algorithm = ConsensusAlgorithm()

        annotations = [
            Annotation(
                id="1",
                annotator_id="ann1",
                example_id="ex1",
                chunk_id="chunk1",
                score=RelevanceScore.PARTIAL,
                confidence=0.8,
            ),
            Annotation(
                id="2",
                annotator_id="ann2",
                example_id="ex1",
                chunk_id="chunk1",
                score=RelevanceScore.HIGHLY_RELEVANT,
                confidence=0.9,
            ),
            Annotation(
                id="3",
                annotator_id="ann3",
                example_id="ex1",
                chunk_id="chunk1",
                score=RelevanceScore.TANGENTIAL,
                confidence=0.7,
            ),
        ]

        result = algorithm.compute_consensus("ex1", "chunk1", annotations)

        # Mean score = (2 + 3 + 1) / 3 = 2.0 (exactly at threshold)
        assert result.mean_score == 2.0
        # Variance = var([2, 3, 1]) with ddof=1 = 1.0 (exactly at threshold)
        assert result.variance == 1.0
        # Since variance equals threshold, it's not > threshold, so decision based on mean
        assert result.final_decision == "include"
        assert not result.requires_expert_review

    def test_majority_exclude(self):
        """Test 2/3 annotators rating ≤1 results in EXCLUDE decision."""
        algorithm = ConsensusAlgorithm()

        annotations = [
            Annotation(
                id="1",
                annotator_id="ann1",
                example_id="ex1",
                chunk_id="chunk1",
                score=RelevanceScore.IRRELEVANT,
                confidence=0.8,
            ),
            Annotation(
                id="2",
                annotator_id="ann2",
                example_id="ex1",
                chunk_id="chunk1",
                score=RelevanceScore.TANGENTIAL,
                confidence=0.9,
            ),
            Annotation(
                id="3",
                annotator_id="ann3",
                example_id="ex1",
                chunk_id="chunk1",
                score=RelevanceScore.PARTIAL,
                confidence=0.7,
            ),
        ]

        result = algorithm.compute_consensus("ex1", "chunk1", annotations)

        # Mean score = (0 + 1 + 2) / 3 = 1.0 (below threshold of 2.0)
        assert result.mean_score == 1.0
        assert result.final_decision == "exclude"
        assert not result.requires_expert_review

    def test_insufficient_annotators_raises_error(self):
        """Test insufficient annotators (<min_annotators) raises ValueError."""
        algorithm = ConsensusAlgorithm(min_annotators=2)

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

        with pytest.raises(ValueError, match="at least 2 annotations"):
            algorithm.compute_consensus("ex1", "chunk1", annotations)

    def test_custom_thresholds(self):
        """Test consensus with custom include and variance thresholds."""
        algorithm = ConsensusAlgorithm(
            variance_threshold=0.5, include_threshold=2.5, min_annotators=2
        )

        annotations = [
            Annotation(
                id="1",
                annotator_id="ann1",
                example_id="ex1",
                chunk_id="chunk1",
                score=RelevanceScore.PARTIAL,
                confidence=0.8,
            ),
            Annotation(
                id="2",
                annotator_id="ann2",
                example_id="ex1",
                chunk_id="chunk1",
                score=RelevanceScore.PARTIAL,
                confidence=0.85,
            ),
        ]

        result = algorithm.compute_consensus("ex1", "chunk1", annotations)

        # Mean = 2.0, which is below the custom threshold of 2.5
        assert result.mean_score == 2.0
        assert result.final_decision == "exclude"


class TestBatchConsensus:
    """Tests for batch consensus processing."""

    def test_batch_consensus_multiple_items(self):
        """Test applying consensus algorithm to multiple items."""
        annotations = [
            # Item 1: Include (unanimous)
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
            # Item 2: Exclude (unanimous)
            Annotation(
                id="3",
                annotator_id="ann1",
                example_id="ex1",
                chunk_id="chunk2",
                score=RelevanceScore.IRRELEVANT,
                confidence=0.8,
            ),
            Annotation(
                id="4",
                annotator_id="ann2",
                example_id="ex1",
                chunk_id="chunk2",
                score=RelevanceScore.IRRELEVANT,
                confidence=0.85,
            ),
            # Item 3: Review (high variance)
            Annotation(
                id="5",
                annotator_id="ann1",
                example_id="ex1",
                chunk_id="chunk3",
                score=RelevanceScore.IRRELEVANT,
                confidence=0.7,
            ),
            Annotation(
                id="6",
                annotator_id="ann2",
                example_id="ex1",
                chunk_id="chunk3",
                score=RelevanceScore.HIGHLY_RELEVANT,
                confidence=0.7,
            ),
        ]

        results = batch_consensus(annotations)

        assert len(results) == 3

        # Check each result
        decisions = {r.chunk_id: r.final_decision for r in results}
        assert decisions["chunk1"] == "include"
        assert decisions["chunk2"] == "exclude"
        assert decisions["chunk3"] == "review"

    def test_batch_consensus_skips_insufficient_annotators(self):
        """Test batch consensus skips items with insufficient annotators."""
        annotations = [
            # Valid item with 2 annotators
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
            # Invalid item with only 1 annotator
            Annotation(
                id="3",
                annotator_id="ann1",
                example_id="ex1",
                chunk_id="chunk2",
                score=RelevanceScore.PARTIAL,
                confidence=0.8,
            ),
        ]

        results = batch_consensus(annotations, min_annotators=2)

        # Should only have 1 result (chunk2 skipped)
        assert len(results) == 1
        assert results[0].chunk_id == "chunk1"

    def test_batch_consensus_custom_thresholds(self):
        """Test batch consensus with custom thresholds."""
        annotations = [
            Annotation(
                id="1",
                annotator_id="ann1",
                example_id="ex1",
                chunk_id="chunk1",
                score=RelevanceScore.PARTIAL,
                confidence=0.8,
            ),
            Annotation(
                id="2",
                annotator_id="ann2",
                example_id="ex1",
                chunk_id="chunk1",
                score=RelevanceScore.PARTIAL,
                confidence=0.85,
            ),
        ]

        # With default threshold (2.0), should include
        results_default = batch_consensus(annotations, include_threshold=2.0)
        assert results_default[0].final_decision == "include"

        # With higher threshold (2.5), should exclude
        results_high = batch_consensus(annotations, include_threshold=2.5)
        assert results_high[0].final_decision == "exclude"
