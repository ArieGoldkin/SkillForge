---
name: prometheus-metrics
description: Prometheus metrics - counters, gauges, histograms
version: 1.0.0
tags: [prometheus, metrics, monitoring, observability]
size: atomic
domain: devops
---

# Prometheus Metrics

## Metric Types

### Counter (Monotonic)

```python
from prometheus_client import Counter

http_requests = Counter(
    'http_requests_total',
    'Total HTTP requests',
    ['method', 'endpoint', 'status']
)

# Usage
http_requests.labels(method='GET', endpoint='/api/users', status=200).inc()
```

### Gauge (Up/Down)

```python
from prometheus_client import Gauge

active_connections = Gauge(
    'active_connections',
    'Active database connections'
)

active_connections.set(25)
active_connections.inc()
active_connections.dec()
```

### Histogram (Distribution)

```python
from prometheus_client import Histogram

request_duration = Histogram(
    'http_request_duration_seconds',
    'Request duration',
    ['method', 'endpoint'],
    buckets=[0.01, 0.05, 0.1, 0.5, 1, 2, 5, 10]
)

with request_duration.labels(method='GET', endpoint='/api').time():
    handle_request()
```

## RED Method

- **Rate**: `rate(http_requests_total[5m])`
- **Errors**: `rate(http_requests_total{status=~"5.."}[5m])`
- **Duration**: `histogram_quantile(0.95, rate(..._bucket[5m]))`

## Cardinality

```python
# ❌ BAD: Unbounded (millions of time series)
Counter('requests', ['user_id'])

# ✅ GOOD: Bounded (~10k series max)
Counter('requests', ['method', 'endpoint', 'status'])
```

**Rule**: Never use unbounded labels (user_id, request_id)

## PromQL Queries

```promql
# Error rate %
sum(rate(http_requests_total{status=~"5.."}[5m])) /
sum(rate(http_requests_total[5m])) * 100

# p95 latency
histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m]))

# Cost per day
sum(increase(llm_cost_dollars_total[1d])) by (model)
```
