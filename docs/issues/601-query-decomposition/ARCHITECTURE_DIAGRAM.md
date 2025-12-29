# Issue #601: Query Decomposition - Architecture Diagrams

**Date:** 2025-12-29
**Status:** Design Complete

---

## Cache Flow Diagram

```
┌──────────────────────────────────────────────────────────────────────────────┐
│                    QUERY DECOMPOSITION CACHE FLOW                            │
├──────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  User Search Query: "How do chunking strategies affect reranking in RAG?"   │
│                                    ↓                                         │
│  ┌────────────────────────────────────────────────────────────────────┐     │
│  │ Step 1: Normalize Query                                           │     │
│  │   - Lowercase: "how do chunking strategies affect reranking..."   │     │
│  │   - Collapse whitespace: single spaces only                       │     │
│  │   - Generate SHA256 hash key                                      │     │
│  └────────────────────────────┬───────────────────────────────────────┘     │
│                               ↓                                             │
│  ┌────────────────────────────────────────────────────────────────────┐     │
│  │ Step 2: L1 Cache Lookup (In-Memory TTLCache)                      │     │
│  │   - Key: SHA256(normalized_query)                                 │     │
│  │   - Storage: Python TTLCache (1000 entries)                       │     │
│  │   - TTL: 5 minutes                                                │     │
│  │   - Latency: <1ms                                                 │     │
│  └──────────┬──────────────────────────────┬──────────────────────────┘     │
│             │                              │                                │
│        ┌────▼─────┐                   ┌────▼─────┐                          │
│        │ L1 HIT   │                   │ L1 MISS  │                          │
│        │ (30-50%) │                   │ (50-70%) │                          │
│        └────┬─────┘                   └────┬─────┘                          │
│             │                              │                                │
│             │                              ↓                                │
│             │         ┌────────────────────────────────────────────┐        │
│             │         │ Step 3: L2 Cache Lookup (Redis Semantic)  │        │
│             │         │   - Semantic similarity search             │        │
│             │         │   - Threshold: 0.92 (92% similarity)       │        │
│             │         │   - TTL: 24 hours                          │        │
│             │         │   - Latency: ~10ms                         │        │
│             │         └─────┬─────────────────────┬────────────────┘        │
│             │               │                     │                         │
│             │          ┌────▼─────┐          ┌────▼─────┐                   │
│             │          │ L2 HIT   │          │ L2 MISS  │                   │
│             │          │ (20-40%) │          │ (30-60%) │                   │
│             │          └────┬─────┘          └────┬─────┘                   │
│             │               │                     │                         │
│             │               │                     ↓                         │
│             │               │    ┌────────────────────────────────────┐     │
│             │               │    │ Step 4: LLM Decomposition          │     │
│             │               │    │   - Model: gpt-4o-mini             │     │
│             │               │    │   - Latency: ~150ms                │     │
│             │               │    │   - Cost: $0.000026/query          │     │
│             │               │    └────┬───────────────────────────────┘     │
│             │               │         │                                     │
│             │               │         ↓                                     │
│             │               │    ┌────────────────────────────────────┐     │
│             │               │    │ Step 5: Store in L1 + L2           │     │
│             │               │    │   - Async write (non-blocking)     │     │
│             │               │    │   - L1: Immediate availability     │     │
│             │               │    │   - L2: Shared across instances    │     │
│             │               │    └────┬───────────────────────────────┘     │
│             │               │         │                                     │
│             └───────────────┴─────────┴─────────────────┐                   │
│                                                          ↓                   │
│                              ┌────────────────────────────────────────┐     │
│                              │ Return: QueryAnalysis                  │     │
│                              │   - is_multi_concept: true             │     │
│                              │   - concepts: ["chunking strategies",  │     │
│                              │               "reranking performance", │     │
│                              │               "RAG architecture"]      │     │
│                              │   - query_type: "multi"                │     │
│                              └────────────────────────────────────────┘     │
│                                                                              │
└──────────────────────────────────────────────────────────────────────────────┘
```

---

## System Integration Diagram

```
┌──────────────────────────────────────────────────────────────────────────────┐
│                   QUERY DECOMPOSITION IN SEARCH PIPELINE                     │
├──────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  Frontend Search Request                                                     │
│       ↓                                                                      │
│  POST /api/v1/search                                                         │
│       ↓                                                                      │
│  ┌────────────────────────────────────────────────────────────────────┐     │
│  │ SearchService.search()                                             │     │
│  │   - Query: "How do chunking strategies affect reranking in RAG?"  │     │
│  │   - Mode: HYBRID                                                   │     │
│  │   - Top K: 10                                                      │     │
│  └────────────────────────────┬───────────────────────────────────────┘     │
│                               ↓                                             │
│  ┌────────────────────────────────────────────────────────────────────┐     │
│  │ QueryAnalyzer.analyze_query() [NEW]                               │     │
│  │   - Check cache (L1 → L2)                                          │     │
│  │   - On miss: Heuristic check → LLM decomposition                   │     │
│  │   - Store in cache                                                 │     │
│  └────────────────────────────┬───────────────────────────────────────┘     │
│                               ↓                                             │
│  ┌────────────────────────────────────────────────────────────────────┐     │
│  │ QueryAnalysis Result                                               │     │
│  │   - is_multi_concept: true                                         │     │
│  │   - concepts: ["chunking", "reranking", "RAG"]                     │     │
│  └────────────────────────────┬───────────────────────────────────────┘     │
│                               ↓                                             │
│                         ┌─────┴─────┐                                       │
│                         │ Routing   │                                       │
│                         └─────┬─────┘                                       │
│                ┌──────────────┼──────────────┐                              │
│                │                             │                              │
│         ┌──────▼──────┐              ┌──────▼──────┐                        │
│         │ Single Path │              │ Multi Path  │                        │
│         └──────┬──────┘              └──────┬──────┘                        │
│                │                             │                              │
│                ↓                             ↓                              │
│  ┌────────────────────────┐   ┌────────────────────────────────────┐       │
│  │ Standard Retrieval     │   │ Multi-Query Retrieval [NEW]        │       │
│  │   - Single query       │   │   - Parallel retrieval per concept │       │
│  │   - HYBRID search      │   │   - 3 × HYBRID search             │       │
│  │   - Top K: 10          │   │   - Top K per concept: 5           │       │
│  └────────┬───────────────┘   └────────┬───────────────────────────┘       │
│           │                            │                                    │
│           │                            ↓                                    │
│           │               ┌────────────────────────────────────┐            │
│           │               │ RRF Fusion                         │            │
│           │               │   - Merge 15 results               │            │
│           │               │   - Deduplicate by chunk_id        │            │
│           │               │   - Re-rank with RRF               │            │
│           │               │   - Return top 10                  │            │
│           │               └────────┬───────────────────────────┘            │
│           │                        │                                        │
│           └────────────────────────┴────────────────┐                       │
│                                                     ↓                       │
│                            ┌────────────────────────────────────────┐       │
│                            │ Final Results                          │       │
│                            │   - 10 SearchResult objects            │       │
│                            │   - Sorted by relevance score          │       │
│                            │   - Diverse concept coverage           │       │
│                            └────────────────────────────────────────┘       │
│                                                     ↓                       │
│                                        Return to Frontend                   │
│                                                                              │
└──────────────────────────────────────────────────────────────────────────────┘
```

---

## Cache Storage Architecture

```
┌──────────────────────────────────────────────────────────────────────────────┐
│                        2-TIER CACHE STORAGE                                  │
├──────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌────────────────────────────────────────────────────────────────────┐     │
│  │ L1 CACHE (In-Memory TTLCache)                                      │     │
│  ├────────────────────────────────────────────────────────────────────┤     │
│  │ Location: backend/app/shared/services/cache/llm_cache_service.py   │     │
│  │ Storage: Python cachetools.TTLCache                                │     │
│  │ Scope: Per backend process (not shared)                            │     │
│  │                                                                     │     │
│  │ Configuration:                                                      │     │
│  │   - LLM_CACHE_L1_SIZE: 1000 entries                                │     │
│  │   - LLM_CACHE_L1_TTL: 300 seconds (5 minutes)                      │     │
│  │                                                                     │     │
│  │ Entry Format:                                                       │     │
│  │   Key: SHA256(agent_type + content_hash + prompt_hash)             │     │
│  │   Value: JSON string of QueryAnalysis                              │     │
│  │     {                                                               │     │
│  │       "is_multi_concept": true,                                    │     │
│  │       "concepts": ["chunking", "reranking", "RAG"],                │     │
│  │       "query_type": "multi"                                        │     │
│  │     }                                                               │     │
│  │                                                                     │     │
│  │ Performance:                                                        │     │
│  │   - Hit latency: <1ms                                              │     │
│  │   - Miss latency: <1ms                                             │     │
│  │   - Memory usage: ~500KB (1000 × ~500 bytes)                       │     │
│  │                                                                     │     │
│  │ Eviction Policy: TTL-based + LRU (cachetools.TTLCache)             │     │
│  └────────────────────────────────────────────────────────────────────┘     │
│                                                                              │
│  ┌────────────────────────────────────────────────────────────────────┐     │
│  │ L2 CACHE (Redis Semantic Cache)                                    │     │
│  ├────────────────────────────────────────────────────────────────────┤     │
│  │ Location: backend/app/shared/services/cache/redis_service.py       │     │
│  │ Storage: Redis with vector similarity                              │     │
│  │ Scope: Shared across all backend instances                         │     │
│  │                                                                     │     │
│  │ Configuration:                                                      │     │
│  │   - REDIS_URL: redis://localhost:6380                              │     │
│  │   - REDIS_SEMANTIC_CACHE_TTL: 86400 seconds (24 hours)             │     │
│  │   - REDIS_SIMILARITY_THRESHOLD: 0.08 (92% similarity)              │     │
│  │                                                                     │     │
│  │ Entry Format:                                                       │     │
│  │   Key: query_decomposition:{query_hash}                            │     │
│  │   Fields:                                                           │     │
│  │     - query: Original query text                                   │     │
│  │     - embedding: Query embedding vector (1536 dims)                │     │
│  │     - result: JSON string of QueryAnalysis                         │     │
│  │     - timestamp: Unix timestamp                                    │     │
│  │                                                                     │     │
│  │ Lookup Process:                                                     │     │
│  │   1. Generate query embedding                                      │     │
│  │   2. Semantic search in Redis (vector similarity)                  │     │
│  │   3. If similarity > 0.92, return cached result                    │     │
│  │   4. Else, cache miss                                              │     │
│  │                                                                     │     │
│  │ Performance:                                                        │     │
│  │   - Hit latency: ~10ms (network + similarity search)               │     │
│  │   - Miss latency: ~10ms (no match found)                           │     │
│  │   - Memory usage: ~5-10MB (5000-10000 × ~1KB)                      │     │
│  │                                                                     │     │
│  │ Eviction Policy: TTL-based (24 hours)                              │     │
│  └────────────────────────────────────────────────────────────────────┘     │
│                                                                              │
└──────────────────────────────────────────────────────────────────────────────┘
```

---

## Latency Comparison

```
┌──────────────────────────────────────────────────────────────────────────────┐
│                     LATENCY BREAKDOWN BY SCENARIO                            │
├──────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  Scenario 1: L1 Cache Hit (30-50% of requests)                              │
│  ────────────────────────────────────────────────                            │
│                                                                              │
│    User Query                                                                │
│         ↓                                                                    │
│    Normalize Query         [ <1ms ]                                          │
│         ↓                                                                    │
│    L1 Lookup (HIT)         [ <1ms ]                                          │
│         ↓                                                                    │
│    Return Cached Result                                                      │
│                                                                              │
│    TOTAL LATENCY: ~1ms                                                       │
│    ═══════════════════════                                                   │
│                                                                              │
│  ─────────────────────────────────────────────────────────────────────────   │
│                                                                              │
│  Scenario 2: L2 Cache Hit (20-40% of requests)                              │
│  ────────────────────────────────────────────────                            │
│                                                                              │
│    User Query                                                                │
│         ↓                                                                    │
│    Normalize Query         [ <1ms ]                                          │
│         ↓                                                                    │
│    L1 Lookup (MISS)        [ <1ms ]                                          │
│         ↓                                                                    │
│    L2 Lookup (HIT)         [ ~10ms ]                                         │
│         ↓                                                                    │
│    Update L1 Cache         [ <1ms ]                                          │
│         ↓                                                                    │
│    Return Cached Result                                                      │
│                                                                              │
│    TOTAL LATENCY: ~12ms                                                      │
│    ════════════════════                                                      │
│                                                                              │
│  ─────────────────────────────────────────────────────────────────────────   │
│                                                                              │
│  Scenario 3: Cache Miss + Heuristic (10-20% of requests)                    │
│  ──────────────────────────────────────────────────────                      │
│                                                                              │
│    User Query                                                                │
│         ↓                                                                    │
│    Normalize Query                  [ <1ms ]                                 │
│         ↓                                                                    │
│    L1 Lookup (MISS)                 [ <1ms ]                                 │
│         ↓                                                                    │
│    L2 Lookup (MISS)                 [ ~10ms ]                                │
│         ↓                                                                    │
│    Heuristic Check (single-concept) [ ~1ms ]                                 │
│         ↓                                                                    │
│    Store in L1 + L2                 [ <5ms async ]                           │
│         ↓                                                                    │
│    Return Analysis                                                           │
│                                                                              │
│    TOTAL LATENCY: ~17ms                                                      │
│    ════════════════════                                                      │
│                                                                              │
│  ─────────────────────────────────────────────────────────────────────────   │
│                                                                              │
│  Scenario 4: Cache Miss + LLM (20-40% of requests)                          │
│  ─────────────────────────────────────────────────                           │
│                                                                              │
│    User Query                                                                │
│         ↓                                                                    │
│    Normalize Query                  [ <1ms ]                                 │
│         ↓                                                                    │
│    L1 Lookup (MISS)                 [ <1ms ]                                 │
│         ↓                                                                    │
│    L2 Lookup (MISS)                 [ ~10ms ]                                │
│         ↓                                                                    │
│    Heuristic Check (multi-concept)  [ ~1ms ]                                 │
│         ↓                                                                    │
│    LLM Decomposition (gpt-4o-mini)  [ ~150ms ]                               │
│         ↓                                                                    │
│    Store in L1 + L2                 [ <5ms async ]                           │
│         ↓                                                                    │
│    Return Analysis                                                           │
│                                                                              │
│    TOTAL LATENCY: ~167ms                                                     │
│    ═════════════════════                                                     │
│                                                                              │
│  ─────────────────────────────────────────────────────────────────────────   │
│                                                                              │
│  WEIGHTED AVERAGE (P50):                                                     │
│    (0.40 × 1ms) + (0.30 × 12ms) + (0.15 × 17ms) + (0.15 × 167ms)            │
│    = 0.4ms + 3.6ms + 2.6ms + 25.0ms                                          │
│    = 31.6ms ≈ 32ms                                                           │
│                                                                              │
│  BEFORE CACHING (baseline): ~150ms                                           │
│  AFTER CACHING (P50): ~32ms                                                  │
│  IMPROVEMENT: 78% faster                                                     │
│                                                                              │
└──────────────────────────────────────────────────────────────────────────────┘
```

---

## Cache Hit Rate Prediction

```
┌──────────────────────────────────────────────────────────────────────────────┐
│                        CACHE HIT RATE ESTIMATION                             │
├──────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  Query Pattern Analysis (from SkillForge evaluation dataset):               │
│                                                                              │
│  ┌────────────────────┬──────────────┬────────────┬──────────────┐          │
│  │ Query Type         │ Frequency    │ L1 Hit     │ L2 Hit       │          │
│  ├────────────────────┼──────────────┼────────────┼──────────────┤          │
│  │ Exact Duplicates   │ 30%          │ 95%        │ 5%           │          │
│  │ Case/Whitespace    │ 10%          │ 80%        │ 20%          │          │
│  │ Paraphrases        │ 15%          │ 10%        │ 70%          │          │
│  │ Semantic Similar   │ 15%          │ 5%         │ 60%          │          │
│  │ Unique Queries     │ 30%          │ 0%         │ 0%           │          │
│  └────────────────────┴──────────────┴────────────┴──────────────┘          │
│                                                                              │
│  Combined Hit Rate Calculation:                                             │
│                                                                              │
│    L1 Hit Rate = (0.30 × 0.95) + (0.10 × 0.80) + (0.15 × 0.10) +            │
│                  (0.15 × 0.05) + (0.30 × 0.00)                               │
│                = 0.285 + 0.08 + 0.015 + 0.0075 + 0.00                        │
│                = 0.3875 ≈ 39%                                                │
│                                                                              │
│    L2 Hit Rate = (0.30 × 0.05) + (0.10 × 0.20) + (0.15 × 0.70) +            │
│                  (0.15 × 0.60) + (0.30 × 0.00)                               │
│                = 0.015 + 0.02 + 0.105 + 0.09 + 0.00                          │
│                = 0.23 ≈ 23%                                                  │
│                                                                              │
│    Combined Hit Rate = L1 + (L2 × (1 - L1))                                 │
│                      = 0.39 + (0.23 × 0.61)                                  │
│                      = 0.39 + 0.14                                           │
│                      = 0.53 ≈ 53%                                            │
│                                                                              │
│  ─────────────────────────────────────────────────────────────────────────   │
│                                                                              │
│  Expected Performance:                                                       │
│                                                                              │
│    ┌──────────────────┬────────────┬────────────┬───────────────┐           │
│    │ Scenario         │ Frequency  │ Latency    │ Weighted      │           │
│    ├──────────────────┼────────────┼────────────┼───────────────┤           │
│    │ L1 Hit           │ 39%        │ ~1ms       │ 0.39ms        │           │
│    │ L2 Hit           │ 23%        │ ~12ms      │ 2.76ms        │           │
│    │ Heuristic Path   │ 13%        │ ~17ms      │ 2.21ms        │           │
│    │ LLM Path         │ 25%        │ ~167ms     │ 41.75ms       │           │
│    └──────────────────┴────────────┴────────────┴───────────────┘           │
│                                                                              │
│    P50 Latency = 0.39 + 2.76 + 2.21 + 41.75 = 47.11ms ≈ 47ms                │
│                                                                              │
│    Baseline (no cache): 150ms                                               │
│    With cache: 47ms                                                          │
│    Improvement: 69% faster                                                   │
│                                                                              │
└──────────────────────────────────────────────────────────────────────────────┘
```

---

**Document Version:** 1.0
**Last Updated:** 2025-12-29
**Related:** CACHING_ARCHITECTURE.md (detailed specification)
