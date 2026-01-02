---
name: db-query-optimization
description: Database query optimization - N+1, EXPLAIN, indexes
version: 1.0.0
tags: [database, performance, optimization, postgresql]
size: atomic
domain: tools
---

# Database Query Optimization

## N+1 Query Problem

```python
# ❌ BAD: N+1 queries (1 + N)
analyses = await session.execute(select(Analysis).limit(8))
for analysis in analyses:
    chunks = await session.execute(
        select(Chunk).where(Chunk.analysis_id == analysis.id)
    )

# ✅ GOOD: Single query with eager loading
from sqlalchemy.orm import selectinload

analyses = await session.execute(
    select(Analysis)
    .options(selectinload(Analysis.chunks))
    .limit(8)
)
```

## Index Types

| Type | Use Case | Example |
|------|----------|---------|
| **B-tree** | Equality, range | `WHERE created_at > '2025-01-01'` |
| **GIN** | Full-text, JSONB | `WHERE tsvector @@ to_tsquery()` |
| **HNSW** | Vector similarity | `ORDER BY embedding <=>` |
| **Hash** | Exact equality | `WHERE id = 'abc123'` |

```sql
-- B-tree for timestamps
CREATE INDEX idx_created ON analyses(created_at DESC);

-- GIN for full-text
CREATE INDEX idx_tsvector ON chunks USING GIN(content_tsvector);

-- HNSW for vectors
CREATE INDEX idx_embedding ON chunks
USING hnsw (embedding vector_cosine_ops)
WITH (m = 16, ef_construction = 64);
```

## EXPLAIN ANALYZE

```sql
EXPLAIN (ANALYZE, BUFFERS, VERBOSE)
SELECT * FROM chunks
WHERE analysis_id = '...'
ORDER BY created_at DESC
LIMIT 10;
```

**Watch for:**
- **Seq Scan** → Add index
- **Execution Time** → Total duration
- **Buffers (shared hit)** → Cache ratio (want high)

## pg_stat_statements

```sql
-- Enable extension
CREATE EXTENSION pg_stat_statements;

-- Find slowest queries
SELECT
    LEFT(query, 60) AS short_query,
    calls,
    ROUND(mean_exec_time::numeric, 2) AS avg_ms
FROM pg_stat_statements
ORDER BY total_exec_time DESC
LIMIT 10;
```

## SkillForge Results

| Optimization | Before | After |
|--------------|--------|-------|
| HNSW vs IVFFlat | 85ms | 5ms |
| Pre-computed tsvector | 50ms | 5ms |
| Eager loading N+1 | 9 queries | 1 query |
