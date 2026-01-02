---
name: observability
description: Complete observability with logs, metrics, traces, and alerts
version: 1.0.0
tags: [observability, logging, metrics, tracing, alerting]
size: composite
atomics:
  - devops/structured-logging
  - devops/prometheus-metrics
  - devops/distributed-tracing
  - devops/alerting-strategy
---

# Observability Composite

Three pillars of observability: logs, metrics, traces.

## When to Use

- Setting up application monitoring
- Implementing structured logging
- Adding metrics and dashboards
- Configuring distributed tracing
- Creating alerting rules

## Atomic Skills

### 1. Structured Logging (`structured-logging`)
JSON logs, correlation IDs, log sampling.

### 2. Prometheus Metrics (`prometheus-metrics`)
Counters, gauges, histograms, PromQL.

### 3. Distributed Tracing (`distributed-tracing`)
OpenTelemetry, spans, sampling strategies.

### 4. Alerting Strategy (`alerting-strategy`)
Severity levels, grouping, inhibition, runbooks.

## Quick Reference

```
┌─────────────────────────────────────────────────────────────┐
│  THREE PILLARS OF OBSERVABILITY                             │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│     LOGS           METRICS          TRACES                  │
│  ──────────     ──────────       ──────────                 │
│  What happened  How system       How requests               │
│  at specific    performs         flow through               │
│  point in time  over time        services                   │
│                                                             │
│  Use JSON       RED method       OpenTelemetry              │
│  Correlation ID Rate/Error/      Parent-child               │
│  Log sampling   Duration         spans                      │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

## Load Order

1. `structured-logging` - Foundation
2. `prometheus-metrics` - Performance data
3. `distributed-tracing` - Request flows
4. `alerting-strategy` - Incident response
