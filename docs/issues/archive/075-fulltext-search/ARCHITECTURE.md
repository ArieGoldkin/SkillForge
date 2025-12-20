# Architecture: Hybrid Full-Text and Semantic Search

## System Overview

This document describes the architecture for implementing hybrid search that combines PostgreSQL full-text search with PGVector semantic search using the Reciprocal Rank Fusion (RRF) algorithm.

## High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         User Request                             │
│                  GET /api/v1/library?query=...                   │
└─────────────────┬───────────────────────────────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────────────────────────────────┐
│                     API Layer (FastAPI)                          │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │  LibraryRouter                                           │   │
│  │  - Validate parameters                                   │   │
│  │  - Route to search mode (hybrid/fulltext/semantic)       │   │
│  │  - Apply filters (content_type, status)                  │   │
│  │  - Format response with pagination                       │   │
│  └──────────────────────────────────────────────────────────┘   │
└─────────────────┬───────────────────────────────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────────────────────────────────┐
│               Repository Layer (SQLAlchemy)                      │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │  AnalysisRepository                                      │   │
│  │  - search_by_text() → Full-text search                  │   │
│  │  - find_similar_analyses() → Semantic search (existing)  │   │
│  │  - hybrid_search() → RRF fusion                          │   │
│  │  - list_analyses() → Filtered pagination                 │   │
│  └──────────────────────────────────────────────────────────┘   │
└─────────────────┬───────────────────────────────────────────────┘
                  │
                  ▼
         ┌────────┴────────┐
         │                 │
         ▼                 ▼
┌──────────────┐   ┌──────────────────┐
│  Full-Text   │   │  Semantic Search │
│    Search    │   │   (PGVector)     │
│              │   │                  │
│ PostgreSQL   │   │  - Generate      │
│ GIN Index    │   │    embedding     │
│ on tsvector  │   │  - Vector        │
│              │   │    similarity    │
│ ts_rank()    │   │  - Cosine dist.  │
└──────┬───────┘   └────────┬─────────┘
       │                    │
       └────────┬───────────┘
                │
                ▼
        ┌───────────────┐
        │  RRF Fusion   │
        │  (0.7 × FTS + │
        │   0.3 × Vec)  │
        └───────┬───────┘
                │
                ▼
        ┌───────────────┐
        │    Results    │
        │   (Sorted)    │
        └───────────────┘
```

## Database Schema Changes

### New Column: search_vector

```sql
-- Add tsvector column to analyses table
ALTER TABLE analyses
ADD COLUMN search_vector tsvector;

-- Weighted text search configuration:
-- 'A' = highest priority (title)
-- 'B' = medium priority (url)
-- 'C' = lowest priority (raw_content)
```

### Weight Configuration

| Field | Weight | Rationale |
|-------|--------|-----------|
| `title` | A (highest) | Title is most descriptive of content |
| `url` | B (medium) | URL often contains keywords |
| `raw_content` | C (lower) | Content may be lengthy and less targeted |

### GIN Index

```sql
-- Create GIN index for fast full-text search
CREATE INDEX idx_analyses_search_vector
ON analyses
USING gin(search_vector);

-- Partial index for completed analyses (most common query)
CREATE INDEX idx_analyses_status_complete
ON analyses (status)
WHERE status = 'complete';
```

**Index Performance**:
- GIN index enables O(log n) search complexity
- Typical index size: ~30% of table size
- Update overhead: Minimal with trigger-based maintenance

### Auto-Update Trigger

```sql
-- Function to update search_vector automatically
CREATE OR REPLACE FUNCTION analyses_search_vector_update()
RETURNS trigger AS $$
BEGIN
  NEW.search_vector :=
    setweight(to_tsvector('english', coalesce(NEW.title, '')), 'A') ||
    setweight(to_tsvector('english', coalesce(NEW.url, '')), 'B') ||
    setweight(to_tsvector('english', coalesce(NEW.raw_content, '')), 'C');
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Trigger on INSERT and UPDATE
CREATE TRIGGER tsvector_update
BEFORE INSERT OR UPDATE ON analyses
FOR EACH ROW
EXECUTE FUNCTION analyses_search_vector_update();
```

**Trigger Benefits**:
- Automatic synchronization (no manual updates needed)
- Minimal performance impact (~10ms overhead per write)
- Guaranteed consistency between content and search_vector

## Hybrid Search Algorithm: RRF (Reciprocal Rank Fusion)

### Formula

For each document `d`, the RRF score is calculated as:

```
RRF(d) = Σ [ 1 / (k + rank_i(d)) ]
```

Where:
- `k` = constant (typically 60, prevents division by zero)
- `rank_i(d)` = rank of document `d` in result set `i`
- Sum is over all result sets (FTS + Vector)

### Weighted RRF Implementation

```python
# Configurable weights
FTS_WEIGHT = 0.7    # Full-text search weight
VECTOR_WEIGHT = 0.3  # Semantic search weight

# Apply weights to RRF scores
final_score = (FTS_WEIGHT * rrf_fts_score) + (VECTOR_WEIGHT * rrf_vector_score)
```

### Why RRF?

1. **Unsupervised**: No training data required
2. **Robust**: Handles varying result set sizes
3. **Proven**: Used by Elasticsearch, Vespa, and other search systems
4. **Simple**: Easy to understand and tune

### Example RRF Calculation

```
Query: "React hooks tutorial"

Full-Text Results:          Semantic Results:
1. Doc A (rank 1)          1. Doc B (rank 1)
2. Doc B (rank 2)          2. Doc A (rank 2)
3. Doc C (rank 3)          3. Doc D (rank 3)

RRF Scores (k=60):
Doc A: 1/(60+1) + 1/(60+2) = 0.0164 + 0.0161 = 0.0325
Doc B: 1/(60+2) + 1/(60+1) = 0.0161 + 0.0164 = 0.0325
Doc C: 1/(60+3) + 0        = 0.0159
Doc D: 0        + 1/(60+3) = 0.0159

Weighted RRF (0.7 FTS + 0.3 Vector):
Doc A: 0.7 * 0.0164 + 0.3 * 0.0161 = 0.0163
Doc B: 0.7 * 0.0161 + 0.3 * 0.0164 = 0.0162
Doc C: 0.7 * 0.0159 + 0           = 0.0111
Doc D: 0            + 0.3 * 0.0159 = 0.0048

Final Ranking: A, B, C, D
```

## Component Architecture

### 1. Repository Layer

```python
# app/db/repositories/analysis_repository.py

class AnalysisRepository:
    """Repository for analysis database operations."""

    async def search_by_text(
        self,
        query: str,
        limit: int = 20,
        content_type: str | None = None,
        status: str | None = None,
    ) -> list[tuple[Analysis, float]]:
        """Full-text search using PostgreSQL GIN index.

        Returns:
            List of (Analysis, rank_score) tuples sorted by relevance
        """
        pass

    async def hybrid_search(
        self,
        query: str,
        limit: int = 20,
        fts_weight: float = 0.7,
        vector_weight: float = 0.3,
        content_type: str | None = None,
        status: str | None = None,
    ) -> list[Analysis]:
        """Hybrid search using RRF fusion.

        Combines full-text and semantic search results.
        """
        pass

    async def list_analyses(
        self,
        limit: int = 20,
        offset: int = 0,
        content_type: str | None = None,
        status: str | None = None,
        order_by: str = "created_at",
    ) -> tuple[list[Analysis], int]:
        """List analyses with filtering and pagination.

        Returns:
            Tuple of (results, total_count)
        """
        pass
```

### 2. API Layer

```python
# app/api/v1/library.py

@router.get("/library")
async def search_library(
    query: str | None = None,
    search_mode: Literal["hybrid", "fulltext", "semantic"] = "hybrid",
    content_type: str | None = None,
    status: str | None = None,
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
) -> LibraryResponse:
    """Search and list analyses with pagination."""
    pass
```

### 3. Schema Layer

```python
# app/schemas/library.py

class LibrarySearchParams(BaseModel):
    """Search parameters for library endpoint."""
    query: str | None = None
    search_mode: Literal["hybrid", "fulltext", "semantic"] = "hybrid"
    content_type: str | None = Field(None, pattern="^(article|video|repo)$")
    status: str | None = Field(None, pattern="^(pending|complete|failed)$")
    limit: int = Field(20, ge=1, le=100)
    offset: int = Field(0, ge=0)

class LibraryItem(BaseModel):
    """Single library item in search results."""
    id: str
    url: str
    title: str | None
    content_type: str
    status: str
    created_at: str
    relevance_score: float | None = None  # Only for search results

class LibraryResponse(BaseModel):
    """Response from library endpoint."""
    results: list[LibraryItem]
    total: int
    limit: int
    offset: int
    search_mode: str
```

## Data Flow

### Full-Text Search Flow

```
1. User Query: "React hooks"
   ↓
2. Parse query to tsquery: to_tsquery('english', 'React & hooks')
   ↓
3. PostgreSQL GIN index search:
   SELECT id, ts_rank(search_vector, query) as rank
   FROM analyses
   WHERE search_vector @@ query
   AND status = 'complete'
   ORDER BY rank DESC
   LIMIT 20
   ↓
4. Return ranked results with scores
```

### Hybrid Search Flow

```
1. User Query: "React hooks"
   ↓
2. Parallel execution:
   ┌─────────────────────┬──────────────────────┐
   │  Full-Text Search   │   Semantic Search    │
   │  (PostgreSQL GIN)   │   (PGVector)         │
   │                     │                      │
   │  Returns 20 items   │   Generate embedding │
   │  with rank scores   │   Search vectors     │
   │                     │   Returns 20 items   │
   └──────────┬──────────┴──────────┬───────────┘
              │                     │
              ▼                     ▼
        ┌─────────────────────────────────┐
        │   Calculate RRF Scores          │
        │   - FTS weight: 0.7             │
        │   - Vector weight: 0.3          │
        │   - Merge and sort by score     │
        └──────────────┬──────────────────┘
                       │
                       ▼
              ┌────────────────┐
              │  Top K Results │
              │   (Sorted)     │
              └────────────────┘
```

## Performance Considerations

### Database Optimization

1. **GIN Index**:
   - Type: `gin(search_vector)`
   - Size: ~30% of table size
   - Update cost: ~10ms per write
   - Search cost: O(log n)

2. **Partial Indexes**:
   ```sql
   -- Index for common status filter
   CREATE INDEX idx_analyses_status_complete
   ON analyses (status)
   WHERE status = 'complete';
   ```

3. **Connection Pool**:
   ```python
   # app/core/config.py
   POOL_SIZE = 20          # Max connections
   MAX_OVERFLOW = 10       # Additional connections
   POOL_TIMEOUT = 30       # Seconds
   ```

### Query Optimization

1. **Limit Result Sets**:
   - Full-text: Fetch 20 candidates
   - Semantic: Fetch 20 candidates
   - Final: Return top K results

2. **Avoid N+1 Queries**:
   - Use SQLAlchemy's `selectinload()` for relationships
   - Batch embedding generation when needed

3. **Caching Strategy**:
   - Cache query embeddings (TTL: 5 minutes)
   - Cache top queries (Redis/Memcached)

### Performance Targets

| Operation | Target | Measurement |
|-----------|--------|-------------|
| Full-text search | < 500ms | 95th percentile |
| Hybrid search | < 750ms | 95th percentile |
| Library listing | < 200ms | 95th percentile |
| Index update | < 10ms | Per write operation |

## Scalability Considerations

### Horizontal Scaling

1. **Read Replicas**:
   - Route search queries to read replicas
   - Master handles writes only

2. **Sharding Strategy**:
   - Shard by content_type (article/video/repo)
   - Each shard maintains own GIN index

3. **Caching Layer**:
   - Redis for query result caching
   - Edge caching for API responses

### Index Maintenance

1. **Automatic Updates**: Trigger-based (real-time)
2. **Rebuild Strategy**:
   - Periodic REINDEX (weekly, off-peak)
   - VACUUM ANALYZE for statistics

3. **Monitoring**:
   - Index bloat detection
   - Query performance metrics
   - Slow query logs

## Security Considerations

1. **SQL Injection Prevention**:
   - Use parameterized queries
   - Validate search mode enum
   - Sanitize text inputs

2. **Rate Limiting**:
   - 100 requests/minute per IP
   - 1000 requests/hour per user

3. **Input Validation**:
   - Limit query length (< 1000 chars)
   - Validate content_type/status enums
   - Sanitize special characters in queries

## Migration Strategy

### Phase 1: Schema Changes (Non-Breaking)
1. Add `search_vector` column (nullable)
2. Create GIN index
3. Create trigger function and trigger

### Phase 2: Backfill (Background)
1. Update existing rows in batches:
   ```sql
   UPDATE analyses
   SET search_vector =
     setweight(to_tsvector('english', coalesce(title, '')), 'A') ||
     setweight(to_tsvector('english', coalesce(url, '')), 'B') ||
     setweight(to_tsvector('english', coalesce(raw_content, '')), 'C')
   WHERE id IN (SELECT id FROM analyses ORDER BY id LIMIT 1000 OFFSET {offset});
   ```
2. Monitor backfill progress

### Phase 3: Deploy Code
1. Deploy repository methods (backward compatible)
2. Deploy API endpoint
3. Update API documentation

### Rollback Plan
1. Remove trigger: `DROP TRIGGER tsvector_update ON analyses;`
2. Remove function: `DROP FUNCTION analyses_search_vector_update();`
3. Remove column: `ALTER TABLE analyses DROP COLUMN search_vector;`
4. Revert code deployment

## Monitoring and Observability

### Key Metrics

1. **Search Performance**:
   - Query latency (p50, p95, p99)
   - Results relevance score
   - Cache hit rate

2. **Database Metrics**:
   - Index size and bloat
   - Query execution time
   - Connection pool usage

3. **Business Metrics**:
   - Search mode distribution
   - Top queries
   - Zero-result searches

### Logging Strategy

```python
# app/core/logging.py

logger.info(
    "hybrid_search_complete",
    query=query,
    search_mode=search_mode,
    fts_results=len(fts_results),
    vector_results=len(vector_results),
    final_results=len(final_results),
    duration_ms=duration,
)
```

## Future Enhancements

1. **Query Expansion**: Synonym support, stemming improvements
2. **Personalization**: User-specific ranking signals
3. **Analytics**: Search result click-through tracking
4. **Auto-Complete**: Suggest-as-you-type functionality
5. **Advanced Filters**: Date ranges, author, tags
6. **Faceted Search**: Aggregations by content_type, date, etc.
