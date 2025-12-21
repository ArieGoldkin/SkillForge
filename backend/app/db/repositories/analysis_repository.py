"""Analysis repository for database operations with vector similarity search.

This module implements the repository pattern for analysis database operations,
including two-stage vector search using pgvector 0.4.1 binary quantization.
"""

import uuid
from typing import TYPE_CHECKING, Annotated, Protocol

from fastapi import Depends
from pgvector.sqlalchemy import BIT, Vector  # type: ignore[import-untyped]
from sqlalchemy import func, select, update
from sqlalchemy.exc import NoResultFound
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.db.models.analysis import Analysis
from app.db.models.progress import AnalysisProgress
from app.db.session import get_db

# Embedding dimensions constant (OpenAI text-embedding-3-small)
EMBEDDING_DIMENSIONS = 1536

if TYPE_CHECKING:
    from collections.abc import AsyncIterator

logger = get_logger(__name__)


class IAnalysisRepository(Protocol):
    """Protocol interface for analysis repository operations."""

    async def get_by_id(self, analysis_id: uuid.UUID) -> Analysis | None:
        """Get a single analysis by ID."""
        ...

    async def create_analysis(
        self,
        *,
        analysis_id: uuid.UUID,
        url: str,
        content_type: str,
        status: str,
        title: str | None = None,
    ) -> Analysis:
        """Create a new analysis record."""
        ...

    async def get_by_url(self, url: str) -> Analysis | None:
        """Get an existing analysis by URL."""
        ...

    async def find_similar_analyses(
        self,
        query_embedding: list[float],
        limit: int = 5,
        fast_search_limit: int = 20,
    ) -> list[Analysis]:
        """Find similar analyses using two-stage vector search."""
        ...

    async def stream_all_analyses(
        self,
        order_by: str = "created_at",
        limit: int | None = None,
    ) -> "AsyncIterator[Analysis]":
        """Stream all analyses using server-side cursor."""
        ...

    async def mark_failed(
        self,
        analysis_id: uuid.UUID,
        error_code: str,
        error_message: str,
        failed_at_stage: str = "extraction",
    ) -> None:
        """Mark an analysis as failed with error details."""
        ...

    async def get_progress_events(self, analysis_id: uuid.UUID) -> list[AnalysisProgress]:
        """Get all progress events for an analysis."""
        ...


class AnalysisRepository:
    """Repository implementation for analysis database operations with vector search."""

    def __init__(self, session: AsyncSession) -> None:
        """Initialize repository with database session.

        Args:
            session: Async database session

        """
        self.session = session

    async def get_by_id(self, analysis_id: uuid.UUID) -> Analysis | None:
        """Get analysis by ID."""
        result = await self.session.execute(select(Analysis).where(Analysis.id == analysis_id))
        return result.scalar_one_or_none()

    async def create_analysis(
        self,
        *,
        analysis_id: uuid.UUID,
        url: str,
        content_type: str,
        status: str,
        title: str | None = None,
    ) -> Analysis:
        """Create a new analysis record."""
        analysis = Analysis(
            id=analysis_id,
            url=url,
            content_type=content_type,
            status=status,
            title=title,
        )
        self.session.add(analysis)
        await self.session.commit()
        await self.session.refresh(analysis)
        return analysis

    async def get_by_url(self, url: str) -> Analysis | None:
        """Get analysis by URL for idempotency check."""
        result = await self.session.execute(select(Analysis).where(Analysis.url == url))
        return result.scalar_one_or_none()

    async def find_similar_analyses(
        self,
        query_embedding: list[float],
        limit: int = 5,
        fast_search_limit: int = 20,
    ) -> list[Analysis]:
        """Find similar analyses using two-stage vector search.

        Stage 1: Fast binary quantization search (top N candidates)
        Stage 2: Re-rank with original vectors (top K results)

        This approach provides 10-100x faster search for large datasets while
        maintaining accuracy through re-ranking with original vectors.

        Args:
            query_embedding: Query embedding vector (1536 dimensions)
            limit: Number of final results to return (default: 5)
            fast_search_limit: Number of candidates from binary search (default: 20)

        Returns:
            List of similar Analysis objects, ordered by similarity

        Example:
            >>> repo = AnalysisRepository(session)
            >>> query_embedding = [0.1] * 1536
            >>> similar = await repo.find_similar_analyses(query_embedding, limit=5)
            >>> len(similar) <= 5
            True

        """
        if not query_embedding:
            logger.warning("find_similar_empty_query")
            return []

        if len(query_embedding) != EMBEDDING_DIMENSIONS:
            logger.error(
                "find_similar_invalid_dimensions",
                expected=EMBEDDING_DIMENSIONS,
                actual=len(query_embedding),
            )
            return []

        # Stage 1: Fast binary quantization search
        # Convert query embedding to binary quantized vector
        # pgvector 0.4.1: Convert Python list to PostgreSQL array format for Vector type
        from sqlalchemy import text

        # Convert Python list to PostgreSQL array format (pgvector-compatible)
        # pgvector expects array format: '[0.1,0.2,0.3,...]' (square brackets, not curly)
        # Safe: query_embedding is list[float] from embedding service, not user input
        vector_array_str = "[" + ",".join(str(x) for x in query_embedding) + "]"
        # Cast array string directly to Vector type
        # Using text() with literal array string is safe here (floats only, no SQL injection)
        query_vector_expr = func.cast(
            text(f"'{vector_array_str}'::vector"),
            Vector(EMBEDDING_DIMENSIONS),
        )
        binary_query = func.binary_quantize(query_vector_expr)

        # Fast search with binary quantization (hamming distance)
        subquery = (
            select(Analysis)
            .where(Analysis.content_embedding.isnot(None))
            .order_by(
                func.cast(
                    func.binary_quantize(Analysis.content_embedding),
                    BIT(EMBEDDING_DIMENSIONS),
                ).hamming_distance(binary_query)
            )
            .limit(fast_search_limit)
            .subquery()
        )

        # Stage 2: Re-rank with original vectors for accuracy
        # Use cosine distance on original vectors for final ranking
        # Reuse the query_vector_expr from stage 1 for consistency
        results = await self.session.scalars(
            select(subquery)
            .order_by(
                subquery.c.content_embedding.cosine_distance(query_vector_expr)  # type: ignore[attr-defined]
            )
            .limit(limit)
        )

        similar_analyses = list(results.all())

        logger.info(
            "find_similar_complete",
            query_dimensions=len(query_embedding),
            fast_search_limit=fast_search_limit,
            final_limit=limit,
            results_count=len(similar_analyses),
        )

        return similar_analyses

    async def stream_all_analyses(
        self,
        order_by: str = "created_at",
        limit: int | None = None,
    ) -> "AsyncIterator[Analysis]":
        """Stream all analyses using server-side cursor.

        Memory-efficient for large datasets. Useful for bulk exports and
        large dataset processing without loading all rows into memory.

        Uses asyncpg 0.31.0 server-side cursor support for efficient iteration.

        Args:
            order_by: Column to order by (default: "created_at")
            limit: Optional limit on number of rows to stream

        Yields:
            Analysis objects one at a time

        Example:
            >>> repo = AnalysisRepository(session)
            >>> async for analysis in repo.stream_all_analyses(limit=100):
            ...     process(analysis)

        Note:
            This method requires a raw asyncpg connection. For production use,
            consider using SQLAlchemy's stream_scalars for better compatibility.

        """
        # Use SQLAlchemy's stream_scalars for memory-efficient streaming
        # This leverages asyncpg 0.31.0's improved cursor support
        # Validate order_by column to prevent SQL injection
        valid_columns = {"created_at", "updated_at", "id", "status"}
        if order_by not in valid_columns:
            order_by = "created_at"

        query = select(Analysis).order_by(getattr(Analysis, order_by))
        if limit:
            query = query.limit(limit)

        # Stream results using SQLAlchemy's stream_scalars for memory-efficient streaming
        # stream_scalars returns an AsyncScalarResult that can be used as a context manager
        # This leverages asyncpg 0.31.0's improved cursor support
        # Type ignore needed because mypy doesn't recognize AsyncScalarResult
        # as async context manager
        async with self.session.stream_scalars(query) as result:  # type: ignore[attr-defined]
            async for analysis in result:
                yield analysis

    async def mark_failed(
        self,
        analysis_id: uuid.UUID,
        error_code: str,
        error_message: str,
        failed_at_stage: str = "extraction",
    ) -> None:
        """Mark an analysis as failed with error details.

        Updates the analysis status to 'failed' and records error information
        for debugging and user-facing error messages.

        Args:
            analysis_id: UUID of the analysis to mark as failed
            error_code: Error code from ExtractionErrorCode enum (e.g., "HTTP_404")
            error_message: Human-readable error description
            failed_at_stage: Workflow stage where failure occurred (default: "extraction")

        Raises:
            NoResultFound: If analysis_id doesn't exist

        """
        stmt = (
            update(Analysis)
            .where(Analysis.id == analysis_id)
            .values(
                status="failed",
                error_code=error_code,
                error_message=error_message,
                failed_at_stage=failed_at_stage,
            )
        )
        result = await self.session.execute(stmt)

        # Type guard: result from execute() is a Result object with rowcount attribute
        if not hasattr(result, "rowcount") or result.rowcount == 0:  # type: ignore[attr-defined]
            msg = f"Analysis {analysis_id} not found"
            raise NoResultFound(msg)

        await self.session.commit()

        logger.info(
            "analysis_marked_failed",
            analysis_id=str(analysis_id),
            error_code=error_code,
            failed_at_stage=failed_at_stage,
        )

    async def get_progress_events(self, analysis_id: uuid.UUID) -> list[AnalysisProgress]:
        """Get all progress events for an analysis, ordered by creation time.

        Returns the stored SSE events from the analysis_progress table,
        allowing reconstruction of the analysis timeline for completed analyses.

        Args:
            analysis_id: UUID of the analysis

        Returns:
            List of AnalysisProgress records ordered by created_at

        """
        result = await self.session.execute(
            select(AnalysisProgress)
            .where(AnalysisProgress.analysis_id == analysis_id)
            .order_by(AnalysisProgress.created_at)
        )
        return list(result.scalars().all())


def get_analysis_repository(
    db: Annotated[AsyncSession, Depends(get_db)],
) -> IAnalysisRepository:
    """Dependency injection function for analysis repository.

    Args:
        db: Database session from dependency injection

    Returns:
        AnalysisRepository instance (implements IAnalysisRepository Protocol)

    """
    return AnalysisRepository(session=db)  # type: ignore[return-value]
