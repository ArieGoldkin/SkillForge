"""Repository for chunk-level embeddings."""

from __future__ import annotations

from collections.abc import Iterable
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.analysis_chunk import AnalysisChunk


class ChunkRepository:
    """Chunk repository for storing and retrieving chunk embeddings."""

    def __init__(self, session: AsyncSession) -> None:
        """Initialize the repository with an async database session."""
        self.session = session

    async def create_many(self, items: Iterable[dict]) -> None:
        """Bulk create analysis chunks from dictionaries."""
        objects = [AnalysisChunk(**item) for item in items]
        self.session.add_all(objects)
        await self.session.flush()

    async def list_by_analysis(self, analysis_id: UUID) -> list[AnalysisChunk]:
        """List all chunks for a given analysis ID."""
        stmt = select(AnalysisChunk).where(AnalysisChunk.analysis_id == analysis_id)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def search_coarse(
        self,
        limit: int = 10,
    ) -> list[tuple[AnalysisChunk, float]]:
        """Search coarse-grained chunks (placeholder for vector search)."""
        stmt = select(AnalysisChunk).where(AnalysisChunk.granularity == "coarse").limit(limit)
        result = await self.session.execute(stmt)
        return [(row, 0.0) for row in result.scalars().all()]

    async def search_fine_by_paths(
        self,
        paths: list[list[str]],
        limit: int = 10,
    ) -> list[tuple[AnalysisChunk, float]]:
        """Search fine-grained chunks constrained to paths (placeholder for vector search)."""
        if not paths:
            return []
        stmt = select(AnalysisChunk).where(AnalysisChunk.granularity == "fine").limit(limit)
        result = await self.session.execute(stmt)
        return [(row, 0.0) for row in result.scalars().all()]
