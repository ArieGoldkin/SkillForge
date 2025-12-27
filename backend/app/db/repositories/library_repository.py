"""Library repository for search and filtering operations.

This module implements the repository pattern for library search operations,
including full-text search, vector similarity search, and hybrid search using
Reciprocal Rank Fusion (RRF).
"""

import math
from typing import Annotated, Protocol
from uuid import UUID

from fastapi import Depends
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.branded_ids import AnalysisID
from app.core.logging import get_logger
from app.db.models.analysis import Analysis
from app.db.session import get_db
from app.schemas.library import LibraryFilters

logger = get_logger(__name__)

# RRF constant for hybrid search (standard value from literature)
RRF_K = 60


class ILibraryRepository(Protocol):
    """Protocol interface for library repository operations."""

    async def search_by_text(
        self,
        query: str,
        limit: int = 20,
        offset: int = 0,
    ) -> list[tuple[Analysis, float]]:
        """Full-text search using the search_vector column."""
        ...

    async def search_by_vector(
        self,
        embedding: list[float],
        limit: int = 20,
    ) -> list[tuple[Analysis, float]]:
        """Semantic search using cosine similarity."""
        ...

    async def hybrid_search(
        self,
        query: str,
        embedding: list[float],
        limit: int = 20,
        offset: int = 0,
    ) -> list[tuple[Analysis, float]]:
        """Combine FTS and vector search using Reciprocal Rank Fusion."""
        ...

    async def list_analyses(
        self,
        filters: LibraryFilters,
        limit: int = 20,
        offset: int = 0,
    ) -> tuple[list[Analysis], int]:
        """List analyses with filtering and pagination."""
        ...

    async def get_search_snippet(
        self,
        analysis_id: AnalysisID,
        query: str,
    ) -> str | None:
        """Generate highlighted search snippet using ts_headline."""
        ...


class LibraryRepository:
    """Repository implementation for library search operations."""

    def __init__(self, session: AsyncSession) -> None:
        """Initialize repository with database session.

        Args:
            session: Async database session

        """
        self.session = session

    async def search_by_text(
        self,
        query: str,
        limit: int = 20,
        offset: int = 0,
    ) -> list[tuple[Analysis, float]]:
        """Full-text search using the search_vector column.

        Uses PostgreSQL's full-text search with plainto_tsquery for user-friendly
        query parsing. Results are ranked using ts_rank_cd (Cover Density ranking).

        Args:
            query: Search query string (plain text, not tsquery syntax)
            limit: Number of results to return (default: 20)
            offset: Number of results to skip (default: 0)

        Returns:
            List of tuples (Analysis, rank_score), ordered by relevance (desc)

        Example:
            >>> repo = LibraryRepository(session)
            >>> results = await repo.search_by_text("postgresql full-text search", limit=10)
            >>> for analysis, rank in results:
            ...     print(f"{analysis.title}: {rank}")

        """
        if not query or not query.strip():
            logger.warning("search_by_text_empty_query")
            return []

        # Use plainto_tsquery for user-friendly query parsing
        ts_query = func.plainto_tsquery("english", query)

        # Search with ranking using ts_rank_cd (Cover Density ranking)
        # ts_rank_cd considers proximity of matching terms
        stmt = (
            select(
                Analysis,
                func.ts_rank_cd(Analysis.search_vector, ts_query).label("rank"),
            )
            .where(Analysis.search_vector.bool_op("@@")(ts_query))
            .where(Analysis.status == "complete")
            .order_by(func.ts_rank_cd(Analysis.search_vector, ts_query).desc())
            .limit(limit)
            .offset(offset)
        )

        result = await self.session.execute(stmt)
        rows = result.all()

        logger.info(
            "search_by_text_complete",
            query=query,
            limit=limit,
            offset=offset,
            results_count=len(rows),
        )

        # Return list of (Analysis, rank) tuples
        return [(row[0], float(row[1])) for row in rows]

    async def search_by_vector(
        self,
        embedding: list[float],
        limit: int = 20,
    ) -> list[tuple[Analysis, float]]:
        """Semantic search using cosine similarity.

        Uses pgvector's cosine distance operator (<=>) for similarity search.
        Lower distance means higher similarity.

        Args:
            embedding: Query embedding vector (1536 dimensions for OpenAI text-embedding-3-small)
            limit: Number of results to return (default: 20)

        Returns:
            List of tuples (Analysis, distance), ordered by similarity (asc distance)

        Example:
            >>> repo = LibraryRepository(session)
            >>> query_embedding = [0.1] * 1536  # From embedding service
            >>> results = await repo.search_by_vector(query_embedding, limit=10)
            >>> for analysis, distance in results:
            ...     print(f"{analysis.title}: {distance}")

        """
        if not embedding:
            logger.warning("search_by_vector_empty_embedding")
            return []

        # Use cosine distance for similarity search (lower = more similar)
        # pgvector's <=> operator computes cosine distance
        stmt = (
            select(
                Analysis,
                Analysis.content_embedding.cosine_distance(embedding).label("distance"),
            )
            .where(Analysis.status == "complete")
            .where(Analysis.content_embedding.isnot(None))
            .order_by(Analysis.content_embedding.cosine_distance(embedding))
            .limit(limit)
        )

        result = await self.session.execute(stmt)
        rows = result.all()

        logger.info(
            "search_by_vector_complete",
            embedding_dimensions=len(embedding),
            limit=limit,
            results_count=len(rows),
        )

        # Return list of (Analysis, distance) tuples, filtering out non-finite scores
        filtered: list[tuple[Analysis, float]] = []
        for row in rows:
            distance = float(row[1])
            if not math.isfinite(distance):
                logger.warning(
                    "search_by_vector_non_finite_distance",
                    analysis_id=str(row[0].id),
                    distance=distance,
                )
                continue
            filtered.append((row[0], distance))
        return filtered

    async def hybrid_search(
        self,
        query: str,
        embedding: list[float],
        limit: int = 20,
        offset: int = 0,
    ) -> list[tuple[Analysis, float]]:
        """Combine FTS and vector search using Reciprocal Rank Fusion (RRF).

        RRF is a rank-based fusion algorithm that combines results from multiple
        search methods. It's more robust than weighted score averaging because
        it doesn't depend on score normalization.

        RRF formula: score = sum(1 / (k + rank)) where k = 60 (standard value)

        Args:
            query: Search query string for full-text search
            embedding: Query embedding vector for semantic search
            limit: Number of final results to return (default: 20)
            offset: Number of results to skip for pagination (default: 0)

        Returns:
            List of tuples (Analysis, rrf_score), ordered by RRF score (desc)

        Example:
            >>> repo = LibraryRepository(session)
            >>> query = "postgresql full-text search"
            >>> embedding = [0.1] * 1536
            >>> results = await repo.hybrid_search(query, embedding, limit=10)
            >>> for analysis, score in results:
            ...     print(f"{analysis.title}: {score}")

        """
        if (not query or not query.strip()) and not embedding:
            logger.warning("hybrid_search_empty_inputs")
            return []

        # Fetch more candidates from each search type for better fusion
        candidate_limit = 50

        # Get top N from each search type
        fts_results = await self.search_by_text(query, limit=candidate_limit, offset=0)
        vector_results = await self.search_by_vector(embedding, limit=candidate_limit)

        # Assign ranks (1-indexed) and compute RRF scores
        # Cast analysis.id to UUID - at runtime it's UUID, but type checker sees Column[UUID]
        fts_ranks: dict[UUID, int] = {
            UUID(str(analysis.id)): i + 1 for i, (analysis, _) in enumerate(fts_results)
        }
        vec_ranks: dict[UUID, int] = {
            UUID(str(analysis.id)): i + 1 for i, (analysis, _) in enumerate(vector_results)
        }

        # Combine unique analysis IDs
        all_ids = set(fts_ranks.keys()) | set(vec_ranks.keys())

        # Calculate RRF score for each analysis
        # If an analysis appears in only one result set, use a high default rank (1000)
        scores: dict[UUID, float] = {}
        for analysis_id in all_ids:
            fts_rank = fts_ranks.get(analysis_id, 1000)  # Default high rank if not found
            vec_rank = vec_ranks.get(analysis_id, 1000)
            # RRF formula: sum of reciprocal ranks
            scores[analysis_id] = (1 / (RRF_K + fts_rank)) + (1 / (RRF_K + vec_rank))

        # Sort by RRF score descending
        sorted_ids = sorted(scores.keys(), key=lambda x: scores[x], reverse=True)

        # Apply pagination
        paginated_ids = sorted_ids[offset : offset + limit]

        # Fetch full Analysis objects in the sorted order
        if not paginated_ids:
            logger.info(
                "hybrid_search_complete",
                query=query,
                limit=limit,
                offset=offset,
                results_count=0,
            )
            return []

        # Fetch analyses by IDs
        stmt = select(Analysis).where(Analysis.id.in_(paginated_ids))
        result = await self.session.execute(stmt)
        # Cast analysis.id to UUID - at runtime it's UUID, but type checker sees Column[UUID]
        analyses_by_id: dict[UUID, Analysis] = {
            UUID(str(analysis.id)): analysis for analysis in result.scalars().all()
        }

        # Build result list in sorted order with RRF scores
        results = [
            (analyses_by_id[analysis_id], scores[analysis_id])
            for analysis_id in paginated_ids
            if analysis_id in analyses_by_id
        ]

        logger.info(
            "hybrid_search_complete",
            query=query,
            limit=limit,
            offset=offset,
            fts_count=len(fts_results),
            vector_count=len(vector_results),
            unique_count=len(all_ids),
            results_count=len(results),
        )

        return results

    async def list_analyses(
        self,
        filters: LibraryFilters,
        limit: int = 20,
        offset: int = 0,
    ) -> tuple[list[Analysis], int]:
        """List analyses with filtering and pagination.

        Args:
            filters: Filter parameters (content_type, status)
            limit: Number of results to return (default: 20)
            offset: Number of results to skip (default: 0)

        Returns:
            Tuple of (analyses_list, total_count)

        Example:
            >>> repo = LibraryRepository(session)
            >>> filters = LibraryFilters(content_type="article", status="complete")
            >>> analyses, total = await repo.list_analyses(filters, limit=20, offset=0)
            >>> print(f"Found {total} articles, showing {len(analyses)}")

        """
        # Build base query
        stmt = select(Analysis)

        # Apply filters
        if filters.content_type:
            stmt = stmt.where(Analysis.content_type == filters.content_type)
        if filters.status:
            stmt = stmt.where(Analysis.status == filters.status)

        # Get total count (before pagination)
        count_stmt = select(func.count()).select_from(stmt.subquery())
        total_result = await self.session.execute(count_stmt)
        total = total_result.scalar() or 0

        # Apply sorting and pagination
        stmt = stmt.order_by(Analysis.created_at.desc()).limit(limit).offset(offset)

        # Execute query
        result = await self.session.execute(stmt)
        analyses = list(result.scalars().all())

        logger.info(
            "list_analyses_complete",
            filters=filters.model_dump(),
            limit=limit,
            offset=offset,
            total=total,
            results_count=len(analyses),
        )

        return analyses, total

    async def get_search_snippet(
        self,
        analysis_id: AnalysisID,
        query: str,
    ) -> str | None:
        """Generate highlighted search snippet using ts_headline.

        Creates a snippet of the content with search terms highlighted using
        <mark> tags. Uses PostgreSQL's ts_headline function for intelligent
        snippet generation.

        Args:
            analysis_id: ID of the analysis to get snippet for
            query: Search query for highlighting

        Returns:
            Highlighted snippet string, or None if analysis not found

        Example:
            >>> repo = LibraryRepository(session)
            >>> snippet = await repo.get_search_snippet(
            ...     UUID("123e4567-e89b-12d3-a456-426614174000"), "postgresql full-text search"
            ... )
            >>> print(snippet)
            "...PostgreSQL provides <mark>full-text search</mark> capabilities..."

        """
        if not query or not query.strip():
            logger.warning("get_search_snippet_empty_query")
            return None

        # Generate highlighted snippet using ts_headline
        # Configuration:
        # - StartSel/StopSel: HTML tags for highlighting
        # - MaxWords: Maximum words in snippet
        # - MinWords: Minimum words in snippet
        # - HighlightAll: Don't highlight if no matches (default: false)
        stmt = select(
            func.ts_headline(
                "english",
                Analysis.raw_content,
                func.plainto_tsquery("english", query),
                "StartSel=<mark>, StopSel=</mark>, MaxWords=50, MinWords=25",
            )
        ).where(Analysis.id == analysis_id)

        result = await self.session.execute(stmt)
        snippet = result.scalar()

        if snippet:
            logger.info(
                "get_search_snippet_complete",
                analysis_id=str(analysis_id),
                query=query,
                snippet_length=len(snippet),
            )
        else:
            logger.warning(
                "get_search_snippet_not_found",
                analysis_id=str(analysis_id),
            )

        return snippet


def get_library_repository(
    db: Annotated[AsyncSession, Depends(get_db)],
) -> ILibraryRepository:
    """Dependency injection function for library repository.

    Args:
        db: Database session from dependency injection

    Returns:
        LibraryRepository instance (implements ILibraryRepository Protocol)

    """
    return LibraryRepository(session=db)
