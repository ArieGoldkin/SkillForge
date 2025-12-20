# Embedding Pipeline Schema Design (Issue #215)

## Executive Summary

This document outlines the database schema hardening for the embedding pipeline to support token-aware chunking with overlap, batch embedding, hash-based deduplication, comprehensive per-chunk metadata, and search performance optimization.

---

## 1. Current Schema Analysis

### 1.1 Existing Tables

#### `analyses` table
```sql
CREATE TABLE analyses (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    url TEXT NOT NULL,
    content_type VARCHAR(50) NOT NULL,  -- 'article', 'video', 'repo'
    title TEXT,
    raw_content TEXT,
    content_embedding VECTOR(1536),  -- OpenAI text-embedding-3-small
    search_vector TSVECTOR,  -- Full-text search (auto-populated by trigger)
    extraction_metadata JSONB,
    status VARCHAR(50) NOT NULL DEFAULT 'pending',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Indexes on analyses
CREATE INDEX ix_analyses_url ON analyses (url);
CREATE INDEX ix_analyses_status ON analyses (status);
CREATE INDEX ix_analyses_search_vector ON analyses USING GIN (search_vector);
CREATE INDEX ix_analyses_embedding_hnsw ON analyses
    USING hnsw (content_embedding vector_cosine_ops)
    WITH (m = 16, ef_construction = 64);
CREATE INDEX ix_analyses_completed ON analyses (created_at)
    WHERE status = 'complete';
```

#### `analysis_chunks` table (Created: 2025-12-09)
```sql
CREATE TABLE analysis_chunks (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    analysis_id UUID NOT NULL REFERENCES analyses(id),

    -- Chunking metadata
    granularity VARCHAR(20) NOT NULL,  -- 'coarse' | 'fine' | 'summary'
    path JSONB NOT NULL,  -- Hierarchical path: ["section", "subsection", "paragraph"]
    section_title TEXT,
    chunk_idx INTEGER NOT NULL,
    chunk_total INTEGER NOT NULL,

    -- Content metadata
    content_type VARCHAR(50),  -- Denormalized from analyses for filtering
    language VARCHAR(20),
    hash VARCHAR(128) NOT NULL,  -- SHA256 hash for deduplication

    -- Embedding metadata
    model VARCHAR(100),
    model_version VARCHAR(50),

    -- Content preview
    snippet TEXT,  -- First ~200 chars for preview/search

    -- Vector embedding
    vector VECTOR(1536) NOT NULL,

    -- Timestamps
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Existing indexes
CREATE INDEX ix_analysis_chunks_analysis_id ON analysis_chunks (analysis_id);
CREATE INDEX ix_analysis_chunks_granularity ON analysis_chunks (granularity);
```

### 1.2 Missing Features (To Be Added)

The current schema is well-structured but lacks:

1. **HNSW index** on `analysis_chunks.vector` for fast semantic search
2. **Full-text search** on `analysis_chunks.snippet` (tsvector + GIN index)
3. **Composite indexes** for common query patterns
4. **Hash-based deduplication index** for efficient cache lookups
5. **Metadata indexes** for filtering by content_type, created_at

---

## 2. Proposed Schema Enhancements

### 2.1 New Columns

#### Add to `analysis_chunks` table:
```sql
-- Add full-text search vector (auto-populated by trigger)
ALTER TABLE analysis_chunks ADD COLUMN content_tsvector TSVECTOR;

-- Optional: Add token count for telemetry (useful for cost tracking)
ALTER TABLE analysis_chunks ADD COLUMN token_count INTEGER;

-- Optional: Add embedding generation metadata
ALTER TABLE analysis_chunks ADD COLUMN embedding_latency_ms FLOAT;
ALTER TABLE analysis_chunks ADD COLUMN was_truncated BOOLEAN DEFAULT FALSE;
```

### 2.2 Performance Indexes

#### 2.2.1 Vector Search (HNSW)
```sql
-- HNSW index for fast approximate nearest neighbor search
-- Uses cosine distance (optimal for normalized vectors)
CREATE INDEX ix_analysis_chunks_vector_hnsw ON analysis_chunks
    USING hnsw (vector vector_cosine_ops)
    WITH (m = 16, ef_construction = 64);

-- Index parameters:
-- - m=16: Number of connections per layer (balance speed/accuracy)
-- - ef_construction=64: Dynamic candidate list size during build
-- - vector_cosine_ops: Optimized for cosine similarity
```

#### 2.2.2 Full-Text Search (GIN)
```sql
-- GIN index for fast keyword search
CREATE INDEX ix_analysis_chunks_content_tsvector ON analysis_chunks
    USING GIN (content_tsvector);

-- Trigger to auto-populate content_tsvector
CREATE OR REPLACE FUNCTION analysis_chunks_tsvector_update() RETURNS trigger AS $$
BEGIN
  NEW.content_tsvector :=
    setweight(to_tsvector('english', COALESCE(NEW.section_title, '')), 'A') ||
    setweight(to_tsvector('english', COALESCE(NEW.snippet, '')), 'B');
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER analysis_chunks_tsvector_trigger
BEFORE INSERT OR UPDATE OF section_title, snippet ON analysis_chunks
FOR EACH ROW EXECUTE FUNCTION analysis_chunks_tsvector_update();
```

#### 2.2.3 Hash-Based Deduplication
```sql
-- Unique index for hash-based deduplication
-- Includes model+version to allow same content with different models
CREATE INDEX ix_analysis_chunks_hash_model ON analysis_chunks (hash, model, model_version);

-- Optional: Unique constraint if strict deduplication is required
-- CREATE UNIQUE INDEX uq_analysis_chunks_hash_model ON analysis_chunks (hash, model, model_version);
```

#### 2.2.4 Composite Indexes for Common Query Patterns
```sql
-- Filter by analysis + granularity (common in hierarchical search)
CREATE INDEX ix_analysis_chunks_analysis_granularity
    ON analysis_chunks (analysis_id, granularity);

-- Filter by content_type + created_at (common in filtered search)
CREATE INDEX ix_analysis_chunks_content_type_created
    ON analysis_chunks (content_type, created_at DESC)
    WHERE content_type IS NOT NULL;

-- Filter by hash for cache lookups (exact match)
CREATE INDEX ix_analysis_chunks_hash
    ON analysis_chunks (hash);
```

### 2.3 Database Triggers & Functions

#### 2.3.1 Auto-update Timestamps
```sql
-- Ensure updated_at is automatically updated
CREATE OR REPLACE FUNCTION update_updated_at_column() RETURNS trigger AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER update_analysis_chunks_updated_at
BEFORE UPDATE ON analysis_chunks
FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
```

---

## 3. Schema Design Decisions

### 3.1 Metadata Storage Strategy

**Decision: Column-based vs JSONB**

We chose **individual columns** for frequently queried metadata (granularity, content_type, chunk_idx) and **JSONB** for hierarchical path data.

**Rationale:**
- Individual columns enable efficient B-tree indexing
- JSONB `path` field supports flexible hierarchical queries with GIN indexes
- Denormalized `content_type` from `analyses` enables chunk-level filtering without joins

**Trade-offs:**
- Slightly higher storage overhead vs pure JSONB
- Better query performance (10-100x faster for indexed columns)
- Simpler query syntax for common filters

### 3.2 Vector Indexing Strategy

**Decision: HNSW with cosine distance**

We chose **HNSW (Hierarchical Navigable Small World)** with `vector_cosine_ops`.

**Rationale:**
- HNSW provides best approximate nearest neighbor (ANN) performance for high-dimensional vectors
- Cosine distance is optimal for normalized embeddings (L2 norm = 1.0)
- Tuning parameters (m=16, ef_construction=64) balance build time and query performance

**Trade-offs:**
- Index build time: ~2-5 seconds per 10k vectors
- Query latency: <5ms for top-10 search (vs 100ms+ without index)
- Index size: ~1.5x vector data size

**Alternatives Considered:**
- IVFFlat: Faster build time but lower accuracy and requires manual tuning (nlist parameter)
- Flat (no index): Only viable for <10k vectors

### 3.3 Hash-Based Deduplication

**Decision: Non-unique hash index**

We chose a **non-unique index** on `(hash, model, model_version)` instead of a unique constraint.

**Rationale:**
- Allows same content to be embedded with different models
- Enables re-embedding if model version changes
- Supports cache invalidation strategies

**Trade-offs:**
- Application-level deduplication logic required (vs database enforcement)
- More flexible but requires careful cache hit logic

**Cache Lookup Query:**
```sql
-- Check if chunk already exists for this content + model
SELECT * FROM analysis_chunks
WHERE hash = $1 AND model = $2 AND model_version = $3
LIMIT 1;
```

### 3.4 Full-Text Search Integration

**Decision: Dedicated tsvector column with trigger**

We chose a **dedicated `content_tsvector` column** auto-populated by trigger.

**Rationale:**
- GIN index on tsvector is 10-100x faster than on-the-fly `to_tsvector()`
- Trigger ensures consistency without application-level logic
- Weighted search (section_title='A', snippet='B') improves relevance

**Trade-offs:**
- Additional storage (~10-20% of text content)
- Minimal write overhead (trigger adds <1ms)

---

## 4. Migration Strategy

### 4.1 Migration Phases

#### Phase 1: Add Missing Indexes (Non-blocking)
```sql
-- CONCURRENT index creation (no table locks)
CREATE INDEX CONCURRENTLY ix_analysis_chunks_vector_hnsw
    ON analysis_chunks USING hnsw (vector vector_cosine_ops)
    WITH (m = 16, ef_construction = 64);

CREATE INDEX CONCURRENTLY ix_analysis_chunks_hash_model
    ON analysis_chunks (hash, model, model_version);

CREATE INDEX CONCURRENTLY ix_analysis_chunks_analysis_granularity
    ON analysis_chunks (analysis_id, granularity);
```

**Estimated Time:** ~30 seconds per 10k rows (HNSW index), <5 seconds for B-tree indexes

#### Phase 2: Add Full-Text Search (Requires brief lock)
```sql
-- Add column (fast, no data rewrite)
ALTER TABLE analysis_chunks ADD COLUMN content_tsvector TSVECTOR;

-- Create trigger function
CREATE OR REPLACE FUNCTION analysis_chunks_tsvector_update() RETURNS trigger AS $$
BEGIN
  NEW.content_tsvector :=
    setweight(to_tsvector('english', COALESCE(NEW.section_title, '')), 'A') ||
    setweight(to_tsvector('english', COALESCE(NEW.snippet, '')), 'B');
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Create trigger
CREATE TRIGGER analysis_chunks_tsvector_trigger
BEFORE INSERT OR UPDATE OF section_title, snippet ON analysis_chunks
FOR EACH ROW EXECUTE FUNCTION analysis_chunks_tsvector_update();

-- Backfill existing rows (batched to avoid long locks)
UPDATE analysis_chunks SET content_tsvector =
  setweight(to_tsvector('english', COALESCE(section_title, '')), 'A') ||
  setweight(to_tsvector('english', COALESCE(snippet, '')), 'B')
WHERE content_tsvector IS NULL;

-- Create index
CREATE INDEX CONCURRENTLY ix_analysis_chunks_content_tsvector
    ON analysis_chunks USING GIN (content_tsvector);
```

**Estimated Time:** <5 seconds for schema changes, ~1 second per 1k rows for backfill

#### Phase 3: Optional Telemetry Columns (Non-blocking)
```sql
ALTER TABLE analysis_chunks ADD COLUMN token_count INTEGER;
ALTER TABLE analysis_chunks ADD COLUMN embedding_latency_ms FLOAT;
ALTER TABLE analysis_chunks ADD COLUMN was_truncated BOOLEAN DEFAULT FALSE;
```

### 4.2 Rollback Plan

```sql
-- Phase 1 Rollback
DROP INDEX CONCURRENTLY IF EXISTS ix_analysis_chunks_vector_hnsw;
DROP INDEX CONCURRENTLY IF EXISTS ix_analysis_chunks_hash_model;
DROP INDEX CONCURRENTLY IF EXISTS ix_analysis_chunks_analysis_granularity;

-- Phase 2 Rollback
DROP TRIGGER IF EXISTS analysis_chunks_tsvector_trigger ON analysis_chunks;
DROP FUNCTION IF EXISTS analysis_chunks_tsvector_update();
DROP INDEX CONCURRENTLY IF EXISTS ix_analysis_chunks_content_tsvector;
ALTER TABLE analysis_chunks DROP COLUMN IF EXISTS content_tsvector;

-- Phase 3 Rollback
ALTER TABLE analysis_chunks DROP COLUMN IF EXISTS token_count;
ALTER TABLE analysis_chunks DROP COLUMN IF EXISTS embedding_latency_ms;
ALTER TABLE analysis_chunks DROP COLUMN IF EXISTS was_truncated;
```

### 4.3 Zero-Downtime Deployment

**Strategy: Blue-Green with CONCURRENT operations**

1. **Pre-migration health check:**
   ```sql
   SELECT COUNT(*) FROM analysis_chunks;  -- Verify table is accessible
   ```

2. **Apply migrations with CONCURRENTLY:**
   - All index creations use `CREATE INDEX CONCURRENTLY`
   - No table-level locks except brief ALTER TABLE for column additions

3. **Post-migration validation:**
   ```sql
   -- Verify indexes exist
   SELECT indexname FROM pg_indexes
   WHERE tablename = 'analysis_chunks';

   -- Verify trigger is active
   SELECT tgname FROM pg_trigger
   WHERE tgrelid = 'analysis_chunks'::regclass;
   ```

4. **Performance benchmarking:**
   ```sql
   -- Test semantic search performance
   EXPLAIN ANALYZE
   SELECT * FROM analysis_chunks
   ORDER BY vector <=> '[0.1, 0.2, ...]'::vector
   LIMIT 10;

   -- Test keyword search performance
   EXPLAIN ANALYZE
   SELECT * FROM analysis_chunks
   WHERE content_tsvector @@ plainto_tsquery('english', 'machine learning')
   ORDER BY ts_rank_cd(content_tsvector, plainto_tsquery('english', 'machine learning')) DESC
   LIMIT 10;
   ```

---

## 5. Query Optimization Patterns

### 5.1 Semantic Search (Vector kNN)
```sql
-- Optimized: Uses HNSW index
SELECT id, analysis_id, snippet, (1 - (vector <=> $1)) AS similarity
FROM analysis_chunks
WHERE content_type = $2  -- Filter before kNN (if selective)
ORDER BY vector <=> $1  -- Cosine distance
LIMIT 10;

-- Query plan should show: Index Scan using ix_analysis_chunks_vector_hnsw
```

### 5.2 Keyword Search (Full-Text)
```sql
-- Optimized: Uses GIN index on content_tsvector
SELECT id, analysis_id, snippet,
       ts_rank_cd(content_tsvector, query) AS rank
FROM analysis_chunks, plainto_tsquery('english', $1) query
WHERE content_tsvector @@ query
ORDER BY rank DESC
LIMIT 10;

-- Query plan should show: Bitmap Index Scan on ix_analysis_chunks_content_tsvector
```

### 5.3 Hybrid Search (RRF Fusion)
```sql
-- Semantic results (CTE)
WITH semantic AS (
    SELECT id, (1 - (vector <=> $1)) AS score
    FROM analysis_chunks
    WHERE content_type = $3
    ORDER BY vector <=> $1
    LIMIT 20
),
-- Keyword results (CTE)
keyword AS (
    SELECT id, ts_rank_cd(content_tsvector, query) AS score
    FROM analysis_chunks, plainto_tsquery('english', $2) query
    WHERE content_tsvector @@ query AND content_type = $3
    ORDER BY score DESC
    LIMIT 20
),
-- RRF fusion
rrf AS (
    SELECT s.id, 1.0 / (60 + row_number() OVER (ORDER BY s.score DESC)) AS rrf_score
    FROM semantic s
    UNION ALL
    SELECT k.id, 1.0 / (60 + row_number() OVER (ORDER BY k.score DESC)) AS rrf_score
    FROM keyword k
)
SELECT rrf.id, SUM(rrf.rrf_score) AS final_score
FROM rrf
GROUP BY rrf.id
ORDER BY final_score DESC
LIMIT 10;
```

### 5.4 Hash-Based Cache Lookup
```sql
-- Deduplication check before embedding
SELECT id, vector FROM analysis_chunks
WHERE hash = $1  -- SHA256 of normalized text
  AND model = $2  -- e.g., 'text-embedding-3-small'
  AND model_version = $3  -- e.g., '1.0'
LIMIT 1;

-- Query plan should show: Index Scan using ix_analysis_chunks_hash_model
```

---

## 6. Index Maintenance & Monitoring

### 6.1 Index Size Monitoring
```sql
-- Check index sizes
SELECT
    schemaname,
    tablename,
    indexname,
    pg_size_pretty(pg_relation_size(indexname::regclass)) AS index_size
FROM pg_indexes
WHERE tablename = 'analysis_chunks'
ORDER BY pg_relation_size(indexname::regclass) DESC;
```

### 6.2 Index Usage Statistics
```sql
-- Check if indexes are being used
SELECT
    schemaname,
    tablename,
    indexname,
    idx_scan,  -- Number of index scans
    idx_tup_read,  -- Tuples read from index
    idx_tup_fetch  -- Tuples fetched from table
FROM pg_stat_user_indexes
WHERE tablename = 'analysis_chunks'
ORDER BY idx_scan DESC;
```

### 6.3 HNSW Index Tuning
```sql
-- Query-time tuning for HNSW accuracy/speed tradeoff
SET hnsw.ef_search = 100;  -- Default: 40, Range: 1-1000
-- Higher values = better accuracy but slower queries
```

### 6.4 Vacuum & Analyze
```sql
-- Regular maintenance (recommended: daily for analysis_chunks)
VACUUM ANALYZE analysis_chunks;

-- Check table bloat
SELECT
    schemaname,
    tablename,
    pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) AS total_size,
    pg_size_pretty(pg_relation_size(schemaname||'.'||tablename)) AS table_size,
    pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename) - pg_relation_size(schemaname||'.'||tablename)) AS index_size
FROM pg_tables
WHERE tablename = 'analysis_chunks';
```

---

## 7. Data Integrity & Constraints

### 7.1 Foreign Key Constraints
```sql
-- Already exists: analysis_id references analyses(id)
-- Ensure cascading deletes are handled properly
ALTER TABLE analysis_chunks
DROP CONSTRAINT IF EXISTS analysis_chunks_analysis_id_fkey,
ADD CONSTRAINT analysis_chunks_analysis_id_fkey
    FOREIGN KEY (analysis_id) REFERENCES analyses(id)
    ON DELETE CASCADE;
```

### 7.2 Check Constraints
```sql
-- Ensure granularity values are valid
ALTER TABLE analysis_chunks
ADD CONSTRAINT chk_granularity
    CHECK (granularity IN ('coarse', 'fine', 'summary'));

-- Ensure chunk_idx is non-negative
ALTER TABLE analysis_chunks
ADD CONSTRAINT chk_chunk_idx_positive
    CHECK (chunk_idx >= 0);

-- Ensure chunk_total is positive
ALTER TABLE analysis_chunks
ADD CONSTRAINT chk_chunk_total_positive
    CHECK (chunk_total > 0);

-- Ensure chunk_idx < chunk_total
ALTER TABLE analysis_chunks
ADD CONSTRAINT chk_chunk_idx_lt_total
    CHECK (chunk_idx < chunk_total);
```

### 7.3 Orphan Cleanup Policy

**Strategy: Periodic cleanup of orphaned chunks**

```sql
-- Find orphaned chunks (analysis_id doesn't exist in analyses)
SELECT COUNT(*) FROM analysis_chunks ac
LEFT JOIN analyses a ON ac.analysis_id = a.id
WHERE a.id IS NULL;

-- Delete orphaned chunks (run periodically, e.g., weekly)
DELETE FROM analysis_chunks ac
WHERE NOT EXISTS (
    SELECT 1 FROM analyses a WHERE a.id = ac.analysis_id
);
```

**Recommendation:** Run as scheduled job (cron/k8s CronJob) with:
- Frequency: Weekly
- Logging: Log number of deleted rows
- Alert threshold: >1000 orphaned rows indicates FK cascade issue

---

## 8. Performance Benchmarks (Estimated)

Based on typical pgvector + PostgreSQL performance:

| Operation | Without Indexes | With Indexes | Speedup |
|-----------|----------------|--------------|---------|
| Semantic search (10k rows) | 150-300ms | 3-8ms | 30-50x |
| Keyword search (10k rows) | 50-100ms | 2-5ms | 20-25x |
| Hybrid search (10k rows) | 200-400ms | 5-12ms | 30-40x |
| Hash cache lookup | 10-20ms | <1ms | 15-20x |
| Batch insert (100 chunks) | 200-400ms | 200-400ms | 1x (no change) |

**Scaling Projections:**

| Chunk Count | HNSW Build Time | Query Latency (p95) | Index Size |
|-------------|----------------|---------------------|------------|
| 10k | ~5s | 5ms | ~50MB |
| 100k | ~45s | 8ms | ~500MB |
| 1M | ~8min | 12ms | ~5GB |
| 10M | ~80min | 20ms | ~50GB |

**Note:** HNSW provides sub-linear query time scaling (O(log N)) vs linear (O(N)) for full scans.

---

## 9. Testing & Validation

### 9.1 Schema Validation Tests
```python
# Test that all indexes exist
def test_schema_indexes_exist(db_session):
    result = db_session.execute("""
        SELECT indexname FROM pg_indexes
        WHERE tablename = 'analysis_chunks'
    """)
    indexes = {row[0] for row in result}

    required_indexes = {
        'ix_analysis_chunks_vector_hnsw',
        'ix_analysis_chunks_content_tsvector',
        'ix_analysis_chunks_hash_model',
        'ix_analysis_chunks_analysis_granularity',
    }

    assert required_indexes.issubset(indexes)

# Test that triggers exist
def test_schema_triggers_exist(db_session):
    result = db_session.execute("""
        SELECT tgname FROM pg_trigger
        WHERE tgrelid = 'analysis_chunks'::regclass
    """)
    triggers = {row[0] for row in result}

    assert 'analysis_chunks_tsvector_trigger' in triggers
```

### 9.2 Performance Tests
```python
# Test semantic search performance
def test_semantic_search_performance(db_session, sample_embedding):
    import time

    start = time.perf_counter()
    result = db_session.execute("""
        SELECT * FROM analysis_chunks
        ORDER BY vector <=> :embedding
        LIMIT 10
    """, {"embedding": sample_embedding})
    latency_ms = (time.perf_counter() - start) * 1000

    assert latency_ms < 50  # p95 should be <50ms
    assert result.rowcount == 10
```

### 9.3 Data Integrity Tests
```python
# Test hash deduplication
def test_hash_deduplication(chunk_repo, sample_chunk_data):
    # Insert first chunk
    chunk1 = chunk_repo.create(sample_chunk_data)

    # Try to insert duplicate (same hash + model)
    cached = chunk_repo.find_by_hash(
        hash=sample_chunk_data['hash'],
        model=sample_chunk_data['model'],
        model_version=sample_chunk_data['model_version'],
    )

    assert cached is not None
    assert cached.id == chunk1.id
```

---

## 10. Appendix

### 10.1 Related Documentation
- PGVector: https://github.com/pgvector/pgvector
- PostgreSQL Full-Text Search: https://www.postgresql.org/docs/current/textsearch.html
- HNSW Algorithm: https://arxiv.org/abs/1603.09320
- Reciprocal Rank Fusion: https://plg.uwaterloo.ca/~gvcormac/cormacksigir09-rrf.pdf

### 10.2 SQLAlchemy Model Reference
See: `/Users/yonatangross/coding/SkillForge/backend/app/models/analysis_chunk.py`

### 10.3 Migration Files
- Initial chunks table: `20251209120000_add_analysis_chunks.py`
- Hardening migration: `20251210_harden_embedding_pipeline.py` (to be created)

---

**Document Version:** 1.0
**Last Updated:** 2025-12-10
**Author:** Backend System Architect (Claude Agent)
**Status:** Ready for Review
