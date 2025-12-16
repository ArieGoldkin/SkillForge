"""Search endpoints for semantic similarity search.

This module provides search functionality using:
1. Analysis-level search: GET /search/similar - Find similar analyses
2. Chunk-level search: POST /search - Semantic, keyword, or hybrid search on content chunks

The chunk-level search supports three modes:
- SEMANTIC: Vector similarity search using embeddings (kNN with cosine similarity)
- KEYWORD: Full-text search using PostgreSQL tsvector
- HYBRID: Combined semantic + keyword search with Reciprocal Rank Fusion (RRF)
"""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.db.repositories.analysis_repository import IAnalysisRepository, get_analysis_repository
from app.db.session import get_db
from app.schemas.search import SearchRequest, SearchResponse
from app.services.embeddings.service import EmbeddingService
from app.services.search.search_service import SearchService

router = APIRouter(tags=["search"])
logger = get_logger(__name__)


@router.get("/search/similar")
async def search_similar_analyses(
    repo: Annotated[IAnalysisRepository, Depends(get_analysis_repository)],
    query: Annotated[str, Query(description="Search query text")],
    limit: Annotated[int, Query(ge=1, le=50, description="Number of results")] = 5,
) -> list[dict[str, object]]:
    """Search for similar analyses using semantic similarity.

    Uses two-stage vector search for optimal performance:
    1. Fast binary quantization search (top 20 candidates)
    2. Re-rank with original vectors (top K results)

    This endpoint prepares for ROADMAP Phase 4.1 (Full-Text Search) by
    implementing the semantic search component. Full-text search can be
    added later for hybrid search capabilities.

    Args:
        query: Search query text
        limit: Number of results to return (1-50)
        repo: Analysis repository dependency

    Returns:
        List of similar analyses with id, url, title, content_type

    Raises:
        HTTPException: 400 if query is empty
        HTTPException: 500 if embedding generation fails

    Example:
        GET /api/v1/search/similar?query=React hooks&limit=5

    """
    if not query or not query.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Query parameter cannot be empty",
        )

    try:
        # Generate embedding for query
        embedding_service = EmbeddingService()
        query_embedding = await embedding_service.generate_embedding(query.strip())
        await embedding_service.close()

        # Find similar analyses using two-stage search
        similar_analyses = await repo.find_similar_analyses(
            query_embedding=query_embedding,
            limit=limit,
        )

        # Format results
        results = [
            {
                "id": str(analysis.id),
                "url": analysis.url,
                "title": analysis.title,
                "content_type": analysis.content_type,
                "status": analysis.status,
                "created_at": analysis.created_at.isoformat() if analysis.created_at else None,
            }
            for analysis in similar_analyses
        ]

        logger.info(
            "search_similar_complete",
            query_length=len(query),
            limit=limit,
            results_count=len(results),
        )

        return results

    except Exception as e:
        logger.error(
            "search_similar_failed",
            query=query,
            error=str(e),
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Search failed",
        ) from e


@router.post("/search")
async def search_chunks(
    request: SearchRequest,
    session: Annotated[AsyncSession, Depends(get_db)],
) -> SearchResponse:
    """Search content chunks using semantic, keyword, or hybrid search.

    Performs search across analysis content chunks with three search modes:

    - **SEMANTIC**: Vector similarity search using embeddings (kNN with cosine similarity)
    - **KEYWORD**: Full-text search using PostgreSQL tsvector with BM25-like ranking
    - **HYBRID**: Combined semantic + keyword search with Reciprocal Rank Fusion (RRF)

    Optional re-ranking can be enabled to improve result relevance using LLM-based scoring.

    Args:
        request: SearchRequest with query, mode, top_k, optional filters and rerank config
        session: Database session dependency

    Returns:
        SearchResponse with results list, total count, original query, and mode

    Raises:
        HTTPException: 400 if query is empty or top_k is invalid
        HTTPException: 500 if search execution fails

    Example:
        POST /api/v1/search
        {
            "query": "How to implement OAuth2 in FastAPI?",
            "mode": "hybrid",
            "top_k": 10,
            "filters": {"content_type": "article"},
            "rerank": {"enabled": true, "candidate_count": 50, "final_count": 10}
        }

    """
    logger.info(
        "search_chunks_request",
        query_length=len(request.query),
        mode=request.mode.value,
        top_k=request.top_k,
        has_filters=request.filters is not None,
        rerank_enabled=request.rerank.enabled if request.rerank else False,
    )

    try:
        # Initialize services
        embedding_service = EmbeddingService()
        search_service = SearchService(session, embedding_service)

        # Execute search with optional re-ranking
        results = await search_service.search(
            query=request.query,
            mode=request.mode,
            top_k=request.top_k,
            filters=request.filters,
            rerank=request.rerank,
        )

        # Close embedding service
        await embedding_service.close()

        logger.info(
            "search_chunks_complete",
            query_length=len(request.query),
            mode=request.mode.value,
            results_count=len(results),
            reranked=request.rerank.enabled if request.rerank else False,
        )

        return SearchResponse(
            results=results,
            total=len(results),
            query=request.query,
            mode=request.mode,
        )

    except ValueError as e:
        logger.warning(
            "search_chunks_validation_error",
            query=request.query[:100],
            error=str(e),
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e

    except Exception as e:
        logger.error(
            "search_chunks_failed",
            query=request.query[:100],
            mode=request.mode.value,
            error=str(e),
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Search failed",
        ) from e
