"""Pydantic schemas for library search and filtering."""

from pydantic import BaseModel, Field


class LibraryFilters(BaseModel):
    """Filter parameters for library listing.

    Attributes:
        content_type: Optional filter by content type (article, video, repo)
        status: Optional filter by analysis status (pending, running, complete, failed)

    Example:
        ```python
        filters = LibraryFilters(content_type="article", status="complete")
        ```

    """

    content_type: str | None = Field(
        default=None,
        description="Filter by content type (article, video, repo)",
    )
    status: str | None = Field(
        default=None,
        description="Filter by analysis status (pending, running, complete, failed)",
    )

    model_config = {
        "json_schema_extra": {
            "example": {
                "content_type": "article",
                "status": "complete",
            }
        }
    }


class LibrarySearchResult(BaseModel):
    """Search result with ranking information.

    Attributes:
        analysis_id: Unique identifier for the analysis
        url: Source URL that was analyzed
        title: Content title (if available)
        content_type: Detected content type (article, video, repo)
        snippet: Search snippet with highlighted matches (for text search)
        rank: Relevance score (for text search) or distance (for vector search)
        created_at: Timestamp when the analysis was created

    Example:
        ```python
        result = LibrarySearchResult(
            analysis_id="123e4567-e89b-12d3-a456-426614174000",
            url="https://example.com/article",
            title="Introduction to PostgreSQL",
            content_type="article",
            snippet="...PostgreSQL provides <mark>full-text search</mark> capabilities...",
            rank=0.87,
            created_at="2024-01-01T12:00:00Z",
        )
        ```

    """

    analysis_id: str = Field(..., description="Unique identifier for the analysis")
    url: str = Field(..., description="Source URL that was analyzed")
    title: str | None = Field(None, description="Content title (if available)")
    content_type: str = Field(..., description="Detected content type")
    snippet: str | None = Field(
        None,
        description="Search snippet with highlighted matches (for text search)",
    )
    rank: float = Field(
        ...,
        description="Relevance score (for text search) or distance (for vector search)",
    )
    created_at: str = Field(..., description="Timestamp when the analysis was created")

    model_config = {
        "json_schema_extra": {
            "example": {
                "analysis_id": "123e4567-e89b-12d3-a456-426614174000",
                "url": "https://example.com/article",
                "title": "Introduction to PostgreSQL",
                "content_type": "article",
                "snippet": "...PostgreSQL provides <mark>full-text search</mark> capabilities...",
                "rank": 0.87,
                "created_at": "2024-01-01T12:00:00Z",
            }
        }
    }


class LibraryListResponse(BaseModel):
    """Paginated library list response.

    Attributes:
        items: List of search results
        total: Total number of results (before pagination)
        limit: Number of items per page
        offset: Number of items skipped

    Example:
        ```python
        response = LibraryListResponse(
            items=[...],
            total=42,
            limit=20,
            offset=0,
        )
        ```

    """

    items: list[LibrarySearchResult] = Field(..., description="List of search results")
    total: int = Field(..., description="Total number of results (before pagination)")
    limit: int = Field(..., description="Number of items per page")
    offset: int = Field(..., description="Number of items skipped")

    model_config = {
        "json_schema_extra": {
            "example": {
                "items": [
                    {
                        "analysis_id": "123e4567-e89b-12d3-a456-426614174000",
                        "url": "https://example.com/article",
                        "title": "Introduction to PostgreSQL",
                        "content_type": "article",
                        "snippet": "...PostgreSQL provides <mark>full-text search</mark>...",
                        "rank": 0.87,
                        "created_at": "2024-01-01T12:00:00Z",
                    }
                ],
                "total": 42,
                "limit": 20,
                "offset": 0,
            }
        }
    }
