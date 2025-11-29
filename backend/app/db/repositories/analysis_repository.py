"""Analysis repository for database operations with vector similarity search.

This module implements the repository pattern for analysis database operations,
including two-stage vector search using pgvector 0.4.1 binary quantization.
"""

from typing import TYPE_CHECKING, Annotated, Protocol

from fastapi import Depends
from pgvector.sqlalchemy import BIT, Vector  # type: ignore[import-untyped]
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.db.session import get_db
from app.models.analysis import Analysis

# Embedding dimensions constant (OpenAI text-embedding-3-small)
EMBEDDING_DIMENSIONS = 1536

if TYPE_CHECKING:
    from collections.abc import AsyncIterator

logger = get_logger(__name__)


class IAnalysisRepository(Protocol):
    """Protocol interface for analysis repository operations."""

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


class AnalysisRepository:
    """Repository implementation for analysis database operations with vector search."""

    def __init__(self, session: AsyncSession) -> None:
        """Initialize repository with database session.

        Args:
            session: Async database session

        """
        self.session = session

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
        # pgvector 0.4.1: Use func.cast with Vector type for Python list conversion
        # Create a literal vector expression from Python list
        from sqlalchemy import literal

        # Convert Python list to SQLAlchemy Vector expression
        query_vector_literal = literal(query_embedding)
        query_vector_expr = func.cast(query_vector_literal, Vector(EMBEDDING_DIMENSIONS))
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
