---
name: caching-hierarchy
description: Multi-level LLM cache hierarchy and decision flow
version: 1.0.0
tags: [llm, caching, architecture]
size: atomic
domain: ai-llm
---

# LLM Cache Hierarchy

## Four-Level Architecture

```
Request → L1 (Exact) → L2 (Semantic) → L3 (Prompt) → L4 (Full LLM)
           ~1ms         ~10ms          ~2s           ~3s
          100%          100%           90%           $$$
```

### L1: In-Memory LRU Cache

- **Match**: Exact content hash
- **Size**: 1,000-10,000 entries
- **TTL**: 5-10 minutes
- **Use**: Duplicate requests in session
- **Savings**: 100% (no API call)

### L2: Redis Semantic Cache

- **Match**: Vector similarity (cosine < 0.08)
- **Size**: 100,000+ entries
- **TTL**: 1-24 hours
- **Use**: Similar but not identical queries
- **Savings**: 100% (no API call)

### L3: Prompt Caching (Claude/GPT native)

- **Match**: Identical prompt prefixes
- **TTL**: 5 minutes (auto-refresh)
- **Use**: Same prompts, different user content
- **Savings**: 90% token cost reduction

### L4: Full LLM Call

- **Match**: None (cache miss)
- **Use**: Novel queries
- **Savings**: None (full cost)

## Decision Flow

```python
async def get_llm_response(query: str, agent_type: str) -> dict:
    # L1: Exact match
    cache_key = hash_content(query)
    if cache_key in lru_cache:
        return lru_cache[cache_key]

    # L2: Semantic similarity
    embedding = await embed_text(query)
    similar = await redis_cache.find_similar(
        embedding=embedding,
        agent_type=agent_type,
        threshold=0.92
    )
    if similar and similar.distance < 0.08:
        lru_cache[cache_key] = similar.response  # Promote to L1
        return similar.response

    # L3 + L4: Prompt cache + LLM call
    response = await llm.generate(
        messages=build_cached_messages(query)
    )

    # Store in L2 and L1
    await redis_cache.set(embedding, response, agent_type)
    lru_cache[cache_key] = response

    return response
```

## Expected Impact

| Layer | Hit Rate | Latency | Cost Savings |
|-------|----------|---------|--------------|
| L1 | 10-20% | ~1ms | 100% |
| L2 | 30-50% | ~10ms | 100% |
| L3 | 80-100% | ~2s | 90% |
| Combined | - | - | 70-95% |

## Similarity Thresholds

| Threshold | Distance | Safety |
|-----------|----------|--------|
| 0.98-1.00 | 0.00-0.02 | Safe to return |
| 0.95-0.98 | 0.02-0.05 | Usually safe |
| 0.92-0.95 | 0.05-0.08 | Validate |
| 0.85-0.92 | 0.08-0.15 | Risky |
| < 0.85 | > 0.15 | Do not return |

**Starting point**: 0.92 (distance < 0.08)

## Local Model Considerations

With Ollama, caching calculus changes:

| Provider | Caching Value | Reason |
|----------|--------------|--------|
| Cloud APIs | **Critical** | $3-15 per MTok |
| Ollama Local | **Optional** | FREE per token |

For local models, L1 only is usually sufficient.
