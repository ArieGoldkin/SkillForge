# Issue #601: Query Decomposition Caching Architecture

**Date:** 2025-12-29
**Author:** Backend System Architect
**Status:** Design Complete - Ready for Implementation

---

## Executive Summary

Query decomposition adds **~100-200ms latency** per search request via LLM-based concept extraction. This document provides a comprehensive caching strategy leveraging SkillForge's **existing 2-tier cache infrastructure** (L1 in-memory + L2 Redis semantic cache) to minimize latency impact while maximizing cache hit rates.

### Key Recommendations

| Aspect | Recommendation | Rationale |
|--------|---------------|-----------|
| **Cache Storage** | **Hybrid: L1 TTLCache (1000 entries) + L2 Redis Semantic Cache** | Leverages existing infrastructure, 50-70% combined hit rate |
| **Cache Key** | **Normalized query text** (lowercase, whitespace-collapsed) | Balances exactness with flexibility |
| **Semantic Matching** | **L2 Redis with 0.92 similarity threshold** | Catches paraphrases/synonyms without false positives |
| **TTL** | **L1: 5 minutes, L2: 24 hours** | Frequent queries stay hot, infrequent expire gracefully |
| **Invalidation** | **Passive TTL expiration only** | No concept drift detected, simpler architecture |

### Expected Impact

```
Before Caching:
  - P50 latency: ~150ms (LLM decomposition)
  - P95 latency: ~250ms (slow LLM responses)
  - Cost: $0.0005 per query (gpt-4o-mini @ $0.15/$0.60 per 1M tokens)

After Caching (50-70% hit rate):
  - P50 latency: ~15ms (L1: <1ms, L2: ~10ms, miss: 150ms)
  - P95 latency: ~80ms (weighted avg with cache hits)
  - Cost: $0.00015-0.00025 per query (50-85% reduction)
  - Cache hit rate: 30-50% (L1), 20-40% (L2), 50-70% (combined)
```

---

## 1. Problem Analysis

### 1.1 Latency Characteristics

Query decomposition requires an LLM call to extract 2-4 concepts from multi-concept queries:

```
Original Query: "How do chunking strategies affect reranking performance in RAG?"
                     ↓
         LLM Decomposer (gpt-4o-mini)
                     ↓
         ~100-200ms latency
                     ↓
Concepts: ["chunking strategies", "reranking performance", "RAG architecture"]
```

**Latency Breakdown:**
- **Network RTT**: 20-40ms (US-West → OpenAI API)
- **LLM Processing**: 60-120ms (gpt-4o-mini, 50 tokens input, ~30 tokens output)
- **JSON Parsing**: 1-5ms (Pydantic validation)
- **Total P50**: ~100-150ms
- **Total P95**: ~200-300ms (slow network, cold model)

### 1.2 Query Characteristics

Analysis of query patterns in SkillForge's retrieval evaluation dataset:

| Query Type | Frequency | Example | Cacheable? |
|------------|-----------|---------|------------|
| **Multi-concept** | 74% (40/55) | "How does X affect Y in Z?" | **High** - Repeated patterns |
| **Single-concept** | 26% (15/55) | "What is semantic chunking?" | **Medium** - Unique variations |
| **Paraphrases** | ~15% | "chunking strategies" ≈ "chunking methods" | **High** - Semantic matching |
| **Identical** | ~30% | Exact duplicates from repeated tests | **Perfect** - Exact match |

**Key Insight:** 30% exact duplicates + 15% semantic equivalents = **45% baseline cache hit rate** without optimization.

---

## 2. Cache Architecture Design

### 2.1 Recommended: Hybrid L1 + L2 Strategy

Leverage SkillForge's **existing 2-tier LLM cache infrastructure** (already deployed for agent caching):

```
┌─────────────────────────────────────────────────────────────────────────┐
│                  QUERY DECOMPOSITION CACHE ARCHITECTURE                 │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  User Query                                                             │
│       ↓                                                                 │
│  ┌─────────────────────────────────────────────────────────┐           │
│  │ 1. Normalize Query                                      │           │
│  │    - Lowercase                                          │           │
│  │    - Collapse whitespace                                │           │
│  │    - Trim                                               │           │
│  └────────────────────┬────────────────────────────────────┘           │
│                       ↓                                                 │
│  ┌─────────────────────────────────────────────────────────┐           │
│  │ 2. L1 Cache Lookup (In-Memory TTLCache)                │           │
│  │    - Key: SHA256(normalized_query)                     │           │
│  │    - Size: 1000 entries                                │           │
│  │    - TTL: 5 minutes                                    │           │
│  │    - Latency: <1ms                                     │           │
│  └────────┬───────────────────────────┬────────────────────┘           │
│           │ HIT (30-50%)              │ MISS                           │
│           ↓                           ↓                                │
│  ┌──────────────────┐  ┌─────────────────────────────────┐            │
│  │ Return Cached    │  │ 3. L2 Cache Lookup (Redis)     │            │
│  │ Decomposition    │  │    - Semantic similarity       │            │
│  └──────────────────┘  │    - Threshold: 0.92           │            │
│                        │    - TTL: 24 hours             │            │
│                        │    - Latency: ~10ms            │            │
│                        └─────┬──────────────┬────────────┘            │
│                              │ HIT (20-40%) │ MISS                    │
│                              ↓              ↓                         │
│                     ┌────────────────┐  ┌──────────────────────┐     │
│                     │ Update L1      │  │ 4. LLM Decomposition │     │
│                     │ Return Result  │  │    - gpt-4o-mini     │     │
│                     └────────────────┘  │    - ~150ms          │     │
│                                         └──────┬───────────────┘     │
│                                                ↓                      │
│                                         ┌──────────────────────┐     │
│                                         │ 5. Store in L1 + L2  │     │
│                                         │    - Async write     │     │
│                                         │    - No blocking     │     │
│                                         └──────────────────────┘     │
│                                                                       │
└───────────────────────────────────────────────────────────────────────┘
```

### 2.2 Cache Key Strategy

**Chosen: Normalized Query Text**

```python
def generate_cache_key(query: str) -> str:
    """Generate cache key from normalized query.

    Normalization:
        - Lowercase (handles case variations)
        - Collapse multiple spaces to single space
        - Strip leading/trailing whitespace
        - SHA256 hash for consistent key length

    Examples:
        "How does chunking affect RAG?"
        "how does chunking affect RAG?"     → Same key (case)
        "How  does  chunking  affect RAG?"  → Same key (whitespace)
        "RAG chunking effects?"             → Different key (word order matters)
    """
    normalized = " ".join(query.strip().lower().split())
    return hashlib.sha256(normalized.encode()).hexdigest()
```

**Why Not Other Strategies?**

| Strategy | Pros | Cons | Decision |
|----------|------|------|----------|
| **Exact query match** | Simple, no false positives | Misses case/whitespace variants (~10% hit rate loss) | ❌ Too strict |
| **Embedding-based** | Catches paraphrases | Slower (embedding generation ~50ms), overkill for L1 | ✅ Use for L2 only |
| **N-gram fingerprint** | Handles typos | Complex, false positives | ❌ Unnecessary complexity |
| **Normalized + hash** | Fast, handles common variations | Misses true synonyms | ✅ **Chosen for L1** |

### 2.3 Semantic Matching (L2 Cache)

**Redis Semantic Cache Configuration:**

```python
# Uses existing RedisSemanticCache from app.shared.services.cache
# Configuration in app/core/config.py:

REDIS_SEMANTIC_CACHE_TTL: int = 86400  # 24 hours
REDIS_SIMILARITY_THRESHOLD: float = 0.08  # ~92% similarity
```

**Similarity Threshold Calibration:**

| Threshold | Example Matches | False Positive Risk | Hit Rate |
|-----------|----------------|---------------------|----------|
| **0.92** (0.08 dist) | "chunking strategies" ≈ "chunking methods" | **Low** (~2%) | **Medium** (~20%) |
| 0.85 (0.15 dist) | "RAG pipeline" ≈ "retrieval augmented generation" | Medium (~5%) | High (~35%) |
| 0.95 (0.05 dist) | Only near-duplicates | Very Low (~0.5%) | Low (~10%) |

**Chosen:** **0.92** (0.08 distance) - Balances semantic flexibility with precision.

### 2.4 TTL Strategy

**Recommendations:**

| Cache Tier | TTL | Rationale |
|------------|-----|-----------|
| **L1 (In-Memory)** | **5 minutes** | Short-term repetition (user refining search query) |
| **L2 (Redis Semantic)** | **24 hours** | Long-term patterns, low storage cost (~1KB per entry) |

**Why 5 minutes for L1?**
- User search sessions typically last 2-10 minutes
- Captures query refinement iterations ("chunking" → "chunking strategies" → "chunking vs paragraph splitting")
- Prevents stale cache from consuming memory indefinitely

**Why 24 hours for L2?**
- Query patterns are stable (e.g., "best RAG practices" doesn't change meaning weekly)
- Low storage cost: 1000 cached queries × 1KB = **1MB Redis memory**
- Allows distributed cache sharing across multiple backend instances

---

## 3. Implementation Plan

### 3.1 File Structure

```
backend/app/shared/services/search/
├── query_decomposition/
│   ├── __init__.py
│   ├── cache.py              # NEW - QueryDecompositionCache wrapper
│   ├── analyzer.py           # NEW - Query analyzer with caching
│   └── schemas.py            # NEW - QueryAnalysis, CacheStats schemas
├── search_service.py         # MODIFIED - Integrate cached decomposition
└── tests/
    └── query_decomposition/
        ├── test_cache.py     # NEW - Cache unit tests
        └── test_analyzer.py  # NEW - Analyzer integration tests
```

### 3.2 Core Components

#### 3.2.1 QueryDecompositionCache

```python
# backend/app/shared/services/search/query_decomposition/cache.py

"""Query decomposition caching with 2-tier hybrid strategy.

Wraps existing LLMCacheService to provide query-specific caching:
- L1: In-memory TTLCache for instant lookups (<1ms)
- L2: Redis semantic cache for cross-instance sharing (~10ms)
"""

import hashlib
from typing import Optional

from app.shared.services.cache.llm_cache_service import get_llm_cache, CacheResult
from app.core.logging import get_logger

from .schemas import QueryAnalysis

logger = get_logger(__name__)


class QueryDecompositionCache:
    """Cache for query decomposition results.

    Leverages existing 2-tier LLM cache infrastructure with
    query-specific key generation and normalization.
    """

    def __init__(self) -> None:
        """Initialize cache with existing LLM cache service."""
        self._cache = get_llm_cache()
        self._cache_hits = 0
        self._cache_misses = 0

    def _normalize_query(self, query: str) -> str:
        """Normalize query for consistent cache keys.

        Handles:
            - Case insensitivity (lowercase)
            - Whitespace normalization (collapse multiple spaces)
            - Trim leading/trailing whitespace

        Examples:
            >>> cache._normalize_query("How does  CHUNKING  affect RAG?")
            "how does chunking affect rag?"
        """
        return " ".join(query.strip().lower().split())

    def _generate_cache_key(self, query: str) -> str:
        """Generate cache key from normalized query.

        Uses SHA256 hash to ensure consistent key length regardless
        of query size (important for L1 cache key comparison).

        Args:
            query: Original search query

        Returns:
            SHA256 hex digest of normalized query
        """
        normalized = self._normalize_query(query)
        return hashlib.sha256(normalized.encode()).hexdigest()

    async def get(self, query: str) -> Optional[QueryAnalysis]:
        """Retrieve cached decomposition result.

        Checks L1 (in-memory) first, then L2 (Redis semantic) on miss.

        Args:
            query: Search query to check cache for

        Returns:
            Cached QueryAnalysis if found, None otherwise

        Performance:
            - L1 hit: <1ms
            - L2 hit: ~10ms
            - Miss: None (no blocking)
        """
        cache_key = self._generate_cache_key(query)

        # L1/L2 lookup via existing LLMCacheService
        result: Optional[CacheResult] = await self._cache.get(
            agent_type="query_decomposition",
            content=query,
            prompt="",  # Not used for decomposition (query is content)
        )

        if result:
            self._cache_hits += 1
            logger.info(
                "query_decomposition_cache_hit",
                cache_level=result.cache_level,
                similarity_score=result.similarity_score,
                query=query[:50],
            )
            # Deserialize from cached JSON string
            import json
            data = json.loads(result.response)
            return QueryAnalysis(**data)

        self._cache_misses += 1
        logger.debug("query_decomposition_cache_miss", query=query[:50])
        return None

    async def set(self, query: str, analysis: QueryAnalysis) -> None:
        """Store decomposition result in cache.

        Writes to both L1 (in-memory) and L2 (Redis) asynchronously.
        Failures are logged but do not raise exceptions.

        Args:
            query: Original search query
            analysis: Decomposition result to cache
        """
        cache_key = self._generate_cache_key(query)

        # Serialize QueryAnalysis to JSON
        import json
        serialized = json.dumps(analysis.model_dump())

        # Store via existing LLMCacheService
        await self._cache.set(
            agent_type="query_decomposition",
            content=query,
            prompt="",
            response=serialized,
        )

        logger.debug(
            "query_decomposition_cached",
            query=query[:50],
            is_multi_concept=analysis.is_multi_concept,
            concept_count=len(analysis.concepts),
        )

    def get_stats(self) -> dict:
        """Return cache statistics for monitoring.

        Returns:
            Dict with cache_hits, cache_misses, hit_rate
        """
        total = self._cache_hits + self._cache_misses
        hit_rate = self._cache_hits / total if total > 0 else 0.0

        return {
            "cache_hits": self._cache_hits,
            "cache_misses": self._cache_misses,
            "hit_rate": hit_rate,
            "l1_stats": self._cache.get_stats().model_dump(),
        }
```

#### 3.2.2 Integration in QueryAnalyzer

```python
# backend/app/shared/services/search/query_decomposition/analyzer.py

"""Query analyzer with LLM-based decomposition and caching."""

from typing import Optional

from app.core.logging import get_logger
from app.shared.services.llm.factory import get_llm_provider

from .cache import QueryDecompositionCache
from .schemas import QueryAnalysis

logger = get_logger(__name__)


class QueryAnalyzer:
    """Analyze queries with LLM decomposition and caching.

    Determines if query requires multi-concept retrieval and
    extracts independent concepts using LLM with 2-tier caching.
    """

    def __init__(self, enable_cache: bool = True) -> None:
        """Initialize analyzer with optional caching.

        Args:
            enable_cache: Enable L1+L2 caching (default: True)
        """
        self._cache = QueryDecompositionCache() if enable_cache else None
        self._llm = None  # Lazy initialization

    async def analyze_query(self, query: str) -> QueryAnalysis:
        """Analyze query with caching.

        Flow:
            1. Check cache (L1 → L2)
            2. On miss: Fast heuristic check
            3. If heuristic indicates multi-concept: LLM decomposition
            4. Store result in cache

        Args:
            query: Search query to analyze

        Returns:
            QueryAnalysis with is_multi_concept, concepts, query_type

        Performance:
            - Cache hit: <10ms (L1: <1ms, L2: ~10ms)
            - Heuristic path: ~5ms
            - LLM path: ~150ms (first time only)
        """
        # 1. Cache lookup
        if self._cache:
            cached = await self._cache.get(query)
            if cached:
                return cached

        # 2. Fast heuristic check
        if not self._has_multi_concept_signals(query):
            result = QueryAnalysis(
                is_multi_concept=False,
                concepts=[query],
                query_type="single",
            )
            if self._cache:
                await self._cache.set(query, result)
            return result

        # 3. LLM decomposition
        result = await self._llm_decompose(query)

        # 4. Cache result
        if self._cache:
            await self._cache.set(query, result)

        return result

    def _has_multi_concept_signals(self, query: str) -> bool:
        """Fast heuristic check for multi-concept queries.

        Looks for signal words: "and", "with", "for", "in",
        "how does", "relationship between", "affect", "compare".

        Returns:
            True if query likely has multiple concepts
        """
        query_lower = query.lower()
        signals = [
            " and ", " with ", " for ", " in ",
            "how does", "relationship between",
            "affect", "compare", "combine", "versus",
        ]
        return any(signal in query_lower for signal in signals)

    async def _llm_decompose(self, query: str) -> QueryAnalysis:
        """Decompose query using LLM.

        Uses gpt-4o-mini with structured output for 2-4 concepts.

        Args:
            query: Query to decompose

        Returns:
            QueryAnalysis with extracted concepts
        """
        if self._llm is None:
            self._llm = get_llm_provider(purpose="fast")  # gpt-4o-mini

        # LLM call with structured output
        response = await self._llm.ainvoke(
            [
                {
                    "role": "system",
                    "content": (
                        "Extract 2-4 independent concepts from the query. "
                        "Return JSON: {\"concepts\": [\"concept1\", \"concept2\"]}"
                    ),
                },
                {
                    "role": "user",
                    "content": f"Query: {query}\\nExtract key concepts.",
                },
            ],
            response_format={"type": "json_object"},
        )

        import json
        data = json.loads(response.content)
        concepts = data.get("concepts", [query])

        return QueryAnalysis(
            is_multi_concept=len(concepts) > 1,
            concepts=concepts,
            query_type="multi" if len(concepts) > 1 else "single",
        )
```

### 3.3 Configuration

Add to `backend/app/core/config.py`:

```python
# Query Decomposition Caching (Issue #601)
QUERY_DECOMPOSITION_CACHE_ENABLED: bool = Field(
    default=True,
    description=(
        "Enable caching for query decomposition results. "
        "Uses existing 2-tier LLM cache (L1 in-memory + L2 Redis). "
        "Reduces latency from ~150ms to <10ms for repeated/similar queries."
    ),
)
```

### 3.4 Metrics & Observability

Add metrics to `MetricsService`:

```python
# In app/shared/services/metrics/service.py

def record_query_decomposition(
    self,
    cache_hit: bool,
    cache_level: Optional[str],  # "l1", "l2", or None
    latency_ms: float,
    is_multi_concept: bool,
    concept_count: int,
) -> None:
    """Record query decomposition metrics.

    Tracks:
        - Cache hit rate by level (L1/L2)
        - Latency distribution (cache vs LLM)
        - Multi-concept query rate
        - Concept extraction counts
    """
    self._increment_counter("query_decomposition.total")

    if cache_hit:
        self._increment_counter(f"query_decomposition.cache_hit.{cache_level}")
    else:
        self._increment_counter("query_decomposition.cache_miss")

    self._record_histogram("query_decomposition.latency_ms", latency_ms)

    if is_multi_concept:
        self._increment_counter("query_decomposition.multi_concept")
        self._record_histogram("query_decomposition.concepts_extracted", concept_count)
```

---

## 4. Performance Analysis

### 4.1 Expected Latency Distribution

**Assumptions:**
- L1 hit rate: 30-50% (recent identical queries)
- L2 hit rate: 20-40% (semantic equivalents)
- Combined hit rate: 50-70%
- LLM latency: 100-200ms (gpt-4o-mini)

**Weighted Average Latency:**

```
P50 = (0.40 × 0.5ms) + (0.30 × 10ms) + (0.30 × 150ms)
    = 0.2ms + 3ms + 45ms
    = 48.2ms ≈ 50ms

P95 = (0.30 × 1ms) + (0.20 × 15ms) + (0.50 × 250ms)
    = 0.3ms + 3ms + 125ms
    = 128.3ms ≈ 130ms

Before caching: P50=150ms, P95=250ms
After caching:  P50=50ms, P95=130ms
Improvement:    67% faster (P50), 48% faster (P95)
```

### 4.2 Cache Size Estimation

**L1 (In-Memory):**
- Max size: 1000 entries (configurable via `LLM_CACHE_L1_SIZE`)
- Entry size: ~500 bytes (query + analysis)
- Total memory: **500KB per backend instance**

**L2 (Redis):**
- Steady state: ~5,000-10,000 unique queries (24-hour window)
- Entry size: ~1KB (query + embedding + analysis)
- Total memory: **5-10MB Redis** (negligible)

### 4.3 Cost Savings

**Without Caching:**
- Query decomposition: 50 input tokens, 30 output tokens
- Model: gpt-4o-mini ($0.15/$0.60 per 1M tokens)
- Cost per query: (50 × $0.15 + 30 × $0.60) / 1M = **$0.000026**
- 10,000 queries/day: **$0.26/day = $7.80/month**

**With 60% Cache Hit Rate:**
- Cached queries: 6,000/day (no cost)
- LLM queries: 4,000/day
- Cost: 4,000 × $0.000026 = **$0.104/day = $3.12/month**
- **Savings: $4.68/month (60% reduction)**

**Note:** Low absolute cost, but scales with query volume. At 100K queries/day: **$780/mo → $312/mo = $468/mo savings**.

---

## 5. Invalidation Strategy

### 5.1 Recommendation: Passive TTL Expiration

**No Active Invalidation Required** - Queries are stateless and decomposition logic is deterministic.

**Rationale:**
- Query concepts don't "change" over time (unlike dynamic content)
- LLM model updates are rare (weeks/months), can tolerate stale cache
- Passive TTL (5min L1, 24hr L2) provides sufficient freshness

### 5.2 When to Invalidate (Future Consideration)

If decomposition logic changes (e.g., new LLM model, updated prompt):

```python
# Option A: Version-based keys
def _generate_cache_key(self, query: str) -> str:
    version = "v1"  # Increment on logic change
    normalized = self._normalize_query(query)
    return hashlib.sha256(f"{version}:{normalized}".encode()).hexdigest()

# Option B: Manual flush
async def flush_cache(self) -> None:
    """Clear all query decomposition cache entries."""
    await self._cache.clear(agent_type="query_decomposition")
```

**Current Decision:** Start with passive TTL, add versioning if needed.

---

## 6. Alternative Approaches (Not Recommended)

### 6.1 Redis Only (No L1)

**Pros:**
- Simpler architecture (single cache tier)
- Shared state across all backend instances

**Cons:**
- Higher latency (~10ms vs <1ms for L1 hits)
- Network dependency for every cache lookup
- Loses 30-50% of cache hits (L1 hit rate)

**Decision:** ❌ Not recommended - L1 provides massive latency win for identical queries.

### 6.2 PostgreSQL Cache Table

**Pros:**
- Persistent, survives Redis restarts
- No additional infrastructure

**Cons:**
- Slower than Redis (~20-50ms vs ~10ms)
- Requires database connection for every cache lookup
- Adds unnecessary load to primary database

**Decision:** ❌ Not recommended - Redis is already deployed and optimized for caching.

### 6.3 Embedding-Based Keys (No Normalization)

**Pros:**
- Maximum semantic flexibility
- Catches all paraphrases

**Cons:**
- Requires embedding generation for every cache lookup (~50ms)
- Defeats purpose of caching (adds latency instead of reducing it)

**Decision:** ❌ Not recommended - Defeats caching purpose. Use semantic matching for L2 only.

---

## 7. Implementation Checklist

- [ ] **Phase 1: Core Cache Service** (2 hours)
  - [ ] Create `query_decomposition/cache.py` with `QueryDecompositionCache`
  - [ ] Add `_normalize_query()` and `_generate_cache_key()` methods
  - [ ] Integrate with existing `LLMCacheService`

- [ ] **Phase 2: Query Analyzer** (3 hours)
  - [ ] Create `query_decomposition/analyzer.py` with `QueryAnalyzer`
  - [ ] Implement `_has_multi_concept_signals()` heuristic
  - [ ] Implement `_llm_decompose()` with gpt-4o-mini
  - [ ] Add cache integration in `analyze_query()`

- [ ] **Phase 3: Schemas** (1 hour)
  - [ ] Create `query_decomposition/schemas.py`
  - [ ] Define `QueryAnalysis` Pydantic model
  - [ ] Define `CacheStats` for observability

- [ ] **Phase 4: Integration** (2 hours)
  - [ ] Modify `search_service.py` to use `QueryAnalyzer`
  - [ ] Update `search()` method to check cache before decomposition
  - [ ] Add config option `QUERY_DECOMPOSITION_CACHE_ENABLED`

- [ ] **Phase 5: Testing** (4 hours)
  - [ ] Unit tests for `QueryDecompositionCache` (cache hits/misses)
  - [ ] Integration tests for `QueryAnalyzer` (heuristic + LLM paths)
  - [ ] End-to-end tests with real searches
  - [ ] Performance benchmarks (measure latency improvement)

- [ ] **Phase 6: Observability** (2 hours)
  - [ ] Add metrics to `MetricsService.record_query_decomposition()`
  - [ ] Add logging for cache hits/misses
  - [ ] Create monitoring dashboard queries (cache hit rate, latency)

**Total Estimated Effort:** **14 hours**

---

## 8. Monitoring & Metrics

### 8.1 Key Metrics to Track

| Metric | Target | Alert Threshold | Action |
|--------|--------|----------------|---------|
| **L1 Hit Rate** | 30-50% | <20% | Investigate query pattern changes |
| **L2 Hit Rate** | 20-40% | <10% | Check Redis connectivity, similarity threshold |
| **Combined Hit Rate** | 50-70% | <40% | Review cache TTL, query diversity |
| **P50 Latency** | <50ms | >100ms | Check L1/L2 cache health |
| **P95 Latency** | <130ms | >200ms | Investigate slow LLM responses |
| **Cache Size (L1)** | ~500KB | >5MB | Reduce `LLM_CACHE_L1_SIZE` |
| **Cache Size (L2)** | ~5-10MB | >50MB | Reduce `REDIS_SEMANTIC_CACHE_TTL` |

### 8.2 Logging Examples

```python
# Cache hit
logger.info(
    "query_decomposition_cache_hit",
    cache_level="l1",  # or "l2"
    query="how does chunking affect rag?",
    concepts=["chunking strategies", "rag performance"],
    latency_ms=0.8,
)

# Cache miss
logger.info(
    "query_decomposition_cache_miss",
    query="new unique query",
    llm_latency_ms=152.3,
    concepts_extracted=3,
)

# Cache stats (periodic)
logger.info(
    "query_decomposition_cache_stats",
    l1_hits=1234,
    l1_misses=456,
    l2_hits=789,
    l2_misses=321,
    hit_rate=0.67,
    l1_size=943,
    l1_max_size=1000,
)
```

---

## 9. Future Optimizations

### 9.1 Adaptive Similarity Threshold

Dynamically adjust L2 similarity threshold based on false positive rate:

```python
# If false positives detected (manual review):
REDIS_SIMILARITY_THRESHOLD: 0.08 → 0.06  # Stricter (95% similarity)

# If hit rate too low:
REDIS_SIMILARITY_THRESHOLD: 0.08 → 0.12  # Looser (88% similarity)
```

### 9.2 Query Prefix Caching

For common query prefixes ("How does X affect Y?"), cache prefix patterns:

```python
# Cache prefix template
"How does {concept1} affect {concept2}?" → Always 2 concepts
```

### 9.3 Batch Decomposition

For multi-query scenarios (e.g., batch evaluation), decompose in parallel:

```python
async def analyze_queries_batch(self, queries: list[str]) -> list[QueryAnalysis]:
    """Batch decomposition with shared LLM call."""
    tasks = [self.analyze_query(q) for q in queries]
    return await asyncio.gather(*tasks)
```

---

## 10. Conclusion

### Summary

| Aspect | Decision |
|--------|----------|
| **Cache Storage** | Hybrid: L1 TTLCache (1000 entries) + L2 Redis Semantic Cache |
| **Cache Key** | SHA256(normalized_query) - lowercase, whitespace-collapsed |
| **Semantic Matching** | L2 Redis with 0.92 similarity threshold |
| **TTL** | L1: 5 minutes, L2: 24 hours |
| **Invalidation** | Passive TTL expiration (no active invalidation) |
| **Expected Performance** | P50: 150ms → 50ms (67% faster), P95: 250ms → 130ms (48% faster) |
| **Expected Hit Rate** | 50-70% combined (L1: 30-50%, L2: 20-40%) |
| **Cost Savings** | 50-85% reduction in LLM API costs |

### Recommendation

**Implement Hybrid L1+L2 Strategy** - Leverages existing infrastructure, provides massive latency reduction with minimal implementation complexity. Start with conservative TTL values (5min L1, 24hr L2) and tune based on real-world metrics.

### Next Steps

1. **Review & Approval** - Backend team review this document
2. **Implementation** - Follow Phase 1-6 checklist (~14 hours)
3. **Testing** - Validate cache hit rates and latency improvements
4. **Monitoring** - Deploy with metrics collection, observe for 1 week
5. **Tuning** - Adjust TTL and similarity thresholds based on production data

---

**Document Version:** 1.0
**Last Updated:** 2025-12-29
**Related Issues:** #601 (Query Decomposition), #218 (Telemetry & Metrics)
**Related PRs:** TBD (implementation PR)
