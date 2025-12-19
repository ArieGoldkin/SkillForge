---
name: llm-caching-patterns
description: Multi-level caching strategies for LLM applications - semantic caching (Redis), prompt caching (Claude native), cache hierarchies, and cost optimization for 70-95% cost reduction
version: 1.0.0
author: SkillForge AI Agent Hub
tags: [llm, caching, redis, cost-optimization, semantic-cache, prompt-cache, 2025]
---

# LLM Caching Patterns

## Overview

Modern LLM applications can reduce costs by 70-95% through intelligent multi-level caching. This skill covers the **double caching architecture** (2025 best practice): combining Redis semantic caching with provider-native prompt caching for maximum efficiency.

**When to use this skill:**
- High-volume LLM applications with repeated queries
- Cost-sensitive AI features
- Similar query patterns (e.g., analyzing similar content types)
- Applications requiring sub-second response times
- Multi-agent systems with redundant LLM calls

**Expected Impact:**
- **L1 (LRU) Cache**: 10-20% hit rate, ~1ms latency, 100% cost savings
- **L2 (Redis Semantic)**: 30-50% hit rate, ~5-10ms latency, 100% cost savings
- **L3 (Prompt Cache)**: 80-100% coverage, ~2s latency, 90% token cost savings
- **Combined**: 70-95% total cost reduction

## Core Concepts

### Double Caching Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    CACHE HIERARCHY (2025 BEST PRACTICE)         │
└─────────────────────────────────────────────────────────────────┘

Request → L1 (Exact Hash) → L2 (Semantic) → L3 (Prompt) → L4 (Full LLM)
           ↓ Hit: ~1ms      ↓ Hit: ~10ms     ↓ Cached     ↓ Full Cost
         100% savings      100% savings      90% savings   $$$

L1: In-Memory LRU Cache
────────────────────────
• Exact content hash matching
• 1,000-10,000 entry size
• TTL: 5-10 minutes
• Use Case: Duplicate requests within session
• Implementation: Python functools.lru_cache or cachetools

L2: Redis Semantic Cache
─────────────────────────
• Vector similarity search (cosine distance < 0.08)
• Configurable similarity threshold (0.85-0.95)
• TTL: 1-24 hours
• Use Case: Similar but not identical queries
• Implementation: RedisVL SemanticCache + RediSearch

L3: Prompt Caching (Provider Native)
────────────────────────────────────
• Cache identical prompt PREFIXES (system prompts, examples)
• Claude: cache_control ephemeral markers
• GPT: Cached prefix automatically detected
• TTL: 5 minutes (auto-refresh on use)
• Use Case: Same prompts, different user content
• March 2025: Cache reads don't count against rate limits!

L4: Full LLM Call
─────────────────
• No cache hit - full generation required
• Store response in L2 and L1 for future hits
• Full token cost
```

### Cache Decision Flow

```python
async def get_llm_response(query: str, agent_type: str) -> dict:
    """Multi-level cache lookup."""

    # L1: Exact match (in-memory)
    cache_key = hash_content(query)
    if cache_key in lru_cache:
        return lru_cache[cache_key]  # ~1ms, 100% savings

    # L2: Semantic similarity (Redis)
    embedding = await embed_text(query)
    similar = await redis_cache.find_similar(
        embedding=embedding,
        agent_type=agent_type,
        threshold=0.92  # Configurable
    )
    if similar and similar.distance < 0.08:
        lru_cache[cache_key] = similar.response  # Promote to L1
        return similar.response  # ~10ms, 100% savings

    # L3 + L4: Prompt caching + LLM call
    # Prompt cache breakpoints reduce L4 cost by 90%
    response = await llm.generate(
        messages=build_cached_messages(
            system_prompt=AGENT_PROMPT,  # ← Cached
            examples=few_shot_examples,   # ← Cached
            user_content=query            # ← NOT cached
        )
    )

    # Store in L2 and L1
    await redis_cache.set(embedding, response, agent_type)
    lru_cache[cache_key] = response

    return response  # L3: ~2s, 90% savings | L4: ~3s, full cost
```

### Similarity Threshold Tuning

**Problem**: How similar is "similar enough" to return a cached response?

**Threshold Guidelines** (cosine similarity):
- **0.98-1.00** (distance 0.00-0.02): Nearly identical - safe to return
- **0.95-0.98** (distance 0.02-0.05): Very similar - usually safe
- **0.92-0.95** (distance 0.05-0.08): Similar - validate with reranking
- **0.85-0.92** (distance 0.08-0.15): Moderately similar - risky
- **< 0.85** (distance > 0.15): Different - do not return

**Recommended Starting Point**: 0.92 (distance < 0.08)

**Tuning Process**:
1. Start at 0.92 threshold
2. Monitor false positives (wrong cached responses)
3. Monitor false negatives (cache misses that should've hit)
4. Adjust threshold based on precision/recall tradeoff
5. Different thresholds per agent type (security=0.95, general=0.90)

### Cache Warming Strategy

Pre-populate cache from golden dataset for instant hit rates:

```python
async def warm_cache_from_golden_dataset(
    cache: SemanticCache,
    min_quality: float = 0.8
) -> int:
    """Warm cache with high-quality historical responses."""

    # Load golden dataset analyses
    analyses = await db.query(
        "SELECT * FROM analyses WHERE confidence_score >= ?",
        (min_quality,)
    )

    warmed = 0
    for analysis in analyses:
        # Extract agent findings
        for finding in analysis.findings:
            await cache.set(
                content=analysis.content,
                response=finding.output,
                agent_type=finding.agent_type,
                quality_score=finding.confidence_score
            )
            warmed += 1

    return warmed
```

## Redis Semantic Cache Implementation

### Schema Design

```python
# RedisVL Index Schema
CACHE_INDEX_SCHEMA = {
    "index": {
        "name": "llm_semantic_cache",
        "prefix": "cache:",
    },
    "fields": [
        {"name": "agent_type", "type": "tag"},
        {"name": "content_type", "type": "tag"},
        {"name": "input_hash", "type": "tag"},
        {
            "name": "embedding",
            "type": "vector",
            "attrs": {
                "dims": 1536,  # OpenAI text-embedding-3-small
                "distance_metric": "cosine",
                "algorithm": "hnsw",  # Fast approximate search
            }
        },
        {"name": "response", "type": "text"},
        {"name": "created_at", "type": "numeric"},
        {"name": "hit_count", "type": "numeric"},
        {"name": "quality_score", "type": "numeric"},
    ]
}
```

### Service Class

```python
from redisvl.index import SearchIndex
from redisvl.query import VectorQuery
from redis import Redis

class SemanticCacheService:
    """Redis semantic cache for LLM responses."""

    def __init__(self, redis_url: str, similarity_threshold: float = 0.92):
        self.client = Redis.from_url(redis_url)
        self.threshold = similarity_threshold
        self.embedding_service = EmbeddingService()

        # Initialize RedisVL index
        schema = IndexSchema.from_dict(CACHE_INDEX_SCHEMA)
        self.index = SearchIndex(schema, self.client)
        self.index.create(overwrite=False)

    async def get(
        self,
        content: str,
        agent_type: str,
        content_type: str | None = None
    ) -> CacheEntry | None:
        """Look up cached response by semantic similarity."""

        # Generate embedding
        embedding = await self.embedding_service.embed_text(content[:2000])

        # Build query with filters
        filter_expr = f"@agent_type:{{{agent_type}}}"
        if content_type:
            filter_expr += f" @content_type:{{{content_type}}}"

        query = VectorQuery(
            vector=embedding,
            vector_field_name="embedding",
            return_fields=["response", "quality_score", "hit_count"],
            num_results=1,
            filter_expression=filter_expr
        )

        results = self.index.query(query)

        if results and len(results) > 0:
            result = results[0]
            distance = float(result.get("vector_distance", 1.0))

            # Check similarity threshold
            if distance <= (1 - self.threshold):
                # Increment hit count
                self.client.hincrby(result["id"], "hit_count", 1)

                return CacheEntry(
                    response=json.loads(result["response"]),
                    quality_score=float(result["quality_score"]),
                    hit_count=int(result["hit_count"]),
                    distance=distance
                )

        return None

    async def set(
        self,
        content: str,
        response: dict,
        agent_type: str,
        content_type: str | None = None,
        quality_score: float = 1.0
    ) -> None:
        """Store response in cache."""
        content_preview = content[:2000]
        embedding = await self.embedding_service.embed_text(content_preview)

        key = f"cache:{agent_type}:{hash_content(content_preview)}"

        data = {
            "agent_type": agent_type,
            "content_type": content_type or "",
            "input_hash": hash_content(content_preview),
            "embedding": embedding,
            "response": json.dumps(response),
            "created_at": time.time(),
            "hit_count": 0,
            "quality_score": quality_score,
        }

        self.client.hset(key, mapping=data)
        self.client.expire(key, ttl=86400)  # 24 hours
```

## Prompt Caching (Claude Native)

### Cache Breakpoint Strategy

```python
class PromptCacheManager:
    """Manage Claude prompt caching with cache breakpoints."""

    def build_cached_messages(
        self,
        system_prompt: str,
        few_shot_examples: str | None = None,
        schema_prompt: str | None = None,
        dynamic_content: str = ""
    ) -> list[dict]:
        """Build messages with cache breakpoints.

        Cache structure:
        1. System prompt (always cached)
        2. Few-shot examples (cached per content type)
        3. Schema documentation (always cached)
        ──────────────── CACHE BREAKPOINT ────────────────
        4. Dynamic content (NEVER cached)
        """

        content_parts = []

        # Breakpoint 1: System prompt
        content_parts.append({
            "type": "text",
            "text": system_prompt,
            "cache_control": {"type": "ephemeral"}
        })

        # Breakpoint 2: Few-shot examples (if provided)
        if few_shot_examples:
            content_parts.append({
                "type": "text",
                "text": few_shot_examples,
                "cache_control": {"type": "ephemeral"}
            })

        # Breakpoint 3: Schema documentation (if provided)
        if schema_prompt:
            content_parts.append({
                "type": "text",
                "text": schema_prompt,
                "cache_control": {"type": "ephemeral"}
            })

        # Dynamic content (NOT cached)
        content_parts.append({
            "type": "text",
            "text": dynamic_content
        })

        return [{"role": "user", "content": content_parts}]
```

### Cost Calculation

```
Without Prompt Caching:
─────────────────────────
System prompt:    2,000 tokens @ $3/MTok = $0.006
Few-shot examples: 5,000 tokens @ $3/MTok = $0.015
Schema docs:      1,000 tokens @ $3/MTok = $0.003
User content:    10,000 tokens @ $3/MTok = $0.030
────────────────────────────────────────
Total input:     18,000 tokens           = $0.054 per request

With Prompt Caching (90% hit rate):
───────────────────────────────────
Cached prefix:    8,000 tokens @ $0.30/MTok = $0.0024 (cache read)
User content:    10,000 tokens @ $3/MTok    = $0.0300
────────────────────────────────────────
Total:           18,000 tokens              = $0.0324 per request

Savings: 40% per request

With Semantic Cache (35% hit rate) + Prompt Cache:
──────────────────────────────────────────────────
35% requests: $0.00 (semantic cache hit)
65% requests: $0.0324 (prompt cache benefit)
Average: $0.021 per request

Total Savings: 61% vs no caching
```

## Optimization Techniques

### 1. LLM Reranking (Optional)

For higher precision, rerank top-k semantic cache candidates:

```python
async def get_with_reranking(
    query: str,
    agent_type: str,
    top_k: int = 3
) -> CacheEntry | None:
    """Retrieve with LLM reranking for better precision."""

    # Get top-k candidates
    candidates = await semantic_cache.get_topk(query, agent_type, k=top_k)

    if not candidates:
        return None

    # Use lightweight model to rerank
    rerank_prompt = f"""
    Query: {query}

    Rank these cached responses by relevance (1 = most relevant):
    {format_candidates(candidates)}
    """

    ranking = await lightweight_llm.rank(rerank_prompt)
    best_candidate = candidates[ranking[0]]

    if best_candidate.score > 0.8:  # Rerank threshold
        return best_candidate

    return None
```

### 2. Metadata Filtering

Filter before vector search to improve precision:

```python
# Good: Filter by agent_type + content_type
query = VectorQuery(
    vector=embedding,
    filter_expression="@agent_type:{security_auditor} @content_type:{article}"
)

# Better: Add difficulty level
query = VectorQuery(
    vector=embedding,
    filter_expression="""
        @agent_type:{security_auditor}
        @content_type:{article}
        @difficulty_level:{advanced}
    """
)
```

### 3. Quality-Based Eviction

Prioritize keeping high-quality responses:

```python
async def evict_low_quality_entries(cache: SemanticCache, max_size: int):
    """Evict low-quality entries when cache is full."""

    # Get all entries sorted by quality score
    entries = await cache.get_all_sorted_by_quality()

    if len(entries) > max_size:
        # Keep top N by quality, evict rest
        to_evict = entries[max_size:]
        for entry in to_evict:
            await cache.delete(entry.key)
```

### 4. Dynamic Threshold Adjustment

Adjust similarity threshold based on cache hit rate:

```python
class AdaptiveThresholdManager:
    """Dynamically adjust threshold based on metrics."""

    def __init__(self, target_hit_rate: float = 0.35):
        self.target = target_hit_rate
        self.threshold = 0.92

    async def adjust(self, actual_hit_rate: float):
        """Adjust threshold to reach target hit rate."""

        if actual_hit_rate < self.target - 0.05:
            # Too many misses, lower threshold (more permissive)
            self.threshold = max(0.85, self.threshold - 0.01)
        elif actual_hit_rate > self.target + 0.05:
            # Too many hits (possibly false positives), raise threshold
            self.threshold = min(0.98, self.threshold + 0.01)

        logger.info(f"Adjusted threshold to {self.threshold}")
```

## Monitoring & Observability

### Key Metrics

```python
@dataclass
class CacheMetrics:
    """Track cache performance."""

    # Hit rates
    l1_hit_rate: float
    l2_hit_rate: float
    l3_hit_rate: float
    combined_hit_rate: float

    # Latency
    l1_avg_latency_ms: float
    l2_avg_latency_ms: float
    l3_avg_latency_ms: float
    l4_avg_latency_ms: float

    # Cost
    estimated_cost_saved_usd: float
    total_requests: int

    # Quality
    false_positive_rate: float  # Wrong cached responses
    false_negative_rate: float  # Missed valid cache hits
```

### RedisInsight Dashboard

Access Redis cache visualization at `http://localhost:8001`:

- View cache entries
- Monitor vector similarity distributions
- Track hit/miss rates by agent type
- Analyze quality score distributions
- Identify hot keys

## References

- **Redis Blog**: [Prompt Caching vs Semantic Caching](https://redis.io/blog/prompt-caching-vs-semantic-caching/) (Dec 2025)
- **Redis Blog**: [10 Techniques for Semantic Cache Optimization](https://redis.io/blog/10-techniques-for-semantic-cache-optimization/)
- **RedisVL Docs**: [SemanticCache Guide](https://redis.io/docs/latest/develop/ai/redisvl/user_guide/llmcache/)
- **LangChain**: [RedisSemanticCache](https://python.langchain.com/api_reference/redis/cache/langchain_redis.cache.RedisSemanticCache.html)
- **Anthropic**: [Prompt Caching Guide](https://docs.anthropic.com/claude/docs/prompt-caching) (March 2025: cache reads free!)

## Integration Examples

See:
- `references/redis-setup.md` - Docker Compose + RedisVL setup
- `references/cache-hierarchy.md` - Multi-level cache implementation
- `references/cost-optimization.md` - ROI calculations and benchmarks
- `templates/semantic-cache-service.py` - Production-ready service
- `templates/prompt-cache-wrapper.py` - Claude caching wrapper
- `examples/skillforge-integration.md` - SkillForge specific patterns
