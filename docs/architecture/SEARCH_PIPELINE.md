# Search Pipeline Architecture

SkillForge implements a multi-stage search pipeline combining semantic search, keyword search, hybrid fusion, query decomposition, and optional re-ranking.

**Target:** 87% retrieval pass rate (up from 73.6%)

---

## Pipeline Overview

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                           SEARCH PIPELINE                                        │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                 │
│   User Query                                                                    │
│       │                                                                         │
│       ▼                                                                         │
│   ┌─────────────────────────────────────────────────────────────────────────┐   │
│   │ 1. QUERY DECOMPOSITION (Issue #601)                                     │   │
│   │    ├─ Heuristic check (<1ms)                                            │   │
│   │    ├─ Cache lookup (L1: <1ms, L2: ~10ms)                                │   │
│   │    └─ LLM extraction (150-250ms) if needed                              │   │
│   │                                                                         │   │
│   │    Multi-concept query → ["concept1", "concept2", "concept3"]           │   │
│   │    Single-concept query → [original_query]                              │   │
│   └─────────────────────────────────────────────────────────────────────────┘   │
│       │                                                                         │
│       ▼                                                                         │
│   ┌─────────────────────────────────────────────────────────────────────────┐   │
│   │ 2. PARALLEL SEARCH (per concept)                                        │   │
│   │                                                                         │   │
│   │    ┌─────────────────────┐    ┌─────────────────────┐                   │   │
│   │    │  SEMANTIC (HNSW)    │    │  KEYWORD (GIN)      │                   │   │
│   │    │  vector <=> embed   │    │  tsvector @@ query  │                   │   │
│   │    │  cosine similarity  │    │  ts_rank scoring    │                   │   │
│   │    └─────────┬───────────┘    └─────────┬───────────┘                   │   │
│   │              │                          │                               │   │
│   │              └──────────┬───────────────┘                               │   │
│   │                         ▼                                               │   │
│   │              ┌──────────────────────┐                                   │   │
│   │              │ HYBRID RRF (k=60)    │                                   │   │
│   │              │ score = Σ 1/(k+rank) │                                   │   │
│   │              └──────────────────────┘                                   │   │
│   └─────────────────────────────────────────────────────────────────────────┘   │
│       │                                                                         │
│       ▼                                                                         │
│   ┌─────────────────────────────────────────────────────────────────────────┐   │
│   │ 3. MULTI-CONCEPT FUSION (if decomposed)                                 │   │
│   │                                                                         │   │
│   │    Results from concept1 ─┐                                             │   │
│   │    Results from concept2 ─┼─► RRF FUSION ─► Merged results              │   │
│   │    Results from concept3 ─┘                                             │   │
│   └─────────────────────────────────────────────────────────────────────────┘   │
│       │                                                                         │
│       ▼                                                                         │
│   ┌─────────────────────────────────────────────────────────────────────────┐   │
│   │ 4. OPTIONAL RE-RANKING                                                  │   │
│   │    Cross-encoder model for fine-grained relevance                       │   │
│   └─────────────────────────────────────────────────────────────────────────┘   │
│       │                                                                         │
│       ▼                                                                         │
│   [Final SearchResults]                                                         │
│                                                                                 │
└─────────────────────────────────────────────────────────────────────────────────┘
```

---

## Stage 1: Query Decomposition

**Location:** `backend/app/shared/services/search/decomposer.py`

### Purpose

Complex queries often span multiple concepts. Decomposition improves retrieval by searching each concept independently.

**Example:**
```
Input:  "How do chunking strategies affect reranking in RAG?"
Output: ["chunking strategies", "reranking methods", "RAG pipeline"]
```

### Architecture

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                         QUERY DECOMPOSER                                         │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                 │
│   Query: "How do chunking strategies affect reranking in RAG?"                  │
│                     │                                                           │
│                     ▼                                                           │
│   ┌─────────────────────────────────────────────────────────────────────────┐   │
│   │ HEURISTIC CHECK (<1ms)                                                  │   │
│   │                                                                         │   │
│   │ Triggers if ANY:                                                        │   │
│   │   • Word count >= 6                                                     │   │
│   │   • Keywords: "and", "or", "vs", "versus", "between"                    │   │
│   │   • Relationship words: "affect", "impact", "relate"                    │   │
│   │   • Multiple technical domains (>= 2)                                   │   │
│   │   • Long question (>= 10 words) with question prefix                    │   │
│   │                                                                         │   │
│   │ Result: True (triggers decomposition) | False (skip to search)         │   │
│   └─────────────────────────────────────────────────────────────────────────┘   │
│                     │ True                                                      │
│                     ▼                                                           │
│   ┌─────────────────────────────────────────────────────────────────────────┐   │
│   │ CACHE LOOKUP                                                            │   │
│   │                                                                         │   │
│   │   L1: In-memory TTLCache                                                │   │
│   │       • Size: 1000 entries                                              │   │
│   │       • TTL: 300 seconds (5 minutes)                                    │   │
│   │       • Latency: <1ms                                                   │   │
│   │       • Hit rate: 30-50%                                                │   │
│   │                                                                         │   │
│   │   L2: Redis semantic cache (planned)                                    │   │
│   │       • Latency: ~10ms                                                  │   │
│   │       • Hit rate: 20-40% additional                                     │   │
│   └─────────────────────────────────────────────────────────────────────────┘   │
│                     │ miss                                                      │
│                     ▼                                                           │
│   ┌─────────────────────────────────────────────────────────────────────────┐   │
│   │ LLM EXTRACTION (150-250ms)                                              │   │
│   │                                                                         │   │
│   │   Model: Coding LLM (Gemini/Claude/Ollama based on config)              │   │
│   │   Output: ConceptExtraction (Pydantic structured output)                │   │
│   │                                                                         │   │
│   │   {                                                                     │   │
│   │     "concepts": ["chunking strategies", "reranking", "RAG pipeline"],   │   │
│   │     "reasoning": "Query spans three distinct topics"                    │   │
│   │   }                                                                     │   │
│   │                                                                         │   │
│   │   Constraints: 1-5 concepts, each a searchable phrase                   │   │
│   └─────────────────────────────────────────────────────────────────────────┘   │
│                                                                                 │
└─────────────────────────────────────────────────────────────────────────────────┘
```

### Configuration

**Location:** `backend/app/core/config.py`

| Setting | Default | Description |
|---------|---------|-------------|
| `QUERY_DECOMPOSITION_ENABLED` | `True` | Feature flag |
| `QUERY_DECOMPOSITION_MIN_WORDS` | `6` | Minimum words to consider |
| `QUERY_DECOMPOSITION_MAX_CONCEPTS` | `5` | Maximum extracted concepts |
| `QUERY_DECOMPOSITION_LLM_TIMEOUT` | `2.0` | LLM timeout in seconds |
| `QUERY_DECOMPOSITION_CACHE_L1_SIZE` | `1000` | L1 cache max entries |
| `QUERY_DECOMPOSITION_CACHE_L1_TTL` | `300` | L1 TTL in seconds |

---

## Stage 2: Hybrid Search

**Location:** `backend/app/db/repositories/chunk_repository.py:202-288`

### Semantic Search (Vector)

Uses pgvector HNSW index for approximate nearest neighbor search:

```python
# Cosine distance calculation
cosine_dist = AnalysisChunk.vector.cosine_distance(query_embedding)
similarity_score = (1 - cosine_dist).label("similarity_score")

# Query with HNSW index
SELECT chunk_id, 1 - (vector <=> $embedding) AS score
FROM analysis_chunks
ORDER BY vector <=> $embedding
LIMIT $fetch_k;
```

### Keyword Search (Full-Text)

Uses GIN index with tsvector for term matching:

```python
# Full-text search with ts_rank
ts_query = func.plainto_tsquery('english', query)
rank = func.ts_rank(AnalysisChunk.content_tsvector, ts_query)

SELECT chunk_id, ts_rank(content_tsvector, plainto_tsquery($query)) AS score
FROM analysis_chunks
WHERE content_tsvector @@ plainto_tsquery($query)
ORDER BY score DESC
LIMIT $fetch_k;
```

### Hybrid Fusion (RRF)

**Location:** `backend/app/shared/services/search/hybrid_fusion.py`

```python
def reciprocal_rank_fusion(
    result_lists: list[list[tuple[str, float]]],
    k: int = 60
) -> list[tuple[str, float]]:
    """
    RRF Formula: RRF_score(item) = Σ 1/(k + rank(item))

    k=60 prevents top-ranked items from dominating.
    Source: SIGIR 2009 paper.
    """
    scores = defaultdict(float)
    for result_list in result_lists:
        for rank, (item_id, _) in enumerate(result_list, start=1):
            scores[item_id] += 1 / (k + rank)

    return sorted(scores.items(), key=lambda x: x[1], reverse=True)
```

**Why k=60?**
- Empirically optimal constant from academic research
- Balances precision vs recall
- Prevents single-source dominance

---

## Stage 3: Multi-Concept Fusion

**Location:** `backend/app/shared/services/search/search_service.py:263-299`

When a query is decomposed into multiple concepts:

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                      MULTI-CONCEPT PARALLEL RETRIEVAL                            │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                 │
│   Concepts: ["chunking strategies", "reranking methods", "RAG pipeline"]        │
│                                                                                 │
│                     ┌──────────────────────────────────────┐                    │
│                     │          asyncio.gather()            │                    │
│                     │         (Semaphore limit: 5)         │                    │
│                     └──────────────────────────────────────┘                    │
│                        │              │              │                          │
│                        ▼              ▼              ▼                          │
│              ┌─────────────┐ ┌─────────────┐ ┌─────────────┐                   │
│              │  Search:    │ │  Search:    │ │  Search:    │                   │
│              │  "chunking  │ │  "reranking │ │  "RAG       │                   │
│              │  strategies"│ │  methods"   │ │  pipeline"  │                   │
│              └──────┬──────┘ └──────┬──────┘ └──────┬──────┘                   │
│                     │              │              │                             │
│                     │   Results    │   Results    │   Results                   │
│                     │              │              │                             │
│                     └──────────────┼──────────────┘                             │
│                                    ▼                                            │
│                     ┌──────────────────────────────────────┐                    │
│                     │          RRF FUSION (k=60)           │                    │
│                     │                                      │                    │
│                     │  Documents appearing in multiple     │                    │
│                     │  concept searches rank highest       │                    │
│                     └──────────────────────────────────────┘                    │
│                                    │                                            │
│                                    ▼                                            │
│                          [Fused Results]                                        │
│                                                                                 │
└─────────────────────────────────────────────────────────────────────────────────┘
```

### Implementation

```python
async def _multi_concept_search(
    self,
    query: str,
    mode: SearchMode,
    fetch_k: int,
    filters: SearchFilters | None,
    concepts: list[str],
) -> list[SearchResult]:
    """Execute multi-concept search with parallel retrieval and RRF fusion."""
    decomposer = QueryDecomposer(embedding_service=self.embedding_service)

    async def concept_search(concept: str, top_k: int) -> list[tuple[str, float]]:
        results = await self._single_concept_search(concept, mode, top_k, filters)
        return [(r.chunk_id, r.score) for r in results]

    # Parallel retrieval with RRF fusion
    fused_chunk_scores = await decomposer.parallel_retrieve(
        concepts=concepts,
        search_fn=concept_search,
        top_k_per_concept=fetch_k,
    )

    return await self._fused_scores_to_results(fused_chunk_scores, query, fetch_k)
```

---

## Stage 4: Re-Ranking (Optional)

**Location:** `backend/app/shared/services/search/reranker.py`

Cross-encoder model for fine-grained relevance scoring:

```python
class ReRanker:
    """Re-ranks search results using a cross-encoder model."""

    async def rerank(
        self,
        query: str,
        results: list[SearchResult],
        top_k: int,
    ) -> list[SearchResult]:
        # Score each (query, document) pair with cross-encoder
        # Returns re-ordered results by relevance
```

**When to use:**
- High-stakes queries requiring precision
- When initial retrieval has many borderline results
- Trade-off: +50-100ms latency for better relevance

---

## Search Modes

| Mode | Strategy | Use Case |
|------|----------|----------|
| `SEMANTIC` | Vector only | Conceptual/meaning-based queries |
| `KEYWORD` | Full-text only | Exact term matching |
| `HYBRID` | RRF fusion | Best of both (default) |

---

## Performance Characteristics

### Latency Profile

| Stage | Single-Concept | Multi-Concept (3) |
|-------|---------------|-------------------|
| Decomposition | <1ms (heuristic skip) | 150-250ms (LLM) or <1ms (cache) |
| Embedding | ~50ms | ~50ms (shared) |
| Semantic Search | ~5ms | ~5ms × 3 (parallel) |
| Keyword Search | ~5ms | ~5ms × 3 (parallel) |
| RRF Fusion | <1ms | <5ms |
| **Total** | **~60ms** | **~210-310ms** (first) or **~65ms** (cached) |

### Cache Impact

| Scenario | Frequency | Overhead |
|----------|-----------|----------|
| Single-concept (heuristic skip) | ~74% | <1ms |
| Multi-concept (L1 cache hit) | ~15% | <1ms |
| Multi-concept (LLM extraction) | ~11% | 150-250ms |

---

## Entry Points

### SearchService.search()

**Location:** `backend/app/shared/services/search/search_service.py`

```python
async def search(
    self,
    query: str,
    mode: SearchMode = SearchMode.HYBRID,
    top_k: int = 10,
    fetch_k: int | None = None,
    filters: SearchFilters | None = None,
    rerank: ReRankConfig | None = None,
) -> list[SearchResult]:
    """Main search entry point with query decomposition."""
```

### API Endpoint

**Location:** `backend/app/api/routes/search.py`

```
POST /api/v1/search
{
    "query": "How do chunking strategies affect reranking?",
    "mode": "hybrid",
    "top_k": 10,
    "filters": {...},
    "rerank": {"enabled": true}
}
```

---

## Error Handling

### Graceful Degradation

1. **LLM decomposition fails** → Falls back to original query as single concept
2. **Individual concept search fails** → Continues with other concepts (partial results)
3. **All concept searches fail** → Returns empty list with warning log
4. **Cache failure** → Bypasses cache, proceeds to LLM

### Exception Types

```python
# decomposer.py
LLM_ERRORS = (ValueError, TypeError, RuntimeError, ValidationError, TimeoutError, ConnectionError)
SEARCH_ERRORS = (ValueError, TypeError, RuntimeError, TimeoutError, ConnectionError, OSError)
```

---

## Monitoring

### Structured Logging

```python
logger.info(
    "query_decomposition_result",
    query=query[:100],
    is_multi_concept=result.is_multi_concept,
    num_concepts=len(result.concepts),
    source=result.source.value,  # "heuristic", "cache_l1", "llm"
    latency_ms=result.latency_ms,
)

logger.info(
    "multi_concept_search_completed",
    query=query[:100],
    num_concepts=len(concepts),
    fused_results_count=len(results),
)
```

### Key Metrics

| Metric | Description | Target |
|--------|-------------|--------|
| Decomposition latency | Time to extract concepts | <250ms (LLM), <1ms (cache) |
| Cache hit rate | L1 + L2 combined | >50% |
| Retrieval pass rate | Relevant docs in top-k | >87% |
| Search P50 latency | Median search time | <100ms |

---

## References

- [Issue #601: Query Decomposition](https://github.com/ArieGoldkin/SkillForge/issues/601)
- [RRF Paper (SIGIR 2009)](https://dl.acm.org/doi/10.1145/1571941.1572114)
- [pgvector HNSW](https://github.com/pgvector/pgvector#hnsw)
- [Database Architecture](./DATABASE.md)
