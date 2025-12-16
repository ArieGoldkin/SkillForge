# Issue #218: Telemetry & Backpressure Quick Reference

**For Developers:** Quick lookup guide for using the telemetry and backpressure system.

---

## How to Emit Metrics

### Import the MetricsService
```python
from app.services.metrics.service import metrics
from app.core.constants import METRIC_EMBEDDING_LATENCY
```

### Increment a Counter
```python
# Simple counter
metrics.increment("embedding.requests.total")

# Counter with labels
metrics.increment(
    "embedding.requests.total",
    labels={"status": "success", "model": "text-embedding-3-small"}
)
```

### Record a Histogram (for percentiles)
```python
import time

start = time.perf_counter()
# ... do work ...
latency_ms = (time.perf_counter() - start) * 1000

metrics.record(
    METRIC_EMBEDDING_LATENCY,
    value=latency_ms,
    labels={"model": "text-embedding-3-small"}
)
```

### Query Percentiles
```python
# Get p50, p95, p99 for a metric
percentiles = metrics.get_percentiles(
    METRIC_EMBEDDING_LATENCY,
    percentiles=[50, 95, 99],
    labels={"model": "text-embedding-3-small"}
)
# Result: {50: 150.0, 95: 300.0, 99: 450.0}
```

---

## How to Use Rate Limiter

### Import the RateLimiter
```python
from app.services.backpressure.rate_limiter import rate_limiter
```

### Acquire Tokens Before API Call
```python
async def generate_embedding(text: str):
    # Calculate token count
    token_count = len(encoding.encode(text))

    # Acquire tokens (will wait if not enough available)
    await rate_limiter.acquire(tokens=token_count)

    # Now safe to call OpenAI API
    response = await openai_client.embeddings.create(...)
```

---

## How to Track Errors

### Import the ErrorTracker
```python
from app.services.backpressure.error_tracker import error_tracker
```

### Record Success/Error
```python
try:
    response = await openai_client.embeddings.create(...)
    error_tracker.record_success()
except openai.RateLimitError as e:
    error_tracker.record_error(status_code=429, is_rate_limit=True)
    raise
except openai.APIError as e:
    error_tracker.record_error(status_code=e.status_code, is_rate_limit=False)
    raise
```

### Check Error Rate
```python
if error_tracker.is_above_threshold():
    logger.warning("Error rate too high, reducing batch size")
    batch_sizer.decrease_size()
```

---

## How to Use Adaptive Batch Sizer

### Import the BatchSizer
```python
from app.services.backpressure.batch_sizer import batch_sizer
```

### Get Current Batch Size
```python
batch_size = batch_sizer.get_batch_size()
chunks_batch = chunks[:batch_size]
```

### Adjust on Error
```python
# Decrease on 429
if status_code == 429:
    batch_sizer.decrease_size(factor=0.5)  # 50% reduction

# Decrease on 5xx
elif 500 <= status_code < 600:
    batch_sizer.decrease_size(factor=0.75)  # 25% reduction
```

### Try to Increase When Healthy
```python
# Periodically check if we can increase
batch_sizer.try_increase_size(error_tracker)
```

---

## Configuration Reference

### Environment Variables (.env)

```bash
# Metrics
METRICS_ENABLED=true
METRICS_LOG_FILE=logs/metrics.jsonl

# Rate Limiting
RATE_LIMIT_ENABLED=true
RATE_LIMIT_TOKENS_PER_MINUTE=10000  # Tier 1: 10k, Tier 2: 50k, Tier 3: 150k

# Batch Sizing
BATCH_SIZE_INITIAL=20
BATCH_SIZE_MIN=1
BATCH_SIZE_MAX=100

# Error Tracking
ERROR_RATE_THRESHOLD=0.05  # 5%
```

### Access Settings in Code
```python
from app.core.config import settings

if settings.METRICS_ENABLED:
    metrics.increment(...)

if settings.RATE_LIMIT_ENABLED:
    await rate_limiter.acquire(...)
```

---

## Standard Metric Names (Constants)

```python
from app.core.constants import (
    # Counters
    METRIC_EMBEDDING_REQUESTS,      # "embedding.requests.total"
    METRIC_EMBEDDING_TOKENS,        # "embedding.tokens.total"
    METRIC_EMBEDDING_BATCHES,       # "embedding.batches.total"
    METRIC_API_ERRORS,              # "api.errors.total"
    METRIC_SEARCH_REQUESTS,         # "search.requests.total"
    METRIC_RERANK_REQUESTS,         # "rerank.requests.total"
    METRIC_DEDUP_CHUNKS,            # "dedup.chunks.total"

    # Histograms
    METRIC_EMBEDDING_LATENCY,       # "embedding.latency_ms"
    METRIC_EMBEDDING_BATCH_SIZE,    # "embedding.batch_size"
    METRIC_EMBEDDING_TOKEN_COUNT,   # "embedding.token_count"
    METRIC_SEARCH_LATENCY,          # "search.latency_ms"
    METRIC_RERANK_LATENCY,          # "rerank.latency_ms"

    # Label values
    LABEL_STATUS_SUCCESS,           # "success"
    LABEL_STATUS_RATE_LIMIT,        # "rate_limit"
    LABEL_STATUS_ERROR,             # "error"
)
```

---

## Common Patterns

### Pattern 1: Instrument a Service Method
```python
import time
from app.services.metrics.service import metrics
from app.services.backpressure.rate_limiter import rate_limiter
from app.services.backpressure.error_tracker import error_tracker
from app.core.constants import (
    METRIC_EMBEDDING_REQUESTS,
    METRIC_EMBEDDING_LATENCY,
    METRIC_API_ERRORS,
)

async def generate_embedding(self, text: str):
    # 1. Acquire rate limit tokens
    token_count = len(self._encoding.encode(text))
    await rate_limiter.acquire(tokens=token_count)

    # 2. Start timer
    start = time.perf_counter()

    try:
        # 3. Make API call
        response = await self.client.embeddings.create(...)

        # 4. Record success metrics
        latency_ms = (time.perf_counter() - start) * 1000
        error_tracker.record_success()

        metrics.increment(
            METRIC_EMBEDDING_REQUESTS,
            labels={"status": "success"}
        )
        metrics.record(
            METRIC_EMBEDDING_LATENCY,
            value=latency_ms,
            labels={"model": self.model}
        )

        return response.data[0].embedding

    except openai.RateLimitError as e:
        # 5. Record 429 error
        error_tracker.record_error(status_code=429, is_rate_limit=True)
        metrics.increment(
            METRIC_API_ERRORS,
            labels={"provider": "openai", "status": "429"}
        )
        batch_sizer.decrease_size(factor=0.5)
        raise

    except openai.APIError as e:
        # 6. Record 5xx error
        status_code = getattr(e, "status_code", 500)
        if 500 <= status_code < 600:
            error_tracker.record_error(status_code=status_code)
            metrics.increment(
                METRIC_API_ERRORS,
                labels={"provider": "openai", "status": str(status_code)}
            )
            batch_sizer.decrease_size(factor=0.75)
        raise
```

### Pattern 2: Batch Processing with Adaptive Sizing
```python
from app.services.backpressure.batch_sizer import batch_sizer
from app.services.backpressure.error_tracker import error_tracker

async def process_chunks(chunks: list[Chunk]):
    while chunks:
        # Get current recommended batch size
        batch_size = batch_sizer.get_batch_size()
        batch = chunks[:batch_size]
        chunks = chunks[batch_size:]

        try:
            # Process batch
            await process_batch(batch)

            # Try to increase size if error rate is low
            batch_sizer.try_increase_size(error_tracker)

        except Exception as e:
            # Decrease size on error (handled in process_batch)
            continue
```

### Pattern 3: Monitor Custom Operation
```python
import time
from app.services.metrics.service import metrics

async def custom_operation():
    start = time.perf_counter()

    try:
        result = await do_something()

        latency_ms = (time.perf_counter() - start) * 1000
        metrics.record(
            "custom.operation.latency_ms",
            value=latency_ms,
            labels={"operation": "something"}
        )
        metrics.increment(
            "custom.operation.total",
            labels={"status": "success"}
        )

        return result

    except Exception as e:
        metrics.increment(
            "custom.operation.total",
            labels={"status": "error", "error_type": type(e).__name__}
        )
        raise
```

---

## Debugging Tips

### Check if Metrics Are Enabled
```python
from app.core.config import settings

if not settings.METRICS_ENABLED:
    logger.warning("Metrics are disabled")
```

### View Current Rate Limiter State
```python
from app.services.backpressure.rate_limiter import rate_limiter

logger.info(
    "rate_limiter_state",
    tokens_available=rate_limiter.tokens,
    capacity=rate_limiter.capacity,
    refill_rate=rate_limiter.refill_rate,
)
```

### Check Error Rate Threshold
```python
from app.services.backpressure.error_tracker import error_tracker

current_rate = error_tracker.get_error_rate()
threshold = settings.ERROR_RATE_THRESHOLD

logger.info(
    "error_rate_check",
    current_rate=current_rate,
    threshold=threshold,
    is_above_threshold=current_rate > threshold,
)
```

### Get Current Batch Size
```python
from app.services.backpressure.batch_sizer import batch_sizer

logger.info(
    "batch_size_status",
    current_size=batch_sizer.current_size,
    min_size=settings.BATCH_SIZE_MIN,
    max_size=settings.BATCH_SIZE_MAX,
)
```

---

## Testing Helpers

### Mock MetricsService in Tests
```python
from unittest.mock import MagicMock, patch

@patch("app.services.metrics.service.metrics")
async def test_my_function(mock_metrics):
    await my_function()

    # Assert metrics were recorded
    mock_metrics.increment.assert_called_with(
        "embedding.requests.total",
        labels={"status": "success"}
    )
    mock_metrics.record.assert_called_once()
```

### Disable Rate Limiting in Tests
```python
from app.core.config import settings

@pytest.fixture
def disable_rate_limiting(monkeypatch):
    monkeypatch.setattr(settings, "RATE_LIMIT_ENABLED", False)
```

### Fast Retry in Tests
```python
from app.core.config import settings

@pytest.fixture
def fast_retries(monkeypatch):
    monkeypatch.setattr(settings, "RETRY_MIN_WAIT_EMBEDDING", 0.1)
    monkeypatch.setattr(settings, "RETRY_MAX_WAIT_EMBEDDING", 0.5)
```

---

## Performance Considerations

### Metrics Overhead
- **Increment/Record:** ~0.05ms per call
- **In-memory aggregation:** ~0.03ms per sample
- **Logging:** ~0.1ms per metric (async I/O)
- **Total:** ~0.2ms per instrumented operation

### Rate Limiter Overhead
- **acquire() when tokens available:** ~0.05ms
- **acquire() when waiting:** Depends on refill rate
- **Async-friendly:** No blocking of event loop

### Memory Usage
- **MetricsService:** ~8KB per histogram (1000 samples × 8 bytes)
- **ErrorTracker:** ~4KB (deque of 100 events)
- **RateLimiter:** Negligible (3 floats)
- **Total:** < 100KB for entire system

---

## Troubleshooting

### Metrics Not Appearing in Logs
1. Check `METRICS_ENABLED=true` in `.env`
2. Verify log file path: `METRICS_LOG_FILE=logs/metrics.jsonl`
3. Check file permissions on `logs/` directory
4. Ensure structlog is configured correctly

### Rate Limiter Blocking Requests
1. Check `RATE_LIMIT_TOKENS_PER_MINUTE` matches OpenAI tier
2. Verify token count calculation is accurate
3. Check refill rate: `capacity / 60.0` tokens/second
4. Increase `RATE_LIMIT_BURST_CAPACITY` for spikes

### Batch Size Not Adapting
1. Check error rate is above `ERROR_RATE_THRESHOLD` (5%)
2. Verify `ERROR_RATE_WINDOW_SECONDS` is reasonable (60s)
3. Ensure `try_increase_size()` is called periodically
4. Check `ERROR_RATE_RECOVERY_WINDOW` (5 minutes)

### High Latency After Adding Metrics
1. Verify metrics logging is async (structlog default)
2. Check log file is not on slow storage
3. Reduce `METRICS_FLUSH_INTERVAL` if buffering too much
4. Consider disabling DEBUG-level metrics in production

---

## CloudWatch Logs Insights Queries

### Find Slow Requests (p95 > 500ms)
```sql
fields @timestamp, value, labels.model
| filter metric_name = "embedding.latency_ms" and value > 500
| sort value desc
```

### Error Rate Over Time
```sql
fields @timestamp, labels.status
| filter metric_name = "embedding.requests.total"
| stats sum(value) as total by labels.status, bin(5m)
```

### Token Truncation Analysis
```sql
fields @timestamp, labels.truncated, value
| filter metric_name = "embedding.tokens.total"
| stats count() as requests, sum(value) as total_tokens by labels.truncated
```

---

**Last Updated:** December 10, 2025
**For More Details:** See `ARCHITECTURE_DESIGN.md` and `ARCHITECTURE_DIAGRAM.md`
