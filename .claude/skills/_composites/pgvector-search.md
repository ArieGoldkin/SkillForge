---
name: pgvector-search
description: Production hybrid search with PGVector + BM25
version: 1.0.0
type: composite
includes:
  - database/pgvector-semantic
  - database/pgvector-keyword
  - database/pgvector-hybrid-rrf
  - database/pgvector-indexing
trigger: "**/search/**/*.py"
---

# PGVector Hybrid Search

Production-grade semantic + keyword search using PostgreSQL.

## When to Use

- Building semantic search (RAG, knowledge bases)
- Implementing hybrid retrieval (vector + keyword)
- Optimizing PGVector performance
- Working with large document collections

## Architecture Overview

```
┌──────────────────────────────────────────────────────────────┐
│                      HYBRID SEARCH                            │
├──────────────────────────────────────────────────────────────┤
│                                                              │
│  Query                                                       │
│    │                                                         │
│    ├──▶ [Embed] ──▶ Vector Search (PGVector) ──▶ Top 30     │
│    │                                                         │
│    └──▶ [Tokenize] ──▶ Keyword Search (BM25) ──▶ Top 30     │
│                              │                               │
│                              ▼                               │
│                   ┌─────────────────────┐                   │
│                   │   RRF Fusion        │                   │
│                   │   (rank-based)      │                   │
│                   └─────────────────────┘                   │
│                              │                               │
│                              ▼                               │
│                        Top 10 Results                        │
│                                                              │
└──────────────────────────────────────────────────────────────┘
```

## Included Skills

1. **pgvector-semantic** - Vector similarity with cosine distance
2. **pgvector-keyword** - Full-text search with BM25 ranking
3. **pgvector-hybrid-rrf** - Reciprocal Rank Fusion combination
4. **pgvector-indexing** - HNSW vs IVFFlat strategies

## Quick Start

```python
async def hybrid_search(
    query: str,
    query_embedding: list[float],
    top_k: int = 10
) -> list[Chunk]:
    """Hybrid search with RRF fusion."""

    K = 60  # RRF smoothing constant
    FETCH = top_k * 3  # Fetch 3x for better coverage

    # Vector search with ranks
    vector_results = await semantic_search(query_embedding, FETCH)

    # Keyword search with ranks
    keyword_results = await keyword_search(query, FETCH)

    # RRF fusion
    scores = {}
    for rank, chunk in enumerate(vector_results, 1):
        scores[chunk.id] = 1.0 / (K + rank)

    for rank, chunk in enumerate(keyword_results, 1):
        scores[chunk.id] = scores.get(chunk.id, 0) + 1.0 / (K + rank)

    # Sort by RRF score
    top_ids = sorted(scores, key=scores.get, reverse=True)[:top_k]
    return await fetch_chunks(top_ids)
```

## Schema

```sql
CREATE TABLE chunks (
    id UUID PRIMARY KEY,
    content TEXT NOT NULL,

    -- Vector embedding (1024 dims for Voyage AI)
    embedding vector(1024),

    -- Pre-computed tsvector for full-text search
    content_tsvector tsvector GENERATED ALWAYS AS (
        to_tsvector('english', content)
    ) STORED
);

-- HNSW for vector search
CREATE INDEX idx_embedding ON chunks
    USING hnsw (embedding vector_cosine_ops);

-- GIN for full-text search
CREATE INDEX idx_tsvector ON chunks
    USING gin (content_tsvector);
```

## Performance Results

SkillForge golden dataset (98 queries):
- **Pass rate:** 91.6%
- **MRR:** 0.686
- **Hybrid vs Vector-only:** +5% pass rate

## See Also

- [pgvector-semantic](../_atomic/database/pgvector-semantic.md)
- [pgvector-keyword](../_atomic/database/pgvector-keyword.md)
- [pgvector-hybrid-rrf](../_atomic/database/pgvector-hybrid-rrf.md)
- [pgvector-indexing](../_atomic/database/pgvector-indexing.md)
