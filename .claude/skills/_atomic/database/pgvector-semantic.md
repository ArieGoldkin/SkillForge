---
name: pgvector-semantic
description: Vector similarity search with PGVector
version: 1.0.0
tags: [pgvector, vector, semantic, embeddings, similarity]
size: atomic
domain: database
---

# PGVector Semantic Search

## How It Works

1. Embed query: `"database indexing"` → `[0.23, -0.15, ..., 0.42]` (1024 dims)
2. Find nearest neighbors: `ORDER BY embedding <=> query_embedding LIMIT 10`
3. Returns: Conceptually similar documents (even with different words)

## Schema

```sql
CREATE TABLE chunks (
    id UUID PRIMARY KEY,
    document_id UUID REFERENCES documents(id),
    content TEXT NOT NULL,
    embedding vector(1024),  -- Voyage AI: 1024 dims
    created_at TIMESTAMP DEFAULT NOW()
);

-- HNSW index for fast similarity search
CREATE INDEX idx_chunks_embedding ON chunks
    USING hnsw (embedding vector_cosine_ops)
    WITH (m = 16, ef_construction = 64);
```

## Basic Query

```sql
-- Find 10 most similar chunks
SELECT id, content, embedding <=> $1 AS distance
FROM chunks
WHERE embedding IS NOT NULL
ORDER BY embedding <=> $1
LIMIT 10;
```

## SQLAlchemy Implementation

```python
from pgvector.sqlalchemy import Vector
from sqlalchemy import select

async def semantic_search(
    query_embedding: list[float],
    top_k: int = 10,
    tenant_id: UUID | None = None
) -> list[Chunk]:
    """Vector similarity search."""

    query = (
        select(Chunk)
        .where(Chunk.embedding.isnot(None))
        .order_by(Chunk.embedding.cosine_distance(query_embedding))
        .limit(top_k)
    )

    if tenant_id:
        query = query.join(Document).where(Document.tenant_id == tenant_id)

    result = await session.execute(query)
    return result.scalars().all()
```

## Distance Functions

| Function | Operator | Use Case |
|----------|----------|----------|
| Cosine | `<=>` | Text embeddings (normalized) |
| L2 (Euclidean) | `<->` | Image embeddings |
| Inner Product | `<#>` | When vectors aren't normalized |

```sql
-- Cosine distance (most common)
ORDER BY embedding <=> query_embedding

-- L2 distance
ORDER BY embedding <-> query_embedding

-- Inner product (negative for max)
ORDER BY embedding <#> query_embedding
```

## Similarity Threshold

```python
# Convert distance to similarity
# Cosine distance: 0 = identical, 2 = opposite
similarity = 1 - distance

# Filter by threshold
MIN_SIMILARITY = 0.75
results = [r for r in results if (1 - r.distance) >= MIN_SIMILARITY]
```

## Strengths & Weaknesses

**Strengths:**
- Captures semantic meaning
- Works across languages
- Handles synonyms ("car" matches "automobile")

**Weaknesses:**
- Slow for exact keyword matches
- Sensitive to embedding quality
- Doesn't handle rare technical terms well
