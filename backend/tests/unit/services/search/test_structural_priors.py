"""Unit tests for StructuralPriorScorer.

Tests cover:
- Section presence boost
- Path depth penalty
- Position-based scoring (early/late)
- Chunk type bonuses
- Batch scoring
- Custom weights
"""

import pytest

from app.core.constants import (
    STRUCTURAL_PATH_DEPTH_THRESHOLD,
    STRUCTURAL_WEIGHT_CODE_BLOCK,
    STRUCTURAL_WEIGHT_HEADING,
    STRUCTURAL_WEIGHT_PATH_DEPTH_PENALTY,
    STRUCTURAL_WEIGHT_POSITION_EARLY,
    STRUCTURAL_WEIGHT_POSITION_LATE,
    STRUCTURAL_WEIGHT_SECTION_PRESENT,
)
from app.schemas.search import ChunkMetadata
from app.shared.services.search.structural_priors import StructuralPriorScorer, StructuralWeights


@pytest.mark.unit
class TestStructuralPriorScorerSectionBoost:
    """Tests for section presence boost."""

    def test_section_present_adds_boost(self):
        """Test that section presence adds the expected boost."""
        scorer = StructuralPriorScorer()
        metadata = ChunkMetadata(section="Introduction")

        score = scorer.score_single(metadata)

        assert score == STRUCTURAL_WEIGHT_SECTION_PRESENT

    def test_section_absent_no_boost(self):
        """Test that absent section gives no boost."""
        scorer = StructuralPriorScorer()
        metadata = ChunkMetadata()

        score = scorer.score_single(metadata)

        assert score == 0.0

    def test_empty_section_no_boost(self):
        """Test that empty section string gives no boost."""
        scorer = StructuralPriorScorer()
        metadata = ChunkMetadata(section="")

        score = scorer.score_single(metadata)

        assert score == 0.0


class TestStructuralPriorScorerPathDepth:
    """Tests for path depth penalty."""

    def test_shallow_path_no_penalty(self):
        """Test that shallow path (depth <= 2) has no penalty."""
        scorer = StructuralPriorScorer()
        metadata = ChunkMetadata(path=["Level1", "Level2"])

        score = scorer.score_single(metadata)

        assert score == 0.0

    def test_deep_path_applies_penalty(self):
        """Test that deep path applies penalty per extra level."""
        scorer = StructuralPriorScorer()
        # Depth 4 = 2 levels beyond threshold
        metadata = ChunkMetadata(path=["L1", "L2", "L3", "L4"])

        score = scorer.score_single(metadata)

        expected_penalty = -STRUCTURAL_WEIGHT_PATH_DEPTH_PENALTY * (
            4 - STRUCTURAL_PATH_DEPTH_THRESHOLD
        )
        assert score == expected_penalty

    def test_empty_path_no_penalty(self):
        """Test that empty path has no penalty."""
        scorer = StructuralPriorScorer()
        metadata = ChunkMetadata(path=[])

        score = scorer.score_single(metadata)

        assert score == 0.0

    def test_none_path_no_penalty(self):
        """Test that None path has no penalty."""
        scorer = StructuralPriorScorer()
        metadata = ChunkMetadata(path=None)

        score = scorer.score_single(metadata)

        assert score == 0.0


class TestStructuralPriorScorerPosition:
    """Tests for position-based scoring."""

    def test_early_position_adds_boost(self):
        """Test that early position (first 20%) adds boost."""
        scorer = StructuralPriorScorer()
        # Position 1 out of 10 = 0.1 ratio (< 0.2 threshold)
        metadata = ChunkMetadata(chunk_idx=1, chunk_total=10)

        score = scorer.score_single(metadata)

        assert score == STRUCTURAL_WEIGHT_POSITION_EARLY

    def test_late_position_applies_penalty(self):
        """Test that late position (last 20%) applies penalty."""
        scorer = StructuralPriorScorer()
        # Position 9 out of 10 = 0.9 ratio (> 0.8 threshold)
        metadata = ChunkMetadata(chunk_idx=9, chunk_total=10)

        score = scorer.score_single(metadata)

        assert score == STRUCTURAL_WEIGHT_POSITION_LATE

    def test_middle_position_neutral(self):
        """Test that middle position has no effect."""
        scorer = StructuralPriorScorer()
        # Position 5 out of 10 = 0.5 ratio (between thresholds)
        metadata = ChunkMetadata(chunk_idx=5, chunk_total=10)

        score = scorer.score_single(metadata)

        assert score == 0.0

    def test_zero_position_is_early(self):
        """Test that position 0 counts as early."""
        scorer = StructuralPriorScorer()
        metadata = ChunkMetadata(chunk_idx=0, chunk_total=10)

        score = scorer.score_single(metadata)

        assert score == STRUCTURAL_WEIGHT_POSITION_EARLY

    def test_missing_position_info_neutral(self):
        """Test that missing position info has no effect."""
        scorer = StructuralPriorScorer()
        metadata = ChunkMetadata(chunk_idx=None, chunk_total=None)

        score = scorer.score_single(metadata)

        assert score == 0.0

    def test_zero_total_handled_safely(self):
        """Test that zero chunk_total is handled without division error."""
        scorer = StructuralPriorScorer()
        metadata = ChunkMetadata(chunk_idx=0, chunk_total=0)

        # Should not raise, uses max(chunk_total, 1)
        score = scorer.score_single(metadata)

        # 0/1 = 0.0, which is < early threshold
        assert score == STRUCTURAL_WEIGHT_POSITION_EARLY


class TestStructuralPriorScorerChunkType:
    """Tests for chunk type bonuses."""

    def test_code_block_adds_boost(self):
        """Test that code_block type adds boost."""
        scorer = StructuralPriorScorer()
        metadata = ChunkMetadata(chunk_type="code_block")

        score = scorer.score_single(metadata)

        assert score == STRUCTURAL_WEIGHT_CODE_BLOCK

    def test_heading_adds_boost(self):
        """Test that heading type adds boost."""
        scorer = StructuralPriorScorer()
        metadata = ChunkMetadata(chunk_type="heading")

        score = scorer.score_single(metadata)

        assert score == STRUCTURAL_WEIGHT_HEADING

    def test_paragraph_type_neutral(self):
        """Test that paragraph type has no bonus."""
        scorer = StructuralPriorScorer()
        metadata = ChunkMetadata(chunk_type="paragraph")

        score = scorer.score_single(metadata)

        assert score == 0.0

    def test_unknown_type_neutral(self):
        """Test that unknown chunk type has no bonus."""
        scorer = StructuralPriorScorer()
        metadata = ChunkMetadata(chunk_type="unknown_type")

        score = scorer.score_single(metadata)

        assert score == 0.0


class TestStructuralPriorScorerCombined:
    """Tests for combined scoring scenarios."""

    def test_all_positive_signals(self):
        """Test combining all positive signals."""
        scorer = StructuralPriorScorer()
        metadata = ChunkMetadata(
            section="Introduction",
            path=["Level1"],  # Shallow path
            chunk_idx=0,
            chunk_total=10,  # Early position
            chunk_type="heading",
        )

        score = scorer.score_single(metadata)

        expected = (
            STRUCTURAL_WEIGHT_SECTION_PRESENT
            + STRUCTURAL_WEIGHT_POSITION_EARLY
            + STRUCTURAL_WEIGHT_HEADING
        )
        assert score == expected

    def test_mixed_signals(self):
        """Test combining positive and negative signals."""
        scorer = StructuralPriorScorer()
        metadata = ChunkMetadata(
            section="Deep Section",  # +0.10
            path=["L1", "L2", "L3", "L4"],  # -0.10 (2 extra levels)
            chunk_idx=9,
            chunk_total=10,  # Late position: -0.05
            chunk_type="code_block",  # +0.05
        )

        score = scorer.score_single(metadata)

        expected = (
            STRUCTURAL_WEIGHT_SECTION_PRESENT
            - STRUCTURAL_WEIGHT_PATH_DEPTH_PENALTY * 2  # 2 levels beyond threshold
            + STRUCTURAL_WEIGHT_POSITION_LATE  # Already negative
            + STRUCTURAL_WEIGHT_CODE_BLOCK
        )
        assert score == expected


class TestStructuralPriorScorerBatch:
    """Tests for batch scoring."""

    def test_batch_scoring_returns_correct_count(self):
        """Test that batch scoring returns score for each input."""
        scorer = StructuralPriorScorer()
        metadata_list = [
            ChunkMetadata(section="Sec1"),
            ChunkMetadata(section="Sec2"),
            ChunkMetadata(),
        ]

        scores = scorer.score_batch(metadata_list)

        assert len(scores) == 3

    def test_batch_scoring_matches_single_scoring(self):
        """Test that batch scoring matches individual scoring."""
        scorer = StructuralPriorScorer()
        metadata_list = [
            ChunkMetadata(section="Introduction", chunk_type="heading"),
            ChunkMetadata(path=["L1", "L2", "L3", "L4"]),
            ChunkMetadata(chunk_idx=0, chunk_total=10),
        ]

        batch_scores = scorer.score_batch(metadata_list)
        single_scores = [scorer.score_single(m) for m in metadata_list]

        assert batch_scores == single_scores

    def test_empty_batch_returns_empty_list(self):
        """Test that empty batch returns empty list."""
        scorer = StructuralPriorScorer()

        scores = scorer.score_batch([])

        assert scores == []


class TestStructuralPriorScorerCustomWeights:
    """Tests for custom weight configuration."""

    def test_custom_weights_override_defaults(self):
        """Test that custom weights override default values."""
        custom_weights = StructuralWeights(
            section_present=0.5,
            position_early=0.3,
        )
        scorer = StructuralPriorScorer(weights=custom_weights)
        metadata = ChunkMetadata(section="Test", chunk_idx=0, chunk_total=10)

        score = scorer.score_single(metadata)

        # Should use custom weights: 0.5 + 0.3 = 0.8
        assert score == 0.8

    def test_default_weights_match_constants(self):
        """Test that default weights match constant values."""
        scorer = StructuralPriorScorer()

        assert scorer.weights.section_present == STRUCTURAL_WEIGHT_SECTION_PRESENT
        assert scorer.weights.path_depth_penalty == STRUCTURAL_WEIGHT_PATH_DEPTH_PENALTY
        assert scorer.weights.position_early == STRUCTURAL_WEIGHT_POSITION_EARLY
        assert scorer.weights.position_late == STRUCTURAL_WEIGHT_POSITION_LATE
        assert scorer.weights.code_block == STRUCTURAL_WEIGHT_CODE_BLOCK
        assert scorer.weights.heading == STRUCTURAL_WEIGHT_HEADING
