---
name: llm-caching
description: Complete LLM caching composite - semantic, prompt, observability
version: 1.0.0
type: composite
includes:
  - ai-llm/caching-hierarchy
  - ai-llm/caching-semantic
  - ai-llm/caching-prompt
  - ai-llm/caching-observability
tags: [llm, caching, cost-optimization, composite]
---

# LLM Caching Composite

Complete multi-level caching for 70-95% cost reduction.

## Included Skills

| Skill | Purpose |
|-------|---------|
| caching-hierarchy | L1/L2/L3/L4 architecture, decision flow |
| caching-semantic | Redis vector cache implementation |
| caching-prompt | Claude native prompt caching |
| caching-observability | Langfuse cost tracking, metrics |

## Quick Start

```bash
# Dependencies
pip install redisvl langfuse anthropic

# Start Redis Stack
docker run -d -p 6379:6379 -p 8001:8001 redis/redis-stack:latest
```

## Cache Flow

```
Request → L1 (LRU) → L2 (Redis) → L3 (Prompt) → L4 (LLM)
           ~1ms       ~10ms        ~2s          ~3s
          100%        100%         90%          $$$
```

## Implementation Checklist

### L1: In-Memory LRU
- [ ] `functools.lru_cache` or `cachetools.LRUCache`
- [ ] Size: 1,000-10,000 entries
- [ ] TTL: 5-10 minutes

### L2: Redis Semantic
- [ ] RedisVL index with embeddings
- [ ] Similarity threshold: 0.92
- [ ] TTL: 24 hours
- [ ] Metadata filtering by agent_type

### L3: Prompt Cache
- [ ] Cache breakpoints in system prompt
- [ ] Few-shot examples cached
- [ ] Schema documentation cached
- [ ] User content NOT cached

### Observability
- [ ] Langfuse `@observe` decorators
- [ ] Cost tracking per agent
- [ ] Cache hit rate monitoring
- [ ] Parent trace linking for rollup

## Expected Results

| Metric | Target |
|--------|--------|
| L1 Hit Rate | 10-20% |
| L2 Hit Rate | 30-50% |
| L3 Coverage | 80-100% |
| Total Savings | 70-95% |

## Usage Pattern

```python
async def get_response(query: str, agent: str) -> str:
    # L1: Exact match
    if (cached := lru_cache.get(hash(query))):
        return cached

    # L2: Semantic similarity
    if (similar := await redis_cache.get(query, agent)):
        lru_cache[hash(query)] = similar
        return similar

    # L3/L4: Prompt cache + LLM
    response = await llm.generate(
        build_cached_messages(query)
    )

    # Store for next time
    await redis_cache.set(query, response, agent)
    lru_cache[hash(query)] = response

    return response
```

## Dashboards

- **Redis**: `http://localhost:8001` (RedisInsight)
- **Langfuse**: `http://localhost:3000` (Cost/Traces)
