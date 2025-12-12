"""Deterministic, offline embeddings for tests and CI.

This module provides a cheap, deterministic embedding implementation that:
- Produces fixed-size vectors compatible with pgvector storage.
- Requires no external API keys.
- Is stable across runs (hash-based), enabling repeatable CI.

It is NOT intended to replace production embeddings; it is for smoke tests,
evaluation, and E2E fixtures where cost and determinism matter.
"""

from __future__ import annotations

import hashlib
import itertools
import math


class DeterministicEmbeddingService:
    """Deterministic embedding service using a hashing trick over tokens."""

    def __init__(self, dims: int = 1536) -> None:
        """Initialize with target embedding dimension."""
        self._dims = dims

    async def generate_embedding(self, text: str, normalize: bool = True) -> list[float]:
        """Generate a deterministic embedding vector for the given text."""
        tokens = [t for t in "".join(c.lower() if c.isalnum() else " " for c in text).split() if t]
        vec = [0.0] * self._dims

        # Unigrams + bigrams to improve phrase matching while staying cheap.
        grams: list[str] = tokens[:]
        grams.extend([f"{a}_{b}" for a, b in itertools.pairwise(tokens)])

        for tok in grams:
            h = hashlib.sha256(tok.encode("utf-8")).digest()
            idx = int.from_bytes(h[:4], "big") % self._dims
            vec[idx] += 1.0

        if normalize:
            norm = math.sqrt(sum(v * v for v in vec)) or 1.0
            vec = [v / norm for v in vec]

        return vec
