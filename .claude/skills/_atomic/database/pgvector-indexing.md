---
name: pgvector-indexing
description: HNSW vs IVFFlat indexing strategies
version: 1.0.0
tags: [pgvector, hnsw, ivfflat, indexing, performance]
size: atomic
domain: database
---

# PGVector Indexing Strategies

## HNSW (Recommended)

Hierarchical Navigable Small World graphs.

```sql
CREATE INDEX idx_embedding ON chunks
    USING hnsw (embedding vector_cosine_ops)
    WITH (m = 16, ef_construction = 64);
```

**Parameters:**
- `m`: Max connections per node (default: 16, higher = more accurate, slower build)
- `ef_construction`: Search width during build (default: 64, higher = better quality)

**Query tuning:**
```sql
SET hnsw.ef_search = 100;  -- Higher = more accurate, slower
```

## IVFFlat (Legacy)

Inverted File with Flat quantization.

```sql
CREATE INDEX idx_embedding ON chunks
    USING ivfflat (embedding vector_cosine_ops)
    WITH (lists = 100);
```

**Parameters:**
- `lists`: Number of clusters (rule: rows/1000, min 100)

**Query tuning:**
```sql
SET ivfflat.probes = 10;  -- Check 10 lists (default: 1)
```

## Comparison

| Feature | HNSW | IVFFlat |
|---------|------|---------|
| Query speed | **10-100x faster** | Slower |
| Build speed | Slower | **Faster** |
| Memory | Higher | Lower |
| Accuracy | **Higher** | Lower |
| Best for | **Production** | Prototyping |

## Distance Operators

| Distance | Operator | Index Ops |
|----------|----------|-----------|
| Cosine | `<=>` | `vector_cosine_ops` |
| L2 | `<->` | `vector_l2_ops` |
| Inner Product | `<#>` | `vector_ip_ops` |

```sql
-- Use matching ops for index
CREATE INDEX idx_cosine ON chunks
    USING hnsw (embedding vector_cosine_ops);

-- Queries MUST use <=> for index to work
SELECT * FROM chunks ORDER BY embedding <=> $1 LIMIT 10;
```

## Index Maintenance

```sql
-- Check index size
SELECT pg_size_pretty(pg_relation_size('idx_chunks_embedding'));

-- Reindex after bulk inserts
REINDEX INDEX idx_chunks_embedding;

-- Analyze for query planner
ANALYZE chunks;
```

## When to Use Each

**HNSW (default choice):**
- Production workloads
- Need fast queries
- < 10M vectors
- Can afford longer index builds

**IVFFlat:**
- Prototyping/development
- Very large datasets (10M+)
- Memory constrained
- Frequent bulk updates

## Performance Tips

```sql
-- Increase maintenance_work_mem for faster index builds
SET maintenance_work_mem = '1GB';

-- Parallel index creation (PG 15+)
SET max_parallel_maintenance_workers = 4;

-- Monitor index usage
SELECT indexrelname, idx_scan, idx_tup_read
FROM pg_stat_user_indexes
WHERE indexrelname LIKE '%embedding%';
```
