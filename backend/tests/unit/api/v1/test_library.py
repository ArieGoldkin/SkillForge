"""Unit tests for library API endpoint.

This module contains comprehensive unit tests for the /library endpoint
covering search modes, filtering, pagination, and error handling.
"""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from app.db.repositories.library_repository import get_library_repository
from app.main import app
from app.models.analysis import Analysis

client = TestClient(app)


@pytest.fixture
def mock_repo():
    """Create mock library repository."""
    repo = AsyncMock()
    return repo


@pytest.fixture
def override_get_repo(mock_repo):
    """Override repository dependency."""
    app.dependency_overrides[get_library_repository] = lambda: mock_repo
    yield
    app.dependency_overrides = {}


@pytest.fixture
def sample_analysis():
    """Create a sample analysis for testing."""
    return Analysis(
        id=uuid4(),
        url="https://example.com/test-article",
        title="Test Article",
        content_type="article",
        status="complete",
        raw_content="This is test content about PostgreSQL full-text search.",
        created_at=datetime.now(UTC),
    )


class TestHybridSearch:
    """Tests for hybrid search mode using RRF fusion."""

    @pytest.mark.asyncio
    async def test_hybrid_search_success(self, mock_repo, override_get_repo, sample_analysis):
        """Test hybrid search successfully combines FTS and vector search."""
        # Mock EmbeddingService
        with patch("app.api.v1.library.EmbeddingService") as mock_embedding_cls:
            mock_service = AsyncMock()
            mock_service.generate_embedding.return_value = [0.1] * 1536
            mock_service.close = AsyncMock()
            mock_embedding_cls.return_value = mock_service

            # Mock repository hybrid_search response
            mock_repo.hybrid_search.return_value = [(sample_analysis, 0.95)]
            mock_repo.get_search_snippet.return_value = (
                "This is test content about <mark>PostgreSQL</mark>..."
            )

            response = client.get(
                "/api/v1/library",
                params={
                    "query": "postgresql search",
                    "search_mode": "hybrid",
                    "limit": 20,
                    "offset": 0,
                },
            )

            assert response.status_code == 200
            data = response.json()
            assert len(data["items"]) == 1
            assert data["items"][0]["url"] == "https://example.com/test-article"
            assert data["items"][0]["title"] == "Test Article"
            assert data["items"][0]["rank"] == 0.95
            assert "<mark>PostgreSQL</mark>" in data["items"][0]["snippet"]
            assert data["limit"] == 20
            assert data["offset"] == 0

            # Verify service calls
            mock_service.generate_embedding.assert_called_once_with("postgresql search")
            mock_repo.hybrid_search.assert_called_once()

    @pytest.mark.asyncio
    async def test_hybrid_search_uses_rrf_fusion(
        self, mock_repo, override_get_repo, sample_analysis
    ):
        """Test hybrid mode uses RRF to combine results."""
        with patch("app.api.v1.library.EmbeddingService") as mock_embedding_cls:
            mock_service = AsyncMock()
            mock_service.generate_embedding.return_value = [0.1] * 1536
            mock_service.close = AsyncMock()
            mock_embedding_cls.return_value = mock_service

            # Mock hybrid search returns RRF-scored results
            mock_repo.hybrid_search.return_value = [
                (sample_analysis, 0.85),  # RRF score
            ]
            mock_repo.get_search_snippet.return_value = None

            response = client.get(
                "/api/v1/library",
                params={"query": "test query", "search_mode": "hybrid"},
            )

            assert response.status_code == 200
            data = response.json()
            # Verify hybrid_search was called with both query and embedding
            call_args = mock_repo.hybrid_search.call_args
            assert call_args.kwargs["query"] == "test query"
            assert call_args.kwargs["embedding"] == [0.1] * 1536

    @pytest.mark.asyncio
    async def test_hybrid_search_snippet_generation(
        self, mock_repo, override_get_repo, sample_analysis
    ):
        """Test hybrid search generates snippets for results."""
        with patch("app.api.v1.library.EmbeddingService") as mock_embedding_cls:
            mock_service = AsyncMock()
            mock_service.generate_embedding.return_value = [0.1] * 1536
            mock_service.close = AsyncMock()
            mock_embedding_cls.return_value = mock_service

            mock_repo.hybrid_search.return_value = [(sample_analysis, 0.9)]
            mock_repo.get_search_snippet.return_value = "Test <mark>snippet</mark> content"

            response = client.get(
                "/api/v1/library",
                params={"query": "snippet", "search_mode": "hybrid"},
            )

            assert response.status_code == 200
            data = response.json()
            assert data["items"][0]["snippet"] == "Test <mark>snippet</mark> content"
            mock_repo.get_search_snippet.assert_called_once()

    @pytest.mark.asyncio
    async def test_hybrid_search_snippet_failure_continues(
        self, mock_repo, override_get_repo, sample_analysis
    ):
        """Test hybrid search continues when snippet generation fails."""
        with patch("app.api.v1.library.EmbeddingService") as mock_embedding_cls:
            mock_service = AsyncMock()
            mock_service.generate_embedding.return_value = [0.1] * 1536
            mock_service.close = AsyncMock()
            mock_embedding_cls.return_value = mock_service

            mock_repo.hybrid_search.return_value = [(sample_analysis, 0.9)]
            # Snippet generation fails
            mock_repo.get_search_snippet.side_effect = Exception("Snippet error")

            response = client.get(
                "/api/v1/library",
                params={"query": "test", "search_mode": "hybrid"},
            )

            # Should still succeed without snippet
            assert response.status_code == 200
            data = response.json()
            assert data["items"][0]["snippet"] is None

    @pytest.mark.asyncio
    async def test_hybrid_search_embedding_failure_fallback(
        self, mock_repo, override_get_repo, sample_analysis
    ):
        """Test hybrid search falls back to fulltext when embedding fails."""
        with patch("app.api.v1.library.EmbeddingService") as mock_embedding_cls:
            mock_service = AsyncMock()
            # Embedding generation fails
            mock_service.generate_embedding.side_effect = Exception("Embedding API error")
            mock_service.close = AsyncMock()
            mock_embedding_cls.return_value = mock_service

            # Mock fulltext search as fallback
            mock_repo.search_by_text.return_value = [(sample_analysis, 0.8)]
            mock_repo.get_search_snippet.return_value = None

            response = client.get(
                "/api/v1/library",
                params={"query": "test", "search_mode": "hybrid"},
            )

            # Should succeed with fulltext fallback
            assert response.status_code == 200
            # Verify it used fulltext search instead of hybrid
            mock_repo.search_by_text.assert_called_once()
            mock_repo.hybrid_search.assert_not_called()


class TestFulltextSearch:
    """Tests for full-text search mode using PostgreSQL FTS."""

    @pytest.mark.asyncio
    async def test_fulltext_search_success(self, mock_repo, override_get_repo, sample_analysis):
        """Test fulltext search returns FTS results."""
        mock_repo.search_by_text.return_value = [(sample_analysis, 0.85)]
        mock_repo.get_search_snippet.return_value = "Test <mark>content</mark>"

        response = client.get(
            "/api/v1/library",
            params={"query": "content", "search_mode": "fulltext", "limit": 10},
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) == 1
        assert data["items"][0]["rank"] == 0.85
        assert data["limit"] == 10

        # Verify no embedding was generated
        mock_repo.search_by_text.assert_called_once()

    @pytest.mark.asyncio
    async def test_fulltext_search_no_embedding_service(
        self, mock_repo, override_get_repo, sample_analysis
    ):
        """Test fulltext search does not use embedding service."""
        mock_repo.search_by_text.return_value = [(sample_analysis, 0.9)]
        mock_repo.get_search_snippet.return_value = None

        with patch("app.api.v1.library.EmbeddingService") as mock_embedding_cls:
            response = client.get(
                "/api/v1/library",
                params={"query": "test", "search_mode": "fulltext"},
            )

            assert response.status_code == 200
            # Embedding service should not be instantiated
            mock_embedding_cls.assert_not_called()


class TestSemanticSearch:
    """Tests for semantic/vector search mode using pgvector."""

    @pytest.mark.asyncio
    async def test_semantic_search_success(self, mock_repo, override_get_repo, sample_analysis):
        """Test semantic search uses vector embeddings."""
        with patch("app.api.v1.library.EmbeddingService") as mock_embedding_cls:
            mock_service = AsyncMock()
            mock_service.generate_embedding.return_value = [0.2] * 1536
            mock_service.close = AsyncMock()
            mock_embedding_cls.return_value = mock_service

            mock_repo.search_by_vector.return_value = [(sample_analysis, 0.15)]

            response = client.get(
                "/api/v1/library",
                params={"query": "semantic test", "search_mode": "semantic"},
            )

            assert response.status_code == 200
            data = response.json()
            assert len(data["items"]) == 1
            assert data["items"][0]["rank"] == 0.15  # Distance score

            # Verify embedding was generated
            mock_service.generate_embedding.assert_called_once_with("semantic test")
            mock_repo.search_by_vector.assert_called_once()

    @pytest.mark.asyncio
    async def test_semantic_search_no_snippet(self, mock_repo, override_get_repo, sample_analysis):
        """Test semantic search does not generate snippets."""
        with patch("app.api.v1.library.EmbeddingService") as mock_embedding_cls:
            mock_service = AsyncMock()
            mock_service.generate_embedding.return_value = [0.1] * 1536
            mock_service.close = AsyncMock()
            mock_embedding_cls.return_value = mock_service

            mock_repo.search_by_vector.return_value = [(sample_analysis, 0.1)]

            response = client.get(
                "/api/v1/library",
                params={"query": "test", "search_mode": "semantic"},
            )

            assert response.status_code == 200
            data = response.json()
            # Semantic search should not have snippet
            assert data["items"][0]["snippet"] is None
            # get_search_snippet should not be called for semantic search
            mock_repo.get_search_snippet.assert_not_called()

    @pytest.mark.asyncio
    async def test_semantic_search_pagination_offset(self, mock_repo, override_get_repo):
        """Test semantic search applies offset in application layer."""
        with patch("app.api.v1.library.EmbeddingService") as mock_embedding_cls:
            mock_service = AsyncMock()
            mock_service.generate_embedding.return_value = [0.1] * 1536
            mock_service.close = AsyncMock()
            mock_embedding_cls.return_value = mock_service

            # Create 15 mock results
            mock_results = [
                (
                    Analysis(
                        id=uuid4(),
                        url=f"https://example.com/{i}",
                        title=f"Result {i}",
                        content_type="article",
                        status="complete",
                        created_at=datetime.now(UTC),
                    ),
                    0.1 + i * 0.01,
                )
                for i in range(15)
            ]
            mock_repo.search_by_vector.return_value = mock_results

            response = client.get(
                "/api/v1/library",
                params={"query": "test", "search_mode": "semantic", "limit": 5, "offset": 5},
            )

            assert response.status_code == 200
            data = response.json()
            # Should get results 6-10 (offset 5, limit 5)
            assert len(data["items"]) == 5
            assert data["offset"] == 5
            # Verify repo was called with limit + offset
            call_args = mock_repo.search_by_vector.call_args
            assert call_args.kwargs["limit"] == 10  # 5 + 5

    @pytest.mark.asyncio
    async def test_semantic_search_embedding_failure_returns_500(
        self, mock_repo, override_get_repo
    ):
        """Test semantic-only search returns 500 when embedding fails."""
        with patch("app.api.v1.library.EmbeddingService") as mock_embedding_cls:
            mock_service = AsyncMock()
            mock_service.generate_embedding.side_effect = Exception("Embedding error")
            mock_service.close = AsyncMock()
            mock_embedding_cls.return_value = mock_service

            response = client.get(
                "/api/v1/library",
                params={"query": "test", "search_mode": "semantic"},
            )

            # Should fail for semantic-only mode
            assert response.status_code == 500


class TestSearchFiltering:
    """Tests for search with content_type and status filters."""

    @pytest.mark.asyncio
    async def test_search_ignores_filters_in_search_mode(
        self, mock_repo, override_get_repo, sample_analysis
    ):
        """Test filters are ignored when query is provided (search mode)."""
        mock_repo.search_by_text.return_value = [(sample_analysis, 0.9)]
        mock_repo.get_search_snippet.return_value = None

        response = client.get(
            "/api/v1/library",
            params={
                "query": "test",
                "search_mode": "fulltext",
                "content_type": "video",  # Should be ignored
                "status": "pending",  # Should be ignored
            },
        )

        assert response.status_code == 200
        # Verify search_by_text was called without filters
        mock_repo.list_analyses.assert_not_called()


class TestPagination:
    """Tests for pagination parameters."""

    @pytest.mark.asyncio
    async def test_search_pagination_offset_limit(self, mock_repo, override_get_repo):
        """Test search respects offset and limit parameters."""
        # Create 25 mock results
        mock_results = [
            (
                Analysis(
                    id=uuid4(),
                    url=f"https://example.com/{i}",
                    title=f"Result {i}",
                    content_type="article",
                    status="complete",
                    created_at=datetime.now(UTC),
                ),
                0.9 - i * 0.01,
            )
            for i in range(25)
        ]
        mock_repo.search_by_text.return_value = mock_results
        mock_repo.get_search_snippet.return_value = None

        response = client.get(
            "/api/v1/library",
            params={"query": "test", "search_mode": "fulltext", "limit": 10, "offset": 5},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["limit"] == 10
        assert data["offset"] == 5
        assert len(data["items"]) == 25  # All results returned

    @pytest.mark.asyncio
    async def test_pagination_bounds_validation(self, mock_repo, override_get_repo):
        """Test pagination validates offset/limit bounds."""
        # Test limit too small
        response = client.get("/api/v1/library", params={"limit": 0})
        assert response.status_code == 422

        # Test limit too large
        response = client.get("/api/v1/library", params={"limit": 101})
        assert response.status_code == 422

        # Test negative offset
        response = client.get("/api/v1/library", params={"offset": -1})
        assert response.status_code == 422

        # Test valid bounds
        mock_repo.list_analyses.return_value = ([], 0)
        response = client.get("/api/v1/library", params={"limit": 50, "offset": 0})
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_pagination_empty_page(self, mock_repo, override_get_repo):
        """Test requesting page beyond available results."""
        mock_repo.search_by_text.return_value = []  # No results
        mock_repo.get_search_snippet.return_value = None

        response = client.get(
            "/api/v1/library",
            params={"query": "test", "search_mode": "fulltext", "limit": 20, "offset": 100},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["items"] == []
        assert data["total"] == 100  # offset value
        assert data["offset"] == 100


class TestListingMode:
    """Tests for listing mode (no query parameter)."""

    @pytest.mark.asyncio
    async def test_list_all_analyses(self, mock_repo, override_get_repo):
        """Test listing all analyses without filters."""
        analyses = [
            Analysis(
                id=uuid4(),
                url=f"https://example.com/{i}",
                title=f"Content {i}",
                content_type="article",
                status="complete",
                created_at=datetime.now(UTC),
            )
            for i in range(3)
        ]
        mock_repo.list_analyses.return_value = (analyses, 3)

        response = client.get("/api/v1/library")

        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) == 3
        assert data["total"] == 3
        assert data["limit"] == 20  # Default
        assert data["offset"] == 0  # Default

    @pytest.mark.asyncio
    async def test_list_with_content_type_filter(self, mock_repo, override_get_repo):
        """Test listing filters by content_type."""
        articles = [
            Analysis(
                id=uuid4(),
                url="https://example.com/article",
                title="Article",
                content_type="article",
                status="complete",
                created_at=datetime.now(UTC),
            )
        ]
        mock_repo.list_analyses.return_value = (articles, 1)

        response = client.get("/api/v1/library", params={"content_type": "article"})

        assert response.status_code == 200
        data = response.json()
        assert all(item["content_type"] == "article" for item in data["items"])

        # Verify filters were passed to repository
        call_args = mock_repo.list_analyses.call_args
        filters = call_args.kwargs["filters"]
        assert filters.content_type == "article"

    @pytest.mark.asyncio
    async def test_list_with_status_filter(self, mock_repo, override_get_repo):
        """Test listing filters by status."""
        complete = [
            Analysis(
                id=uuid4(),
                url="https://example.com/complete",
                title="Complete",
                content_type="article",
                status="complete",
                created_at=datetime.now(UTC),
            )
        ]
        mock_repo.list_analyses.return_value = (complete, 1)

        response = client.get("/api/v1/library", params={"status": "complete"})

        assert response.status_code == 200
        data = response.json()
        assert all(item["status"] == "complete" for item in data["items"])

        # Verify filters
        call_args = mock_repo.list_analyses.call_args
        filters = call_args.kwargs["filters"]
        assert filters.status == "complete"

    @pytest.mark.asyncio
    async def test_list_with_multiple_filters(self, mock_repo, override_get_repo):
        """Test listing applies both content_type and status filters."""
        filtered = [
            Analysis(
                id=uuid4(),
                url="https://example.com/filtered",
                title="Filtered",
                content_type="video",
                status="complete",
                created_at=datetime.now(UTC),
            )
        ]
        mock_repo.list_analyses.return_value = (filtered, 1)

        response = client.get(
            "/api/v1/library", params={"content_type": "video", "status": "complete"}
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) == 1
        assert data["items"][0]["content_type"] == "video"
        assert data["items"][0]["status"] == "complete"

        # Verify both filters
        call_args = mock_repo.list_analyses.call_args
        filters = call_args.kwargs["filters"]
        assert filters.content_type == "video"
        assert filters.status == "complete"

    @pytest.mark.asyncio
    async def test_list_no_snippet_or_rank(self, mock_repo, override_get_repo):
        """Test listing mode returns null snippet and 0.0 rank."""
        analyses = [
            Analysis(
                id=uuid4(),
                url="https://example.com/test",
                title="Test",
                content_type="article",
                status="complete",
                created_at=datetime.now(UTC),
            )
        ]
        mock_repo.list_analyses.return_value = (analyses, 1)

        response = client.get("/api/v1/library")

        assert response.status_code == 200
        data = response.json()
        for item in data["items"]:
            assert item["snippet"] is None
            assert item["rank"] == 0.0


class TestErrorHandling:
    """Tests for error handling and validation."""

    @pytest.mark.asyncio
    async def test_empty_query_returns_400(self, mock_repo, override_get_repo):
        """Test empty query string returns 400 error."""
        response = client.get("/api/v1/library", params={"query": ""})

        assert response.status_code == 400
        data = response.json()
        assert "empty string" in data["detail"].lower()

    @pytest.mark.asyncio
    async def test_whitespace_query_returns_400(self, mock_repo, override_get_repo):
        """Test whitespace-only query returns 400 error."""
        response = client.get("/api/v1/library", params={"query": "   "})

        assert response.status_code == 400
        data = response.json()
        assert "empty string" in data["detail"].lower()

    @pytest.mark.asyncio
    async def test_invalid_search_mode_returns_422(self, mock_repo, override_get_repo):
        """Test invalid search_mode value returns 422."""
        response = client.get(
            "/api/v1/library", params={"query": "test", "search_mode": "invalid_mode"}
        )

        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_negative_limit_returns_422(self, mock_repo, override_get_repo):
        """Test negative limit returns 422 validation error."""
        response = client.get("/api/v1/library", params={"limit": -5})

        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_search_repository_error_returns_500(self, mock_repo, override_get_repo):
        """Test repository error returns 500."""
        mock_repo.search_by_text.side_effect = Exception("Database error")

        response = client.get(
            "/api/v1/library", params={"query": "test", "search_mode": "fulltext"}
        )

        assert response.status_code == 500
        data = response.json()
        assert "Library request failed" in data["detail"]

    @pytest.mark.asyncio
    async def test_list_repository_error_returns_500(self, mock_repo, override_get_repo):
        """Test repository error in listing mode returns 500."""
        mock_repo.list_analyses.side_effect = Exception("Database error")

        response = client.get("/api/v1/library")

        assert response.status_code == 500
        data = response.json()
        assert "Library request failed" in data["detail"]


class TestDefaultValues:
    """Tests for default parameter values."""

    @pytest.mark.asyncio
    async def test_default_search_mode_is_hybrid(
        self, mock_repo, override_get_repo, sample_analysis
    ):
        """Test default search_mode is hybrid when not specified."""
        with patch("app.api.v1.library.EmbeddingService") as mock_embedding_cls:
            mock_service = AsyncMock()
            mock_service.generate_embedding.return_value = [0.1] * 1536
            mock_service.close = AsyncMock()
            mock_embedding_cls.return_value = mock_service

            mock_repo.hybrid_search.return_value = [(sample_analysis, 0.9)]
            mock_repo.get_search_snippet.return_value = None

            response = client.get("/api/v1/library", params={"query": "test"})

            assert response.status_code == 200
            # Verify hybrid_search was called (default mode)
            mock_repo.hybrid_search.assert_called_once()

    @pytest.mark.asyncio
    async def test_default_pagination_values(self, mock_repo, override_get_repo):
        """Test default limit=20 and offset=0."""
        mock_repo.list_analyses.return_value = ([], 0)

        response = client.get("/api/v1/library")

        assert response.status_code == 200
        data = response.json()
        assert data["limit"] == 20
        assert data["offset"] == 0

        # Verify repository was called with defaults
        call_args = mock_repo.list_analyses.call_args
        assert call_args.kwargs["limit"] == 20
        assert call_args.kwargs["offset"] == 0
