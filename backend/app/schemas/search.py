"""Pydantic schemas for search API endpoints."""

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field


class SearchMode(str, Enum):
    """Search mode enumeration for different search strategies.

    Attributes:
        SEMANTIC: Vector similarity search using embeddings
        KEYWORD: Traditional keyword-based search
        HYBRID: Combined semantic and keyword search

    """

    SEMANTIC = "semantic"
    KEYWORD = "keyword"
    HYBRID = "hybrid"


class DateRange(BaseModel):
    """Date range filter for search queries.

    Attributes:
        start: Start datetime for filtering results (inclusive)
        end: End datetime for filtering results (inclusive)

    Example:
        ```python
        date_range = DateRange(start=datetime(2024, 1, 1), end=datetime(2024, 12, 31))
        ```

    """

    start: datetime | None = Field(
        default=None, description="Start datetime for filtering results (inclusive)"
    )
    end: datetime | None = Field(
        default=None, description="End datetime for filtering results (inclusive)"
    )

    model_config = {
        "json_schema_extra": {
            "example": {
                "start": "2024-01-01T00:00:00Z",
                "end": "2024-12-31T23:59:59Z",
            }
        }
    }


class ReRankConfig(BaseModel):
    """Configuration for optional re-ranking stage.

    Re-ranking uses an LLM to re-score top candidates for improved
    relevance. This adds latency but can significantly improve result
    quality for complex queries.

    Attributes:
        enabled: Whether to enable re-ranking
        candidate_count: Number of candidates to consider for re-ranking
        final_count: Number of results to return after re-ranking
        use_structural_priors: Whether to apply metadata-based scoring
        timeout_seconds: Maximum time for re-ranking before fallback

    Example:
        ```python
        config = ReRankConfig(
            enabled=True,
            candidate_count=50,
            final_count=10,
            timeout_seconds=5.0,
        )
        ```

    """

    enabled: bool = Field(default=False, description="Enable LLM-based re-ranking of results")
    candidate_count: int = Field(
        default=50,
        ge=10,
        le=100,
        description="Number of candidates to consider for re-ranking",
    )
    final_count: int = Field(
        default=10,
        ge=1,
        le=50,
        description="Number of results to return after re-ranking",
    )
    use_structural_priors: bool = Field(
        default=True,
        description="Apply metadata-based scoring boosts (position, path, type)",
    )
    timeout_seconds: float = Field(
        default=5.0,
        ge=1.0,
        le=30.0,
        description="Maximum seconds for re-ranking before fallback to base ranking",
    )

    model_config = {
        "json_schema_extra": {
            "example": {
                "enabled": True,
                "candidate_count": 50,
                "final_count": 10,
                "use_structural_priors": True,
                "timeout_seconds": 5.0,
            }
        }
    }


class SearchFilters(BaseModel):
    """Filter criteria for search queries.

    Attributes:
        content_type: Filter by content type (article, video, repo)
        date_range: Filter by date range
        analysis_id: Filter to specific analysis ID
        tags: Filter by tags (matches any tag in list)

    Example:
        ```python
        filters = SearchFilters(
            content_type="article",
            date_range=DateRange(start=datetime(2024, 1, 1)),
            tags=["python", "fastapi"],
        )
        ```

    """

    content_type: str | None = Field(
        default=None, description="Filter by content type (article, video, repo)"
    )
    date_range: DateRange | None = Field(default=None, description="Filter by date range")
    analysis_id: str | None = Field(default=None, description="Filter to specific analysis ID")
    tags: list[str] | None = Field(
        default=None, description="Filter by tags (matches any tag in list)"
    )

    model_config = {
        "json_schema_extra": {
            "example": {
                "content_type": "article",
                "date_range": {
                    "start": "2024-01-01T00:00:00Z",
                    "end": "2024-12-31T23:59:59Z",
                },
                "analysis_id": "123e4567-e89b-12d3-a456-426614174000",
                "tags": ["python", "fastapi"],
            }
        }
    }


class SearchRequest(BaseModel):
    """Request schema for search queries.

    Attributes:
        query: Search query string (1-1000 characters)
        mode: Search mode (semantic, keyword, or hybrid)
        top_k: Maximum number of results to return (1-100)
        filters: Optional filter criteria
        rerank: Optional re-ranking configuration for improved relevance

    Example:
        ```python
        request = SearchRequest(
            query="How to implement authentication in FastAPI?",
            mode=SearchMode.HYBRID,
            top_k=10,
            filters=SearchFilters(content_type="article"),
            rerank=ReRankConfig(enabled=True, final_count=5),
        )
        ```

    """

    query: str = Field(
        ..., min_length=1, max_length=1000, description="Search query string (1-1000 characters)"
    )
    mode: SearchMode = Field(
        default=SearchMode.HYBRID,
        description="Search mode (semantic, keyword, or hybrid)",
    )
    top_k: int = Field(
        default=10, ge=1, le=100, description="Maximum number of results to return (1-100)"
    )
    filters: SearchFilters | None = Field(default=None, description="Optional filter criteria")
    rerank: ReRankConfig | None = Field(
        default=None,
        description="Optional re-ranking configuration for improved relevance",
    )

    model_config = {
        "json_schema_extra": {
            "example": {
                "query": "How to implement authentication in FastAPI?",
                "mode": "hybrid",
                "top_k": 10,
                "filters": {"content_type": "article", "tags": ["python", "fastapi"]},
                "rerank": {
                    "enabled": True,
                    "candidate_count": 50,
                    "final_count": 10,
                    "use_structural_priors": True,
                    "timeout_seconds": 5.0,
                },
            }
        }
    }


class ChunkMetadata(BaseModel):
    """Metadata for a search result chunk.

    Attributes:
        section: Section or heading name where chunk was found
        path: Hierarchical path to chunk (as string or list for display)
        content_type: Type of content (article, video, repo)
        chunk_type: Type of chunk (paragraph, code_block, heading, etc.)
        language: Content language
        chunk_idx: Chunk index within section
        chunk_total: Total chunks in section

    Example:
        ```python
        metadata = ChunkMetadata(
            section="Authentication",
            path="Introduction > Authentication > OAuth2",
            content_type="article",
            chunk_type="paragraph",
        )
        ```

    """

    section: str | None = Field(
        default=None, description="Section or heading name where chunk was found"
    )
    path: str | list | None = Field(
        default=None,
        description="Hierarchical path to chunk (string or array)",
    )
    content_type: str | None = Field(
        default=None, description="Type of content (article, video, repo)"
    )
    chunk_type: str | None = Field(
        default=None, description="Type of chunk (paragraph, code_block, heading, etc.)"
    )
    language: str | None = Field(default=None, description="Content language")
    chunk_idx: int | None = Field(default=None, description="Chunk index within section")
    chunk_total: int | None = Field(default=None, description="Total chunks in section")

    model_config = {
        "json_schema_extra": {
            "example": {
                "section": "Authentication",
                "path": "Introduction > Authentication > OAuth2",
                "content_type": "article",
                "chunk_type": "paragraph",
            }
        }
    }


class SearchResult(BaseModel):
    """Individual search result.

    Attributes:
        chunk_id: Unique identifier for the chunk
        analysis_id: ID of the analysis this chunk belongs to
        content: Full content of the chunk
        snippet: Highlighted excerpt from the chunk
        score: Relevance score (0.0-1.0)
        metadata: Additional metadata about the chunk
        created_at: Timestamp when the chunk was created

    Example:
        ```python
        result = SearchResult(
            chunk_id="chunk-123",
            analysis_id="123e4567-e89b-12d3-a456-426614174000",
            content="FastAPI provides built-in support for OAuth2...",
            snippet="FastAPI provides <mark>built-in support</mark> for OAuth2...",
            score=0.95,
            metadata=ChunkMetadata(section="Authentication"),
            created_at=datetime.now(),
        )
        ```

    """

    chunk_id: str = Field(..., description="Unique identifier for the chunk")
    analysis_id: str = Field(..., description="ID of the analysis this chunk belongs to")
    content: str = Field(..., description="Full content of the chunk")
    snippet: str = Field(..., description="Highlighted excerpt from the chunk")
    score: float = Field(..., ge=0.0, le=1.0, description="Relevance score (0.0-1.0)")
    metadata: ChunkMetadata = Field(..., description="Additional metadata about the chunk")
    created_at: datetime = Field(..., description="Timestamp when the chunk was created")

    model_config = {
        "json_schema_extra": {
            "example": {
                "chunk_id": "chunk-123",
                "analysis_id": "123e4567-e89b-12d3-a456-426614174000",
                "content": "FastAPI provides built-in support for OAuth2 authentication...",
                "snippet": "FastAPI provides <mark>built-in support</mark> for OAuth2...",
                "score": 0.95,
                "metadata": {
                    "section": "Authentication",
                    "path": "Introduction > Authentication > OAuth2",
                    "content_type": "article",
                    "chunk_type": "paragraph",
                },
                "created_at": "2024-01-15T10:30:00Z",
            }
        }
    }


class SearchResponse(BaseModel):
    """Response schema for search queries.

    Attributes:
        results: List of search results
        total: Total number of results found
        query: Original search query
        mode: Search mode used

    Example:
        ```python
        response = SearchResponse(
            results=[SearchResult(...)],
            total=42,
            query="How to implement authentication in FastAPI?",
            mode=SearchMode.HYBRID,
        )
        ```

    """

    results: list[SearchResult] = Field(..., description="List of search results")
    total: int = Field(..., ge=0, description="Total number of results found")
    query: str = Field(..., description="Original search query")
    mode: SearchMode = Field(..., description="Search mode used")

    model_config = {
        "json_schema_extra": {
            "example": {
                "results": [
                    {
                        "chunk_id": "chunk-123",
                        "analysis_id": "123e4567-e89b-12d3-a456-426614174000",
                        "content": "FastAPI provides built-in support for OAuth2 authentication...",
                        "snippet": "FastAPI provides <mark>built-in support</mark> for OAuth2...",
                        "score": 0.95,
                        "metadata": {
                            "section": "Authentication",
                            "path": "Introduction > Authentication > OAuth2",
                            "content_type": "article",
                            "chunk_type": "paragraph",
                        },
                        "created_at": "2024-01-15T10:30:00Z",
                    }
                ],
                "total": 42,
                "query": "How to implement authentication in FastAPI?",
                "mode": "hybrid",
            }
        }
    }
