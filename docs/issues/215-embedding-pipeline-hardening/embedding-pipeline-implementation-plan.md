# Embedding Pipeline Implementation Plan (Issue #215)

## Overview

This document provides the implementation plan for hardening the backend embedding pipeline with the database schema changes, following the design in `embedding-pipeline-schema-design.md`.

---

## 1. Database Schema Changes Summary

### 1.1 Current State
- `analysis_chunks` table exists with basic fields (created 2025-12-09)
- Missing performance indexes (HNSW, GIN)
- Missing data integrity constraints
- No full-text search capability

### 1.2 Proposed State
- HNSW index on `vector` column for fast semantic search
- Full-text search with `content_tsvector` + GIN index + auto-update trigger
- Hash-based deduplication index for cache lookups
- Composite indexes for common query patterns
- Check constraints for data integrity
- Telemetry columns for observability

### 1.3 Files Modified/Created

```
backend/
├── app/models/analysis_chunk.py           # UPDATED: Added new columns, constraints
├── alembic/versions/
│   └── 20251210_harden_embedding_pipeline.py  # NEW: Migration
└── docs/
    ├── embedding-pipeline-schema-design.md          # NEW: Design doc
    └── embedding-pipeline-implementation-plan.md    # NEW: This file
```

---

## 2. Migration Execution Plan

### 2.1 Pre-Migration Checklist

- [ ] Review design document: `docs/embedding-pipeline-schema-design.md`
- [ ] Backup production database (if applying to prod)
- [ ] Verify no active writes to `analysis_chunks` table (or use CONCURRENTLY)
- [ ] Check disk space (HNSW index ~1.5x vector data size)
- [ ] Estimate migration time based on row count

**Migration Time Estimates:**
```
Rows      | HNSW Index | Other Indexes | Total Time
----------|------------|---------------|------------
1,000     | ~1s        | ~1s           | ~5s
10,000    | ~5s        | ~2s           | ~10s
100,000   | ~45s       | ~5s           | ~60s
1,000,000 | ~8min      | ~30s          | ~10min
```

### 2.2 Migration Steps

#### Step 1: Apply Migration
```bash
cd backend

# Check current migration status
alembic current

# Preview migration (dry run)
alembic upgrade head --sql > migration_preview.sql
cat migration_preview.sql

# Apply migration
alembic upgrade head

# Verify migration applied
alembic current
# Expected: 20251210_harden
```

#### Step 2: Verify Indexes Created
```sql
-- Connect to database and verify indexes
SELECT
    schemaname,
    tablename,
    indexname,
    indexdef
FROM pg_indexes
WHERE tablename = 'analysis_chunks'
ORDER BY indexname;

-- Expected indexes:
-- 1. ix_analysis_chunks_vector_hnsw (HNSW)
-- 2. ix_analysis_chunks_content_tsvector (GIN)
-- 3. ix_analysis_chunks_hash_model (B-tree)
-- 4. ix_analysis_chunks_analysis_granularity (B-tree)
-- 5. ix_analysis_chunks_content_type_created (B-tree, partial)
-- 6. Plus existing indexes (analysis_id, granularity, hash)
```

#### Step 3: Verify Triggers Created
```sql
-- Verify triggers exist
SELECT tgname, tgtype, tgenabled
FROM pg_trigger
WHERE tgrelid = 'analysis_chunks'::regclass;

-- Expected triggers:
-- 1. analysis_chunks_tsvector_trigger
-- 2. update_analysis_chunks_updated_at
```

#### Step 4: Verify Constraints
```sql
-- Verify check constraints
SELECT conname, contype, pg_get_constraintdef(oid)
FROM pg_constraint
WHERE conrelid = 'analysis_chunks'::regclass
  AND contype = 'c';

-- Expected constraints:
-- 1. chk_granularity (granularity IN ...)
-- 2. chk_chunk_idx_positive (chunk_idx >= 0)
-- 3. chk_chunk_total_positive (chunk_total > 0)
-- 4. chk_chunk_idx_lt_total (chunk_idx < chunk_total)
```

#### Step 5: Test Query Performance
```sql
-- Test semantic search (should use HNSW index)
EXPLAIN ANALYZE
SELECT * FROM analysis_chunks
ORDER BY vector <=> '[0.1, 0.2, ...]'::vector(1536)
LIMIT 10;
-- Verify: "Index Scan using ix_analysis_chunks_vector_hnsw"

-- Test keyword search (should use GIN index)
EXPLAIN ANALYZE
SELECT * FROM analysis_chunks
WHERE content_tsvector @@ plainto_tsquery('english', 'machine learning')
ORDER BY ts_rank_cd(content_tsvector, plainto_tsquery('english', 'machine learning')) DESC
LIMIT 10;
-- Verify: "Bitmap Index Scan on ix_analysis_chunks_content_tsvector"

-- Test hash cache lookup (should use B-tree index)
EXPLAIN ANALYZE
SELECT * FROM analysis_chunks
WHERE hash = 'abc123...' AND model = 'text-embedding-3-small'
LIMIT 1;
-- Verify: "Index Scan using ix_analysis_chunks_hash_model"
```

### 2.3 Rollback Plan

If issues are encountered:

```bash
# Rollback to previous migration
alembic downgrade -1

# Verify rollback
alembic current
# Expected: 20251209120000

# Verify indexes removed
psql -c "SELECT indexname FROM pg_indexes WHERE tablename = 'analysis_chunks'"
```

---

## 3. Application Code Changes

### 3.1 Required Code Updates

#### 3.1.1 Update `ChunkRepository` to use new indexes

**File:** `app/db/repositories/chunk_repository.py`

The repository already supports semantic, keyword, and hybrid search. Verify these methods leverage the new indexes:

```python
# Semantic search - should automatically use HNSW index
async def semantic_search(
    self,
    query_embedding: list[float],
    limit: int = 10,
    filters: dict | None = None,
) -> list[tuple[AnalysisChunk, float]]:
    # Uses: ix_analysis_chunks_vector_hnsw
    cosine_dist = AnalysisChunk.vector.cosine_distance(query_embedding)
    # ... existing code
```

```python
# Keyword search - UPDATE to use content_tsvector instead of snippet
async def keyword_search(
    self,
    query_text: str,
    limit: int = 10,
    filters: dict | None = None,
) -> list[tuple[AnalysisChunk, float]]:
    # OLD: Uses to_tsvector(snippet) - on-the-fly conversion
    # content_tsvector = func.to_tsvector("english", AnalysisChunk.snippet)

    # NEW: Use pre-computed content_tsvector - uses GIN index
    tsquery = func.plainto_tsquery("english", query_text)
    score = func.ts_rank_cd(AnalysisChunk.content_tsvector, tsquery).label("score")

    query = (
        select(AnalysisChunk, score)
        .where(AnalysisChunk.content_tsvector.op("@@")(tsquery))
        .order_by(score.desc())
    )

    # Apply filters...
    # Execute query...
```

**ACTION REQUIRED:** Update `keyword_search()` method to use `content_tsvector` column.

#### 3.1.2 Add hash-based cache lookup method

**File:** `app/db/repositories/chunk_repository.py`

Add new method for deduplication:

```python
async def find_by_hash(
    self,
    hash: str,
    model: str,
    model_version: str,
) -> AnalysisChunk | None:
    """Find chunk by content hash and model for deduplication.

    Args:
        hash: SHA256 hash of normalized content
        model: Embedding model name (e.g., 'text-embedding-3-small')
        model_version: Model version (e.g., '1.0')

    Returns:
        Existing chunk if found, None otherwise

    """
    stmt = select(AnalysisChunk).where(
        AnalysisChunk.hash == hash,
        AnalysisChunk.model == model,
        AnalysisChunk.model_version == model_version,
    ).limit(1)

    result = await self.session.execute(stmt)
    return result.scalar_one_or_none()
```

**ACTION REQUIRED:** Add `find_by_hash()` method to repository.

#### 3.1.3 Update chunk creation to populate new fields

**File:** `app/services/embeddings.py` (or chunking service)

When creating chunks, populate telemetry fields:

```python
async def create_chunk_with_embedding(
    self,
    content: str,
    analysis_id: UUID,
    **metadata,
) -> AnalysisChunk:
    """Create chunk with embedding and telemetry."""

    # Calculate hash for deduplication
    content_normalized = content.strip().lower()
    content_hash = hashlib.sha256(content_normalized.encode()).hexdigest()

    # Check cache first
    existing = await chunk_repo.find_by_hash(
        hash=content_hash,
        model=self.model,
        model_version=self.model_version,
    )
    if existing:
        logger.info("embedding_cache_hit", hash=content_hash[:8])
        return existing

    # Generate embedding with timing
    start_time = time.perf_counter()
    text, token_count, was_truncated = await self._prepare_text(content)
    embedding = await self.generate_embedding(text)
    latency_ms = (time.perf_counter() - start_time) * 1000

    # Create chunk with all metadata
    chunk_data = {
        "analysis_id": analysis_id,
        "snippet": content[:200],
        "vector": embedding,
        "hash": content_hash,
        "model": self.model,
        "model_version": self.model_version,
        "token_count": token_count,
        "embedding_latency_ms": latency_ms,
        "was_truncated": was_truncated,
        **metadata,
    }

    return await chunk_repo.create(chunk_data)
```

**ACTION REQUIRED:** Update embedding service to:
1. Calculate SHA256 hash of normalized content
2. Check cache using `find_by_hash()` before embedding
3. Populate `token_count`, `embedding_latency_ms`, `was_truncated` fields

### 3.2 Optional Code Enhancements

#### 3.2.1 Add metrics for cache hit rate

```python
# In EmbeddingService
def __init__(self):
    # ... existing init
    self._cache_hits = 0
    self._cache_misses = 0

async def generate_embedding(self, text: str) -> EmbeddingVector:
    # Check cache
    if cached := await self._check_cache(text):
        self._cache_hits += 1
        self._metrics.record_cache_hit(provider="openai")
        return cached

    self._cache_misses += 1
    # ... existing embedding logic

def get_cache_stats(self) -> dict:
    """Return cache statistics."""
    total = self._cache_hits + self._cache_misses
    hit_rate = self._cache_hits / total if total > 0 else 0.0
    return {
        "cache_hits": self._cache_hits,
        "cache_misses": self._cache_misses,
        "hit_rate": hit_rate,
    }
```

#### 3.2.2 Add batch embedding with deduplication

```python
async def generate_embeddings_batch(
    self,
    texts: list[str],
) -> list[EmbeddingVector]:
    """Generate embeddings for multiple texts with deduplication.

    Args:
        texts: List of text strings to embed

    Returns:
        List of embedding vectors (same order as input)

    """
    # Calculate hashes for all texts
    hashes = [hashlib.sha256(t.strip().lower().encode()).hexdigest() for t in texts]

    # Check cache for all hashes
    cache_results = await self._check_cache_bulk(hashes)

    # Identify texts that need embedding
    texts_to_embed = []
    text_indices = []
    for i, (text, cached) in enumerate(zip(texts, cache_results)):
        if cached is None:
            texts_to_embed.append(text)
            text_indices.append(i)

    # Generate embeddings for uncached texts
    if texts_to_embed:
        new_embeddings = await self._generate_batch_openai(texts_to_embed)
    else:
        new_embeddings = []

    # Merge cached and new embeddings
    results = [None] * len(texts)
    for i, cached in enumerate(cache_results):
        if cached is not None:
            results[i] = cached

    for idx, embedding in zip(text_indices, new_embeddings):
        results[idx] = embedding

    return results
```

---

## 4. Testing Strategy

### 4.1 Unit Tests

**File:** `tests/unit/test_chunk_repository.py`

```python
import pytest
from app.db.repositories.chunk_repository import ChunkRepository
from app.models.analysis_chunk import AnalysisChunk


@pytest.mark.asyncio
async def test_find_by_hash_existing(db_session, sample_chunk):
    """Test finding existing chunk by hash."""
    repo = ChunkRepository(db_session)

    # Create chunk
    chunk = await repo.create(sample_chunk)

    # Find by hash
    found = await repo.find_by_hash(
        hash=chunk.hash,
        model=chunk.model,
        model_version=chunk.model_version,
    )

    assert found is not None
    assert found.id == chunk.id
    assert found.hash == chunk.hash


@pytest.mark.asyncio
async def test_find_by_hash_not_found(db_session):
    """Test finding non-existent chunk by hash."""
    repo = ChunkRepository(db_session)

    found = await repo.find_by_hash(
        hash="nonexistent_hash",
        model="text-embedding-3-small",
        model_version="1.0",
    )

    assert found is None


@pytest.mark.asyncio
async def test_keyword_search_uses_tsvector(db_session, sample_chunks):
    """Test keyword search uses content_tsvector index."""
    repo = ChunkRepository(db_session)

    # Create chunks
    for chunk_data in sample_chunks:
        await repo.create(chunk_data)

    # Execute keyword search
    results = await repo.keyword_search(
        query_text="machine learning",
        limit=10,
    )

    assert len(results) > 0

    # Verify query plan uses GIN index
    # (This requires raw SQL execution to check EXPLAIN output)
```

### 4.2 Integration Tests

**File:** `tests/integration/test_embedding_pipeline.py`

```python
import hashlib
import pytest
from app.services.embeddings import EmbeddingService
from app.db.repositories.chunk_repository import ChunkRepository


@pytest.mark.asyncio
async def test_embedding_deduplication(db_session):
    """Test that identical content reuses cached embeddings."""
    embedding_service = EmbeddingService()
    chunk_repo = ChunkRepository(db_session)

    content = "This is test content for deduplication"
    content_hash = hashlib.sha256(content.encode()).hexdigest()

    # First embedding (cache miss)
    chunk1_data = {
        "analysis_id": uuid.uuid4(),
        "snippet": content,
        "hash": content_hash,
        "model": "text-embedding-3-small",
        "model_version": "1.0",
        "granularity": "fine",
        "path": ["test"],
        "chunk_idx": 0,
        "chunk_total": 1,
    }
    embedding1 = await embedding_service.generate_embedding(content)
    chunk1_data["vector"] = embedding1
    chunk1 = await chunk_repo.create(chunk1_data)

    # Second embedding (cache hit)
    cached_chunk = await chunk_repo.find_by_hash(
        hash=content_hash,
        model="text-embedding-3-small",
        model_version="1.0",
    )

    assert cached_chunk is not None
    assert cached_chunk.id == chunk1.id
    assert cached_chunk.vector == embedding1


@pytest.mark.asyncio
async def test_telemetry_fields_populated(db_session):
    """Test that telemetry fields are populated correctly."""
    embedding_service = EmbeddingService()
    chunk_repo = ChunkRepository(db_session)

    content = "x" * 10000  # Content that will be truncated
    embedding = await embedding_service.generate_embedding(content)

    chunk_data = {
        "analysis_id": uuid.uuid4(),
        "snippet": content[:200],
        "vector": embedding,
        "hash": hashlib.sha256(content.encode()).hexdigest(),
        "model": "text-embedding-3-small",
        "model_version": "1.0",
        "granularity": "fine",
        "path": ["test"],
        "chunk_idx": 0,
        "chunk_total": 1,
        "token_count": 8000,
        "embedding_latency_ms": 50.0,
        "was_truncated": True,
    }

    chunk = await chunk_repo.create(chunk_data)

    assert chunk.token_count == 8000
    assert chunk.embedding_latency_ms > 0
    assert chunk.was_truncated is True
```

### 4.3 Performance Tests

**File:** `tests/performance/test_search_performance.py`

```python
import pytest
import time
from app.services.search.search_service import SearchService


@pytest.mark.performance
@pytest.mark.asyncio
async def test_semantic_search_latency(db_session, embedding_service, sample_chunks):
    """Test semantic search latency with HNSW index."""
    search_service = SearchService(db_session, embedding_service)

    # Create 10k chunks
    # ... (populate database)

    # Measure search latency
    query = "machine learning algorithms"
    start = time.perf_counter()
    results = await search_service.search(
        query=query,
        mode=SearchMode.SEMANTIC,
        top_k=10,
    )
    latency_ms = (time.perf_counter() - start) * 1000

    assert len(results) == 10
    assert latency_ms < 50  # p95 should be <50ms


@pytest.mark.performance
@pytest.mark.asyncio
async def test_keyword_search_latency(db_session, embedding_service, sample_chunks):
    """Test keyword search latency with GIN index."""
    search_service = SearchService(db_session, embedding_service)

    # Create 10k chunks
    # ... (populate database)

    # Measure search latency
    query = "machine learning algorithms"
    start = time.perf_counter()
    results = await search_service.search(
        query=query,
        mode=SearchMode.KEYWORD,
        top_k=10,
    )
    latency_ms = (time.perf_counter() - start) * 1000

    assert len(results) > 0
    assert latency_ms < 20  # p95 should be <20ms
```

---

## 5. Monitoring & Observability

### 5.1 Key Metrics to Track

Add these metrics to your observability system:

1. **Embedding Cache Metrics:**
   - `embedding_cache_hit_rate`: Percentage of cache hits
   - `embedding_cache_hits_total`: Total cache hits
   - `embedding_cache_misses_total`: Total cache misses

2. **Search Performance Metrics:**
   - `search_latency_ms`: Search query latency by mode (semantic/keyword/hybrid)
   - `search_results_count`: Number of results returned
   - `search_filter_applied`: Whether filters were applied

3. **Index Usage Metrics:**
   - `index_scans_total`: Number of index scans by index name
   - `index_tuples_read`: Tuples read from indexes
   - `table_seq_scans`: Sequential scans (should be low)

4. **Telemetry Metrics:**
   - `embedding_token_count`: Distribution of token counts
   - `embedding_truncation_rate`: Percentage of truncated embeddings
   - `embedding_latency_ms`: Embedding generation latency

### 5.2 Database Monitoring Queries

Add these to your monitoring dashboard:

```sql
-- Index usage statistics
SELECT
    schemaname,
    tablename,
    indexname,
    idx_scan,
    idx_tup_read,
    idx_tup_fetch
FROM pg_stat_user_indexes
WHERE tablename = 'analysis_chunks'
ORDER BY idx_scan DESC;

-- Cache hit rate (application-level)
SELECT
    COUNT(*) FILTER (WHERE created_at > NOW() - INTERVAL '1 hour') AS chunks_created_1h,
    AVG(embedding_latency_ms) AS avg_latency_ms,
    AVG(token_count) AS avg_token_count,
    COUNT(*) FILTER (WHERE was_truncated) AS truncated_count
FROM analysis_chunks;

-- Table size and growth
SELECT
    pg_size_pretty(pg_total_relation_size('analysis_chunks')) AS total_size,
    pg_size_pretty(pg_relation_size('analysis_chunks')) AS table_size,
    pg_size_pretty(pg_total_relation_size('analysis_chunks') - pg_relation_size('analysis_chunks')) AS index_size;
```

### 5.3 Alerting Rules

Configure alerts for:

1. **Slow Search Queries:**
   - Trigger: Search latency p95 > 100ms
   - Action: Investigate index usage, consider tuning

2. **Low Cache Hit Rate:**
   - Trigger: Cache hit rate < 30%
   - Action: Verify deduplication logic, check hash collisions

3. **High Truncation Rate:**
   - Trigger: Truncation rate > 10%
   - Action: Review chunking strategy, adjust token limits

4. **Index Bloat:**
   - Trigger: Index size > 2x table size
   - Action: Run VACUUM, REINDEX if necessary

---

## 6. Rollout Plan

### 6.1 Staging Environment

1. **Apply migration to staging:**
   ```bash
   # Connect to staging database
   alembic upgrade head
   ```

2. **Run performance tests:**
   ```bash
   pytest tests/performance/ -v
   ```

3. **Monitor for 24 hours:**
   - Check index usage statistics
   - Verify cache hit rates
   - Monitor search latency

4. **Validate data integrity:**
   ```sql
   -- Check for constraint violations
   SELECT * FROM analysis_chunks
   WHERE chunk_idx >= chunk_total;  -- Should return 0 rows

   SELECT * FROM analysis_chunks
   WHERE granularity NOT IN ('coarse', 'fine', 'summary');  -- Should return 0 rows
   ```

### 6.2 Production Rollout

**Prerequisites:**
- [ ] Staging validation complete
- [ ] Performance benchmarks meet targets
- [ ] Rollback plan tested
- [ ] On-call engineer assigned
- [ ] Database backup completed

**Rollout Steps:**

1. **Announce maintenance window (if needed):**
   - Window: 5-10 minutes for migration
   - Impact: No downtime (CONCURRENT index creation)

2. **Apply migration:**
   ```bash
   # Connect to production database
   alembic upgrade head
   ```

3. **Monitor migration progress:**
   ```sql
   -- Check active index builds
   SELECT
       now()::time(0),
       a.query,
       p.phase,
       p.blocks_total,
       p.blocks_done,
       round((p.blocks_done / p.blocks_total::numeric) * 100, 2) AS percent_done
   FROM pg_stat_progress_create_index p
   JOIN pg_stat_activity a ON p.pid = a.pid;
   ```

4. **Verify migration success:**
   ```bash
   alembic current
   # Expected: 20251210_harden
   ```

5. **Run validation queries:**
   ```sql
   -- Verify indexes exist
   SELECT count(*) FROM pg_indexes
   WHERE tablename = 'analysis_chunks';
   -- Expected: 8+ indexes

   -- Verify triggers exist
   SELECT count(*) FROM pg_trigger
   WHERE tgrelid = 'analysis_chunks'::regclass;
   -- Expected: 2 triggers
   ```

6. **Monitor application metrics:**
   - Search latency p95
   - Cache hit rate
   - Database CPU/memory
   - Error rates

7. **Soak test for 1 hour:**
   - Monitor all metrics
   - Check for anomalies
   - Verify no errors

8. **All clear or rollback:**
   - If issues: `alembic downgrade -1`
   - If success: Announce completion

---

## 7. Success Criteria

The migration is successful if:

- [ ] All indexes created without errors
- [ ] Search latency improved by 20-50x
- [ ] Cache hit rate > 30% (after warm-up period)
- [ ] No application errors related to schema changes
- [ ] Constraint violations = 0
- [ ] Database CPU/memory within normal range
- [ ] No customer-reported issues

---

## 8. Next Steps

After successful migration:

1. **Update code to use new features:**
   - [ ] Update `ChunkRepository.keyword_search()` to use `content_tsvector`
   - [ ] Add `ChunkRepository.find_by_hash()` method
   - [ ] Update embedding service to populate telemetry fields
   - [ ] Implement hash-based deduplication

2. **Implement batch embedding:**
   - [ ] Add batch endpoint to embedding service
   - [ ] Update chunking pipeline to use batch API
   - [ ] Optimize batch size for throughput/latency

3. **Add monitoring dashboards:**
   - [ ] Create Grafana dashboard for embedding metrics
   - [ ] Configure alerts for anomalies
   - [ ] Set up weekly performance reports

4. **Document for team:**
   - [ ] Add migration details to team wiki
   - [ ] Update API documentation
   - [ ] Create runbook for common issues

---

## 9. References

- Design Document: `docs/embedding-pipeline-schema-design.md`
- Migration File: `alembic/versions/20251210_harden_embedding_pipeline.py`
- SQLAlchemy Model: `app/models/analysis_chunk.py`
- Issue Tracker: GitHub Issue #215

---

**Document Version:** 1.0
**Last Updated:** 2025-12-10
**Author:** Backend System Architect (Claude Agent)
**Status:** Ready for Implementation
