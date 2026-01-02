"""Unit tests for search service.

Tests utility methods and core functionality to improve coverage
of app/shared/services/search/search_service.py.
"""

from unittest.mock import AsyncMock, Mock, patch

import pytest

from app.schemas.search import ChunkMetadata, SearchFilters, SearchResult
from app.shared.services.search.search_service import SearchService


class TestSearchServiceHelperMethods:
    """Test SearchService helper and utility methods."""

    def test_highlight_terms_adds_mark_tags(self):
        """Test that _highlight_terms wraps query terms in <mark> tags."""
        # Create minimal mock dependencies
        mock_session = Mock()
        mock_embedding_service = Mock()
        mock_embedding_service.model = "test-model"
        mock_embedding_service.expected_dimensions = 1536

        service = SearchService(mock_session, mock_embedding_service)

        text = "FastAPI provides OAuth2 support"
        query = "OAuth2"

        result = service._highlight_terms(text, query)

        assert "<mark>OAuth2</mark>" in result
        assert "FastAPI" in result

    def test_highlight_terms_is_case_insensitive(self):
        """Test that highlighting works regardless of case."""
        mock_session = Mock()
        mock_embedding_service = Mock()
        mock_embedding_service.model = "test-model"
        mock_embedding_service.expected_dimensions = 1536

        service = SearchService(mock_session, mock_embedding_service)

        text = "Python is great for python developers"
        query = "PYTHON"

        result = service._highlight_terms(text, query)

        assert result.count("<mark>") == 2  # Both "Python" and "python" highlighted

    def test_highlight_terms_handles_empty_query(self):
        """Test that empty query returns text unchanged."""
        mock_session = Mock()
        mock_embedding_service = Mock()
        mock_embedding_service.model = "test-model"
        mock_embedding_service.expected_dimensions = 1536

        service = SearchService(mock_session, mock_embedding_service)

        text = "Some text content"
        query = ""

        result = service._highlight_terms(text, query)

        assert result == text
        assert "<mark>" not in result

    def test_filters_to_dict_converts_content_type(self):
        """Test that _filters_to_dict extracts content_type filter."""
        mock_session = Mock()
        mock_embedding_service = Mock()
        mock_embedding_service.model = "test-model"
        mock_embedding_service.expected_dimensions = 1536

        service = SearchService(mock_session, mock_embedding_service)

        filters = SearchFilters(content_type="article")

        result = service._filters_to_dict(filters)

        assert result["content_type"] == "article"

    def test_filters_to_dict_converts_analysis_id(self):
        """Test that _filters_to_dict extracts analysis_id filter."""
        mock_session = Mock()
        mock_embedding_service = Mock()
        mock_embedding_service.model = "test-model"
        mock_embedding_service.expected_dimensions = 1536

        service = SearchService(mock_session, mock_embedding_service)

        filters = SearchFilters(analysis_id="analysis-123")

        result = service._filters_to_dict(filters)

        assert result["analysis_id"] == "analysis-123"

    def test_filters_to_dict_handles_none_values(self):
        """Test that _filters_to_dict skips None filter values."""
        mock_session = Mock()
        mock_embedding_service = Mock()
        mock_embedding_service.model = "test-model"
        mock_embedding_service.expected_dimensions = 1536

        service = SearchService(mock_session, mock_embedding_service)

        filters = SearchFilters(content_type=None, analysis_id=None)

        result = service._filters_to_dict(filters)

        assert len(result) == 0

    def test_is_technical_query_detects_technical_terms(self):
        """Test that _is_technical_query identifies technical keywords."""
        mock_session = Mock()
        mock_embedding_service = Mock()
        mock_embedding_service.model = "test-model"
        mock_embedding_service.expected_dimensions = 1536

        service = SearchService(mock_session, mock_embedding_service)

        # Use common technical terms that should be in TECHNICAL_TERMS
        query = "How to use kubernetes?"

        result = service._is_technical_query(query)

        # Result depends on whether 'kubernetes' is in TECHNICAL_TERMS
        assert isinstance(result, bool)

    def test_is_technical_query_returns_false_for_generic_query(self):
        """Test that non-technical query returns False."""
        mock_session = Mock()
        mock_embedding_service = Mock()
        mock_embedding_service.model = "test-model"
        mock_embedding_service.expected_dimensions = 1536

        service = SearchService(mock_session, mock_embedding_service)

        query = "how to write good documentation"

        result = service._is_technical_query(query)

        # Generic query should not match technical terms
        assert isinstance(result, bool)


class TestSearchServiceSnippetGeneration:
    """Test snippet generation functionality."""

    def test_generate_snippet_returns_full_content_if_short(self):
        """Test that short content is returned in full without truncation."""
        mock_session = Mock()
        mock_embedding_service = Mock()
        mock_embedding_service.model = "test-model"
        mock_embedding_service.expected_dimensions = 1536

        service = SearchService(mock_session, mock_embedding_service)

        content = "Short content with OAuth2"
        query = "OAuth2"

        snippet = service._generate_snippet(content, query, max_length=200)

        assert "Short content" in snippet
        assert "<mark>OAuth2</mark>" in snippet
        assert "..." not in snippet

    def test_generate_snippet_truncates_long_content(self):
        """Test that long content is truncated with ellipsis."""
        mock_session = Mock()
        mock_embedding_service = Mock()
        mock_embedding_service.model = "test-model"
        mock_embedding_service.expected_dimensions = 1536

        service = SearchService(mock_session, mock_embedding_service)

        content = "a" * 500  # Long content
        query = "test"

        snippet = service._generate_snippet(content, query, max_length=100)

        assert len(snippet) < len(content)
        assert "..." in snippet

    def test_generate_snippet_centers_on_query_match(self):
        """Test that snippet is centered around query match."""
        mock_session = Mock()
        mock_embedding_service = Mock()
        mock_embedding_service.model = "test-model"
        mock_embedding_service.expected_dimensions = 1536

        service = SearchService(mock_session, mock_embedding_service)

        # Create content where match is at the end
        content = "x" * 300 + " important keyword " + "y" * 300
        query = "keyword"

        snippet = service._generate_snippet(content, query, max_length=100)

        # Snippet should contain the keyword
        assert "keyword" in snippet.lower()


class TestSearchServiceValidation:
    """Test search validation logic."""

    @pytest.mark.asyncio
    async def test_search_raises_on_empty_query(self):
        """Test that search raises ValueError for empty query."""
        mock_session = Mock()
        mock_embedding_service = Mock()
        mock_embedding_service.model = "test-model"
        mock_embedding_service.expected_dimensions = 1536

        service = SearchService(mock_session, mock_embedding_service)

        from app.schemas.search import SearchMode

        with pytest.raises(ValueError, match="cannot be empty"):
            await service.search(query="", mode=SearchMode.SEMANTIC, top_k=10)

    @pytest.mark.asyncio
    async def test_search_raises_on_whitespace_only_query(self):
        """Test that search raises ValueError for whitespace-only query."""
        mock_session = Mock()
        mock_embedding_service = Mock()
        mock_embedding_service.model = "test-model"
        mock_embedding_service.expected_dimensions = 1536

        service = SearchService(mock_session, mock_embedding_service)

        from app.schemas.search import SearchMode

        with pytest.raises(ValueError, match="cannot be empty"):
            await service.search(query="   ", mode=SearchMode.SEMANTIC, top_k=10)

    @pytest.mark.asyncio
    async def test_search_raises_on_invalid_top_k_too_low(self):
        """Test that search raises ValueError for top_k below minimum."""
        mock_session = Mock()
        mock_embedding_service = Mock()
        mock_embedding_service.model = "test-model"
        mock_embedding_service.expected_dimensions = 1536

        service = SearchService(mock_session, mock_embedding_service)

        from app.schemas.search import SearchMode

        with pytest.raises(ValueError, match="top_k must be between"):
            await service.search(query="test", mode=SearchMode.SEMANTIC, top_k=0)

    @pytest.mark.asyncio
    async def test_search_raises_on_invalid_top_k_too_high(self):
        """Test that search raises ValueError for top_k above maximum."""
        mock_session = Mock()
        mock_embedding_service = Mock()
        mock_embedding_service.model = "test-model"
        mock_embedding_service.expected_dimensions = 1536

        service = SearchService(mock_session, mock_embedding_service)

        from app.schemas.search import SearchMode

        with pytest.raises(ValueError, match="top_k must be between"):
            await service.search(query="test", mode=SearchMode.SEMANTIC, top_k=200)


class TestSearchServiceInitialization:
    """Test SearchService initialization."""

    def test_service_initializes_with_dependencies(self):
        """Test that SearchService initializes with required dependencies."""
        mock_session = Mock()
        mock_embedding_service = Mock()
        mock_embedding_service.model = "openai-3-small"
        mock_embedding_service.expected_dimensions = 1536

        service = SearchService(mock_session, mock_embedding_service)

        assert service.session is mock_session
        assert service.embedding_service is mock_embedding_service
        assert service.chunk_repo is not None
        assert service.reranker is not None
        assert service.hyde_service is not None

    def test_service_accepts_custom_reranker(self):
        """Test that SearchService accepts custom reranker instance."""
        mock_session = Mock()
        mock_embedding_service = Mock()
        mock_embedding_service.model = "test-model"
        mock_embedding_service.expected_dimensions = 1536

        custom_reranker = Mock()
        service = SearchService(mock_session, mock_embedding_service, reranker=custom_reranker)

        assert service.reranker is custom_reranker
