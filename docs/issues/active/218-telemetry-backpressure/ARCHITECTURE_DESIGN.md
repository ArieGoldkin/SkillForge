# Issue #218: Telemetry & Backpressure Architecture Design

**Author:** Backend System Architect Agent
**Date:** December 10, 2025
**Status:** Design Review
**Related Issues:** #215 (Embedding Pipeline), #216 (Search API), #217 (Re-Ranker)

---

## Executive Summary

This document specifies the architecture for adding production-grade telemetry and adaptive backpressure to SkillForge's embedding pipeline (EmbeddingService, SearchService, ReRanker). The design prioritizes **lightweight instrumentation** with minimal runtime overhead while providing actionable metrics for monitoring 429/5xx errors and optimizing batch processing.

**Key Decisions:**
- **Metrics Library:** Custom counters/histograms via structlog (no Prometheus dependency)
- **Backpressure:** Token bucket rate limiter + exponential backoff (no circuit breaker)
- **Configuration:** Pydantic-based with environment variables
- **Storage:** Append-only metrics log file + structured logging

---

## 1. System Context

### Current Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                        EMBEDDING PIPELINE                           │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  ┌──────────────┐      ┌───────────────┐      ┌──────────────┐    │
│  │   Chunker    │─────▶│   Embedding   │─────▶│   Store in   │    │
│  │  (batches)   │      │    Service    │      │   PGVector   │    │
│  └──────────────┘      └───────────────┘      └──────────────┘    │
│                               │                                     │
│                               │ OpenAI API                         │
│                               │ text-embedding-3-small             │
│                               │ (8,191 token limit)                │
│                               ▼                                     │
│                        ┌─────────────┐                             │
│                        │   Retries   │                             │
│                        │ (tenacity)  │                             │
│                        └─────────────┘                             │
│                                                                     │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │              SEARCH & RETRIEVAL                             │  │
│  ├──────────────────────────────────────────────────────────────┤  │
│  │  SearchService ──▶ ChunkRepository ──▶ PGVector            │  │
│  │       │                                                      │  │
│  │       └──▶ ReRanker (GPT-4o-mini)                           │  │
│  └──────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────┘
```

### Issues Without Telemetry

1. **Blind to rate limits:** 429 errors happen, but no tracking of frequency
2. **No token visibility:** Unknown if we're hitting 8K token limit often
3. **No performance baseline:** P50/P95 latency unknown
4. **Inefficient batching:** No data on optimal batch sizes
5. **Silent failures:** 5xx errors from OpenAI not monitored

---

## 2. Architecture Design

### 2.1 Metrics Collection Layer

We'll use **structlog-based metrics** (already installed) instead of Prometheus to minimize dependencies.

```
┌────────────────────────────────────────────────────────────────────┐
│                      METRICS ARCHITECTURE                          │
├────────────────────────────────────────────────────────────────────┤
│                                                                    │
│  ┌──────────────────┐                                             │
│  │  Application     │                                             │
│  │  Code            │                                             │
│  │  (emit metrics)  │                                             │
│  └────────┬─────────┘                                             │
│           │                                                        │
│           ▼                                                        │
│  ┌──────────────────┐                                             │
│  │  MetricsService  │◀──── Singleton, thread-safe               │
│  │  (record())      │                                             │
│  └────────┬─────────┘                                             │
│           │                                                        │
│           ├──▶ structlog (JSON logs)                              │
│           │                                                        │
│           └──▶ In-memory aggregation (p50/p95 calculation)        │
│                                                                    │
│  ┌──────────────────────────────────────────────────────────────┐ │
│  │  Metrics Output                                             │ │
│  ├──────────────────────────────────────────────────────────────┤ │
│  │  logs/metrics.jsonl  ─────▶  Grafana Loki / CloudWatch      │ │
│  │  (newline-delimited JSON)                                   │ │
│  └──────────────────────────────────────────────────────────────┘ │
│                                                                    │
└────────────────────────────────────────────────────────────────────┘
```

**Why structlog over Prometheus?**
- ✅ Already installed and configured
- ✅ Zero additional runtime dependencies
- ✅ Easier to integrate with existing logging infrastructure
- ✅ Works natively with cloud log aggregators (CloudWatch, Loki, Datadog)
- ❌ No built-in /metrics HTTP endpoint (acceptable trade-off)

### 2.2 Metrics Specification

#### Counter Metrics
```python
# Embedding API calls
embedding.requests.total (labels: status=success|rate_limit|error)
embedding.tokens.total (labels: truncated=true|false)
embedding.batches.total (labels: size_bucket=1-10|11-50|51-100)

# Search operations
search.requests.total (labels: mode=semantic|keyword|hybrid, reranked=true|false)
search.cache.hits (labels: mode=semantic|keyword|hybrid)

# Deduplication
dedup.chunks.total (labels: action=kept|removed)

# Error tracking
api.errors.total (labels: provider=openai, status=429|500|502|503|504)
```

#### Histogram Metrics (for percentiles)
```python
# Latency tracking (in milliseconds)
embedding.latency_ms (buckets: p50, p95, p99)
search.latency_ms (buckets: p50, p95, p99)
rerank.latency_ms (buckets: p50, p95, p99)

# Size tracking
embedding.batch_size (buckets: p50, p95, p99)
embedding.token_count (buckets: p50, p95, p99)
```

### 2.3 Structured Logging Schema

All metrics are emitted as structured logs with a standard schema:

```json
{
  "timestamp": "2025-12-10T14:32:15.123Z",
  "level": "info",
  "logger": "app.services.metrics",
  "event": "metric_recorded",
  "metric_name": "embedding.latency_ms",
  "metric_type": "histogram",
  "value": 145.2,
  "labels": {
    "model": "text-embedding-3-small",
    "truncated": "false"
  },
  "metadata": {
    "service": "embedding_service",
    "batch_size": 5,
    "token_count": 1234
  }
}
```

**No raw text logged** - only hashes, lengths, and metadata per Issue #218 requirements.

### 2.4 Adaptive Backpressure System

```
┌─────────────────────────────────────────────────────────────────────┐
│                   BACKPRESSURE ARCHITECTURE                         │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │  RateLimiter (Token Bucket)                                 │  │
│  ├──────────────────────────────────────────────────────────────┤  │
│  │  - Capacity: 10,000 tokens/minute (configurable)           │  │
│  │  - Refill rate: ~167 tokens/sec                            │  │
│  │  - Per-service instance (in-memory)                         │  │
│  └──────────────────────────────────────────────────────────────┘  │
│                                                                     │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │  Error Rate Tracker (Sliding Window)                        │  │
│  ├──────────────────────────────────────────────────────────────┤  │
│  │  - Window: 60 seconds                                       │  │
│  │  - Threshold: 5% of requests = 429/5xx                      │  │
│  │  - Action: Reduce batch size by 50%                         │  │
│  └──────────────────────────────────────────────────────────────┘  │
│                                                                     │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │  Adaptive Batch Sizing                                      │  │
│  ├──────────────────────────────────────────────────────────────┤  │
│  │  Initial: 20 chunks/batch                                   │  │
│  │  Min: 1 chunk/batch                                         │  │
│  │  Max: 100 chunks/batch                                      │  │
│  │  Increase: +10% if error rate < 1% for 5 minutes           │  │
│  │  Decrease: -50% on 429, -25% on 5xx                        │  │
│  └──────────────────────────────────────────────────────────────┘  │
│                                                                     │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │  Exponential Backoff (Enhanced)                             │  │
│  ├──────────────────────────────────────────────────────────────┤  │
│  │  Base delay: 2 seconds                                      │  │
│  │  Multiplier: 2x                                             │  │
│  │  Max delay: 16 seconds                                      │  │
│  │  Jitter: ±20% (prevent thundering herd)                    │  │
│  │  Max retries: 3 (existing tenacity config)                 │  │
│  └──────────────────────────────────────────────────────────────┘  │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

**Flow:**

```
Request ──▶ RateLimiter.acquire()
              │
              ├─ Tokens available? ──▶ Proceed ──▶ API Call
              │                                        │
              └─ No tokens? ──▶ Wait & retry          │
                                                       ▼
                                                  ┌─────────┐
                                                  │ Success │
                                                  └────┬────┘
                                                       │
                                    ┌──────────────────┴──────────────────┐
                                    │                                     │
                                    ▼                                     ▼
                              200 OK                               429/5xx Error
                                    │                                     │
                                    │                                     ▼
                                    │                            ErrorRateTracker
                                    │                            .record_error()
                                    │                                     │
                                    │                                     ▼
                                    │                            Error rate > 5%?
                                    │                                     │
                                    │                              ┌──────┴──────┐
                                    │                              │             │
                                    │                             Yes           No
                                    │                              │             │
                                    │                              ▼             │
                                    │                    AdaptiveBatchSizer      │
                                    │                    .decrease_size()        │
                                    │                              │             │
                                    └──────────────────────────────┴─────────────┘
                                                       │
                                                       ▼
                                                 Log metrics
```

---

## 3. Implementation Specification

### 3.1 File Structure

```
backend/app/
├── services/
│   ├── metrics/
│   │   ├── __init__.py
│   │   ├── service.py              # MetricsService singleton
│   │   ├── collectors.py           # Counter, Histogram classes
│   │   └── aggregators.py          # P50/P95 calculation
│   ├── backpressure/
│   │   ├── __init__.py
│   │   ├── rate_limiter.py         # Token bucket implementation
│   │   ├── error_tracker.py        # Sliding window error rate
│   │   ├── batch_sizer.py          # Adaptive batch size logic
│   │   └── backoff.py              # Jittered exponential backoff
│   └── embeddings.py               # MODIFIED: Add metrics/backpressure
│   └── search/
│       ├── search_service.py       # MODIFIED: Add metrics
│       └── reranker.py             # MODIFIED: Add metrics
├── core/
│   ├── config.py                   # MODIFIED: Add backpressure settings
│   └── constants.py                # MODIFIED: Add metric constants
└── tests/
    ├── unit/
    │   ├── services/
    │   │   ├── metrics/
    │   │   │   ├── test_service.py
    │   │   │   ├── test_collectors.py
    │   │   │   └── test_aggregators.py
    │   │   └── backpressure/
    │   │       ├── test_rate_limiter.py
    │   │       ├── test_error_tracker.py
    │   │       ├── test_batch_sizer.py
    │   │       └── test_backoff.py
    └── integration/
        └── services/
            └── test_embedding_with_backpressure.py
```

### 3.2 Configuration Schema

Add to `backend/app/core/config.py`:

```python
class Settings(BaseSettings):
    # ... existing settings ...

    # ===== Metrics Configuration =====
    METRICS_ENABLED: bool = Field(
        default=True,
        description="Enable metrics collection and logging"
    )
    METRICS_LOG_FILE: str = Field(
        default="logs/metrics.jsonl",
        description="Path to metrics log file (newline-delimited JSON)"
    )
    METRICS_FLUSH_INTERVAL: int = Field(
        default=60,
        description="Flush in-memory metrics to log every N seconds"
    )

    # ===== Backpressure Configuration =====
    # Rate Limiting
    RATE_LIMIT_ENABLED: bool = Field(
        default=True,
        description="Enable token bucket rate limiting for API calls"
    )
    RATE_LIMIT_TOKENS_PER_MINUTE: int = Field(
        default=10_000,
        description="OpenAI API rate limit (tokens per minute, tier-dependent)"
    )
    RATE_LIMIT_BURST_CAPACITY: int = Field(
        default=2_000,
        description="Burst capacity for token bucket (allow short spikes)"
    )

    # Adaptive Batch Sizing
    BATCH_SIZE_INITIAL: int = Field(
        default=20,
        description="Initial batch size for embedding requests"
    )
    BATCH_SIZE_MIN: int = Field(
        default=1,
        description="Minimum batch size (safety floor)"
    )
    BATCH_SIZE_MAX: int = Field(
        default=100,
        description="Maximum batch size (API limit)"
    )
    BATCH_SIZE_DECREASE_FACTOR: float = Field(
        default=0.5,
        description="Factor to decrease batch size on errors (0.5 = 50% reduction)"
    )
    BATCH_SIZE_INCREASE_FACTOR: float = Field(
        default=1.1,
        description="Factor to increase batch size when healthy (1.1 = 10% increase)"
    )

    # Error Rate Tracking
    ERROR_RATE_WINDOW_SECONDS: int = Field(
        default=60,
        description="Sliding window for error rate calculation (seconds)"
    )
    ERROR_RATE_THRESHOLD: float = Field(
        default=0.05,
        description="Error rate threshold to trigger backpressure (0.05 = 5%)"
    )
    ERROR_RATE_RECOVERY_WINDOW: int = Field(
        default=300,
        description="Healthy period before increasing batch size (seconds)"
    )

    # Retry Configuration (Enhanced)
    RETRY_JITTER_MIN: float = Field(
        default=0.8,
        description="Minimum jitter factor for retry delays (0.8 = -20%)"
    )
    RETRY_JITTER_MAX: float = Field(
        default=1.2,
        description="Maximum jitter factor for retry delays (1.2 = +20%)"
    )

    # Guardrails
    VECTOR_DIMENSION_CHECK: bool = Field(
        default=True,
        description="Validate embedding dimensions on read from database"
    )
    ORPHAN_CHUNK_DETECTION: bool = Field(
        default=True,
        description="Detect chunks with missing analysis_id references"
    )
```

### 3.3 Environment Variables

Add to `backend/.env.example`:

```bash
# ===== Metrics Configuration =====
METRICS_ENABLED=true
METRICS_LOG_FILE=logs/metrics.jsonl
METRICS_FLUSH_INTERVAL=60

# ===== Backpressure Configuration =====
# Rate Limiting (OpenAI tier-dependent)
# Tier 1: 10,000 TPM | Tier 2: 50,000 TPM | Tier 3: 150,000 TPM
RATE_LIMIT_ENABLED=true
RATE_LIMIT_TOKENS_PER_MINUTE=10000
RATE_LIMIT_BURST_CAPACITY=2000

# Adaptive Batch Sizing
BATCH_SIZE_INITIAL=20
BATCH_SIZE_MIN=1
BATCH_SIZE_MAX=100
BATCH_SIZE_DECREASE_FACTOR=0.5
BATCH_SIZE_INCREASE_FACTOR=1.1

# Error Rate Tracking
ERROR_RATE_WINDOW_SECONDS=60
ERROR_RATE_THRESHOLD=0.05
ERROR_RATE_RECOVERY_WINDOW=300

# Retry Jitter (prevent thundering herd)
RETRY_JITTER_MIN=0.8
RETRY_JITTER_MAX=1.2

# Guardrails
VECTOR_DIMENSION_CHECK=true
ORPHAN_CHUNK_DETECTION=true
```

### 3.4 Constants

Add to `backend/app/core/constants.py`:

```python
# ===== Metrics Constants =====
# Metric Names
METRIC_EMBEDDING_REQUESTS = "embedding.requests.total"
METRIC_EMBEDDING_TOKENS = "embedding.tokens.total"
METRIC_EMBEDDING_BATCHES = "embedding.batches.total"
METRIC_EMBEDDING_LATENCY = "embedding.latency_ms"
METRIC_EMBEDDING_BATCH_SIZE = "embedding.batch_size"
METRIC_EMBEDDING_TOKEN_COUNT = "embedding.token_count"

METRIC_SEARCH_REQUESTS = "search.requests.total"
METRIC_SEARCH_LATENCY = "search.latency_ms"
METRIC_SEARCH_CACHE_HITS = "search.cache.hits"

METRIC_RERANK_REQUESTS = "rerank.requests.total"
METRIC_RERANK_LATENCY = "rerank.latency_ms"

METRIC_DEDUP_CHUNKS = "dedup.chunks.total"
METRIC_API_ERRORS = "api.errors.total"

# Metric Types
METRIC_TYPE_COUNTER = "counter"
METRIC_TYPE_HISTOGRAM = "histogram"
METRIC_TYPE_GAUGE = "gauge"

# Label Values
LABEL_STATUS_SUCCESS = "success"
LABEL_STATUS_RATE_LIMIT = "rate_limit"
LABEL_STATUS_ERROR = "error"

# Batch Size Buckets
BATCH_SIZE_BUCKET_SMALL = "1-10"
BATCH_SIZE_BUCKET_MEDIUM = "11-50"
BATCH_SIZE_BUCKET_LARGE = "51-100"

# HTTP Status Categories
HTTP_STATUS_RATE_LIMIT = 429
HTTP_STATUS_5XX_MIN = 500
HTTP_STATUS_5XX_MAX = 599
```

---

## 4. Implementation Details

### 4.1 MetricsService (Singleton)

```python
# backend/app/services/metrics/service.py

from typing import Any
import time
from threading import Lock
from collections import defaultdict, deque
from app.core.logging import get_logger
from app.core.config import settings

logger = get_logger(__name__)

class MetricsService:
    """Thread-safe singleton for metrics collection."""

    _instance = None
    _lock = Lock()

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return

        self._counters: dict[str, int] = defaultdict(int)
        self._histograms: dict[str, deque] = defaultdict(
            lambda: deque(maxlen=1000)  # Keep last 1000 samples
        )
        self._data_lock = Lock()
        self._initialized = True

        logger.info(
            "metrics_service_initialized",
            enabled=settings.METRICS_ENABLED,
            log_file=settings.METRICS_LOG_FILE,
        )

    def increment(
        self,
        metric_name: str,
        value: int = 1,
        labels: dict[str, str] | None = None,
    ) -> None:
        """Increment a counter metric."""
        if not settings.METRICS_ENABLED:
            return

        # Create unique key from metric name + labels
        key = self._make_key(metric_name, labels)

        with self._data_lock:
            self._counters[key] += value

        # Log immediately for real-time monitoring
        logger.info(
            "metric_recorded",
            metric_name=metric_name,
            metric_type=METRIC_TYPE_COUNTER,
            value=value,
            labels=labels or {},
        )

    def record(
        self,
        metric_name: str,
        value: float,
        labels: dict[str, str] | None = None,
    ) -> None:
        """Record a histogram metric (for percentile calculation)."""
        if not settings.METRICS_ENABLED:
            return

        key = self._make_key(metric_name, labels)

        with self._data_lock:
            self._histograms[key].append(value)

        logger.info(
            "metric_recorded",
            metric_name=metric_name,
            metric_type=METRIC_TYPE_HISTOGRAM,
            value=value,
            labels=labels or {},
        )

    def get_percentiles(
        self,
        metric_name: str,
        percentiles: list[int] = [50, 95, 99],
        labels: dict[str, str] | None = None,
    ) -> dict[int, float]:
        """Calculate percentiles for a histogram metric."""
        key = self._make_key(metric_name, labels)

        with self._data_lock:
            values = sorted(self._histograms.get(key, []))

        if not values:
            return {p: 0.0 for p in percentiles}

        result = {}
        for p in percentiles:
            idx = int((p / 100.0) * len(values))
            idx = min(idx, len(values) - 1)
            result[p] = values[idx]

        return result

    def _make_key(
        self,
        metric_name: str,
        labels: dict[str, str] | None,
    ) -> str:
        """Create unique key from metric name and labels."""
        if not labels:
            return metric_name

        label_str = ",".join(
            f"{k}={v}" for k, v in sorted(labels.items())
        )
        return f"{metric_name}{{{label_str}}}"

# Global singleton instance
metrics = MetricsService()
```

### 4.2 RateLimiter (Token Bucket)

```python
# backend/app/services/backpressure/rate_limiter.py

import time
import asyncio
from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)

class TokenBucketRateLimiter:
    """Token bucket rate limiter for API calls."""

    def __init__(
        self,
        capacity: int | None = None,
        refill_rate: float | None = None,
    ):
        """
        Args:
            capacity: Maximum tokens in bucket (defaults to settings)
            refill_rate: Tokens added per second (defaults to capacity/60)
        """
        self.capacity = capacity or settings.RATE_LIMIT_TOKENS_PER_MINUTE
        self.refill_rate = refill_rate or (self.capacity / 60.0)
        self.tokens = float(self.capacity)
        self.last_refill = time.monotonic()
        self._lock = asyncio.Lock()

        logger.info(
            "rate_limiter_initialized",
            capacity=self.capacity,
            refill_rate=self.refill_rate,
        )

    async def acquire(self, tokens: int = 1) -> None:
        """
        Acquire N tokens from bucket, waiting if necessary.

        Args:
            tokens: Number of tokens to acquire (e.g., token count for text)
        """
        if not settings.RATE_LIMIT_ENABLED:
            return

        async with self._lock:
            while True:
                # Refill tokens based on elapsed time
                now = time.monotonic()
                elapsed = now - self.last_refill
                self.tokens = min(
                    self.capacity,
                    self.tokens + (elapsed * self.refill_rate)
                )
                self.last_refill = now

                # Check if we have enough tokens
                if self.tokens >= tokens:
                    self.tokens -= tokens
                    logger.debug(
                        "rate_limit_acquired",
                        tokens_requested=tokens,
                        tokens_remaining=self.tokens,
                    )
                    return

                # Wait until we have enough tokens
                wait_time = (tokens - self.tokens) / self.refill_rate
                logger.warning(
                    "rate_limit_waiting",
                    tokens_requested=tokens,
                    tokens_available=self.tokens,
                    wait_seconds=wait_time,
                )
                await asyncio.sleep(wait_time)

# Global singleton instance
rate_limiter = TokenBucketRateLimiter()
```

### 4.3 ErrorRateTracker (Sliding Window)

```python
# backend/app/services/backpressure/error_tracker.py

import time
from collections import deque
from dataclasses import dataclass
from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)

@dataclass
class ErrorEvent:
    """Record of an API error event."""
    timestamp: float
    status_code: int
    is_rate_limit: bool

class ErrorRateTracker:
    """Track error rate using sliding window."""

    def __init__(self, window_seconds: int | None = None):
        self.window_seconds = window_seconds or settings.ERROR_RATE_WINDOW_SECONDS
        self.errors: deque[ErrorEvent] = deque()
        self.total_requests = 0

        logger.info(
            "error_tracker_initialized",
            window_seconds=self.window_seconds,
        )

    def record_success(self) -> None:
        """Record a successful request."""
        self.total_requests += 1
        self._cleanup_old_events()

    def record_error(
        self,
        status_code: int,
        is_rate_limit: bool = False,
    ) -> None:
        """Record an error event."""
        self.total_requests += 1
        self.errors.append(ErrorEvent(
            timestamp=time.monotonic(),
            status_code=status_code,
            is_rate_limit=is_rate_limit,
        ))
        self._cleanup_old_events()

        logger.warning(
            "api_error_recorded",
            status_code=status_code,
            is_rate_limit=is_rate_limit,
            error_rate=self.get_error_rate(),
        )

    def get_error_rate(self) -> float:
        """Calculate error rate in sliding window."""
        self._cleanup_old_events()

        if self.total_requests == 0:
            return 0.0

        return len(self.errors) / self.total_requests

    def is_above_threshold(self) -> bool:
        """Check if error rate exceeds threshold."""
        return self.get_error_rate() > settings.ERROR_RATE_THRESHOLD

    def _cleanup_old_events(self) -> None:
        """Remove events outside the sliding window."""
        cutoff = time.monotonic() - self.window_seconds
        while self.errors and self.errors[0].timestamp < cutoff:
            self.errors.popleft()

# Global singleton instance
error_tracker = ErrorRateTracker()
```

### 4.4 AdaptiveBatchSizer

```python
# backend/app/services/backpressure/batch_sizer.py

import time
from app.core.config import settings
from app.core.logging import get_logger
from app.services.metrics.service import metrics
from app.core.constants import METRIC_EMBEDDING_BATCH_SIZE

logger = get_logger(__name__)

class AdaptiveBatchSizer:
    """Dynamically adjust batch size based on error rate."""

    def __init__(self):
        self.current_size = settings.BATCH_SIZE_INITIAL
        self.last_increase = time.monotonic()

        logger.info(
            "batch_sizer_initialized",
            initial_size=self.current_size,
        )

    def get_batch_size(self) -> int:
        """Get current recommended batch size."""
        return self.current_size

    def decrease_size(self, factor: float | None = None) -> None:
        """Decrease batch size due to errors."""
        factor = factor or settings.BATCH_SIZE_DECREASE_FACTOR
        new_size = max(
            settings.BATCH_SIZE_MIN,
            int(self.current_size * factor)
        )

        if new_size != self.current_size:
            logger.warning(
                "batch_size_decreased",
                old_size=self.current_size,
                new_size=new_size,
                factor=factor,
            )
            self.current_size = new_size
            metrics.record(
                METRIC_EMBEDDING_BATCH_SIZE,
                value=float(new_size),
                labels={"adjustment": "decrease"},
            )

    def try_increase_size(self, error_tracker) -> None:
        """Try to increase batch size if error rate is low."""
        now = time.monotonic()
        recovery_window = settings.ERROR_RATE_RECOVERY_WINDOW

        # Only increase if we've been healthy for recovery window
        if (now - self.last_increase) < recovery_window:
            return

        if error_tracker.get_error_rate() < 0.01:  # < 1% error rate
            new_size = min(
                settings.BATCH_SIZE_MAX,
                int(self.current_size * settings.BATCH_SIZE_INCREASE_FACTOR)
            )

            if new_size != self.current_size:
                logger.info(
                    "batch_size_increased",
                    old_size=self.current_size,
                    new_size=new_size,
                )
                self.current_size = new_size
                self.last_increase = now
                metrics.record(
                    METRIC_EMBEDDING_BATCH_SIZE,
                    value=float(new_size),
                    labels={"adjustment": "increase"},
                )

# Global singleton instance
batch_sizer = AdaptiveBatchSizer()
```

---

## 5. Integration Points

### 5.1 EmbeddingService Modifications

```python
# backend/app/services/embeddings.py (ADDITIONS)

from app.services.metrics.service import metrics
from app.services.backpressure.rate_limiter import rate_limiter
from app.services.backpressure.error_tracker import error_tracker
from app.services.backpressure.batch_sizer import batch_sizer
from app.core.constants import (
    METRIC_EMBEDDING_REQUESTS,
    METRIC_EMBEDDING_LATENCY,
    METRIC_EMBEDDING_TOKEN_COUNT,
    METRIC_API_ERRORS,
)

class EmbeddingService:
    async def generate_embedding(self, text: str, normalize: bool = True) -> EmbeddingVector:
        # ... existing code ...

        # NEW: Token count for rate limiting
        tokens = self._encoding.encode(text)
        token_count = len(tokens)

        # NEW: Acquire tokens from rate limiter
        await rate_limiter.acquire(tokens=token_count)

        # NEW: Record start time for latency
        start_time = time.perf_counter()

        try:
            # ... existing OpenAI API call ...

            # NEW: Record success
            latency_ms = (time.perf_counter() - start_time) * 1000
            error_tracker.record_success()
            metrics.increment(
                METRIC_EMBEDDING_REQUESTS,
                labels={"status": "success"},
            )
            metrics.record(
                METRIC_EMBEDDING_LATENCY,
                value=latency_ms,
                labels={"model": self.model},
            )
            metrics.record(
                METRIC_EMBEDDING_TOKEN_COUNT,
                value=float(token_count),
                labels={"truncated": str(truncated).lower()},
            )

            return embedding

        except openai.RateLimitError as e:
            # NEW: Record 429 error
            error_tracker.record_error(status_code=429, is_rate_limit=True)
            metrics.increment(
                METRIC_API_ERRORS,
                labels={"provider": "openai", "status": "429"},
            )
            batch_sizer.decrease_size(factor=0.5)  # 50% reduction on 429
            raise

        except openai.APIError as e:
            # NEW: Record 5xx error
            status_code = getattr(e, "status_code", 500)
            if 500 <= status_code < 600:
                error_tracker.record_error(status_code=status_code, is_rate_limit=False)
                metrics.increment(
                    METRIC_API_ERRORS,
                    labels={"provider": "openai", "status": str(status_code)},
                )
                batch_sizer.decrease_size(factor=0.75)  # 25% reduction on 5xx
            raise
```

---

## 6. Guardrails Implementation

### 6.1 Vector Dimension Validation

```python
# backend/app/db/repositories/chunk_repository.py (ADDITION)

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)

async def get_chunks_by_analysis(
    self,
    analysis_id: str,
) -> list[AnalysisChunk]:
    """Get all chunks for an analysis with dimension validation."""
    chunks = await self.session.execute(
        select(AnalysisChunk).where(AnalysisChunk.analysis_id == analysis_id)
    )
    results = chunks.scalars().all()

    # Validate dimensions if enabled
    if settings.VECTOR_DIMENSION_CHECK:
        for chunk in results:
            if chunk.embedding and len(chunk.embedding) != settings.EMBEDDING_DIMENSIONS:
                logger.error(
                    "invalid_embedding_dimensions",
                    chunk_id=str(chunk.id),
                    expected=settings.EMBEDDING_DIMENSIONS,
                    actual=len(chunk.embedding),
                )
                # Option 1: Raise error
                # raise ValueError(f"Invalid embedding dimensions: {len(chunk.embedding)}")
                # Option 2: Mark for re-embedding (safer)
                chunk.embedding = None

    return results
```

### 6.2 Orphan Chunk Detection

```python
# backend/app/db/repositories/chunk_repository.py (ADDITION)

async def detect_orphan_chunks(self) -> list[str]:
    """Detect chunks with missing analysis_id references."""
    if not settings.ORPHAN_CHUNK_DETECTION:
        return []

    query = """
    SELECT c.id
    FROM analysis_chunks c
    LEFT JOIN analyses a ON c.analysis_id = a.id
    WHERE a.id IS NULL
    """

    result = await self.session.execute(text(query))
    orphan_ids = [str(row[0]) for row in result]

    if orphan_ids:
        logger.warning(
            "orphan_chunks_detected",
            count=len(orphan_ids),
            sample_ids=orphan_ids[:5],
        )

    return orphan_ids
```

---

## 7. Monitoring & Alerts

### 7.1 Key Metrics to Monitor

```
┌────────────────────────────────────────────────────────────────────┐
│                    PRODUCTION MONITORING                           │
├────────────────────────────────────────────────────────────────────┤
│                                                                    │
│  🔴 CRITICAL ALERTS (PagerDuty)                                   │
│  ─────────────────────────────────────────────────────────────────│
│  • Error rate > 10% for 5 minutes                                 │
│  • P95 latency > 5 seconds for embedding                          │
│  • Orphan chunks > 100                                            │
│  • Rate limit hits > 50/hour                                      │
│                                                                    │
│  🟡 WARNING ALERTS (Slack)                                        │
│  ─────────────────────────────────────────────────────────────────│
│  • Error rate > 5% for 5 minutes                                  │
│  • P95 latency > 2 seconds for search                             │
│  • Batch size reduced to minimum (1)                              │
│  • Token truncation > 20% of requests                             │
│                                                                    │
│  📊 DASHBOARDS                                                     │
│  ─────────────────────────────────────────────────────────────────│
│  • Grafana: Real-time latency graphs (p50/p95/p99)               │
│  • CloudWatch: Error rate trends + alarms                         │
│  • Datadog: Batch size adaptation over time                       │
│                                                                    │
└────────────────────────────────────────────────────────────────────┘
```

### 7.2 Sample Grafana Queries (via CloudWatch Logs Insights)

```sql
-- P95 Embedding Latency
fields @timestamp, value
| filter metric_name = "embedding.latency_ms"
| stats percentile(value, 95) as p95_latency by bin(5m)

-- Error Rate by Status Code
fields @timestamp, labels.status
| filter metric_name = "api.errors.total"
| stats count() by labels.status, bin(1m)

-- Batch Size Adaptation
fields @timestamp, value, labels.adjustment
| filter metric_name = "embedding.batch_size"
| stats latest(value) by bin(1m)

-- Token Truncation Rate
fields @timestamp, labels.truncated
| filter metric_name = "embedding.tokens.total"
| stats count() by labels.truncated, bin(5m)
```

---

## 8. Testing Strategy

### 8.1 Unit Tests

```python
# backend/tests/unit/services/backpressure/test_rate_limiter.py

@pytest.mark.asyncio
async def test_rate_limiter_blocks_when_capacity_exceeded():
    limiter = TokenBucketRateLimiter(capacity=100, refill_rate=10)

    # Consume all tokens
    await limiter.acquire(tokens=100)

    # Next request should block
    start = time.time()
    await limiter.acquire(tokens=10)
    elapsed = time.time() - start

    assert elapsed >= 0.9  # Should wait ~1 second for 10 tokens at 10/sec
```

### 8.2 Integration Tests

```python
# backend/tests/integration/services/test_embedding_with_backpressure.py

@pytest.mark.asyncio
async def test_embedding_service_adapts_to_rate_limits(mock_openai):
    """Verify batch size decreases on 429 errors."""
    service = EmbeddingService()

    # Simulate 429 error
    mock_openai.embeddings.create.side_effect = openai.RateLimitError("Rate limit")

    initial_size = batch_sizer.get_batch_size()

    with pytest.raises(openai.RateLimitError):
        await service.generate_embedding("test")

    # Batch size should be reduced
    assert batch_sizer.get_batch_size() < initial_size
```

---

## 9. Performance Impact Analysis

### 9.1 Runtime Overhead

```
┌────────────────────────────────────────────────────────────────────┐
│                   OVERHEAD ESTIMATION                              │
├────────────────────────────────────────────────────────────────────┤
│                                                                    │
│  Operation                    | Overhead     | Per Request        │
│  ────────────────────────────────────────────────────────────────│
│  Metrics logging (structlog)  | ~0.1ms       | Negligible         │
│  Token bucket acquire         | ~0.05ms      | Negligible         │
│  Error rate tracking          | ~0.02ms      | Negligible         │
│  In-memory aggregation        | ~0.03ms      | Negligible         │
│  ────────────────────────────────────────────────────────────────│
│  TOTAL OVERHEAD               | ~0.2ms       | < 0.1% @ 200ms p95 │
│                                                                    │
└────────────────────────────────────────────────────────────────────┘
```

### 9.2 Memory Usage

- Metrics in-memory storage: ~1000 samples × 8 bytes = 8KB per histogram
- Error tracker deque: ~100 events × 40 bytes = 4KB
- **Total:** < 100KB for full metrics system

---

## 10. Migration Path

### Phase 1: Metrics Only (Week 1)
1. Add `MetricsService` and `constants`
2. Instrument `EmbeddingService` with basic counters
3. Deploy to staging, validate logs

### Phase 2: Backpressure (Week 2)
4. Add `RateLimiter` and `ErrorRateTracker`
5. Integrate with `EmbeddingService`
6. Deploy to staging, load test

### Phase 3: Adaptive Controls (Week 3)
7. Add `AdaptiveBatchSizer`
8. Full integration across services
9. Production deployment with feature flags

### Phase 4: Guardrails (Week 4)
10. Vector dimension validation
11. Orphan chunk detection
12. Monitoring dashboard setup

---

## 11. Open Questions

1. **Metrics Retention:** How long to keep in-memory histogram data?
   - **Recommendation:** 1000 samples per metric (last ~16 minutes at 1 req/sec)

2. **Log Rotation:** Should we rotate `metrics.jsonl`?
   - **Recommendation:** Use `logrotate` with 7-day retention

3. **Multi-Instance Coordination:** How to handle rate limiting across multiple FastAPI workers?
   - **Current:** Per-process rate limiter (safe but conservative)
   - **Future:** Redis-based distributed rate limiter

4. **Cost Tracking:** Should we add OpenAI API cost estimation?
   - **Recommendation:** Add in Phase 2 with `METRIC_EMBEDDING_COST` counter

---

## 12. Success Criteria

✅ **Implementation Complete When:**
- [ ] All metrics emit to structured logs
- [ ] P50/P95 latency tracked for embedding/search/rerank
- [ ] Token count and truncation logged (no raw text)
- [ ] 429/5xx errors tracked with adaptive batch sizing
- [ ] Rate limiter prevents API quota exhaustion
- [ ] Jittered retries prevent thundering herd
- [ ] Vector dimension validation catches corrupted embeddings
- [ ] Orphan chunk detection runs on schedule
- [ ] Unit tests cover 80%+ of new code
- [ ] Integration tests verify backpressure behavior
- [ ] Documentation updated with configuration guide

---

## Appendix A: Alternative Approaches Considered

### Prometheus + Grafana
**Pros:** Industry standard, rich ecosystem
**Cons:** Requires additional infrastructure, /metrics endpoint, scraping setup
**Decision:** Rejected due to complexity for MVP

### Circuit Breaker Pattern
**Pros:** More sophisticated failure handling
**Cons:** Overkill for simple rate limiting, harder to tune
**Decision:** Rejected in favor of token bucket simplicity

### Redis-Based Rate Limiting
**Pros:** Shared state across workers
**Cons:** Adds dependency, network latency
**Decision:** Deferred to future (start with in-memory)

---

**END OF DESIGN DOCUMENT**
