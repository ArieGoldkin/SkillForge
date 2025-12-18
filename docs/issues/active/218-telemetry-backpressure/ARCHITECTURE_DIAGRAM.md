# Issue #218: Telemetry & Backpressure System Diagram

## High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         SKILLFORGE TELEMETRY SYSTEM                         │
│                         (Lightweight, structlog-based)                      │
└─────────────────────────────────────────────────────────────────────────────┘

                                 ┌─────────────────┐
                                 │  FastAPI App    │
                                 └────────┬────────┘
                                          │
                    ┌─────────────────────┼─────────────────────┐
                    │                     │                     │
                    ▼                     ▼                     ▼
         ┌──────────────────┐  ┌──────────────────┐  ┌──────────────────┐
         │ EmbeddingService │  │  SearchService   │  │    ReRanker      │
         └────────┬─────────┘  └────────┬─────────┘  └────────┬─────────┘
                  │                     │                     │
                  │                     │                     │
         ┌────────┴─────────────────────┴─────────────────────┴────────┐
         │              INSTRUMENTATION LAYER                          │
         │  ┌───────────────────────────────────────────────────────┐  │
         │  │  MetricsService (singleton, thread-safe)             │  │
         │  │  • increment(counter, labels)                        │  │
         │  │  • record(histogram, value, labels)                  │  │
         │  │  • get_percentiles(metric, [p50, p95, p99])          │  │
         │  └───────────────────────────────────────────────────────┘  │
         └─────────────────────────────┬───────────────────────────────┘
                                       │
                  ┌────────────────────┼────────────────────┐
                  ▼                    ▼                    ▼
         ┌────────────────┐   ┌────────────────┐  ┌──────────────────┐
         │   structlog    │   │  In-Memory     │  │  logs/metrics    │
         │  (JSON logs)   │   │  Aggregation   │  │     .jsonl       │
         └────────┬───────┘   └────────┬───────┘  └────────┬─────────┘
                  │                    │                    │
                  └──────────┬─────────┴────────────────────┘
                             ▼
                    ┌─────────────────┐
                    │  CloudWatch /   │
                    │  Grafana Loki   │
                    │  / Datadog      │
                    └─────────────────┘
```

---

## Backpressure Control Flow

```
┌───────────────────────────────────────────────────────────────────────────┐
│                     ADAPTIVE BACKPRESSURE PIPELINE                        │
└───────────────────────────────────────────────────────────────────────────┘

    ┌─────────────────────────────────────────────────────────────────────┐
    │  STEP 1: RATE LIMITING (Token Bucket)                              │
    └─────────────────────────────────────────────────────────────────────┘
                                    │
                      Request (text, token_count)
                                    │
                                    ▼
                         ┌─────────────────────┐
                         │  RateLimiter        │
                         │  .acquire(tokens)   │
                         └──────────┬──────────┘
                                    │
                    ┌───────────────┴───────────────┐
                    │                               │
                    ▼                               ▼
            Tokens Available                 No Tokens
                    │                               │
                    │                               ▼
                    │                    ┌──────────────────┐
                    │                    │  Wait & Refill   │
                    │                    │  (async sleep)   │
                    │                    └────────┬─────────┘
                    │                             │
                    └─────────────────────────────┘
                                    │
    ┌─────────────────────────────────────────────────────────────────────┐
    │  STEP 2: API CALL WITH MONITORING                                   │
    └─────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
                         ┌─────────────────────┐
                         │  OpenAI API Call    │
                         │  (with retry)       │
                         └──────────┬──────────┘
                                    │
                    ┌───────────────┴───────────────┐
                    │                               │
                    ▼                               ▼
                200 OK                       429 / 5xx Error
                    │                               │
                    ▼                               ▼
         ┌──────────────────┐           ┌──────────────────────┐
         │ ErrorTracker     │           │  ErrorTracker        │
         │ .record_success()│           │  .record_error(...)  │
         └──────────┬───────┘           └──────────┬───────────┘
                    │                               │
                    │                               ▼
                    │                    ┌──────────────────────┐
                    │                    │  Error rate > 5%?    │
                    │                    └──────────┬───────────┘
                    │                               │
                    │                    ┌──────────┴──────────┐
                    │                    │                     │
                    │                   Yes                   No
                    │                    │                     │
                    │                    ▼                     │
                    │         ┌──────────────────────┐         │
                    │         │  AdaptiveBatchSizer  │         │
                    │         │  .decrease_size()    │         │
                    │         │  (50% for 429,       │         │
                    │         │   25% for 5xx)       │         │
                    │         └──────────────────────┘         │
                    │                                          │
                    └──────────────┬───────────────────────────┘
                                   │
    ┌─────────────────────────────────────────────────────────────────────┐
    │  STEP 3: METRICS EMISSION                                           │
    └─────────────────────────────────────────────────────────────────────┘
                                   │
                                   ▼
                        ┌──────────────────────┐
                        │  MetricsService      │
                        │  • Latency (p95)     │
                        │  • Token count       │
                        │  • Error count       │
                        │  • Batch size        │
                        └──────────┬───────────┘
                                   │
                                   ▼
                        ┌──────────────────────┐
                        │  structlog →         │
                        │  logs/metrics.jsonl  │
                        └──────────────────────┘
```

---

## Component Interaction Diagram

```
┌───────────────────────────────────────────────────────────────────────────┐
│                    COMPONENT INTERACTION FLOW                             │
└───────────────────────────────────────────────────────────────────────────┘

┌────────────────────┐
│  EmbeddingService  │
│  .generate_embed() │
└─────────┬──────────┘
          │
          │ 1. Check batch size
          ▼
┌────────────────────┐      ┌──────────────────┐
│ AdaptiveBatchSizer │─────▶│ Current size: 20 │
└────────────────────┘      └──────────────────┘
          │
          │ 2. Acquire rate limit tokens
          ▼
┌────────────────────┐      ┌──────────────────────────┐
│  RateLimiter       │─────▶│ Wait if capacity < need  │
└────────────────────┘      └──────────────────────────┘
          │
          │ 3. Call OpenAI API
          ▼
┌────────────────────┐
│  OpenAI Client     │
│  (async + retry)   │
└─────────┬──────────┘
          │
          ├───────────────────────────┐
          │                           │
          ▼                           ▼
    200 Success                  429/5xx Error
          │                           │
          │                           ▼
          │                  ┌──────────────────┐
          │                  │  ErrorTracker    │
          │                  │  • Sliding window│
          │                  │  • Calculate %   │
          │                  └────────┬─────────┘
          │                           │
          │                           ▼
          │                  Error rate > 5%?
          │                           │
          │                           ├─────Yes────▶ BatchSizer.decrease()
          │                           │
          │                           └─────No─────▶ (no action)
          │
          │ 4. Record metrics
          ▼
┌────────────────────┐
│  MetricsService    │
│  • increment()     │
│  • record()        │
└─────────┬──────────┘
          │
          ▼
┌────────────────────┐      ┌──────────────────────────┐
│   structlog        │─────▶│ {"metric_name": "...",  │
│  JSON renderer     │      │  "value": 123.4,         │
└────────────────────┘      │  "labels": {...}}        │
                            └──────────────────────────┘
```

---

## Metrics Flow Architecture

```
┌───────────────────────────────────────────────────────────────────────────┐
│                         METRICS DATA FLOW                                 │
└───────────────────────────────────────────────────────────────────────────┘

Application Code                    MetricsService               Output
═══════════════                    ════════════════             ══════

┌─────────────┐
│ increment() │───▶ Counter: "embedding.requests.total"
└─────────────┘         │           {status: "success"}: 1234
                        │
                        ├──▶ structlog.info(...)
                        │           │
                        │           ▼
                        │    logs/metrics.jsonl
                        │    {"metric_name": "embedding.requests.total",
                        │     "value": 1234, "labels": {"status": "success"}}
                        │
                        └──▶ In-memory aggregation (hourly flush)


┌─────────────┐
│   record()  │───▶ Histogram: "embedding.latency_ms"
└─────────────┘         │           deque([145.2, 198.7, 134.5, ...])
                        │                    ↓
                        │           Calculate p50/p95/p99
                        │                    ↓
                        ├──▶ structlog.info(...)
                        │           │
                        │           ▼
                        │    logs/metrics.jsonl
                        │    {"metric_name": "embedding.latency_ms",
                        │     "value": 145.2, "labels": {"model": "..."}}
                        │
                        └──▶ Percentile query API
                                    │
                                    ▼
                             {p50: 150.0, p95: 300.0, p99: 450.0}
```

---

## Guardrails Architecture

```
┌───────────────────────────────────────────────────────────────────────────┐
│                    DATA INTEGRITY GUARDRAILS                              │
└───────────────────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────────────────┐
│  VECTOR DIMENSION VALIDATION                                             │
├──────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  ChunkRepository.get_chunks_by_analysis()                                │
│          │                                                               │
│          ▼                                                               │
│  ┌─────────────────────────────────────────────┐                        │
│  │  For each chunk with embedding:             │                        │
│  │    if len(embedding) != 1536:               │                        │
│  │      • Log error with chunk_id              │                        │
│  │      • Option 1: Raise ValueError           │                        │
│  │      • Option 2: Mark for re-embedding      │                        │
│  │        (chunk.embedding = None)             │                        │
│  └─────────────────────────────────────────────┘                        │
│                                                                          │
└──────────────────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────────────────┐
│  ORPHAN CHUNK DETECTION                                                  │
├──────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  Scheduled Task (hourly via cron/Celery)                                │
│          │                                                               │
│          ▼                                                               │
│  ┌─────────────────────────────────────────────┐                        │
│  │  SQL Query:                                 │                        │
│  │    SELECT c.id                              │                        │
│  │    FROM analysis_chunks c                   │                        │
│  │    LEFT JOIN analyses a ON c.analysis_id=a.id                       │
│  │    WHERE a.id IS NULL                       │                        │
│  └───────────────────┬─────────────────────────┘                        │
│                      │                                                   │
│                      ▼                                                   │
│  ┌─────────────────────────────────────────────┐                        │
│  │  If orphans found:                          │                        │
│  │    • Log warning with count + sample IDs    │                        │
│  │    • Alert on-call engineer (if > 100)      │                        │
│  │    • Queue cleanup job                      │                        │
│  └─────────────────────────────────────────────┘                        │
│                                                                          │
└──────────────────────────────────────────────────────────────────────────┘
```

---

## Configuration Overview

```
┌───────────────────────────────────────────────────────────────────────────┐
│                       CONFIGURATION HIERARCHY                             │
└───────────────────────────────────────────────────────────────────────────┘

Environment Variables (.env)
═════════════════════════════

METRICS_ENABLED=true
METRICS_LOG_FILE=logs/metrics.jsonl
METRICS_FLUSH_INTERVAL=60

RATE_LIMIT_ENABLED=true
RATE_LIMIT_TOKENS_PER_MINUTE=10000        # OpenAI Tier 1
RATE_LIMIT_BURST_CAPACITY=2000

BATCH_SIZE_INITIAL=20
BATCH_SIZE_MIN=1
BATCH_SIZE_MAX=100
BATCH_SIZE_DECREASE_FACTOR=0.5            # 50% reduction on error
BATCH_SIZE_INCREASE_FACTOR=1.1            # 10% increase when healthy

ERROR_RATE_WINDOW_SECONDS=60              # Sliding window
ERROR_RATE_THRESHOLD=0.05                 # 5% error rate threshold
ERROR_RATE_RECOVERY_WINDOW=300            # 5 minutes healthy before increase

RETRY_JITTER_MIN=0.8                      # -20% jitter
RETRY_JITTER_MAX=1.2                      # +20% jitter

VECTOR_DIMENSION_CHECK=true
ORPHAN_CHUNK_DETECTION=true

         │
         ▼
┌────────────────────────┐
│  Pydantic Settings     │
│  (app/core/config.py)  │
└────────┬───────────────┘
         │
         ▼
┌────────────────────────────────────────────────┐
│  Runtime Components                            │
│  ────────────────────────────────────────────  │
│  • MetricsService (singleton)                  │
│  • RateLimiter (per-service)                   │
│  • ErrorTracker (sliding window)               │
│  • AdaptiveBatchSizer (dynamic)                │
└────────────────────────────────────────────────┘
```

---

## Deployment Architecture

```
┌───────────────────────────────────────────────────────────────────────────┐
│                    PRODUCTION DEPLOYMENT FLOW                             │
└───────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────┐
│  Development                                                            │
├─────────────────────────────────────────────────────────────────────────┤
│  • Metrics to console (structlog.dev.ConsoleRenderer)                  │
│  • Rate limiting disabled                                              │
│  • Aggressive logging (DEBUG level)                                    │
└─────────────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────────────┐
│  Staging                                                                │
├─────────────────────────────────────────────────────────────────────────┤
│  • Metrics to JSON logs (structlog.processors.JSONRenderer)            │
│  • Rate limiting enabled (conservative settings)                       │
│  • Load testing with backpressure validation                           │
│  • CloudWatch Logs ingestion setup                                     │
└─────────────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────────────┐
│  Production                                                             │
├─────────────────────────────────────────────────────────────────────────┤
│  ┌───────────────────────────────────────────────────────────────────┐ │
│  │  FastAPI Pods (Kubernetes / ECS)                                  │ │
│  │  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐  │ │
│  │  │ Worker 1        │  │ Worker 2        │  │ Worker 3        │  │ │
│  │  │ (rate limiter)  │  │ (rate limiter)  │  │ (rate limiter)  │  │ │
│  │  └────────┬────────┘  └────────┬────────┘  └────────┬────────┘  │ │
│  │           │                    │                    │            │ │
│  │           └────────────────────┴────────────────────┘            │ │
│  │                               │                                  │ │
│  │                               ▼                                  │ │
│  │                    logs/metrics.jsonl                            │ │
│  │                     (container logs)                             │ │
│  └───────────────────────────────────────────────────────────────────┘ │
│                                │                                       │
│                                ▼                                       │
│  ┌───────────────────────────────────────────────────────────────────┐ │
│  │  CloudWatch Logs / Grafana Loki                                   │ │
│  │  • Log aggregation from all pods                                  │ │
│  │  • Metric extraction via Insights queries                         │ │
│  │  • Alarms on error rate / latency                                 │ │
│  └───────────────────────────────────────────────────────────────────┘ │
│                                │                                       │
│                                ▼                                       │
│  ┌───────────────────────────────────────────────────────────────────┐ │
│  │  Grafana Dashboards                                               │ │
│  │  • Embedding p95 latency (target: < 200ms)                        │ │
│  │  • Error rate by provider (target: < 1%)                          │ │
│  │  • Batch size adaptation trends                                   │ │
│  │  • Token usage & truncation rate                                  │ │
│  └───────────────────────────────────────────────────────────────────┘ │
│                                │                                       │
│                                ▼                                       │
│  ┌───────────────────────────────────────────────────────────────────┐ │
│  │  Alerts (PagerDuty / Slack)                                       │ │
│  │  🔴 Critical: Error rate > 10% for 5 min                          │ │
│  │  🟡 Warning: P95 latency > 2 sec                                  │ │
│  └───────────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────────────┘
```

---

**Last Updated:** December 10, 2025
**Status:** Design Review
**Related:** `ARCHITECTURE_DESIGN.md`
