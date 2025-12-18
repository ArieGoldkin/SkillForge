"""MetricsService - Central metrics collection and emission.

Provides a singleton service for recording and emitting metrics
through structlog without requiring external dependencies.
"""

from __future__ import annotations

import threading
from functools import lru_cache
from typing import Any

import structlog

from app.shared.services.metrics.collectors import Counter, Histogram, LabeledCounter, Timer

logger = structlog.get_logger(__name__)

# Batch size bucket thresholds
BATCH_SIZE_SMALL_THRESHOLD = 10
BATCH_SIZE_MEDIUM_THRESHOLD = 50


class MetricsService:
    """Centralized metrics collection service.

    Thread-safe singleton that manages all application metrics
    and emits them via structured logging.
    """

    _instance: MetricsService | None = None
    _lock = threading.Lock()

    def __new__(cls) -> MetricsService:
        """Ensure singleton instance."""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    def __init__(self) -> None:
        """Initialize metrics collections."""
        if getattr(self, "_initialized", False):
            return

        self._initialized = True
        self._enabled = True

        # Embedding metrics
        self.embedding_requests = LabeledCounter(
            name="embedding.requests.total",
            labels=["status"],
            description="Total embedding API requests",
        )
        self.embedding_tokens = LabeledCounter(
            name="embedding.tokens.total",
            labels=["truncated"],
            description="Total tokens processed",
        )
        self.embedding_batches = LabeledCounter(
            name="embedding.batches.total",
            labels=["size_bucket"],
            description="Total batches by size",
        )
        self.embedding_latency = Histogram(
            name="embedding.latency_ms",
            description="Embedding generation latency in milliseconds",
        )

        # Search metrics
        self.search_requests = LabeledCounter(
            name="search.requests.total",
            labels=["mode", "reranked"],
            description="Total search requests",
        )
        self.search_latency = Histogram(
            name="search.latency_ms",
            description="Search latency in milliseconds",
        )

        # Re-rank metrics
        self.rerank_requests = Counter(
            name="rerank.requests.total",
            description="Total re-rank requests",
        )
        self.rerank_latency = Histogram(
            name="rerank.latency_ms",
            description="Re-rank latency in milliseconds",
        )

        # Error metrics
        self.api_errors = LabeledCounter(
            name="api.errors.total",
            labels=["provider", "status"],
            description="API errors by provider and status code",
        )

        # Deduplication metrics
        self.dedup_chunks = LabeledCounter(
            name="dedup.chunks.total",
            labels=["action"],
            description="Chunks kept or removed by deduplication",
        )

        # Cache metrics
        self.cache_hits = LabeledCounter(
            name="cache.hits.total",
            labels=["cache_type"],
            description="Cache hits by type",
        )

        # Truncation metrics
        self.truncations = Counter(
            name="embedding.truncations.total",
            description="Total text truncations",
        )

        # Batch size tracking
        self.batch_sizes = Histogram(
            name="embedding.batch_size",
            description="Embedding batch sizes",
        )

        # Token count tracking
        self.token_counts = Histogram(
            name="embedding.token_count",
            description="Token counts per embedding request",
        )

        logger.info("metrics_service_initialized")

    def enable(self) -> None:
        """Enable metrics collection."""
        self._enabled = True
        logger.info("metrics_enabled")

    def disable(self) -> None:
        """Disable metrics collection."""
        self._enabled = False
        logger.info("metrics_disabled")

    @property
    def enabled(self) -> bool:
        """Check if metrics collection is enabled."""
        return self._enabled

    def timer(self, histogram: Histogram) -> Timer:
        """Create a timer context manager for the given histogram."""
        return Timer(histogram)

    def record_embedding_request(
        self,
        *,
        status: str,
        latency_ms: float,
        token_count: int,
        truncated: bool = False,
        batch_size: int = 1,
    ) -> None:
        """Record an embedding request with all associated metrics."""
        if not self._enabled:
            return

        self.embedding_requests.inc(status=status)
        self.embedding_latency.observe(latency_ms)
        self.embedding_tokens.inc(value=token_count, truncated=str(truncated).lower())
        self.token_counts.observe(token_count)

        if truncated:
            self.truncations.inc()

        # Bucket batch sizes
        if batch_size <= BATCH_SIZE_SMALL_THRESHOLD:
            size_bucket = "1-10"
        elif batch_size <= BATCH_SIZE_MEDIUM_THRESHOLD:
            size_bucket = "11-50"
        else:
            size_bucket = "51-100"

        self.embedding_batches.inc(size_bucket=size_bucket)
        self.batch_sizes.observe(batch_size)

        logger.debug(
            "embedding_request_recorded",
            status=status,
            latency_ms=latency_ms,
            token_count=token_count,
            truncated=truncated,
            batch_size=batch_size,
        )

    def record_search_request(
        self,
        *,
        mode: str,
        reranked: bool,
        latency_ms: float,
        results_count: int,
    ) -> None:
        """Record a search request with all associated metrics."""
        if not self._enabled:
            return

        self.search_requests.inc(mode=mode, reranked=str(reranked).lower())
        self.search_latency.observe(latency_ms)

        logger.debug(
            "search_request_recorded",
            mode=mode,
            reranked=reranked,
            latency_ms=latency_ms,
            results_count=results_count,
        )

    def record_rerank_request(
        self, *, latency_ms: float, input_count: int, output_count: int
    ) -> None:
        """Record a re-rank request."""
        if not self._enabled:
            return

        self.rerank_requests.inc()
        self.rerank_latency.observe(latency_ms)

        logger.debug(
            "rerank_request_recorded",
            latency_ms=latency_ms,
            input_count=input_count,
            output_count=output_count,
        )

    def record_api_error(self, *, provider: str, status: int | str) -> None:
        """Record an API error."""
        if not self._enabled:
            return

        self.api_errors.inc(provider=provider, status=str(status))

        logger.warning(
            "api_error_recorded",
            provider=provider,
            status=status,
        )

    def record_dedup(self, *, kept: int, removed: int) -> None:
        """Record deduplication results."""
        if not self._enabled:
            return

        self.dedup_chunks.inc(value=kept, action="kept")
        self.dedup_chunks.inc(value=removed, action="removed")

        logger.debug(
            "dedup_recorded",
            kept=kept,
            removed=removed,
        )

    def record_cache_hit(self, *, cache_type: str) -> None:
        """Record a cache hit."""
        if not self._enabled:
            return

        self.cache_hits.inc(cache_type=cache_type)

    def record_batch_embedding(
        self,
        *,
        batch_count: int,
        total_latency_ms: float,
        avg_batch_size: int,
    ) -> None:
        """Record batch embedding metrics for Issue #215 hardening.

        Args:
            batch_count: Total number of texts embedded
            total_latency_ms: Total latency across all batches
            avg_batch_size: Average batch size used

        """
        if not self._enabled:
            return

        # Use existing counters to track batch-level stats
        self.batch_sizes.observe(avg_batch_size)

        logger.info(
            "batch_embedding_recorded",
            batch_count=batch_count,
            total_latency_ms=total_latency_ms,
            avg_batch_size=avg_batch_size,
            throughput_per_second=batch_count / (total_latency_ms / 1000)
            if total_latency_ms > 0
            else 0,
        )

    def record_dedup_stats(
        self,
        *,
        total: int,
        skipped: int,
        embedded: int,
    ) -> None:
        """Record deduplication statistics for Issue #215 hardening.

        Args:
            total: Total chunks before deduplication
            skipped: Chunks skipped due to existing embeddings
            embedded: Chunks that needed embedding

        """
        if not self._enabled:
            return

        # Record as dedup kept/removed
        self.record_dedup(kept=embedded, removed=skipped)

        logger.info(
            "dedup_stats_recorded",
            total=total,
            skipped=skipped,
            embedded=embedded,
            skip_rate=skipped / total if total > 0 else 0,
        )

    def get_summary(self) -> dict[str, Any]:
        """Get a summary of all metrics."""
        return {
            "embedding": {
                "requests": self.embedding_requests.get_all(),
                "latency": self.embedding_latency.get_stats(),
                "tokens": self.embedding_tokens.get_all(),
                "batches": self.embedding_batches.get_all(),
                "truncations": self.truncations.get(),
            },
            "search": {
                "requests": self.search_requests.get_all(),
                "latency": self.search_latency.get_stats(),
            },
            "rerank": {
                "requests": self.rerank_requests.get(),
                "latency": self.rerank_latency.get_stats(),
            },
            "errors": self.api_errors.get_all(),
            "dedup": self.dedup_chunks.get_all(),
            "cache": self.cache_hits.get_all(),
        }

    def emit_summary(self) -> None:
        """Emit a summary of all metrics via structured logging."""
        if not self._enabled:
            return

        summary = self.get_summary()
        logger.info("metrics_summary", **summary)

    def reset_all(self) -> dict[str, Any]:
        """Reset all metrics and return previous values."""
        summary = self.get_summary()

        self.embedding_requests.reset()
        self.embedding_latency.reset()
        self.embedding_tokens.reset()
        self.embedding_batches.reset()
        self.truncations.reset()
        self.batch_sizes.reset()
        self.token_counts.reset()
        self.search_requests.reset()
        self.search_latency.reset()
        self.rerank_requests.reset()
        self.rerank_latency.reset()
        self.api_errors.reset()
        self.dedup_chunks.reset()
        self.cache_hits.reset()

        logger.info("metrics_reset")
        return summary


@lru_cache(maxsize=1)
def get_metrics_service() -> MetricsService:
    """Get the singleton MetricsService instance."""
    return MetricsService()
