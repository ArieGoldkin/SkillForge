"""Integration tests for search API endpoint.

Tests the full search flow including:
- API endpoint validation
- Database query execution (requires database)
- Response format validation
- Error handling

Note: These tests require a running PostgreSQL database with pgvector extension.
They will be skipped if DATABASE_URL is not configured.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture
def test_client():
    """Create a test client for the FastAPI app."""
    return TestClient(app)


class TestSearchAPIValidation:
    """Tests for search API input validation."""

    def test_search_empty_query_returns_422(self, test_client):
        """Test that empty query returns 422 validation error."""
        response = test_client.post(
            "/api/v1/search",
            json={"query": "", "mode": "hybrid", "top_k": 10},
        )
        assert response.status_code == 422  # Pydantic validation

    def test_search_missing_query_returns_422(self, test_client):
        """Test that missing query field returns 422."""
        response = test_client.post(
            "/api/v1/search",
            json={"mode": "hybrid", "top_k": 10},
        )
        assert response.status_code == 422

    def test_search_invalid_mode_returns_422(self, test_client):
        """Test that invalid mode returns 422."""
        response = test_client.post(
            "/api/v1/search",
            json={"query": "test query", "mode": "invalid_mode", "top_k": 10},
        )
        assert response.status_code == 422

    def test_search_top_k_below_minimum_returns_422(self, test_client):
        """Test that top_k below 1 returns 422."""
        response = test_client.post(
            "/api/v1/search",
            json={"query": "test query", "mode": "hybrid", "top_k": 0},
        )
        assert response.status_code == 422

    def test_search_top_k_above_maximum_returns_422(self, test_client):
        """Test that top_k above 100 returns 422."""
        response = test_client.post(
            "/api/v1/search",
            json={"query": "test query", "mode": "hybrid", "top_k": 101},
        )
        assert response.status_code == 422

    def test_search_query_too_long_returns_422(self, test_client):
        """Test that query exceeding 1000 chars returns 422."""
        long_query = "a" * 1001
        response = test_client.post(
            "/api/v1/search",
            json={"query": long_query, "mode": "hybrid", "top_k": 10},
        )
        assert response.status_code == 422


class TestSearchAPIResponseFormat:
    """Tests for search API response format."""

    def test_search_returns_correct_response_structure(self, test_client):
        """Test that search returns correctly formatted response."""
        with (
            patch("app.api.v1.analysis.search.EmbeddingService") as mock_embed_class,
            patch("app.api.v1.analysis.search.SearchService") as mock_search_class,
        ):
            # Mock embedding service
            mock_embed = MagicMock()
            mock_embed.close = AsyncMock()
            mock_embed_class.return_value = mock_embed

            # Mock search service to return empty results
            mock_search = MagicMock()
            mock_search.search = AsyncMock(return_value=[])
            mock_search_class.return_value = mock_search

            response = test_client.post(
                "/api/v1/search",
                json={"query": "test query", "mode": "hybrid", "top_k": 10},
            )

            assert response.status_code == 200
            data = response.json()

            # Verify response structure
            assert "results" in data
            assert "total" in data
            assert "query" in data
            assert "mode" in data

            # Verify types
            assert isinstance(data["results"], list)
            assert isinstance(data["total"], int)
            assert data["query"] == "test query"
            assert data["mode"] == "hybrid"

    def test_search_accepts_all_modes(self, test_client):
        """Test that all search modes are accepted."""
        with (
            patch("app.api.v1.analysis.search.EmbeddingService") as mock_embed_class,
            patch("app.api.v1.analysis.search.SearchService") as mock_search_class,
        ):
            mock_embed = MagicMock()
            mock_embed.close = AsyncMock()
            mock_embed_class.return_value = mock_embed

            mock_search = MagicMock()
            mock_search.search = AsyncMock(return_value=[])
            mock_search_class.return_value = mock_search

            for mode in ["semantic", "keyword", "hybrid"]:
                response = test_client.post(
                    "/api/v1/search",
                    json={"query": "test", "mode": mode, "top_k": 5},
                )
                assert response.status_code == 200, f"Mode {mode} failed"
                assert response.json()["mode"] == mode

    def test_search_with_filters(self, test_client):
        """Test that search accepts filter parameters."""
        with (
            patch("app.api.v1.analysis.search.EmbeddingService") as mock_embed_class,
            patch("app.api.v1.analysis.search.SearchService") as mock_search_class,
        ):
            mock_embed = MagicMock()
            mock_embed.close = AsyncMock()
            mock_embed_class.return_value = mock_embed

            mock_search = MagicMock()
            mock_search.search = AsyncMock(return_value=[])
            mock_search_class.return_value = mock_search

            response = test_client.post(
                "/api/v1/search",
                json={
                    "query": "test query",
                    "mode": "hybrid",
                    "top_k": 10,
                    "filters": {"content_type": "article"},
                },
            )

            assert response.status_code == 200

    def test_search_default_values(self, test_client):
        """Test that search uses correct default values."""
        with (
            patch("app.api.v1.analysis.search.EmbeddingService") as mock_embed_class,
            patch("app.api.v1.analysis.search.SearchService") as mock_search_class,
        ):
            mock_embed = MagicMock()
            mock_embed.close = AsyncMock()
            mock_embed_class.return_value = mock_embed

            mock_search = MagicMock()
            mock_search.search = AsyncMock(return_value=[])
            mock_search_class.return_value = mock_search

            # Only provide required query field
            response = test_client.post(
                "/api/v1/search",
                json={"query": "test query"},
            )

            assert response.status_code == 200
            data = response.json()

            # Default mode should be hybrid
            assert data["mode"] == "hybrid"


class TestSearchAPIErrorHandling:
    """Tests for search API error handling."""

    def test_search_embedding_error_returns_500(self, test_client):
        """Test that embedding errors return 500."""
        from app.core.exceptions import EmbeddingError

        with (
            patch("app.api.v1.analysis.search.EmbeddingService") as mock_embed_class,
            patch("app.api.v1.analysis.search.SearchService") as mock_search_class,
        ):
            mock_embed = MagicMock()
            mock_embed.close = AsyncMock()
            mock_embed_class.return_value = mock_embed

            mock_search = MagicMock()
            mock_search.search = AsyncMock(side_effect=EmbeddingError("API error"))
            mock_search_class.return_value = mock_search

            response = test_client.post(
                "/api/v1/search",
                json={"query": "test query", "mode": "semantic"},
            )

            assert response.status_code == 500
            # API returns generic error message for security (no internal details exposed)
            assert response.json()["detail"] == "Search failed"

    def test_search_value_error_returns_400(self, test_client):
        """Test that validation errors return 400."""
        with (
            patch("app.api.v1.analysis.search.EmbeddingService") as mock_embed_class,
            patch("app.api.v1.analysis.search.SearchService") as mock_search_class,
        ):
            mock_embed = MagicMock()
            mock_embed.close = AsyncMock()
            mock_embed_class.return_value = mock_embed

            mock_search = MagicMock()
            mock_search.search = AsyncMock(side_effect=ValueError("Invalid parameter"))
            mock_search_class.return_value = mock_search

            response = test_client.post(
                "/api/v1/search",
                json={"query": "test query"},
            )

            assert response.status_code == 400

    def test_search_generic_error_returns_500(self, test_client):
        """Test that generic errors return 500."""
        with (
            patch("app.api.v1.analysis.search.EmbeddingService") as mock_embed_class,
            patch("app.api.v1.analysis.search.SearchService") as mock_search_class,
        ):
            mock_embed = MagicMock()
            mock_embed.close = AsyncMock()
            mock_embed_class.return_value = mock_embed

            mock_search = MagicMock()
            mock_search.search = AsyncMock(side_effect=RuntimeError("Unexpected error"))
            mock_search_class.return_value = mock_search

            response = test_client.post(
                "/api/v1/search",
                json={"query": "test query"},
            )

            assert response.status_code == 500
            assert response.json()["detail"] == "Search failed"


class TestSearchAPIMockedResults:
    """Tests for search API with mocked search results."""

    def test_search_returns_results_with_correct_fields(self, test_client):
        """Test that search results contain all expected fields."""
        from datetime import UTC, datetime

        from app.schemas.search import ChunkMetadata, SearchResult

        mock_result = SearchResult(
            chunk_id="chunk-123",
            analysis_id="analysis-456",
            content="Test content about OAuth2 authentication.",
            snippet="Test content about <mark>OAuth2</mark> authentication.",
            score=0.95,
            metadata=ChunkMetadata(
                section="Authentication",
                path="Intro > Auth",
                content_type="article",
                chunk_type="paragraph",
            ),
            created_at=datetime.now(UTC),
        )

        with (
            patch("app.api.v1.analysis.search.EmbeddingService") as mock_embed_class,
            patch("app.api.v1.analysis.search.SearchService") as mock_search_class,
        ):
            mock_embed = MagicMock()
            mock_embed.close = AsyncMock()
            mock_embed_class.return_value = mock_embed

            mock_search = MagicMock()
            mock_search.search = AsyncMock(return_value=[mock_result])
            mock_search_class.return_value = mock_search

            response = test_client.post(
                "/api/v1/search",
                json={"query": "OAuth2", "mode": "hybrid"},
            )

            assert response.status_code == 200
            data = response.json()

            assert data["total"] == 1
            result = data["results"][0]

            # Verify result fields
            assert result["chunk_id"] == "chunk-123"
            assert result["analysis_id"] == "analysis-456"
            assert result["content"] == "Test content about OAuth2 authentication."
            assert "<mark>" in result["snippet"]
            assert result["score"] == 0.95
            assert result["metadata"]["section"] == "Authentication"
            assert result["metadata"]["chunk_type"] == "paragraph"
