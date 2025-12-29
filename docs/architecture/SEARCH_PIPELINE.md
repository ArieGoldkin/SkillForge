# Search Pipeline Architecture

SkillForge implements a multi-stage search pipeline combining semantic search, keyword search, hybrid fusion, query decomposition, HyDE (Hypothetical Document Embeddings), and optional re-ranking.

**Target:** 92% retrieval pass rate (up from 87%)

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
│   │ 2. HyDE - HYPOTHETICAL DOCUMENT EMBEDDINGS (Issue #602)                 │   │
│   │    ├─ Cache lookup (L1: <1ms)                                           │   │
│   │    └─ LLM generation (200-400ms) if cache miss                          │   │
│   │                                                                         │   │
│   │    "scaling async pipelines" →                                          │   │
│   │      "To scale async pipelines, use event-driven messaging..."          │   │
│   │                                                                         │   │
│   │    ✓ Bridges vocabulary gap between queries and documents               │   │
│   │    ✓ Fixes 18% of failures due to terminology mismatch                  │   │
│   └─────────────────────────────────────────────────────────────────────────┘   │
│       │                                                                         │
│       ▼                                                                         │
│   ┌─────────────────────────────────────────────────────────────────────────┐   │
│   │ 3. PARALLEL SEARCH (per concept)                                        │   │
│   │                                                                         │   │
│   │    ┌─────────────────────┐    ┌─────────────────────┐                   │   │
│   │    │  SEMANTIC (HNSW)    │    │  KEYWORD (GIN)      │                   │   │
│   │    │  HyDE embed <=> doc │    │  tsvector @@ query  │                   │   │
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
│   │ 4. MULTI-CONCEPT FUSION (if decomposed)                                 │   │
│   │                                                                         │   │
│   │    Results from concept1 ─┐                                             │   │
│   │    Results from concept2 ─┼─► RRF FUSION ─► Merged results              │   │
│   │    Results from concept3 ─┘                                             │   │
│   └─────────────────────────────────────────────────────────────────────────┘   │
│       │                                                                         │
│       ▼                                                                         │
│   ┌─────────────────────────────────────────────────────────────────────────┐   │
│   │ 5. OPTIONAL RE-RANKING                                                  │   │
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

## Stage 2: HyDE (Hypothetical Document Embeddings)

**Location:** `backend/app/shared/services/search/hyde.py`

### Purpose

HyDE addresses vocabulary mismatch between user queries and document content. Instead of embedding the raw query, HyDE generates a hypothetical document that would answer the query, then embeds that document.

**Problem:**
```
Query:      "scaling async data pipelines"
Documents:  Use terms like "event-driven messaging", "Apache Kafka", "message brokers"
Result:     Direct embedding fails due to vocabulary mismatch (18% of failures)
```

**Solution:**
```
Query:      "scaling async data pipelines"
HyDE:       "To scale asynchronous data pipelines, use event-driven messaging
             with Apache Kafka. Message brokers provide reliable delivery..."
Embedding:  HyDE document now contains corpus vocabulary → Better matches!
```

### Architecture

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                            HyDE SERVICE                                          │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                 │
│   Query/Concept: "scaling async data pipelines"                                 │
│                     │                                                           │
│                     ▼                                                           │
│   ┌─────────────────────────────────────────────────────────────────────────┐   │
│   │ CACHE LOOKUP (<1ms)                                                     │   │
│   │                                                                         │   │
│   │   L1: In-memory dict with TTL                                           │   │
│   │       • Size: 500 entries                                               │   │
│   │       • TTL: 300 seconds (5 minutes)                                    │   │
│   │       • Latency: <1ms                                                   │   │
│   │       • Hit rate: 60-70% (concepts are reused across queries)           │   │
│   │                                                                         │   │
│   │   L2: Redis semantic cache (planned)                                    │   │
│   └─────────────────────────────────────────────────────────────────────────┘   │
│                     │ miss                                                      │
│                     ▼                                                           │
│   ┌─────────────────────────────────────────────────────────────────────────┐   │
│   │ LLM GENERATION (200-400ms)                                              │   │
│   │                                                                         │   │
│   │   Model: Gemini Flash / Claude / Ollama (based on config)               │   │
│   │   Output: HypotheticalDocument (Pydantic structured output)             │   │
│   │   Timeout: 3 seconds (falls back to direct embedding)                   │   │
│   │                                                                         │   │
│   │   Prompt: "Given a search query, write a short factual document         │   │
│   │            that would answer this query using technical terminology."   │   │
│   │                                                                         │   │
│   │   Output: {                                                             │   │
│   │     "document": "To scale asynchronous data pipelines, use event-       │   │
│   │                  driven messaging with Apache Kafka..."                 │   │
│   │   }                                                                     │   │
│   └─────────────────────────────────────────────────────────────────────────┘   │
│                     │                                                           │
│                     ▼                                                           │
│   ┌─────────────────────────────────────────────────────────────────────────┐   │
│   │ EMBEDDING GENERATION                                                    │   │
│   │                                                                         │   │
│   │   Input: Hypothetical document (or original query if fallback)          │   │
│   │   Output: 1536-dimensional embedding                                    │   │
│   │   Model: text-embedding-3-small (OpenAI) or Nomic (Ollama)              │   │
│   └─────────────────────────────────────────────────────────────────────────┘   │
│                                                                                 │
└─────────────────────────────────────────────────────────────────────────────────┘
```

### Graceful Degradation

HyDE is designed to never block or fail search:

1. **LLM timeout (3s)** → Falls back to direct embedding of original query
2. **LLM error** → Falls back to direct embedding of original query
3. **Cache miss** → Proceeds to LLM, caches result for future queries

### Integration with Search

HyDE is integrated into `_semantic_search()` and `_hybrid_search()` methods:

```python
async def _semantic_search(self, query: str, ...) -> list[SearchResult]:
    # Use HyDE for improved semantic matching (Issue #602)
    hyde_result = await self.hyde_service.generate(query)
    query_embedding = hyde_result.embedding  # HyDE embedding, not raw query

    # Use HyDE embedding for vector search
    chunks_with_scores = await self.chunk_repo.semantic_search(
        query_embedding=query_embedding,
        ...
    )
```

### Expected Impact

| Metric | Before HyDE | After HyDE | Improvement |
|--------|-------------|------------|-------------|
| Retrieval pass rate | 87% | 92% | +5 points |
| Vocabulary mismatch failures | 18% | ~5% | -13 points |
| P50 latency | 60ms | 260ms | +200ms |
| P50 latency (cached) | 60ms | 65ms | +5ms |

### Configuration

HyDE configuration is in `backend/app/shared/services/search/hyde.py`:

| Constant | Value | Description |
|----------|-------|-------------|
| `HYDE_MAX_TOKENS` | `150` | Max tokens in hypothetical doc |
| `HYDE_TIMEOUT_SECONDS` | `3.0` | LLM timeout before fallback |
| `HYDE_TEMPERATURE` | `0.3` | LLM temperature (low for consistency) |
| `HYDE_CACHE_L1_SIZE` | `500` | In-memory cache max entries |
| `HYDE_CACHE_L1_TTL` | `300` | Cache TTL in seconds |

---

## Stage 3: Parallel Search (Hybrid)

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

## Stage 4: Multi-Concept Fusion

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

## Stage 5: Re-Ranking (Optional)

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
- [Issue #602: HyDE for Vocabulary Mismatch](https://github.com/ArieGoldkin/SkillForge/issues/602)
- [HyDE Paper (arXiv 2022)](https://arxiv.org/abs/2212.10496) - "Precise Zero-Shot Dense Retrieval without Relevance Labels"
- [RRF Paper (SIGIR 2009)](https://dl.acm.org/doi/10.1145/1571941.1572114)
- [pgvector HNSW](https://github.com/pgvector/pgvector#hnsw)
- [Database Architecture](./DATABASE.md)
