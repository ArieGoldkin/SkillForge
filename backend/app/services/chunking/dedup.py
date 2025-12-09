"""Shingle/hash deduplication for chunk payloads."""

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


def _hash_text(text: str) -> str:
    return hashlib.sha256(text.strip().lower().encode("utf-8")).hexdigest()


def deduplicate(chunks: Iterable[ChunkText]) -> tuple[list[ChunkText], DedupStats]:
    """Remove duplicate chunk texts based on hash."""
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
