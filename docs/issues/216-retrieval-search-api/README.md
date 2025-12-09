# Issue #216: Retrieval & Search API (Semantic + Hybrid)

**Status:** 🚧 **IN PROGRESS**
**Assignee:** Yonatan
**Sprint:** Sprint 8 - Embeddings & Search
**Story Points:** 5 pts
**GitHub Issue:** [#216](https://github.com/ArieGoldkin/SkillForge/issues/216)

---

## Issue Overview

**Title:** Sprint 8: Retrieval & Search API (Semantic + Hybrid)

**Description:**
Expose backend search that supports semantic kNN over pgvector and hybrid (tsvector BM25 + vector) with score fusion, filters, snippets, and path metadata. Coarse-to-fine aware.

**Labels:** `backend`, `feature`, `sprint-8`, `python`, `api`, `search`, `pgvector`

**Dependencies:**
- Issue #221 (Hierarchical Chunking) - ✅ Merged

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                        ISSUE #216: RETRIEVAL & SEARCH API                   │
│                         Coarse-to-Fine Search Architecture                  │
└─────────────────────────────────────────────────────────────────────────────┘

                              ┌──────────────────┐
                              │   FastAPI        │
                              │   /api/v1/search │
                              └────────┬─────────┘
                                       │
                    ┌──────────────────┼──────────────────┐
                    ▼                  ▼                  ▼
           ┌────────────────┐ ┌────────────────┐ ┌────────────────┐
           │ SearchRequest  │ │ SearchFilters  │ │ Pagination     │
           │ - query (str)  │ │ - content_type │ │ - limit: 10    │
           │ - mode: hybrid │ │ - date_range   │ │ - offset: 0    │
           │ - top_k: 10    │ │ - library_id   │ │                │
           └────────┬───────┘ └────────┬───────┘ └────────┬───────┘
                    │                  │                  │
                    └──────────────────┼──────────────────┘
                                       ▼
                         ┌─────────────────────────┐
                         │      SearchService      │
                         │  app/services/search/   │
                         │     search_service.py   │
                         └────────────┬────────────┘
                                      │
              ┌───────────────────────┼───────────────────────┐
              ▼                       ▼                       ▼
     ┌────────────────┐     ┌────────────────┐     ┌────────────────┐
     │  SEMANTIC      │     │   HYBRID       │     │   KEYWORD      │
     │  (Vector kNN)  │     │ (RRF Fusion)   │     │  (BM25/tsvec)  │
     │                │     │                │     │                │
     │ cosine_distance│     │ Semantic +     │     │ ts_rank_cd     │
     │ HNSW index     │     │ Keyword scores │     │ tsvector index │
     └────────┬───────┘     └────────┬───────┘     └────────┬───────┘
              │                      │                      │
              └──────────────────────┼──────────────────────┘
                                     ▼
                      ┌──────────────────────────────┐
                      │        ChunkRepository       │
                      │  app/db/repositories/        │
                      │     chunk_repository.py      │
                      └──────────────┬───────────────┘
                                     │
                                     ▼
          ┌───────────────────────────────────────────────────────┐
          │                     PostgreSQL + pgvector             │
          │  ┌─────────────────────────────────────────────────┐  │
          │  │              analysis_chunks table               │  │
          │  │  ┌─────────┬──────────┬──────────┬───────────┐  │  │
          │  │  │   id    │ content  │embedding │ metadata  │  │  │
          │  │  │  (UUID) │  (TEXT)  │Vector(1536)│ (JSONB) │  │  │
          │  │  └─────────┴──────────┴──────────┴───────────┘  │  │
          │  │                                                  │  │
          │  │  INDEXES:                                        │  │
          │  │  • HNSW (embedding) - vector_cosine_ops         │  │
          │  │  • GIN (content_tsvector) - full-text search    │  │
          │  │  • BTREE (analysis_id) - FK lookup              │  │
          │  └─────────────────────────────────────────────────┘  │
          └───────────────────────────────────────────────────────┘
```

---

## Search Modes

| Mode | Algorithm | Index | Use Case |
|------|-----------|-------|----------|
| **Semantic** | Cosine distance kNN | HNSW | "Find conceptually similar content" |
| **Keyword** | BM25 (ts_rank_cd) | GIN | "Find exact phrase matches" |
| **Hybrid** | RRF Fusion (k=60) | Both | "Best of both worlds" |

---

## Data Flow

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                          SEARCH REQUEST FLOW                                │
└─────────────────────────────────────────────────────────────────────────────┘

  User Query                    Embedding                      Database
      │                            │                              │
      ▼                            ▼                              ▼
┌──────────┐   1. Parse    ┌──────────────┐   2. Embed    ┌──────────────┐
│ "machine │──────────────▶│ SearchRequest│──────────────▶│ EmbeddingAPI │
│ learning │               │ mode=hybrid  │               │ (OpenAI)     │
│ basics"  │               │ top_k=10     │               └──────┬───────┘
└──────────┘               └──────────────┘                      │
                                  │                              │
                                  ▼                              ▼
                           ┌──────────────────────────────────────────┐
                           │           SearchService.search()         │
                           └──────────────────────────────────────────┘
                                             │
            ┌────────────────────────────────┼────────────────────────────────┐
            │ mode == "semantic"             │ mode == "hybrid"               │
            ▼                                ▼                                │
     ┌──────────────┐               ┌──────────────────┐                      │
     │ Vector kNN   │               │  PARALLEL EXEC   │                      │
     │ ORDER BY     │               │  ┌────────────┐  │                      │
     │ embedding <=>│               │  │Vector kNN  │  │                      │
     │ query_vec    │               │  └─────┬──────┘  │                      │
     │ LIMIT top_k  │               │        │         │                      │
     └──────┬───────┘               │  ┌─────▼──────┐  │                      │
            │                       │  │ BM25 Search│  │                      │
            │                       │  │ ts_rank_cd │  │                      │
            │                       │  └─────┬──────┘  │                      │
            │                       │        │         │                      │
            │                       │  ┌─────▼──────┐  │                      │
            │                       │  │ RRF Fusion │  │                      │
            │                       │  │ k=60       │  │                      │
            │                       │  └─────┬──────┘  │                      │
            │                       └────────┼─────────┘                      │
            │                                │                                │
            └────────────────────────────────┼────────────────────────────────┘
                                             ▼
                                    ┌────────────────┐
                                    │ SearchResult[] │
                                    │ - chunk_id     │
                                    │ - content      │
                                    │ - score        │
                                    │ - snippet      │
                                    │ - metadata     │
                                    └────────────────┘
```

---

## Hybrid Search: RRF Fusion Algorithm

```
┌─────────────────────────────────────────────────────────────────────────────┐
│               RECIPROCAL RANK FUSION (RRF) - k=60                           │
└─────────────────────────────────────────────────────────────────────────────┘

                    Vector Results              BM25 Results
                    (by cosine dist)            (by ts_rank)
                         │                           │
                         ▼                           ▼
                ┌────────────────┐          ┌────────────────┐
                │ 1. chunk_A     │          │ 1. chunk_C     │
                │ 2. chunk_B     │          │ 2. chunk_A     │
                │ 3. chunk_C     │          │ 3. chunk_D     │
                │ 4. chunk_D     │          │ 4. chunk_B     │
                └────────────────┘          └────────────────┘
                         │                           │
                         └───────────┬───────────────┘
                                     ▼
                    ┌─────────────────────────────────┐
                    │   RRF Score Calculation          │
                    │                                  │
                    │   score(d) = Σ 1/(k + rank(d))   │
                    │              for each ranker     │
                    │                                  │
                    │   chunk_A: 1/61 + 1/62 = 0.032   │
                    │   chunk_B: 1/62 + 1/64 = 0.032   │
                    │   chunk_C: 1/63 + 1/61 = 0.032   │
                    │   chunk_D: 1/64 + 1/63 = 0.031   │
                    └─────────────────────────────────┘
                                     │
                                     ▼
                         ┌───────────────────┐
                         │   Final Ranking   │
                         │ 1. chunk_A (0.032)│
                         │ 2. chunk_C (0.032)│
                         │ 3. chunk_B (0.032)│
                         │ 4. chunk_D (0.031)│
                         └───────────────────┘
```

---

## File Structure

```
backend/
├── app/
│   ├── api/
│   │   └── v1/
│   │       └── search.py                 # NEW: Search endpoint
│   │
│   ├── db/
│   │   └── repositories/
│   │       └── chunk_repository.py       # NEW: Chunk data access layer
│   │
│   ├── models/
│   │   └── analysis_chunk.py             # NEW: AnalysisChunk SQLAlchemy model
│   │
│   ├── schemas/
│   │   └── search.py                     # NEW: Search request/response schemas
│   │
│   └── services/
│       └── search/
│           ├── __init__.py               # NEW: Package exports
│           ├── search_service.py         # NEW: Search orchestration
│           ├── vector_search.py          # NEW: pgvector kNN operations
│           ├── keyword_search.py         # NEW: BM25/tsvector operations
│           └── hybrid_fusion.py          # NEW: RRF score fusion
│
├── alembic/
│   └── versions/
│       └── 20251209_add_chunk_indexes.py # NEW: HNSW + GIN indexes
│
└── tests/
    ├── unit/
    │   └── services/
    │       └── search/
    │           └── test_search_service.py    # NEW: Search service tests
    └── integration/
        └── search/
            └── test_search_api.py            # NEW: API integration tests
```

---

## Database Schema

```sql
-- Analysis Chunks Table
CREATE TABLE analysis_chunks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    analysis_id UUID NOT NULL REFERENCES analyses(id) ON DELETE CASCADE,

    -- Content
    content TEXT NOT NULL,
    chunk_type VARCHAR(50) NOT NULL,  -- 'section', 'paragraph', 'code_block'
    sequence_order INTEGER NOT NULL,

    -- Vector embedding (1536 dimensions for text-embedding-3-small)
    embedding VECTOR(1536),

    -- Full-text search (auto-generated tsvector)
    content_tsvector TSVECTOR GENERATED ALWAYS AS (to_tsvector('english', content)) STORED,

    -- Metadata (for filtering)
    metadata JSONB DEFAULT '{}',

    -- Timestamps
    created_at TIMESTAMPTZ DEFAULT NOW() NOT NULL,

    -- Constraints
    CONSTRAINT valid_chunk_type CHECK (chunk_type IN ('section', 'paragraph', 'code_block', 'header'))
);

-- INDEXES FOR SEARCH PERFORMANCE
-- ==============================

-- 1. HNSW Index for Vector Similarity (cosine distance)
CREATE INDEX idx_chunks_embedding_hnsw
    ON analysis_chunks
    USING hnsw (embedding vector_cosine_ops)
    WITH (m = 16, ef_construction = 64);

-- 2. GIN Index for Full-Text Search (BM25-like ranking)
CREATE INDEX idx_chunks_content_tsvector
    ON analysis_chunks
    USING GIN (content_tsvector);

-- 3. BTREE for FK lookups and filtering
CREATE INDEX idx_chunks_analysis_id
    ON analysis_chunks (analysis_id);

-- 4. JSONB Index for metadata filtering
CREATE INDEX idx_chunks_metadata
    ON analysis_chunks
    USING GIN (metadata jsonb_path_ops);
```

---

## API Endpoint

### `POST /api/v1/search`

**Description:** Search chunks using semantic, keyword, or hybrid mode.

**Request Body:**
```json
{
  "query": "machine learning basics",
  "mode": "hybrid",
  "top_k": 10,
  "filters": {
    "content_type": "article",
    "date_range": {
      "start": "2024-01-01",
      "end": "2024-12-31"
    }
  }
}
```

**Response:**
```json
{
  "results": [
    {
      "chunk_id": "550e8400-e29b-41d4-a716-446655440000",
      "analysis_id": "660e8400-e29b-41d4-a716-446655440001",
      "content": "Machine learning is a subset of artificial intelligence...",
      "snippet": "...Machine learning is a <mark>subset</mark> of artificial...",
      "score": 0.92,
      "metadata": {
        "section": "Introduction",
        "path": "Introduction > Overview > Paragraph 1",
        "content_type": "article"
      },
      "created_at": "2024-12-09T10:30:00Z"
    }
  ],
  "total": 42,
  "query": "machine learning basics",
  "mode": "hybrid"
}
```

**Search Modes:**
- `semantic` - Vector similarity only (cosine distance via HNSW)
- `keyword` - Full-text search only (BM25 via ts_rank_cd)
- `hybrid` - Combined using RRF fusion (default)

**Filters:**
- `content_type` - Filter by content type (article, video, repo)
- `date_range` - Filter by created_at range
- `library_id` - Filter by library collection (future)
- `tags` - Filter by metadata tags (future)

---

## Implementation Tasks

### Phase 1: Database Layer
- [ ] Create `AnalysisChunk` SQLAlchemy model
- [ ] Create Alembic migration with indexes (HNSW, GIN, BTREE)
- [ ] Create `ChunkRepository` with search methods

### Phase 2: Search Service
- [ ] Create search schemas (request/response/filters)
- [ ] Implement vector search (`vector_search.py`)
- [ ] Implement keyword search (`keyword_search.py`)
- [ ] Implement hybrid fusion (`hybrid_fusion.py`)
- [ ] Create `SearchService` orchestrator

### Phase 3: API Layer
- [ ] Create `POST /api/v1/search` endpoint
- [ ] Add pagination support (limit/offset)
- [ ] Add snippet generation with highlights

### Phase 4: Testing
- [ ] Unit tests for search service (>80% coverage)
- [ ] Integration tests for search API
- [ ] Performance tests for index efficiency

---

## Key Code Patterns

### Vector kNN Search

```python
from sqlalchemy import select
from pgvector.sqlalchemy import Vector

async def semantic_search(
    session: AsyncSession,
    query_embedding: list[float],
    limit: int = 10,
) -> list[AnalysisChunk]:
    """Vector kNN search using cosine distance."""
    stmt = (
        select(AnalysisChunk)
        .order_by(
            AnalysisChunk.embedding.cosine_distance(query_embedding)
        )
        .limit(limit)
    )
    result = await session.execute(stmt)
    return list(result.scalars().all())
```

### RRF Fusion

```python
def reciprocal_rank_fusion(
    result_lists: list[list[SearchResult]],
    k: int = 60,
) -> list[SearchResult]:
    """Combine multiple ranked lists using RRF."""
    scores: dict[str, float] = {}

    for results in result_lists:
        for rank, result in enumerate(results, start=1):
            chunk_id = str(result.chunk_id)
            scores[chunk_id] = scores.get(chunk_id, 0) + 1 / (k + rank)

    sorted_ids = sorted(scores.keys(), key=lambda x: scores[x], reverse=True)
    return [results_by_id[chunk_id] for chunk_id in sorted_ids]
```

---

## Performance Considerations

**Index Choice - HNSW vs IVFFlat:**
- **HNSW**: Better recall (98%+), faster queries (~10ms), slightly more memory
- **IVFFlat**: Lower memory, requires periodic retraining
- **Decision**: Use HNSW for production workloads

**Query Performance Targets:**
- Semantic search: < 100ms for 10k chunks
- Hybrid search: < 200ms (parallel vector + BM25)
- Pagination: O(1) with OFFSET/LIMIT

**Memory Estimates:**
- HNSW index: ~1.5KB per vector (1536 dims)
- 100k chunks: ~150MB index memory
- Acceptable for single-server MVP

---

## Acceptance Criteria

- [x] POST /api/v1/search accepts query, mode, top_k, filters
- [ ] Semantic mode: Returns top-k chunks by cosine similarity
- [ ] Hybrid mode: Combines vector + keyword with RRF fusion
- [ ] Keyword mode: Uses PostgreSQL full-text search (ts_rank_cd)
- [ ] Filters: content_type, date_range work correctly
- [ ] Snippets: Each result includes highlighted text snippet
- [ ] Metadata: Each result includes path (section > subsection > chunk)
- [ ] Tests: >80% coverage, all CI checks passing

---

## Architectural Decisions

### Why HNSW over IVFFlat?
- Better recall (98%+ vs 90%+ at same query time)
- No periodic retraining required
- Faster query execution
- Trade-off: ~30% more memory usage

### Why RRF over Linear Combination?
- Parameter-free (only k=60 constant)
- Robust to score distribution differences
- Works well when vector and BM25 scores have different scales
- Standard practice in production search systems

### Why Generated TSVECTOR Column?
- PostgreSQL handles index maintenance automatically
- No application-side preprocessing required
- Consistent tokenization across inserts/queries
- Supports English stemming and stop words

---

## References

- [pgvector Documentation](https://github.com/pgvector/pgvector)
- [pgvector-python SQLAlchemy Examples](https://github.com/pgvector/pgvector-python)
- [PostgreSQL Full-Text Search](https://www.postgresql.org/docs/current/textsearch.html)
- [Reciprocal Rank Fusion Paper](https://plg.uwaterloo.ca/~gvcormac/cormacksigir09-rrf.pdf)
- [HNSW Algorithm Paper](https://arxiv.org/abs/1603.09320)

---

## Related Issues

- **Issue #221** (Hierarchical Chunking) - ✅ Prerequisite complete
- **Issue #93** (Embeddings Similarity Search) - Future enhancement
- **Issue #217** (Re-ranker Implementation) - Future enhancement

---

**Last Updated:** December 2024
**Next Steps:** Implement Phase 1 (Database Layer)
