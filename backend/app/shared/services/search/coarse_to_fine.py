"""Coarse-to-fine retrieval over chunk store (placeholder vector search)."""

from __future__ import annotations

from typing import TYPE_CHECKING

from app.db.models.analysis_chunk import AnalysisChunk

if TYPE_CHECKING:
    from app.db.repositories.chunk_repository import ChunkRepository


async def retrieve_coarse_to_fine(
    repo: ChunkRepository,
    *,
    top_k_coarse: int = 5,
    top_k_fine: int = 5,
) -> list[dict]:
    """Retrieve coarse chunks, then fine chunks constrained to coarse paths.

    Note: Vector search scoring is placeholder (0.0). Replace with pgvector kNN.
    """
    coarse_hits = await repo.search_coarse(limit=top_k_coarse)
    coarse_paths: list[list[str]] = [
        # SQLAlchemy Column type - ty can't infer list() on Column[ARRAY]
        list(hit.path) if hit.path else []  # type: ignore[arg-type]
        for hit, _ in coarse_hits
        if isinstance(hit, AnalysisChunk) and hit.path
    ]

    fine_hits = await repo.search_fine_by_paths(coarse_paths, limit=top_k_fine)

    results: list[dict] = []
    for chunk, score in fine_hits:
        results.append(
            {
                "analysis_id": str(chunk.analysis_id),
                "chunk_id": str(chunk.id),
                "score": score,
                "snippet": chunk.snippet,
                "section_title": chunk.section_title,
                "path": chunk.path,
                "granularity": chunk.granularity,
                "created_at": chunk.created_at,
            }
        )
    return results
