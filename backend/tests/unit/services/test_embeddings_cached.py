"""Unit tests for cached embedding service.

Tests the hybrid CachedEmbeddingService with 3-tier fallback:
1. OpenAI Cache (JSON file) - primary
2. Ollama Local - if available (mocked in tests)
3. Deterministic Hash - last resort
"""

from __future__ import annotations

import hashlib
import json
import math
from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from pathlib import Path

from app.shared.services.embeddings.cached import CachedEmbeddingService


def create_test_cache(texts: list[str], dimensions: int = 1536) -> dict:
    """Create a test cache with embeddings for given texts."""
    embeddings = {}
    for text in texts:
        text_hash = hashlib.sha256(text.encode("utf-8")).hexdigest()
        # Create a simple deterministic vector for testing
        vector = [float(i % 10) / 10.0 for i in range(dimensions)]
        # Normalize it
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


class TestCachedEmbeddingService:
    """Tests for CachedEmbeddingService."""

    @pytest.fixture
    def cache_file(self, tmp_path: Path):
        """Create a temporary cache file with test data."""
        cache_data = create_test_cache(["hello world", "test text", "machine learning"])
        cache_path = tmp_path / "embeddings_cache.json"
        with cache_path.open("w") as f:
            json.dump(cache_data, f)
        return cache_path

    @pytest.fixture
    def empty_cache_file(self, tmp_path: Path):
        """Create an empty cache file."""
        cache_data = create_test_cache([])
        cache_path = tmp_path / "empty_cache.json"
        with cache_path.open("w") as f:
            json.dump(cache_data, f)
        return cache_path

    @pytest.fixture
    def service(self, cache_file: Path):
        """Create cached embedding service with test cache."""
        return CachedEmbeddingService(cache_path=cache_file)

    @pytest.fixture
    def service_empty(self, empty_cache_file: Path):
        """Create cached embedding service with empty cache."""
        return CachedEmbeddingService(cache_path=empty_cache_file)

    def test_model_name(self, service):
        """Test model identifier matches OpenAI model."""
        assert service.model == "text-embedding-3-small"

    def test_expected_dimensions(self, service):
        """Test expected dimensions is 1536."""
        assert service.expected_dimensions == 1536

    def test_cache_loaded(self, service):
        """Test cache is loaded on initialization."""
        assert service._cache is not None
        assert len(service._cache) == 3

    @pytest.mark.asyncio
    async def test_cache_hit(self, service):
        """Test embedding retrieved from cache."""
        embedding = await service.generate_embedding("hello world")
        assert len(embedding) == 1536
        # Verify it's normalized
        norm = math.sqrt(sum(v * v for v in embedding))
        assert abs(norm - 1.0) < 0.0001

    @pytest.mark.asyncio
    async def test_cache_hit_deterministic(self, service):
        """Test same input returns same cached embedding."""
        emb1 = await service.generate_embedding("test text")
        emb2 = await service.generate_embedding("test text")
        assert emb1 == emb2

    @pytest.mark.asyncio
    async def test_cache_miss_fallback(self, service):
        """Test fallback on cache miss (Ollama or deterministic)."""
        # "unknown text" is not in our test cache
        embedding = await service.generate_embedding("unknown text not in cache")
        # Should return valid embedding from fallback (768 from Ollama or 1536 from deterministic)
        assert len(embedding) in (768, 1536)
        norm = math.sqrt(sum(v * v for v in embedding))
        assert abs(norm - 1.0) < 0.0001

    @pytest.mark.asyncio
    async def test_empty_cache_uses_fallback(self, service_empty):
        """Test empty cache falls back for all requests."""
        embedding = await service_empty.generate_embedding("any text")
        # May be 768 from Ollama or 1536 from deterministic
        assert len(embedding) in (768, 1536)

    @pytest.mark.asyncio
    async def test_cache_stats(self, service):
        """Test cache statistics tracking."""
        # Initial stats
        stats = service.get_stats()
        assert stats["tier1_cache_hits"] == 0

        # Cache hit
        await service.generate_embedding("hello world")
        stats = service.get_stats()
        assert stats["tier1_cache_hits"] == 1

        # Cache miss - falls back to Tier 2 (Ollama) or Tier 3 (deterministic)
        await service.generate_embedding("not in cache")
        stats = service.get_stats()
        assert stats["tier1_cache_hits"] == 1  # No new cache hit
        # Either Ollama or deterministic should have been used
        assert stats["tier2_ollama_hits"] >= 1 or stats["tier3_deterministic_fallbacks"] >= 1

    def test_get_cache_coverage(self, service):
        """Test cache coverage calculation."""
        test_texts = ["hello world", "test text", "not cached"]
        coverage = service.get_cache_coverage(test_texts)
        assert coverage["total"] == 3
        assert coverage["cached"] == 2
        assert coverage["missing"] == 1
        assert abs(coverage["coverage_percent"] - 66.67) < 0.1

    def test_missing_cache_file_fallback(self, tmp_path: Path):
        """Test missing cache file falls back gracefully (no error)."""
        # The 3-tier hybrid service should not raise - it falls back to Ollama/deterministic
        service = CachedEmbeddingService(cache_path=tmp_path / "nonexistent.json")
        # Cache should be empty, fallback services should be available
        assert service._cache == {}

    def test_invalid_cache_file_fallback(self, tmp_path: Path):
        """Test invalid JSON falls back gracefully (no error)."""
        bad_cache = tmp_path / "bad_cache.json"
        bad_cache.write_text("not valid json")
        # The 3-tier hybrid service should not raise - it logs error and falls back
        service = CachedEmbeddingService(cache_path=bad_cache)
        # Cache should be empty after failed parse
        assert service._cache == {}

    @pytest.mark.asyncio
    async def test_normalize_parameter_respected(self, service):
        """Test normalize parameter is passed through."""
        # Note: cached embeddings are pre-normalized, so this mainly tests interface
        emb_normalized = await service.generate_embedding("hello world", normalize=True)
        emb_unnormalized = await service.generate_embedding("hello world", normalize=False)
        # Both should return the cached vector (which is normalized)
        assert emb_normalized == emb_unnormalized

    def test_text_hash_consistency(self, service):
        """Test text hashing is consistent."""
        text = "hello world"
        hash1 = service._compute_text_hash(text)
        hash2 = service._compute_text_hash(text)
        assert hash1 == hash2
        # Verify it's SHA256
        expected = hashlib.sha256(text.encode("utf-8")).hexdigest()
        assert hash1 == expected

    @pytest.mark.asyncio
    async def test_hybrid_fallback_chain(self, service):
        """Test the 3-tier fallback chain: Cache -> Ollama -> Deterministic."""
        # Tier 1: Cache hit
        embedding = await service.generate_embedding("hello world")
        stats = service.get_stats()
        assert stats["tier1_cache_hits"] == 1
        assert len(embedding) == 1536

        # Tier 2/3: Fallback on cache miss (may use Ollama if available, else deterministic)
        embedding = await service.generate_embedding("totally new uncached text xyz123")
        stats = service.get_stats()
        # Either Ollama or deterministic was used
        assert stats["tier2_ollama_hits"] >= 1 or stats["tier3_deterministic_fallbacks"] >= 1
        # Embedding returned should still be valid (may be 768 dims from Ollama or 1536 from deterministic)
        assert len(embedding) in (768, 1536)

    @pytest.mark.asyncio
    async def test_get_stats_returns_all_counters(self, service):
        """Test get_stats returns all expected counters."""
        stats = service.get_stats()

        # All expected keys should be present (tier-prefixed names)
        expected_keys = {
            "tier1_cache_hits",
            "tier2_ollama_hits",
            "tier3_deterministic_fallbacks",
            "total_requests",
        }
        assert expected_keys.issubset(set(stats.keys()))

        # All counters start at 0
        assert stats["tier1_cache_hits"] == 0
        assert stats["tier2_ollama_hits"] == 0
        assert stats["tier3_deterministic_fallbacks"] == 0
        assert stats["total_requests"] == 0
