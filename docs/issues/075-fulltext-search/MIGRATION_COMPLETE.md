# Migration Complete - Issue #75 Full-Text Search

## Migration File
**Location**: `/Users/yonatangross/coding/SkillForge/backend/alembic/versions/20251204091348_add_fulltext_search.py`

**Revision ID**: `20251204091348`
**Revises**: `22f9ee8b619b` (add_tutor_session_fields)
**Created**: 2025-12-04 09:13:48

## Changes Applied

### 1. Full-Text Search Column
- Added `search_vector` column (TSVECTOR) to `analyses` table
- Column is nullable to support existing rows
- Auto-populated via trigger function

### 2. Trigger Function & Trigger
- **Function**: `analyses_search_vector_update()`
- **Trigger**: `analyses_search_vector_trigger`
- **Fires**: BEFORE INSERT OR UPDATE of `title`, `url`, `raw_content`
- **Weight Priority**:
  - Title: 'A' (highest)
  - URL: 'B' (medium)
  - Raw Content: 'C' (lowest)

### 3. Indexes Created

#### GIN Index (Full-Text Search)
```sql
CREATE INDEX ix_analyses_search_vector ON analyses USING GIN (search_vector);
```
- Enables fast full-text search queries
- Supports `ts_query` and `ts_rank` operations

#### HNSW Index (Vector Similarity Search)
```sql
CREATE INDEX ix_analyses_embedding_hnsw ON analyses
USING hnsw (content_embedding vector_cosine_ops)
WITH (m = 16, ef_construction = 64);
```
- **CRITICAL**: This index was previously missing!
- Enables fast approximate nearest neighbor search
- Parameters:
  - `m=16`: Connections per layer (speed/accuracy balance)
  - `ef_construction=64`: Index build quality
  - `vector_cosine_ops`: Cosine similarity operator

#### Partial Index (Query Optimization)
```sql
CREATE INDEX ix_analyses_completed ON analyses (created_at DESC)
WHERE status = 'complete';
```
- Optimizes queries for completed analyses
- Reduces index size by filtering on status
- Sorted by `created_at DESC` for recent-first queries

### 4. Data Population
- All existing rows updated with computed `search_vector`
- Uses COALESCE to handle NULL values gracefully

## Downgrade Support
Full rollback capability:
1. Drops all 3 indexes
2. Drops trigger
3. Drops trigger function
4. Drops `search_vector` column

## Testing Checklist

### Pre-Migration
- [ ] Backup database
- [ ] Check current Alembic revision: `alembic current`
- [ ] Verify no pending migrations: `alembic heads`

### Run Migration
```bash
cd backend
alembic upgrade head
```

### Post-Migration Verification
```sql
-- Verify search_vector column exists
SELECT column_name, data_type
FROM information_schema.columns
WHERE table_name = 'analyses' AND column_name = 'search_vector';

-- Verify GIN index
SELECT indexname, indexdef
FROM pg_indexes
WHERE tablename = 'analyses' AND indexname = 'ix_analyses_search_vector';

-- Verify HNSW index
SELECT indexname, indexdef
FROM pg_indexes
WHERE tablename = 'analyses' AND indexname = 'ix_analyses_embedding_hnsw';

-- Verify trigger
SELECT trigger_name, event_manipulation, event_object_table
FROM information_schema.triggers
WHERE trigger_name = 'analyses_search_vector_trigger';

-- Test full-text search
SELECT id, title, ts_rank(search_vector, to_tsquery('english', 'react')) AS rank
FROM analyses
WHERE search_vector @@ to_tsquery('english', 'react')
ORDER BY rank DESC
LIMIT 5;

-- Test vector similarity (requires existing embeddings)
SELECT id, title,
  1 - (content_embedding <=> '[0.1, 0.2, ...]'::vector(768)) AS similarity
FROM analyses
WHERE content_embedding IS NOT NULL
ORDER BY content_embedding <=> '[0.1, 0.2, ...]'::vector(768)
LIMIT 5;
```

## Performance Notes

### Expected Impact
- **Full-text queries**: < 50ms for most queries (with GIN index)
- **Vector queries**: < 100ms for k-NN searches (with HNSW index)
- **Index size**: ~15-20% of raw content size (GIN) + ~10% (HNSW)
- **Insert/Update overhead**: ~5-10ms per row (trigger execution)

### Monitoring Recommendations
```sql
-- Index usage statistics
SELECT schemaname, tablename, indexname, idx_scan, idx_tup_read, idx_tup_fetch
FROM pg_stat_user_indexes
WHERE tablename = 'analyses';

-- Index size
SELECT indexrelname, pg_size_pretty(pg_relation_size(indexrelid))
FROM pg_stat_user_indexes
WHERE schemaname = 'public' AND tablename = 'analyses';
```

## Integration with API

### Endpoints Updated
See `API_SPEC.md` for complete endpoint specifications:
- `GET /api/v1/analyses/search` - Hybrid search endpoint
- Query parameters support both full-text and vector search

### Usage Example
```python
# Full-text search
from sqlalchemy import func

query = session.query(Analysis).filter(
    Analysis.search_vector.op('@@')(func.to_tsquery('english', 'react & typescript'))
).order_by(
    func.ts_rank(Analysis.search_vector, func.to_tsquery('english', 'react & typescript')).desc()
)

# Vector similarity
from pgvector.sqlalchemy import Vector

embedding = [0.1, 0.2, ...]  # 768-dimensional vector
query = session.query(Analysis).order_by(
    Analysis.content_embedding.cosine_distance(embedding)
).limit(10)
```

## Next Steps
1. Run migration on development database
2. Test full-text search queries
3. Test vector similarity queries
4. Update API endpoints to use new indexes
5. Run migration on staging/production

## References
- Issue: #75 Full-Text Search
- Implementation Plan: `IMPLEMENTATION_PLAN.md`
- API Specification: `API_SPEC.md`
- Testing Strategy: `TESTING_STRATEGY.md`
