"""Unit tests for SearchService.

Tests cover:
- Search method routing (semantic, keyword, hybrid)
- Query validation (empty query, invalid top_k)
- Snippet generation with highlighting
- Filter conversion to repository format
- Score normalization
"""

import uuid
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio

from app.schemas.search import SearchFilters, SearchMode
from app.shared.services.search import SearchService

@pytest.mark.unit


@pytest.fixture
def mock_embedding_service():
    """Create a mock EmbeddingService."""
    mock = MagicMock()
    mock.model = "text-embedding-3-small"
    mock.expected_dimensions = 1536
    # Generate a mock embedding vector
    mock.generate_embedding = AsyncMock(return_value=[0.1] * 1536)
    return mock


@pytest.fixture
def mock_session():
    """Create a mock AsyncSession."""
    return MagicMock()


@pytest.fixture
def mock_chunk():
    """Create a mock AnalysisChunk for testing."""
    mock = MagicMock()
    mock.id = uuid.uuid4()
    mock.analysis_id = uuid.uuid4()
    mock.content = "FastAPI provides built-in OAuth2 authentication support for secure APIs."
    mock.chunk_type = "paragraph"
    mock.chunk_metadata = {
        "section": "Authentication",
        "path": "Introduction > Auth",
        "content_type": "article",
    }
    mock.created_at = datetime.now(UTC)
    return mock


@pytest_asyncio.fixture
async def search_service(mock_session, mock_embedding_service):
    """Create a SearchService with mocked dependencies."""
    with patch("app.db.repositories.chunk_repository.ChunkRepository") as mock_chunk_repo_class:
        mock_chunk_repo = MagicMock()
        mock_chunk_repo.semantic_search = AsyncMock(return_value=[])
        mock_chunk_repo.keyword_search = AsyncMock(return_value=[])
        mock_chunk_repo.hybrid_search = AsyncMock(return_value=[])
        mock_chunk_repo_class.return_value = mock_chunk_repo

        service = SearchService(mock_session, mock_embedding_service)
        # Replace the chunk_repo with our mock
        service.chunk_repo = mock_chunk_repo
        yield service


class TestSearchServiceValidation:
    """Tests for SearchService input validation."""

    @pytest.mark.asyncio
    async def test_search_empty_query_raises_value_error(self, search_service):
        """Test that empty query raises ValueError."""
        with pytest.raises(ValueError, match="Search query cannot be empty"):
            await search_service.search(
                query="",
                mode=SearchMode.HYBRID,
                top_k=10,
            )

    @pytest.mark.asyncio
    async def test_search_whitespace_query_raises_value_error(self, search_service):
        """Test that whitespace-only query raises ValueError."""
        with pytest.raises(ValueError, match="Search query cannot be empty"):
            await search_service.search(
                query="   \n\t  ",
                mode=SearchMode.HYBRID,
                top_k=10,
            )

    @pytest.mark.asyncio
    async def test_search_top_k_below_minimum_raises_value_error(self, search_service):
        """Test that top_k below 1 raises ValueError."""
        with pytest.raises(ValueError, match="top_k must be between"):
            await search_service.search(
                query="test query",
                mode=SearchMode.HYBRID,
                top_k=0,
            )

    @pytest.mark.asyncio
    async def test_search_top_k_above_maximum_raises_value_error(self, search_service):
        """Test that top_k above 100 raises ValueError."""
        with pytest.raises(ValueError, match="top_k must be between"):
            await search_service.search(
                query="test query",
                mode=SearchMode.HYBRID,
                top_k=101,
            )


class TestSearchServiceRouting:
    """Tests for SearchService mode routing."""

    @pytest.mark.asyncio
    async def test_search_routes_to_semantic_search(self, search_service, mock_embedding_service):
        """Test that SEMANTIC mode calls semantic_search."""
        await search_service.search(
            query="test query",
            mode=SearchMode.SEMANTIC,
            top_k=10,
        )

        # Verify embedding was generated
        mock_embedding_service.generate_embedding.assert_called_once()

        # Verify semantic_search was called
        search_service.chunk_repo.semantic_search.assert_called_once()
        search_service.chunk_repo.keyword_search.assert_not_called()
        search_service.chunk_repo.hybrid_search.assert_not_called()

    @pytest.mark.asyncio
    async def test_search_routes_to_keyword_search(self, search_service):
        """Test that KEYWORD mode calls keyword_search."""
        await search_service.search(
            query="test query",
            mode=SearchMode.KEYWORD,
            top_k=10,
        )

        # Verify keyword_search was called
        search_service.chunk_repo.keyword_search.assert_called_once()
        search_service.chunk_repo.semantic_search.assert_not_called()
        search_service.chunk_repo.hybrid_search.assert_not_called()

    @pytest.mark.asyncio
    async def test_search_routes_to_hybrid_search(self, search_service, mock_embedding_service):
        """Test that HYBRID mode calls hybrid_search."""
        await search_service.search(
            query="test query",
            mode=SearchMode.HYBRID,
            top_k=10,
        )

        # Verify embedding was generated for hybrid search
        mock_embedding_service.generate_embedding.assert_called_once()

        # Verify hybrid_search was called
        search_service.chunk_repo.hybrid_search.assert_called_once()
        search_service.chunk_repo.semantic_search.assert_not_called()
        search_service.chunk_repo.keyword_search.assert_not_called()


class TestSearchServiceResults:
    """Tests for SearchService result processing."""

    @pytest.mark.asyncio
    async def test_semantic_search_returns_search_results(self, search_service, mock_chunk):
        """Test that semantic search returns properly formatted SearchResult."""
        # Mock the repository to return chunks with scores
        search_service.chunk_repo.semantic_search = AsyncMock(return_value=[(mock_chunk, 0.95)])

        results = await search_service.search(
            query="OAuth2 authentication",
            mode=SearchMode.SEMANTIC,
            top_k=10,
        )

        assert len(results) == 1
        result = results[0]
        assert result.chunk_id == str(mock_chunk.id)
        assert result.analysis_id == str(mock_chunk.analysis_id)
        assert result.content == mock_chunk.content
        assert result.score == 0.95
        assert result.metadata.chunk_type == "paragraph"
        assert result.metadata.section == "Authentication"

    @pytest.mark.asyncio
    async def test_keyword_search_normalizes_scores(self, search_service, mock_chunk):
        """Test that keyword search normalizes scores to 0.0-1.0 range."""
        # Mock repository to return chunks with varying ts_rank scores
        mock_chunk2 = MagicMock()
        mock_chunk2.id = uuid.uuid4()
        mock_chunk2.analysis_id = uuid.uuid4()
        mock_chunk2.content = "OAuth2 is a protocol."
        mock_chunk2.chunk_type = "paragraph"
        mock_chunk2.chunk_metadata = {}
        mock_chunk2.created_at = datetime.now(UTC)

        search_service.chunk_repo.keyword_search = AsyncMock(
            return_value=[
                (mock_chunk, 0.8),  # Higher score
                (mock_chunk2, 0.4),  # Lower score
            ]
        )

        results = await search_service.search(
            query="OAuth2",
            mode=SearchMode.KEYWORD,
            top_k=10,
        )

        assert len(results) == 2
        # First result should be normalized to 1.0 (highest score)
        assert results[0].score == 1.0
        # Second result should be 0.5 (0.4/0.8)
        assert results[1].score == 0.5

    @pytest.mark.asyncio
    async def test_hybrid_search_returns_rrf_scores(self, search_service, mock_chunk):
        """Test that hybrid search returns RRF-fused scores."""
        search_service.chunk_repo.hybrid_search = AsyncMock(
            return_value=[(mock_chunk, 0.033)]  # Typical RRF score
        )

        results = await search_service.search(
            query="OAuth2 authentication",
            mode=SearchMode.HYBRID,
            top_k=10,
        )

        assert len(results) == 1
        # RRF scores are normalized to 0.0-1.0
        assert 0.0 <= results[0].score <= 1.0


class TestSearchServiceSnippets:
    """Tests for SearchService snippet generation."""

    @pytest.fixture
    def service_with_mocks(self, mock_session, mock_embedding_service):
        """Create service for testing snippet generation."""
        with patch("app.db.repositories.chunk_repository.ChunkRepository") as mock_repo_class:
            mock_repo = MagicMock()
            mock_repo.semantic_search = AsyncMock(return_value=[])
            mock_repo_class.return_value = mock_repo
            service = SearchService(mock_session, mock_embedding_service)
            return service

    def test_generate_snippet_highlights_terms(self, service_with_mocks):
        """Test that query terms are highlighted with <mark> tags."""
        snippet = service_with_mocks._generate_snippet(
            content="FastAPI provides OAuth2 support.",
            query="OAuth2",
            max_length=100,
        )

        assert "<mark>OAuth2</mark>" in snippet

    def test_generate_snippet_case_insensitive(self, service_with_mocks):
        """Test that highlighting is case-insensitive."""
        snippet = service_with_mocks._generate_snippet(
            content="oauth2 and OAUTH2 are both valid.",
            query="OAuth2",
            max_length=100,
        )

        assert snippet.count("<mark>") == 2

    def test_generate_snippet_centers_on_match(self, service_with_mocks):
        """Test that snippet is centered around the first match."""
        long_content = "A" * 100 + " OAuth2 is here " + "B" * 100
        snippet = service_with_mocks._generate_snippet(
            content=long_content,
            query="OAuth2",
            max_length=50,
        )

        # Should contain the highlighted term
        assert "<mark>OAuth2</mark>" in snippet
        # Should have ellipsis for truncation
        assert "..." in snippet

    def test_generate_snippet_no_match_returns_beginning(self, service_with_mocks):
        """Test that no match returns beginning of content."""
        snippet = service_with_mocks._generate_snippet(
            content="This is a long content without any relevant terms.",
            query="OAuth2",
            max_length=20,
        )

        assert snippet.startswith("This is")
        assert snippet.endswith("...")

    def test_generate_snippet_short_content_unchanged(self, service_with_mocks):
        """Test that short content is returned unchanged."""
        short_content = "OAuth2 rocks!"
        snippet = service_with_mocks._generate_snippet(
            content=short_content,
            query="OAuth2",
            max_length=200,
        )

        # Should be unchanged except for highlighting
        assert snippet == "<mark>OAuth2</mark> rocks!"


class TestSearchServiceFilters:
    """Tests for SearchService filter handling."""

    def test_filters_to_dict_with_content_type(self, mock_session, mock_embedding_service):
        """Test filter conversion with content_type."""
        with patch("app.db.repositories.chunk_repository.ChunkRepository"):
            service = SearchService(mock_session, mock_embedding_service)

            filters = SearchFilters(content_type="article")
            result = service._filters_to_dict(filters)

            assert result == {"content_type": "article"}

    def test_filters_to_dict_with_analysis_id(self, mock_session, mock_embedding_service):
        """Test filter conversion with analysis_id."""
        with patch("app.db.repositories.chunk_repository.ChunkRepository"):
            service = SearchService(mock_session, mock_embedding_service)

            filters = SearchFilters(analysis_id="123e4567-e89b-12d3-a456-426614174000")
            result = service._filters_to_dict(filters)

            assert result == {"analysis_id": "123e4567-e89b-12d3-a456-426614174000"}

    def test_filters_to_dict_with_multiple_filters(self, mock_session, mock_embedding_service):
        """Test filter conversion with multiple filters."""
        with patch("app.db.repositories.chunk_repository.ChunkRepository"):
            service = SearchService(mock_session, mock_embedding_service)

            filters = SearchFilters(
                content_type="video",
                analysis_id="123e4567-e89b-12d3-a456-426614174000",
            )
            result = service._filters_to_dict(filters)

            assert result == {
                "content_type": "video",
                "analysis_id": "123e4567-e89b-12d3-a456-426614174000",
            }

    def test_filters_to_dict_empty_returns_empty_dict(self, mock_session, mock_embedding_service):
        """Test that empty filters returns empty dict."""
        with patch("app.db.repositories.chunk_repository.ChunkRepository"):
            service = SearchService(mock_session, mock_embedding_service)

            filters = SearchFilters()  # No filters set
            result = service._filters_to_dict(filters)

            assert result == {}


class TestSearchServiceIntegration:
    """Integration-style unit tests for complete search flow."""

    @pytest.mark.asyncio
    async def test_full_semantic_search_flow(
        self, search_service, mock_chunk, mock_embedding_service
    ):
        """Test complete semantic search flow with all components."""
        search_service.chunk_repo.semantic_search = AsyncMock(return_value=[(mock_chunk, 0.92)])

        results = await search_service.search(
            query="OAuth2 authentication FastAPI",
            mode=SearchMode.SEMANTIC,
            top_k=5,
            filters=SearchFilters(content_type="article"),
        )

        # Verify embedding was generated
        mock_embedding_service.generate_embedding.assert_called_once_with(
            text="OAuth2 authentication FastAPI",
            normalize=True,
        )

        # Verify repository was called with correct params
        call_args = search_service.chunk_repo.semantic_search.call_args
        assert call_args.kwargs["limit"] == 5
        assert call_args.kwargs["filters"] == {"content_type": "article"}

        # Verify result structure
        assert len(results) == 1
        result = results[0]
        assert result.score == 0.92
        assert "<mark>" in result.snippet  # Highlighting applied
        assert result.metadata.content_type == "article"

    @pytest.mark.asyncio
    async def test_search_with_empty_results(self, search_service):
        """Test search returns empty list when no results found."""
        search_service.chunk_repo.hybrid_search = AsyncMock(return_value=[])

        results = await search_service.search(
            query="nonexistent query terms",
            mode=SearchMode.HYBRID,
            top_k=10,
        )

        assert results == []
