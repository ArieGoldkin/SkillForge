"""Shingle/hash deduplication for chunk payloads.

Provides two levels of deduplication:
1. In-memory: Quick content-only hash for within-batch dedup
2. Model-aware: Hash includes model+version to trigger re-embedding on model upgrade
"""

from __future__ import annotations

import hashlib
from collections.abc import Iterable
from dataclasses import dataclass

from app.services.chunking.chunker import ChunkText


@dataclass
class DedupStats:
    """Statistics from deduplication operation."""

    kept: int
    dropped: int


@dataclass
class DatabaseDedupStats:
    """Extended statistics for database-aware deduplication (Issue #215)."""

    total: int  # Total chunks before dedup
    skipped: int  # Chunks skipped (already in database)
    to_embed: int  # Chunks that need embedding


def _hash_text(text: str) -> str:
    """Content-only hash for in-memory deduplication."""
    return hashlib.sha256(text.strip().lower().encode("utf-8")).hexdigest()


def compute_chunk_hash(
    text: str,
    model: str,
    model_version: str,
) -> str:
    """Compute model-aware hash for database deduplication.

    This hash includes model and version information so that chunks
    are automatically re-embedded when the embedding model changes.

    Args:
        text: The chunk text content
        model: Embedding model name (e.g., 'text-embedding-3-small')
        model_version: Model version string

    Returns:
        SHA256 hash of normalized content + model info

    """
    normalized_text = text.strip().lower()
    content = f"{normalized_text}|{model}|{model_version}"
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


def deduplicate(chunks: Iterable[ChunkText]) -> tuple[list[ChunkText], DedupStats]:
    """Remove duplicate chunk texts based on content hash (in-memory).

    This is fast in-memory deduplication for removing duplicates within
    a single batch. For database-aware deduplication that skips chunks
    that already have embeddings, use deduplicate_with_database().
    """
    seen: set[str] = set()
    kept: list[ChunkText] = []
    dropped = 0

    for chunk in chunks:
        h = _hash_text(chunk.text)
        if h in seen:
            dropped += 1
            continue
        seen.add(h)
        kept.append(chunk)

    return kept, DedupStats(kept=len(kept), dropped=dropped)


def deduplicate_with_hashes(
    chunks: list[ChunkText],
    existing_hashes: set[str],
    model: str,
    model_version: str,
) -> tuple[list[ChunkText], DatabaseDedupStats]:
    """Filter out chunks that already have embeddings in the database.

    This function checks computed hashes against a set of existing hashes
    from the database to avoid re-embedding unchanged content.

    Args:
        chunks: List of chunks to potentially embed
        existing_hashes: Set of hashes that already exist in database
        model: Embedding model name
        model_version: Model version string

    Returns:
        Tuple of (new_chunks, stats) where new_chunks need embedding

    Example:
        >>> chunks = [ChunkText(...), ChunkText(...)]
        >>> # Query database for existing hashes
        >>> existing = await repo.get_existing_hashes(analysis_id, chunk_hashes)
        >>> new_chunks, stats = deduplicate_with_hashes(chunks, existing, model, version)
        >>> # Only embed new_chunks

    """
    new_chunks: list[ChunkText] = []
    skipped = 0

    for chunk in chunks:
        chunk_hash = compute_chunk_hash(chunk.text, model, model_version)

        if chunk_hash in existing_hashes:
            skipped += 1
            continue

        new_chunks.append(chunk)

    return new_chunks, DatabaseDedupStats(
        total=len(chunks),
        skipped=skipped,
        to_embed=len(new_chunks),
    )
