# Issue #218: Telemetry & Backpressure for Embedding Pipeline

**Status:** Design Complete (December 10, 2025)
**Sprint:** Sprint 8 - Embeddings & Search
**Priority:** MEDIUM
**Estimated Effort:** 4 weeks (phased rollout)

---

## Overview

Add production-grade telemetry and adaptive backpressure controls to SkillForge's embedding pipeline to:
- Monitor latency (p50/p95/p99), token counts, batch sizes, and error rates
- Prevent 429 rate limit errors through token bucket rate limiting
- Adapt batch sizes dynamically based on error rates
- Provide structured logging for metrics (no Prometheus dependency)
- Add guardrails for vector dimension validation and orphan chunk detection

---

## Key Design Decisions

### 1. Metrics Library: structlog (Zero New Dependencies)
- Uses existing structlog installation
- Emits metrics as JSON logs to `logs/metrics.jsonl`
- Compatible with CloudWatch Logs Insights, Grafana Loki, Datadog
- In-memory aggregation for p50/p95/p99 percentile calculation
- **Performance:** < 0.2ms overhead per request, < 100KB memory

### 2. Rate Limiting: Token Bucket Algorithm
- Default: 10,000 tokens/minute (OpenAI Tier 1)
- Configurable per OpenAI tier (Tier 2: 50k TPM, Tier 3: 150k TPM)
- Per-service instance (future: Redis for distributed limiting)
- Async-friendly with automatic wait/refill

### 3. Adaptive Batch Sizing
- Initial: 20 chunks/batch
- Range: 1-100 chunks
- Decrease 50% on 429 errors, 25% on 5xx errors
- Increase 10% when error rate < 1% for 5 minutes
- Prevents both rate limit exhaustion and under-utilization

### 4. Error Tracking: Sliding Window
- 60-second window for error rate calculation
- Threshold: 5% error rate triggers batch size reduction
- Tracks 429 (rate limit) vs 5xx (server errors) separately
- Graceful degradation on high error rates

### 5. Retry Strategy: Exponential Backoff with Jitter
- Base delay: 2 seconds, max: 16 seconds
- Multiplier: 2x per retry
- Jitter: ±20% to prevent thundering herd
- Integrates with existing tenacity configuration

---

## Architecture Files

| File | Description |
|------|-------------|
| [`ARCHITECTURE_DESIGN.md`](./ARCHITECTURE_DESIGN.md) | Complete technical specification (12 sections, 600+ lines) |
| [`ARCHITECTURE_DIAGRAM.md`](./ARCHITECTURE_DIAGRAM.md) | ASCII diagrams for all system components |
| `README.md` | This file - executive summary |

---

## Metrics Tracked

### Counters
- `embedding.requests.total` - API call count (labels: status=success/rate_limit/error)
- `embedding.tokens.total` - Token usage (labels: truncated=true/false)
- `embedding.batches.total` - Batch count (labels: size_bucket=1-10/11-50/51-100)
- `search.requests.total` - Search count (labels: mode=semantic/keyword/hybrid)
- `api.errors.total` - Error count (labels: provider=openai, status=429/5xx)
- `dedup.chunks.total` - Dedup count (labels: action=kept/removed)

### Histograms (p50/p95/p99)
- `embedding.latency_ms` - Embedding generation time
- `search.latency_ms` - Search query time
- `rerank.latency_ms` - Re-ranking time
- `embedding.batch_size` - Actual batch sizes used
- `embedding.token_count` - Tokens per request

---

## File Structure

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
```

---

## Configuration (Environment Variables)

### Metrics
```bash
METRICS_ENABLED=true
METRICS_LOG_FILE=logs/metrics.jsonl
METRICS_FLUSH_INTERVAL=60  # seconds
```

### Rate Limiting
```bash
RATE_LIMIT_ENABLED=true
RATE_LIMIT_TOKENS_PER_MINUTE=10000  # OpenAI tier-dependent
RATE_LIMIT_BURST_CAPACITY=2000
```

### Batch Sizing
```bash
BATCH_SIZE_INITIAL=20
BATCH_SIZE_MIN=1
BATCH_SIZE_MAX=100
BATCH_SIZE_DECREASE_FACTOR=0.5  # 50% reduction on error
BATCH_SIZE_INCREASE_FACTOR=1.1  # 10% increase when healthy
```

### Error Tracking
```bash
ERROR_RATE_WINDOW_SECONDS=60
ERROR_RATE_THRESHOLD=0.05  # 5% error rate
ERROR_RATE_RECOVERY_WINDOW=300  # 5 minutes
```

### Retry Configuration
```bash
RETRY_JITTER_MIN=0.8  # -20% jitter
RETRY_JITTER_MAX=1.2  # +20% jitter
```

### Guardrails
```bash
VECTOR_DIMENSION_CHECK=true
ORPHAN_CHUNK_DETECTION=true
```

---

## Migration Path (4 Weeks)

### Phase 1: Metrics Only (Week 1)
- **Goal:** Add basic metrics without changing behavior
- **Tasks:**
  1. Create `MetricsService` and `collectors.py`
  2. Add constants to `app/core/constants.py`
  3. Instrument `EmbeddingService.generate_embedding()`
  4. Deploy to staging, validate logs in CloudWatch
- **Success Criteria:** Metrics appear in logs, no performance degradation

### Phase 2: Backpressure (Week 2)
- **Goal:** Add rate limiting and error tracking
- **Tasks:**
  1. Implement `RateLimiter` (token bucket)
  2. Implement `ErrorRateTracker` (sliding window)
  3. Integrate with `EmbeddingService`
  4. Load test in staging (simulate 429 errors)
- **Success Criteria:** Rate limiter prevents quota exhaustion, error tracker detects spikes

### Phase 3: Adaptive Controls (Week 3)
- **Goal:** Dynamic batch sizing based on error rates
- **Tasks:**
  1. Implement `AdaptiveBatchSizer`
  2. Wire up batch size adjustments on errors
  3. Full integration testing with all services
  4. Production deployment with feature flags
- **Success Criteria:** Batch size adapts to error rates, system self-heals

### Phase 4: Guardrails (Week 4)
- **Goal:** Data integrity validation
- **Tasks:**
  1. Add vector dimension validation in `ChunkRepository`
  2. Implement orphan chunk detection query
  3. Set up Grafana dashboards
  4. Configure CloudWatch alarms
- **Success Criteria:** Corrupted vectors caught, orphans detected, alerts firing

---

## Monitoring & Alerts

### Critical Alerts (PagerDuty)
- Error rate > 10% for 5 minutes
- P95 latency > 5 seconds for embedding
- Orphan chunks > 100
- Rate limit hits > 50/hour

### Warning Alerts (Slack)
- Error rate > 5% for 5 minutes
- P95 latency > 2 seconds for search
- Batch size reduced to minimum (1)
- Token truncation > 20% of requests

### Grafana Dashboards
- Real-time latency graphs (p50/p95/p99)
- Error rate trends by status code
- Batch size adaptation over time
- Token usage and truncation rate

---

## Performance Impact

| Metric | Value | Impact |
|--------|-------|--------|
| Overhead per request | ~0.2ms | < 0.1% at 200ms p95 |
| Memory usage | < 100KB | Negligible |
| Log file size | ~1MB/day | At 100 req/min |

---

## Sample Metrics Log Entry

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

**Note:** No raw text is logged - only hashes, lengths, and metadata per Issue #218 requirements.

---

## CloudWatch Logs Insights Queries

### P95 Embedding Latency
```sql
fields @timestamp, value
| filter metric_name = "embedding.latency_ms"
| stats percentile(value, 95) as p95_latency by bin(5m)
```

### Error Rate by Status Code
```sql
fields @timestamp, labels.status
| filter metric_name = "api.errors.total"
| stats count() by labels.status, bin(1m)
```

### Batch Size Adaptation
```sql
fields @timestamp, value, labels.adjustment
| filter metric_name = "embedding.batch_size"
| stats latest(value) by bin(1m)
```

### Token Truncation Rate
```sql
fields @timestamp, labels.truncated
| filter metric_name = "embedding.tokens.total"
| stats count() by labels.truncated, bin(5m)
```

---

## Testing Strategy

### Unit Tests
- Token bucket refill math
- Error rate calculation accuracy
- Batch size adjustment logic
- Percentile calculation correctness

### Integration Tests
- Rate limiter blocks when capacity exceeded
- Batch size decreases on 429 errors
- Error tracker sliding window works
- Metrics emit to structured logs

### Load Tests
- Simulate 429 errors, verify backoff
- Test batch size adaptation under load
- Validate rate limiter at API limits
- Measure performance overhead

---

## Alternative Approaches Considered

### Prometheus + Grafana
- **Pros:** Industry standard, rich ecosystem
- **Cons:** Additional infrastructure, /metrics endpoint, scraping setup
- **Decision:** Rejected due to complexity for MVP

### Circuit Breaker Pattern
- **Pros:** More sophisticated failure handling
- **Cons:** Overkill for simple rate limiting, harder to tune
- **Decision:** Rejected in favor of token bucket simplicity

### Redis-Based Rate Limiting
- **Pros:** Shared state across workers
- **Cons:** Adds dependency, network latency
- **Decision:** Deferred to future (start with in-memory)

---

## Dependencies

| Component | Dependency | Status |
|-----------|-----------|--------|
| Metrics logging | `structlog` | ✅ Already installed |
| Rate limiting | None | ✅ Pure Python |
| Error tracking | None | ✅ Pure Python |
| Batch sizing | None | ✅ Pure Python |
| Configuration | `pydantic-settings` | ✅ Already installed |

**Total new dependencies:** 0

---

## Success Criteria

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
- [ ] Grafana dashboards deployed
- [ ] CloudWatch alarms configured

---

## Related Issues

- **#215:** Embedding Pipeline Hardening - Foundation for telemetry
- **#216:** Retrieval & Search API - Benefits from search latency metrics
- **#217:** Re-Ranker - Benefits from re-rank latency metrics
- **#219:** Eval Harness - Uses metrics for A/B testing embeddings
- **#220:** PII/Safety Guardrails - Shares vector validation code

---

## Next Steps

1. **Review architecture design** with team
2. **Estimate implementation effort** per phase
3. **Create GitHub issues** for each phase
4. **Set up staging environment** for metrics testing
5. **Configure CloudWatch Logs** ingestion
6. **Begin Phase 1 implementation** (Metrics Only)

---

**Last Updated:** December 10, 2025
**Author:** Backend System Architect Agent
**Status:** Design Review → Ready for Implementation Planning
