"""Search endpoints for semantic and hybrid content retrieval.

This module provides REST API endpoints for searching analysis chunks using:
- Semantic search (vector similarity via pgvector)
- Keyword search (full-text search via PostgreSQL tsvector)
- Hybrid search (RRF fusion of semantic + keyword)

Architecture:
- Uses SearchService for search orchestration
- Uses EmbeddingService for query embeddings (via SearchService)
- Returns ranked results with snippets and metadata

Performance targets:
- Semantic search: < 100ms p95
- Hybrid search: < 200ms p95
"""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import EmbeddingError
from app.core.logging import get_logger
from app.db.session import get_db
from app.schemas.search import SearchRequest, SearchResponse
from app.services.embeddings import EmbeddingService
from app.services.search import SearchService

router = APIRouter(prefix="/search", tags=["search"])
logger = get_logger(__name__)


@router.post("")
async def search(
    request: SearchRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> SearchResponse:
    """Search chunks using semantic, keyword, or hybrid mode.

    Performs content search across analysis chunks using different search strategies:
    - **semantic**: Vector similarity search using embeddings (cosine distance)
    - **keyword**: Full-text search using PostgreSQL tsvector (BM25-like)
    - **hybrid**: Combined search with RRF score fusion (default)

    Args:
        request: Search request with query, mode, top_k, and optional filters
        db: Database session dependency

    Returns:
        SearchResponse with ranked results, total count, and query metadata

    Raises:
        HTTPException: 400 if query is empty
        HTTPException: 422 if request validation fails (handled by Pydantic)
        HTTPException: 500 if search fails

    Example:
        ```python
        request = SearchRequest(query="machine learning basics", mode=SearchMode.HYBRID, top_k=10)
        response = await search(request, db)
        ```

    """
    embedding_service = None
    search_service = None

    try:
        # Initialize services
        embedding_service = EmbeddingService()
        search_service = SearchService(db, embedding_service)

        logger.info(
            "search_request_received",
            query=request.query[:100],
            mode=request.mode.value,
            top_k=request.top_k,
            has_filters=request.filters is not None,
        )

        # Execute search via SearchService
        results = await search_service.search(
            query=request.query,
            mode=request.mode,
            top_k=request.top_k,
            filters=request.filters,
        )

        logger.info(
            "search_request_completed",
            query=request.query[:50],
            mode=request.mode.value,
            result_count=len(results),
        )

        return SearchResponse(
            results=results,
            total=len(results),
            query=request.query,
            mode=request.mode,
        )

    except ValueError as e:
        # Handle validation errors (empty query, invalid top_k)
        logger.warning("search_validation_error", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e

    except EmbeddingError as e:
        # Handle embedding generation failures
        logger.exception("search_embedding_error", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate query embedding",
        ) from e

    except Exception as e:
        logger.exception("search_failed", query=request.query[:50], error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Search failed",
        ) from e

    finally:
        # Clean up resources
        if embedding_service:
            await embedding_service.close()
