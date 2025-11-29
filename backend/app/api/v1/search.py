"""Search endpoints for semantic similarity search.

This module provides search functionality using two-stage vector search
for finding similar analyses based on semantic similarity.
"""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.core.logging import get_logger
from app.db.repositories.analysis_repository import IAnalysisRepository, get_analysis_repository
from app.services.embeddings import EmbeddingService

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
