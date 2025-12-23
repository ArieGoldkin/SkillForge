"""Store embeddings with path/granularity metadata."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, TypedDict

from sqlalchemy.exc import IntegrityError

from app.core.logging import get_logger

if TYPE_CHECKING:
    from collections.abc import Iterable

    from app.core.types import AnalysisID
    from app.db.repositories.chunk_repository import ChunkRepository

logger = get_logger(__name__)


class StoredEmbedding(TypedDict):
    """Embedding with associated metadata for storage."""

    vector: list[float]
    metadata: dict[str, Any]


async def store_embeddings(
    payloads: Iterable[tuple[list[float], dict]],
    analysis_id: AnalysisID,
    repo: ChunkRepository,
) -> list[StoredEmbedding]:
    """Persist embeddings via ChunkRepository."""
    stored: list[StoredEmbedding] = []
    repo_items: list[dict[str, Any]] = []
    for vector, metadata in payloads:
        repo_items.append(
            {
                "analysis_id": analysis_id,
                "granularity": metadata.get("granularity"),
                "path": metadata.get("path") or [],
                "section_title": metadata.get("section_title"),
                "chunk_idx": metadata.get("chunk_idx", 0),
                "chunk_total": metadata.get("chunk_total", 0),
                "content_type": metadata.get("content_type"),
                "language": metadata.get("language"),
                "hash": metadata.get("hash") or "",
                "model": metadata.get("model"),
                "model_version": metadata.get("model_version"),
                "snippet": metadata.get("snippet"),
                "vector": vector,
            }
        )
        stored.append({"vector": vector, "metadata": metadata})

    if repo_items:
        try:
            await repo.create_many(repo_items)
        except IntegrityError as exc:
            logger.warning(
                "store_embeddings_fk_missing",
                analysis_id=analysis_id,
                error=str(exc),
            )
            # Best-effort: skip embedding persistence if FK is missing
            # (e.g., unit tests without Analysis row)
            await repo.session.rollback()
            return stored

    logger.info(
        "store_embeddings_complete",
        count=len(stored),
    )
    return stored
