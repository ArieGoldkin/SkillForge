"""Library endpoints for search and content listing.

This module provides the unified library endpoint that supports:
- Full-text search (PostgreSQL FTS)
- Semantic/vector search (pgvector cosine similarity)
- Hybrid search (Reciprocal Rank Fusion combining FTS + vector)
- Filtered listing (by content_type and status)
"""

from enum import Enum
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from starlette import status as http_status

from app.core.logging import get_logger
from app.db.repositories.library_repository import ILibraryRepository, get_library_repository
from app.schemas.library import LibraryFilters, LibraryListResponse, LibrarySearchResult
from app.services.embeddings import EmbeddingService

router = APIRouter(tags=["library"])
logger = get_logger(__name__)


class SearchMode(str, Enum):
    """Search mode for library queries.

    Attributes:
        hybrid: Combined FTS + vector search using RRF (default)
        fulltext: Full-text search only using PostgreSQL FTS
        semantic: Vector similarity search only using pgvector

    """

    hybrid = "hybrid"
    fulltext = "fulltext"
    semantic = "semantic"


@router.get("/library")
async def get_library(  # noqa: PLR0913, PLR0912, PLR0915
    repo: Annotated[ILibraryRepository, Depends(get_library_repository)],
    query: Annotated[str | None, Query(description="Search query")] = None,
    content_type: Annotated[
        str | None,
        Query(description="Filter by content type (article, video, repo)"),
    ] = None,
    status: Annotated[
        str | None,
        Query(description="Filter by analysis status (pending, running, complete, failed)"),
    ] = None,
    search_mode: Annotated[
        SearchMode,
        Query(description="Search mode (hybrid, fulltext, semantic)"),
    ] = SearchMode.hybrid,
    limit: Annotated[
        int,
        Query(ge=1, le=100, description="Results per page"),
    ] = 20,
    offset: Annotated[
        int,
        Query(ge=0, description="Pagination offset"),
    ] = 0,
) -> LibraryListResponse:
    """Get library contents with optional search and filtering.

    This endpoint supports two modes:

    1. **Search mode** (when `query` is provided):
       - `hybrid`: Combines full-text and semantic search using RRF (default)
       - `fulltext`: PostgreSQL full-text search only
       - `semantic`: Vector similarity search only

    2. **Listing mode** (when `query` is NOT provided):
       - Returns all analyses with optional filters
       - Ordered by creation date (newest first)
       - `search_mode` parameter is ignored

    Args:
        repo: Library repository dependency
        query: Optional search query string
        content_type: Optional filter by content type (article, video, repo)
        status: Optional filter by analysis status (pending, complete, failed)
        search_mode: Search algorithm (hybrid, fulltext, semantic)
        limit: Number of results per page (1-100, default: 20)
        offset: Number of results to skip for pagination (default: 0)

    Returns:
        LibraryListResponse with items, total, limit, and offset

    Raises:
        HTTPException: 400 if query is empty string
        HTTPException: 500 if search operation fails

    Examples:
        GET /api/v1/library?query=React hooks&search_mode=hybrid&limit=10
        GET /api/v1/library?content_type=article&status=complete
        GET /api/v1/library?query=TypeScript&search_mode=fulltext

    """
    try:
        # Validate query if provided
        if query is not None and not query.strip():
            raise HTTPException(
                status_code=http_status.HTTP_400_BAD_REQUEST,
                detail="Query parameter cannot be empty string. Omit parameter for listing mode.",
            )

        # Search mode: query is provided
        if query and query.strip():
            logger.info(
                "library_search_start",
                query=query,
                search_mode=search_mode.value,
                limit=limit,
                offset=offset,
            )

            # Initialize embedding service for semantic/hybrid search
            embedding_service: EmbeddingService | None = None
            query_embedding: list[float] = []

            # Generate embedding if needed for semantic or hybrid search
            if search_mode in (SearchMode.semantic, SearchMode.hybrid):
                try:
                    embedding_service = EmbeddingService()
                    query_embedding = await embedding_service.generate_embedding(query.strip())
                except Exception as e:
                    logger.warning(
                        "library_embedding_failed",
                        query=query,
                        search_mode=search_mode.value,
                        error=str(e),
                        fallback_to_fulltext=True,
                    )
                    # Fallback to full-text search if embedding fails
                    if search_mode == SearchMode.hybrid:
                        # For hybrid, fallback to fulltext
                        search_mode = SearchMode.fulltext
                    else:
                        # For semantic-only, raise error
                        raise HTTPException(
                            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
                            detail="Embedding generation failed",
                        ) from e
                finally:
                    if embedding_service:
                        await embedding_service.close()

            # Execute search based on mode
            if search_mode == SearchMode.hybrid:
                results = await repo.hybrid_search(
                    query=query,
                    embedding=query_embedding,
                    limit=limit,
                    offset=offset,
                )
            elif search_mode == SearchMode.fulltext:
                results = await repo.search_by_text(
                    query=query,
                    limit=limit,
                    offset=offset,
                )
            elif search_mode == SearchMode.semantic:
                # For semantic search, don't apply offset at repository level
                # (vector search doesn't support offset well)
                all_results = await repo.search_by_vector(
                    embedding=query_embedding,
                    limit=limit + offset,  # Fetch extra to support pagination
                )
                # Apply offset in application layer
                results = all_results[offset : offset + limit]
            else:
                # Should never reach here due to Enum validation
                raise HTTPException(
                    status_code=http_status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid search_mode: {search_mode}",
                )

            # Get search snippets for results (only for fulltext and hybrid)
            items: list[LibrarySearchResult] = []
            for analysis, score in results:
                # Get snippet if using text search
                snippet: str | None = None
                if search_mode in (SearchMode.fulltext, SearchMode.hybrid):
                    try:
                        # Type ignore: analysis.id is UUID at runtime, mypy sees Column[UUID]
                        snippet = await repo.get_search_snippet(
                            analysis_id=analysis.id,  # type: ignore[arg-type]
                            query=query,
                        )
                    except Exception as e:  # noqa: BLE001 - snippet failures are non-critical
                        logger.warning(
                            "library_snippet_failed",
                            analysis_id=str(analysis.id),
                            error=str(e),
                        )

                # Type casts needed: SQLAlchemy Column types to Python types
                items.append(
                    LibrarySearchResult(
                        analysis_id=str(analysis.id),  # type: ignore[arg-type]
                        url=str(analysis.url),
                        title=str(analysis.title) if analysis.title else None,
                        content_type=str(analysis.content_type),
                        snippet=snippet,
                        rank=score,
                        created_at=analysis.created_at.isoformat() if analysis.created_at else "",
                    )
                )

            # For search mode, total is approximate (we don't count all matches)
            # This is acceptable for search UX
            total = len(items) + offset if len(items) == limit else offset + len(items)

            logger.info(
                "library_search_complete",
                query=query,
                search_mode=search_mode.value,
                limit=limit,
                offset=offset,
                results_count=len(items),
            )

            return LibraryListResponse(
                items=items,
                total=total,
                limit=limit,
                offset=offset,
            )

        # Listing mode: no query provided
        else:
            logger.info(
                "library_list_start",
                content_type=content_type,
                status_filter=status,
                limit=limit,
                offset=offset,
            )

            # Build filters
            filters = LibraryFilters(
                content_type=content_type,
                status=status,
            )

            # Get paginated list with total count
            analyses, total = await repo.list_analyses(
                filters=filters,
                limit=limit,
                offset=offset,
            )

            # Build response items
            # Type casts needed: SQLAlchemy Column types to Python types
            items = [
                LibrarySearchResult(
                    analysis_id=str(analysis.id),  # type: ignore[arg-type]
                    url=str(analysis.url),
                    title=str(analysis.title) if analysis.title else None,
                    content_type=str(analysis.content_type),
                    snippet=None,  # No snippet in listing mode
                    rank=0.0,  # No ranking in listing mode
                    created_at=analysis.created_at.isoformat() if analysis.created_at else "",
                )
                for analysis in analyses
            ]

            logger.info(
                "library_list_complete",
                filters=filters.model_dump(),
                limit=limit,
                offset=offset,
                total=total,
                results_count=len(items),
            )

            return LibraryListResponse(
                items=items,
                total=total,
                limit=limit,
                offset=offset,
            )

    except HTTPException:
        # Re-raise HTTP exceptions without modification
        raise

    except Exception as e:
        logger.error(
            "library_request_failed",
            query=query,
            search_mode=search_mode.value if query else None,
            content_type=content_type,
            status_filter=status,
            error=str(e),
            exc_info=True,
        )
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Library request failed",
        ) from e
