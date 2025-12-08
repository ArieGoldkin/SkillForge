"""Unit tests for library schemas."""

import pytest
from pydantic import ValidationError

from app.schemas.library import LibraryFilters, LibraryListResponse, LibrarySearchResult


class TestLibraryFilters:
    """Tests for LibraryFilters schema."""

    def test_library_filters_no_filters(self):
        """Test LibraryFilters with no filters."""
        filters = LibraryFilters()
        assert filters.content_type is None
        assert filters.status is None

    def test_library_filters_with_content_type(self):
        """Test LibraryFilters with content_type."""
        filters = LibraryFilters(content_type="article")
        assert filters.content_type == "article"
        assert filters.status is None

    def test_library_filters_with_status(self):
        """Test LibraryFilters with status."""
        filters = LibraryFilters(status="complete")
        assert filters.content_type is None
        assert filters.status == "complete"

    def test_library_filters_with_all_fields(self):
        """Test LibraryFilters with all fields."""
        filters = LibraryFilters(content_type="video", status="pending")
        assert filters.content_type == "video"
        assert filters.status == "pending"

    def test_library_filters_serialization(self):
        """Test LibraryFilters model_dump."""
        filters = LibraryFilters(content_type="article", status="complete")
        data = filters.model_dump()
        assert data["content_type"] == "article"
        assert data["status"] == "complete"

    def test_library_filters_empty_strings_allowed(self):
        """Test LibraryFilters allows empty strings (but they're meaningless)."""
        # Pydantic doesn't validate enum values by default
        filters = LibraryFilters(content_type="", status="")
        assert filters.content_type == ""
        assert filters.status == ""


class TestLibrarySearchResult:
    """Tests for LibrarySearchResult schema."""

    def test_library_search_result_required_fields(self):
        """Test LibrarySearchResult with required fields only."""
        result = LibrarySearchResult(
            analysis_id="123e4567-e89b-12d3-a456-426614174000",
            url="https://example.com/article",
            content_type="article",
            status="complete",
            rank=0.87,
            created_at="2024-01-01T12:00:00Z",
        )
        assert result.analysis_id == "123e4567-e89b-12d3-a456-426614174000"
        assert result.url == "https://example.com/article"
        assert result.content_type == "article"
        assert result.rank == 0.87
        assert result.created_at == "2024-01-01T12:00:00Z"
        assert result.title is None
        assert result.snippet is None

    def test_library_search_result_all_fields(self):
        """Test LibrarySearchResult with all fields."""
        result = LibrarySearchResult(
            analysis_id="123e4567-e89b-12d3-a456-426614174000",
            url="https://example.com/article",
            title="Introduction to PostgreSQL",
            content_type="article",
            snippet="...PostgreSQL provides <mark>full-text search</mark> capabilities...",
            status="complete",
            rank=0.87,
            created_at="2024-01-01T12:00:00Z",
        )
        assert result.title == "Introduction to PostgreSQL"
        assert (
            result.snippet == "...PostgreSQL provides <mark>full-text search</mark> capabilities..."
        )

    def test_library_search_result_missing_required_fields(self):
        """Test LibrarySearchResult raises ValidationError when required fields missing."""
        with pytest.raises(ValidationError) as exc_info:
            LibrarySearchResult(
                url="https://example.com/article",
                content_type="article",
                # Missing analysis_id, rank, created_at
            )
        errors = exc_info.value.errors()
        error_fields = {err["loc"][0] for err in errors}
        assert "analysis_id" in error_fields
        assert "rank" in error_fields
        assert "created_at" in error_fields
        assert "status" in error_fields

    def test_library_search_result_rank_type_validation(self):
        """Test LibrarySearchResult rank must be float."""
        # Should accept int and convert to float
        result = LibrarySearchResult(
            analysis_id="123e4567-e89b-12d3-a456-426614174000",
            url="https://example.com/article",
            content_type="article",
            status="complete",
            rank=1,  # int
            created_at="2024-01-01T12:00:00Z",
        )
        assert result.rank == 1.0
        assert isinstance(result.rank, float)

    def test_library_search_result_serialization(self):
        """Test LibrarySearchResult model_dump."""
        result = LibrarySearchResult(
            analysis_id="123e4567-e89b-12d3-a456-426614174000",
            url="https://example.com/article",
            title="Test Article",
            content_type="article",
            snippet="Test snippet",
            status="complete",
            rank=0.87,
            created_at="2024-01-01T12:00:00Z",
        )
        data = result.model_dump()
        assert data["analysis_id"] == "123e4567-e89b-12d3-a456-426614174000"
        assert data["url"] == "https://example.com/article"
        assert data["title"] == "Test Article"
        assert data["content_type"] == "article"
        assert data["snippet"] == "Test snippet"
        assert data["rank"] == 0.87
        assert data["created_at"] == "2024-01-01T12:00:00Z"

    def test_library_search_result_json_serialization(self):
        """Test LibrarySearchResult can be serialized to JSON."""
        result = LibrarySearchResult(
            analysis_id="123e4567-e89b-12d3-a456-426614174000",
            url="https://example.com/article",
            content_type="article",
            status="complete",
            rank=0.87,
            created_at="2024-01-01T12:00:00Z",
        )
        json_str = result.model_dump_json()
        assert "123e4567-e89b-12d3-a456-426614174000" in json_str
        assert "https://example.com/article" in json_str


class TestLibraryListResponse:
    """Tests for LibraryListResponse schema."""

    def test_library_list_response_required_fields(self):
        """Test LibraryListResponse with required fields."""
        response = LibraryListResponse(
            items=[],
            total=0,
            limit=20,
            offset=0,
        )
        assert response.items == []
        assert response.total == 0
        assert response.limit == 20
        assert response.offset == 0

    def test_library_list_response_with_items(self):
        """Test LibraryListResponse with search result items."""
        items = [
            LibrarySearchResult(
                analysis_id="123e4567-e89b-12d3-a456-426614174000",
                url="https://example.com/article1",
                title="Article 1",
                content_type="article",
                status="complete",
                rank=0.9,
                created_at="2024-01-01T12:00:00Z",
            ),
            LibrarySearchResult(
                analysis_id="223e4567-e89b-12d3-a456-426614174000",
                url="https://example.com/article2",
                title="Article 2",
                content_type="article",
                status="complete",
                rank=0.8,
                created_at="2024-01-02T12:00:00Z",
            ),
        ]
        response = LibraryListResponse(
            items=items,
            total=42,
            limit=20,
            offset=0,
        )
        assert len(response.items) == 2
        assert response.total == 42
        assert response.items[0].title == "Article 1"
        assert response.items[1].title == "Article 2"

    def test_library_list_response_missing_required_fields(self):
        """Test LibraryListResponse raises ValidationError when required fields missing."""
        with pytest.raises(ValidationError) as exc_info:
            LibraryListResponse(
                items=[],
                # Missing total, limit, offset
            )
        errors = exc_info.value.errors()
        error_fields = {err["loc"][0] for err in errors}
        assert "total" in error_fields
        assert "limit" in error_fields
        assert "offset" in error_fields

    def test_library_list_response_pagination_values(self):
        """Test LibraryListResponse pagination field types."""
        response = LibraryListResponse(
            items=[],
            total=100,
            limit=20,
            offset=40,
        )
        assert isinstance(response.total, int)
        assert isinstance(response.limit, int)
        assert isinstance(response.offset, int)
        assert response.total == 100
        assert response.limit == 20
        assert response.offset == 40

    def test_library_list_response_serialization(self):
        """Test LibraryListResponse model_dump."""
        items = [
            LibrarySearchResult(
                analysis_id="123e4567-e89b-12d3-a456-426614174000",
                url="https://example.com/article",
                content_type="article",
                status="complete",
                rank=0.87,
                created_at="2024-01-01T12:00:00Z",
            )
        ]
        response = LibraryListResponse(
            items=items,
            total=42,
            limit=20,
            offset=0,
        )
        data = response.model_dump()
        assert len(data["items"]) == 1
        assert data["total"] == 42
        assert data["limit"] == 20
        assert data["offset"] == 0

    def test_library_list_response_json_serialization(self):
        """Test LibraryListResponse can be serialized to JSON."""
        response = LibraryListResponse(
            items=[],
            total=0,
            limit=20,
            offset=0,
        )
        json_str = response.model_dump_json()
        assert '"items":[]' in json_str or '"items": []' in json_str
        assert '"total":0' in json_str or '"total": 0' in json_str

    def test_library_list_response_items_type_validation(self):
        """Test LibraryListResponse items must be list of LibrarySearchResult."""
        # Should raise ValidationError if items contains wrong type
        with pytest.raises(ValidationError):
            LibraryListResponse(
                items=["not", "a", "search", "result"],
                total=0,
                limit=20,
                offset=0,
            )

    def test_library_list_response_empty_page(self):
        """Test LibraryListResponse for empty page (offset beyond results)."""
        response = LibraryListResponse(
            items=[],
            total=42,
            limit=20,
            offset=60,  # Beyond total results
        )
        assert len(response.items) == 0
        assert response.total == 42
        assert response.offset == 60
