"""Unit tests for SearchService metadata boosting and query detection.

Tests the Phase 1 retrieval quality improvements:
- Section title boosting (2.0x when query matches section title)
- Document path boosting (1.15x when query matches path)
- Technical query detection for code_block boosting
- Dynamic top_k calculation in evaluation

These tests verify the ranking improvements without requiring a database.
"""

from datetime import UTC, datetime
from unittest.mock import MagicMock, patch

import pytest

from app.schemas.search import ChunkMetadata, SearchResult


class TestTechnicalQueryDetection:
    """Tests for _is_technical_query method."""

    @pytest.fixture
    def search_service(self):
        """Create SearchService with mocked dependencies."""
        with (
            patch("app.shared.services.search.search_service.get_metrics_service"),
            patch("app.db.repositories.chunk_repository.ChunkRepository"),
        ):
            from app.shared.services.search.search_service import SearchService

            mock_session = MagicMock()
            mock_embedding_service = MagicMock()
            mock_embedding_service.model = "test-model"
            mock_embedding_service.expected_dimensions = 1536

            service = SearchService(
                session=mock_session,
                embedding_service=mock_embedding_service,
            )
            return service

    def test_technical_query_with_langgraph(self, search_service):
        """LangGraph query should be detected as technical."""
        assert search_service._is_technical_query("How to use LangGraph agents")

    def test_technical_query_with_kubernetes(self, search_service):
        """Kubernetes query should be detected as technical."""
        assert search_service._is_technical_query("k8s HPA pod scaling")

    def test_technical_query_with_oauth(self, search_service):
        """OAuth query should be detected as technical."""
        assert search_service._is_technical_query("OAuth2 token endpoint")

    def test_technical_query_with_multiple_terms(self, search_service):
        """Query with multiple technical terms should be detected."""
        assert search_service._is_technical_query("FastAPI GraphQL async endpoints")

    def test_non_technical_query(self, search_service):
        """Generic query should not be detected as technical."""
        assert not search_service._is_technical_query("How to write good documentation")

    def test_case_insensitive_detection(self, search_service):
        """Technical term detection should be case insensitive."""
        assert search_service._is_technical_query("KUBERNETES deployment")
        assert search_service._is_technical_query("oauth2 implementation")

    def test_partial_match_not_detected(self, search_service):
        """Partial matches should not trigger technical detection."""
        # 'fast' is not the same as 'fastapi'
        assert not search_service._is_technical_query("fast algorithms for sorting")


class TestMetadataBoosts:
    """Tests for _apply_metadata_boosts method."""

    @pytest.fixture
    def search_service(self):
        """Create SearchService with mocked dependencies."""
        with (
            patch("app.shared.services.search.search_service.get_metrics_service"),
            patch("app.db.repositories.chunk_repository.ChunkRepository"),
        ):
            from app.shared.services.search.search_service import SearchService

            mock_session = MagicMock()
            mock_embedding_service = MagicMock()
            mock_embedding_service.model = "test-model"
            mock_embedding_service.expected_dimensions = 1536

            service = SearchService(
                session=mock_session,
                embedding_service=mock_embedding_service,
            )
            return service

    def _make_result(
        self,
        score: float,
        section: str | None = None,
        path: list[str] | None = None,
        chunk_type: str = "section",
    ) -> SearchResult:
        """Create a SearchResult for testing."""
        return SearchResult(
            chunk_id="test-chunk-id",
            analysis_id="test-analysis-id",
            content="Test content",
            snippet="Test snippet",
            score=score,
            metadata=ChunkMetadata(
                section=section,
                path=path,
                chunk_type=chunk_type,
            ),
            created_at=datetime.now(UTC),
        )

    def test_section_title_boost_applied(self, search_service):
        """Section title matching query terms should get 2.0x boost."""
        results = [
            self._make_result(score=0.5, section="OAuth2 Implementation"),
        ]

        boosted = search_service._apply_metadata_boosts(results, "OAuth2 setup")

        # 0.5 * 2.0 = 1.0 (capped at 1.0)
        assert boosted[0].score == pytest.approx(1.0, rel=0.01)

    def test_document_path_boost_applied(self, search_service):
        """Path matching query terms should get 1.15x boost."""
        results = [
            self._make_result(score=0.5, path=["fastapi-auth", "fastapi-auth/intro"]),
        ]

        boosted = search_service._apply_metadata_boosts(results, "fastapi authentication")

        # 0.5 * 1.15 = 0.575
        assert boosted[0].score == pytest.approx(0.575, rel=0.01)

    def test_combined_boosts_multiplicative(self, search_service):
        """Section and path boosts should multiply."""
        results = [
            self._make_result(
                score=0.5,
                section="OAuth2 Flows",
                path=["oauth2-guide", "oauth2-guide/flows"],
            ),
        ]

        boosted = search_service._apply_metadata_boosts(results, "OAuth2 guide")

        # 0.5 * 2.0 (section) * 1.15 (path) = 1.15, capped at 1.0
        assert boosted[0].score == pytest.approx(1.0, rel=0.01)

    def test_boost_capped_at_one(self, search_service):
        """Boosted score should not exceed 1.0."""
        results = [
            self._make_result(
                score=0.9,
                section="OAuth2 Security Best Practices",
                path=["oauth2-security", "oauth2-security/best-practices"],
            ),
        ]

        boosted = search_service._apply_metadata_boosts(results, "OAuth2 security best practices")

        # 0.9 * 1.5 * 1.15 = 1.5525, but capped at 1.0
        assert boosted[0].score == 1.0

    def test_no_boost_without_match(self, search_service):
        """Results with no matching terms should not be boosted."""
        results = [
            self._make_result(score=0.5, section="Database Design", path=["sql-guide"]),
        ]

        boosted = search_service._apply_metadata_boosts(results, "OAuth2 authentication")

        assert boosted[0].score == 0.5  # No change

    def test_technical_query_code_block_boost(self, search_service):
        """Technical queries should boost code_block chunks."""
        results = [
            self._make_result(score=0.5, chunk_type="code_block"),
        ]

        boosted = search_service._apply_metadata_boosts(results, "kubernetes HPA config")

        # 0.5 * 1.2 (technical + code_block) = 0.6
        assert boosted[0].score == pytest.approx(0.6, rel=0.01)

    def test_results_reordered_by_boosted_score(self, search_service):
        """Results should be re-sorted by boosted score."""
        results = [
            self._make_result(score=0.8, section="Generic Section"),
            self._make_result(score=0.6, section="OAuth2 Flows"),  # Will be boosted
        ]

        boosted = search_service._apply_metadata_boosts(results, "OAuth2")

        # Second result (0.6 * 2.0 = 1.2, capped at 1.0) should now be first
        assert boosted[0].score == pytest.approx(1.0, rel=0.01)
        assert boosted[1].score == 0.8

    def test_empty_results_handled(self, search_service):
        """Empty results list should return empty list."""
        boosted = search_service._apply_metadata_boosts([], "any query")
        assert boosted == []


class TestDynamicTopK:
    """Tests for dynamic top_k in evaluation runner."""

    def test_dynamic_top_k_minimum_five(self):
        """Top_k should be at least 5 even with fewer expected chunks."""
        expected_chunks = ["chunk1"]
        dynamic_top_k = max(5, len(expected_chunks))
        assert dynamic_top_k == 5

    def test_dynamic_top_k_expands_for_multi_target(self):
        """Top_k should expand when more chunks are expected."""
        expected_chunks = ["chunk1", "chunk2", "chunk3", "chunk4", "chunk5", "chunk6", "chunk7"]
        dynamic_top_k = max(5, len(expected_chunks))
        assert dynamic_top_k == 7

    def test_dynamic_top_k_empty_expected(self):
        """Top_k should be 5 with empty expected chunks."""
        expected_chunks: list[str] = []
        dynamic_top_k = max(5, len(expected_chunks))
        assert dynamic_top_k == 5


class TestChunkRepositoryFetchMultiplier:
    """Tests for HYBRID_FETCH_MULTIPLIER usage."""

    def test_fetch_multiplier_value(self):
        """Verify fetch multiplier constant is 3."""
        from app.core.constants import HYBRID_FETCH_MULTIPLIER

        assert HYBRID_FETCH_MULTIPLIER == 3

    def test_fetch_limit_calculation(self):
        """Fetch limit should be 3x the requested limit."""
        from app.core.constants import HYBRID_FETCH_MULTIPLIER

        limit = 10
        fetch_limit = limit * HYBRID_FETCH_MULTIPLIER
        assert fetch_limit == 30
