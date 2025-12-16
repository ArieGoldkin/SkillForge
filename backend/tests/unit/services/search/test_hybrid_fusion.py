"""Unit tests for Reciprocal Rank Fusion algorithm."""

from app.shared.services.search.hybrid_fusion import reciprocal_rank_fusion
import pytest

@pytest.mark.unit


class TestReciprocalRankFusion:
    """Tests for the RRF algorithm implementation."""

    def test_basic_fusion_two_lists(self):
        """Test basic fusion of two result lists."""
        semantic = [("doc1", 0.95), ("doc2", 0.80), ("doc3", 0.75)]
        keyword = [("doc2", 10.5), ("doc1", 8.2), ("doc4", 7.1)]

        result = reciprocal_rank_fusion([semantic, keyword])

        # doc2 appears first in keyword (rank 1) and second in semantic (rank 2)
        # doc1 appears first in semantic (rank 1) and second in keyword (rank 2)
        # Both should have same RRF score, but order depends on dict iteration
        assert len(result) == 4
        top_items = [item for item, _ in result[:2]]
        assert "doc1" in top_items
        assert "doc2" in top_items

    def test_empty_lists(self):
        """Test fusion with empty input."""
        result = reciprocal_rank_fusion([])
        assert result == []

    def test_single_list(self):
        """Test fusion with single list."""
        single = [("doc1", 0.9), ("doc2", 0.8)]
        result = reciprocal_rank_fusion([single])

        assert len(result) == 2
        assert result[0][0] == "doc1"  # Higher rank
        assert result[1][0] == "doc2"

    def test_custom_k_parameter(self):
        """Test that k parameter affects scores."""
        results = [("doc1", 1.0)]

        # With k=60 (default), score = 1/(60+1) ≈ 0.0164
        result_k60 = reciprocal_rank_fusion([results], k=60)
        # With k=10, score = 1/(10+1) ≈ 0.0909
        result_k10 = reciprocal_rank_fusion([results], k=10)

        assert result_k10[0][1] > result_k60[0][1]

    def test_unique_items_combined(self):
        """Test that items appearing in multiple lists get higher scores."""
        list1 = [("shared", 1.0), ("only1", 0.9)]
        list2 = [("shared", 1.0), ("only2", 0.9)]

        result = reciprocal_rank_fusion([list1, list2])

        # "shared" should have highest score (appears in both)
        assert result[0][0] == "shared"

    def test_score_calculation(self):
        """Test exact RRF score calculation."""
        # Single item, single list, rank 1: score = 1/(60+1) = 1/61
        result = reciprocal_rank_fusion([[("doc", 1.0)]], k=60)
        expected_score = 1.0 / (60 + 1)
        assert abs(result[0][1] - expected_score) < 0.0001

    def test_preserves_all_items(self):
        """Test that all unique items are preserved."""
        list1 = [("a", 1), ("b", 2)]
        list2 = [("c", 1), ("d", 2)]
        list3 = [("e", 1)]

        result = reciprocal_rank_fusion([list1, list2, list3])

        result_items = {item for item, _ in result}
        assert result_items == {"a", "b", "c", "d", "e"}

    def test_descending_order(self):
        """Test that results are sorted by score descending."""
        results = [("a", 1), ("b", 2), ("c", 3)]
        result = reciprocal_rank_fusion([results])

        scores = [score for _, score in result]
        assert scores == sorted(scores, reverse=True)
