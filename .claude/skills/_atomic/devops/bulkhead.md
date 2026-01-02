---
name: bulkhead
description: Bulkhead pattern for failure isolation
version: 1.0.0
tags: [resilience, bulkhead, isolation, fault-tolerance]
size: atomic
domain: devops
---

# Bulkhead Pattern

## Concept

Isolate failures by partitioning resources into independent pools.

```
┌────────────────┐  ┌────────────────┐
│ TIER 1: Critical│  │ TIER 2: Standard│
│  (5 workers)   │  │  (3 workers)   │
│  ┌─┐ ┌─┐ ┌─┐   │  │  ┌─┐ ┌─┐ ┌─┐  │
│  │█│ │█│ │░│   │  │  │█│ │░│ │░│  │
│  └─┘ └─┘ └─┘   │  │  └─┘ └─┘ └─┘  │
└────────────────┘  └────────────────┘

█ = Active    ░ = Available
```

## Implementation

```python
import asyncio

class Bulkhead:
    def __init__(self, name: str, max_concurrent: int, max_queue: int):
        self.name = name
        self.semaphore = asyncio.Semaphore(max_concurrent)
        self.queue_semaphore = asyncio.Semaphore(max_queue)

    async def execute(self, func, *args, **kwargs):
        if not self.queue_semaphore.locked():
            async with self.queue_semaphore:
                async with self.semaphore:
                    return await func(*args, **kwargs)
        raise BulkheadFullError(f"{self.name} bulkhead full")
```

## Tier Configuration

| Tier | Workers | Queue | Timeout | Use Case |
|------|---------|-------|---------|----------|
| Critical | 5 | 10 | 300s | Synthesis, quality gate |
| Standard | 3 | 5 | 120s | Analysis agents |
| Optional | 2 | 3 | 60s | Enrichment, caching |

## Usage

```python
# Define tiers
critical = Bulkhead("critical", max_concurrent=5, max_queue=10)
standard = Bulkhead("standard", max_concurrent=3, max_queue=5)

# Route by priority
async def run_agent(agent_name: str, task):
    bulkhead = critical if agent_name == "synthesis" else standard

    try:
        return await bulkhead.execute(agent.run, task)
    except BulkheadFullError:
        return await fallback_response()
```

## Benefits

- Tier 3 overload doesn't affect Tier 1
- Critical operations always have capacity
- Graceful degradation of optional features
