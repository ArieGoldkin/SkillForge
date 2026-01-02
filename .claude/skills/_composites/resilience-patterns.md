---
name: resilience-patterns
description: Fault tolerance with circuit breakers, bulkheads, and retries
version: 1.0.0
tags: [resilience, fault-tolerance, circuit-breaker, retry]
size: composite
atomics:
  - devops/circuit-breaker
  - devops/bulkhead
  - devops/retry-strategies
  - devops/llm-resilience
---

# Resilience Patterns Composite

Production-grade fault tolerance for distributed systems.

## When to Use

- Building fault-tolerant multi-agent systems
- Implementing LLM API integrations
- Protecting against cascade failures
- Adding graceful degradation

## Atomic Skills

### 1. Circuit Breaker (`circuit-breaker`)
States (closed/open/half-open), failure thresholds.

### 2. Bulkhead (`bulkhead`)
Isolation tiers, resource partitioning.

### 3. Retry Strategies (`retry-strategies`)
Exponential backoff, jitter, error classification.

### 4. LLM Resilience (`llm-resilience`)
Fallback chains, token budgets, cost control.

## Quick Reference

```
┌─────────────────────────────────────────────────────────────┐
│  RESILIENCE PATTERN SELECTION                               │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  External service calls? ──► Circuit Breaker                │
│  Multi-tenant/multi-agent? ──► Bulkhead                     │
│  Transient failures? ──► Retry + Backoff                    │
│  LLM calls? ──► Fallback Chain + Token Budget               │
│                                                             │
│  INTEGRATION POINTS:                                        │
│  - Workflow agents: Circuit breaker + Bulkhead tier         │
│  - LLM calls: Fallback chain + Retry logic                  │
│  - External APIs: Circuit breaker + Rate limiting           │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

## Load Order

1. `circuit-breaker` - Cascade failure prevention
2. `bulkhead` - Isolation tiers
3. `retry-strategies` - Automatic recovery
4. `llm-resilience` - LLM-specific patterns
