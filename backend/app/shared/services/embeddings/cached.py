"""Cached embeddings with 3-tier hybrid fallback.

This module provides a cached embedding implementation with intelligent fallback:

Tier 1: OpenAI Cache (JSON file)
    - Primary, production-accurate embeddings
    - Pre-computed OpenAI text-embedding-3-small (1536 dims)
    - Fastest, zero cost per lookup

Tier 2: Ollama Local (FREE, semantic)
    - If cache miss and Ollama available
    - Uses OllamaEmbeddingService for local inference
    - Different dimensions (768 for nomic-embed-text)
    - Zero API cost, semantic quality

Tier 3: Deterministic Hash (Always works)
    - Last resort fallback
    - Deterministic hashing of text
    - Works offline, no dependencies
    - Not semantically meaningful but consistent

Key Features:
- Handles dimension mismatch gracefully (logs warning)
- Checks OLLAMA_ENABLED and service availability
- Tracks statistics: cache_hits, ollama_hits, deterministic_fallbacks
- Maintains same interface as other embedding services

Issue #606: CI Cost Reduction via Local Models
"""

from __future__ import annotations

import hashlib
import json
import logging
from pathlib import Path
from typing import Any

from app.core.config import settings
from app.core.exceptions import EmbeddingError

from .deterministic import DeterministicEmbeddingService
from .ollama_service import OllamaEmbeddingService

logger = logging.getLogger(__name__)


class CachedEmbeddingService:
    """Cached embedding service with 3-tier hybrid fallback.

    Fallback order:
    1. OpenAI cache (JSON file) - primary, production-accurate
    2. Ollama local (if enabled and available) - FREE, semantic
    3. Deterministic hash - last resort, always works
    """

    # Match interface expected by SearchService
    model: str = "text-embedding-3-small"

    def __init__(
        self,
        cache_path: str | Path,
        expected_dimensions: int = 1536,
    ) -> None:
        """Initialize with cache file path and expected dimensions.

        Args:
            cache_path: Path to JSON cache file with pre-computed embeddings
            expected_dimensions: Expected embedding dimension (default: 1536)

        Raises:
            FileNotFoundError: If cache file does not exist
            json.JSONDecodeError: If cache file is not valid JSON

        """
        self._cache_path = Path(cache_path)
        self._expected_dimensions = expected_dimensions
        self._cache: dict[str, list[float]] = {}

        # Tier 2: Ollama local (lazy initialization)
        self._ollama: OllamaEmbeddingService | None = None
        self._ollama_available = False

        # Tier 3: Deterministic fallback
        self._deterministic = DeterministicEmbeddingService(dims=expected_dimensions)

        # Statistics tracking (type annotated to avoid Literal[0] inference)
        self._cache_hits: int = 0  # Tier 1: OpenAI cache hits
        self._ollama_hits: int = 0  # Tier 2: Ollama local hits
        self._deterministic_fallbacks: int = 0  # Tier 3: Deterministic hash fallbacks
        self._dimension_mismatch_warnings: int = 0  # Track dimension mismatches

        self._load_cache()
        self._initialize_ollama()

    @property
    def expected_dimensions(self) -> int:
        """Return the expected embedding dimensions."""
        return self._expected_dimensions

    @property
    def cache_hits(self) -> int:
        """Return number of Tier 1 cache hits."""
        return self._cache_hits

    @property
    def cache_misses(self) -> int:
        """Return number of cache misses (sum of Tier 2 + Tier 3)."""
        return self._ollama_hits + self._deterministic_fallbacks

    @property
    def ollama_hits(self) -> int:
        """Return number of Tier 2 Ollama hits."""
        return self._ollama_hits

    @property
    def deterministic_fallbacks(self) -> int:
        """Return number of Tier 3 deterministic fallbacks."""
        return self._deterministic_fallbacks

    def get_stats(self) -> dict[str, Any]:
        """Get comprehensive statistics on tier usage.

        Returns:
            Dictionary with tier usage counters and percentages

        Example:
            {
                "tier1_cache_hits": 850,
                "tier2_ollama_hits": 100,
                "tier3_deterministic_fallbacks": 50,
                "total_requests": 1000,
                "tier1_percent": 85.0,
                "tier2_percent": 10.0,
                "tier3_percent": 5.0,
                "dimension_mismatch_warnings": 100
            }

        """
        total = self._cache_hits + self._ollama_hits + self._deterministic_fallbacks

        # Calculate percentages (use max(1, total) to avoid division by zero warning)
        divisor = max(1, total)
        tier1_pct = round(self._cache_hits / divisor * 100, 2) if total > 0 else 0.0
        tier2_pct = round(self._ollama_hits / divisor * 100, 2) if total > 0 else 0.0
        tier3_pct = round(self._deterministic_fallbacks / divisor * 100, 2) if total > 0 else 0.0

        return {
            "tier1_cache_hits": self._cache_hits,
            "tier2_ollama_hits": self._ollama_hits,
            "tier3_deterministic_fallbacks": self._deterministic_fallbacks,
            "total_requests": total,
            "tier1_percent": tier1_pct,
            "tier2_percent": tier2_pct,
            "tier3_percent": tier3_pct,
            "dimension_mismatch_warnings": self._dimension_mismatch_warnings,
            "ollama_available": self._ollama_available,
        }

    def _compute_text_hash(self, text: str) -> str:
        """Compute SHA256 hash of text for cache lookup.

        Args:
            text: Input text to hash

        Returns:
            Hexadecimal SHA256 hash string

        """
        return hashlib.sha256(text.encode("utf-8")).hexdigest()

    def get_cache_coverage(self, texts: list[str]) -> dict[str, Any]:
        """Check cache coverage for a list of texts.

        Args:
            texts: List of texts to check

        Returns:
            Dictionary with coverage statistics

        """
        total = len(texts)
        cached = sum(1 for t in texts if self._compute_text_hash(t) in self._cache)
        missing = total - cached
        coverage_percent = (cached / total * 100) if total > 0 else 0.0

        return {
            "total": total,
            "cached": cached,
            "missing": missing,
            "coverage_percent": round(coverage_percent, 2),
        }

    def _load_cache(self) -> None:
        """Load embeddings cache from JSON file (Tier 1)."""
        if not self._cache_path.exists():
            logger.warning(
                "Cache file not found: %s - will use Tier 2 (Ollama) or Tier 3 (deterministic) fallbacks",
                self._cache_path,
            )
            return

        try:
            with self._cache_path.open() as f:
                data: dict[str, Any] = json.load(f)

            # Validate cache format
            if "embeddings" not in data:
                logger.error("Invalid cache format: missing 'embeddings' key")
                return

            # Validate dimensions match
            cache_dims = data.get("dimensions")
            if cache_dims and cache_dims != self._expected_dimensions:
                logger.warning(
                    "Cache dimensions (%d) don't match expected (%d) - will handle gracefully",
                    cache_dims,
                    self._expected_dimensions,
                )

            # Load embeddings into memory, indexed by hash
            embeddings = data["embeddings"]
            self._cache = {hash_key: entry["vector"] for hash_key, entry in embeddings.items()}

            logger.info(
                "Loaded %d cached embeddings from %s (model=%s, dims=%d) - Tier 1 active",
                len(self._cache),
                self._cache_path,
                data.get("model", "unknown"),
                cache_dims or self._expected_dimensions,
            )

        except json.JSONDecodeError:
            logger.exception("Failed to parse cache JSON")
        except OSError:
            logger.exception("Failed to load cache")

    def _initialize_ollama(self) -> None:
        """Initialize Ollama service if enabled and available (Tier 2)."""
        if not settings.OLLAMA_ENABLED:
            logger.info(
                "Ollama disabled (OLLAMA_ENABLED=false) - Tier 2 unavailable, will use Tier 3 (deterministic) on cache miss"
            )
            return

        try:
            # Lazy initialization - only create if enabled
            self._ollama = OllamaEmbeddingService()

            # Check if actually available
            if self._ollama.is_available:
                self._ollama_available = True
                logger.info(
                    "Ollama service initialized and available - Tier 2 active (model=%s, dims=%d)",
                    self._ollama.model,
                    self._ollama.expected_dimensions,
                )

                # Warn about dimension mismatch if present
                if self._ollama.expected_dimensions != self._expected_dimensions:
                    logger.warning(
                        "Ollama dimensions (%d) don't match cache dimensions (%d) - will handle gracefully",
                        self._ollama.expected_dimensions,
                        self._expected_dimensions,
                    )
            else:
                logger.warning(
                    "Ollama enabled but service not reachable at %s - Tier 2 unavailable, will use Tier 3 (deterministic) on cache miss",
                    settings.OLLAMA_HOST,
                )
                self._ollama = None

        except (OSError, ValueError, ImportError) as e:
            logger.warning(
                "Failed to initialize Ollama service: %s - Tier 2 unavailable, will use Tier 3 (deterministic) on cache miss",
                str(e),
            )
            self._ollama = None

    def _hash_text(self, text: str) -> str:
        """Generate SHA256 hash of text for cache key lookup.

        Args:
            text: Input text to hash

        Returns:
            Hexadecimal SHA256 hash string

        """
        return hashlib.sha256(text.encode("utf-8")).hexdigest()

    async def generate_embedding(self, text: str, normalize: bool = True) -> list[float]:
        """Generate embedding vector for the given text using 3-tier fallback.

        Tier 1: Check OpenAI cache (JSON file) - primary, production-accurate
        Tier 2: Use Ollama local if enabled and available - FREE, semantic
        Tier 3: Fall back to deterministic hash - last resort, always works

        Args:
            text: Input text to embed
            normalize: Whether to normalize the vector (passed to fallbacks)

        Returns:
            Embedding vector as list of floats

        """
        text_hash = self._hash_text(text)

        # Tier 1: Check OpenAI cache first
        if text_hash in self._cache:
            self._cache_hits += 1
            embedding = self._cache[text_hash]

            # Check dimension mismatch
            if len(embedding) != self._expected_dimensions:
                self._dimension_mismatch_warnings += 1
                logger.warning(
                    "Tier 1 cache dimension mismatch: expected %d, got %d (hash %s...)",
                    self._expected_dimensions,
                    len(embedding),
                    text_hash[:16],
                )

            return embedding

        # Tier 2: Try Ollama local if available
        if self._ollama_available and self._ollama is not None:
            try:
                self._ollama_hits += 1
                embedding = await self._ollama.generate_embedding(text, normalize=normalize)

                # Check dimension mismatch
                if len(embedding) != self._expected_dimensions:
                    self._dimension_mismatch_warnings += 1
                    logger.warning(
                        "Tier 2 Ollama dimension mismatch: expected %d, got %d (text preview: %s...)",
                        self._expected_dimensions,
                        len(embedding),
                        text[:100],
                    )

                logger.debug(
                    "Tier 2 hit: Ollama generated embedding (hash %s..., dims=%d)",
                    text_hash[:16],
                    len(embedding),
                )
                return embedding

            except (EmbeddingError, OSError, ValueError) as e:
                # Ollama failed - fall through to Tier 3
                logger.warning(
                    "Tier 2 Ollama failed: %s - falling back to Tier 3 (deterministic)",
                    str(e),
                )

        # Tier 3: Deterministic fallback (always works)
        self._deterministic_fallbacks += 1
        logger.warning(
            "Cache miss for text hash %s (preview: %s...) - using Tier 3 deterministic fallback",
            text_hash[:16],
            text[:100],
        )

        return await self._deterministic.generate_embedding(text, normalize=normalize)
