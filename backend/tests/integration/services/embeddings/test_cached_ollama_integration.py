"""Integration tests for CachedEmbeddingService with real Ollama.

These tests require Ollama to be running locally with nomic-embed-text model.
They verify the full 3-tier fallback chain works with real services.

Skip these tests if Ollama is not available (CI environments).
"""

from __future__ import annotations

import hashlib
import json
import math
from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from pathlib import Path

from app.core.config import settings
from app.shared.services.embeddings.cached import CachedEmbeddingService


def create_test_cache(texts: list[str], dimensions: int = 1536) -> dict:
    """Create a test cache with embeddings for given texts."""
    embeddings = {}
    for text in texts:
        text_hash = hashlib.sha256(text.encode("utf-8")).hexdigest()
        vector = [float(i % 10) / 10.0 for i in range(dimensions)]
        norm = math.sqrt(sum(v * v for v in vector))
        vector = [v / norm for v in vector]
        embeddings[text_hash] = {
            "text_preview": text[:100],
            "vector": vector,
        }
    return {
        "version": "1.0",
        "model": "text-embedding-3-small",
        "dimensions": dimensions,
        "generated_at": "2025-12-29T00:00:00Z",
        "embeddings": embeddings,
    }


@pytest.fixture
def cache_file(tmp_path: Path):
    """Create a temporary cache file with test data."""
    cache_data = create_test_cache(["hello world", "test text"])
    cache_path = tmp_path / "embeddings_cache.json"
    with cache_path.open("w") as f:
        json.dump(cache_data, f)
    return cache_path


@pytest.fixture
def empty_cache_file(tmp_path: Path):
    """Create an empty cache file."""
    cache_data = create_test_cache([])
    cache_path = tmp_path / "empty_cache.json"
    with cache_path.open("w") as f:
        json.dump(cache_data, f)
    return cache_path


# Skip all tests if Ollama is not enabled
pytestmark = pytest.mark.skipif(
    not settings.OLLAMA_ENABLED,
    reason="OLLAMA_ENABLED=false, skipping Ollama integration tests",
)


class TestCachedEmbeddingServiceWithOllama:
    """Integration tests with real Ollama service."""

    @pytest.mark.asyncio
    async def test_tier2_ollama_fallback(self, empty_cache_file: Path):
        """Test Tier 2 (Ollama) is used on cache miss when available."""
        service = CachedEmbeddingService(cache_path=empty_cache_file)

        # Skip if Ollama not available
        if not service._ollama_available:
            pytest.skip("Ollama service not reachable")

        # Generate embedding for uncached text
        embedding = await service.generate_embedding("test embedding for ollama")

        # Should use Ollama (768 dimensions for nomic-embed-text)
        stats = service.get_stats()
        assert stats["tier2_ollama_hits"] == 1
        assert stats["tier3_deterministic_fallbacks"] == 0
        assert len(embedding) == 768  # Ollama's nomic-embed-text dimension

    @pytest.mark.asyncio
    async def test_full_fallback_chain(self, cache_file: Path):
        """Test complete 3-tier fallback chain with real services."""
        service = CachedEmbeddingService(cache_path=cache_file)

        # Skip if Ollama not available
        if not service._ollama_available:
            pytest.skip("Ollama service not reachable")

        # Tier 1: Cache hit
        embedding1 = await service.generate_embedding("hello world")
        assert len(embedding1) == 1536  # From cache (OpenAI dimensions)
        assert service.get_stats()["tier1_cache_hits"] == 1

        # Tier 2: Ollama fallback
        embedding2 = await service.generate_embedding("uncached ollama test")
        assert len(embedding2) == 768  # From Ollama
        assert service.get_stats()["tier2_ollama_hits"] == 1

    @pytest.mark.asyncio
    async def test_dimension_mismatch_handling(self, empty_cache_file: Path):
        """Test that dimension mismatch between cache and Ollama is handled."""
        service = CachedEmbeddingService(cache_path=empty_cache_file)

        # Skip if Ollama not available
        if not service._ollama_available:
            pytest.skip("Ollama service not reachable")

        # Generate embedding (will use Ollama with 768 dims)
        embedding = await service.generate_embedding("dimension mismatch test")

        # Should track the dimension mismatch warning
        stats = service.get_stats()
        assert stats["dimension_mismatch_warnings"] >= 1
        assert len(embedding) == 768  # Ollama dimension, not cache dimension
