# 🎯 Langfuse-First Architecture with Smart PostgreSQL Projections
## Recommended Approach for Feedback & Metrics Analytics

**Date:** December 22, 2025  
**Status:** Architecture Recommendation  
**Principle:** Langfuse as source of truth, PostgreSQL for fast queries

---

## 🎯 Core Principle: Event Sourcing + CQRS Projection

**Langfuse = Event Store (Source of Truth)**  
**PostgreSQL = Read Model (Fast Query Cache)**

```
┌─────────────────────────────────────────────────────────────────────┐
│                    LANGFUSE-FIRST ARCHITECTURE                       │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  WRITE PATH (Event Sourcing)                                        │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │  1. User submits feedback                                     │  │
│  │     → POST /api/v1/annotations/feedback                       │  │
│  │                                                                │  │
│  │  2. Write to Langfuse FIRST (authoritative)                   │  │
│  │     → LangfuseService.submit_score(                           │  │
│  │         trace_id=artifact.trace_id,                           │  │
│  │         name="user_feedback",                                 │  │
│  │         value=1.0 or 0.0                                      │  │
│  │       )                                                        │  │
│  │                                                                │  │
│  │  3. Project to PostgreSQL (denormalized read model)           │  │
│  │     → INSERT INTO artifact_feedback_cache (                   │  │
│  │         artifact_id, trace_id, score, timestamp               │  │
│  │       )                                                        │  │
│  │     → UPDATE artifact_metrics (thumbs_up_count, etc.)         │  │
│  └──────────────────────────────────────────────────────────────┘  │
│                                                                      │
│  READ PATH (CQRS - Command Query Responsibility Segregation)       │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │  Fast Queries: PostgreSQL (projection/cache)                  │  │
│  │  - GET /api/v1/artifacts/{id}/feedback/stats                  │  │
│  │    → SELECT thumbs_up_count, thumbs_down_count FROM ...       │  │
│  │                                                                 │  │
│  │  Detailed Traces: Langfuse API (source of truth)              │  │
│  │  - GET /api/v1/artifacts/{id}/feedback/trace                  │  │
│  │    → LangfuseService.get_trace(trace_id)                      │  │
│  │    → Includes full context, metadata, comments                 │  │
│  └──────────────────────────────────────────────────────────────┘  │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 📊 Recommended Database Schema (Minimal Projection)

Store **only** what's needed for fast queries, not full duplication:

```sql
-- Lightweight projection table (read model)
CREATE TABLE artifact_feedback_cache (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    artifact_id UUID NOT NULL REFERENCES artifacts(id) ON DELETE CASCADE,
    trace_id TEXT NOT NULL,  -- Link back to Langfuse trace
    
    -- Denormalized feedback data (for fast queries)
    score NUMERIC(3,2) NOT NULL,  -- 1.0 (thumbs_up) or 0.0 (thumbs_down)
    feedback_type TEXT NOT NULL CHECK (feedback_type IN ('thumbs_up', 'thumbs_down')),
    
    -- Minimal metadata for analytics
    user_id UUID,  -- NULL until auth implemented (Issue #421)
    comment TEXT,  -- First 200 chars (truncated for storage efficiency)
    
    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    
    -- Indexes for fast queries
    CONSTRAINT artifact_feedback_cache_artifact_trace_unique UNIQUE (artifact_id, trace_id)
);

CREATE INDEX idx_artifact_feedback_cache_artifact_id ON artifact_feedback_cache(artifact_id);
CREATE INDEX idx_artifact_feedback_cache_created_at ON artifact_feedback_cache(created_at);
CREATE INDEX idx_artifact_feedback_cache_user_id ON artifact_feedback_cache(user_id) WHERE user_id IS NOT NULL;

-- Aggregated metrics (materialized view for even faster queries)
CREATE TABLE artifact_metrics (
    artifact_id UUID PRIMARY KEY REFERENCES artifacts(id) ON DELETE CASCADE,
    
    -- Aggregated counts (updated on feedback insert)
    thumbs_up_count INTEGER NOT NULL DEFAULT 0,
    thumbs_down_count INTEGER NOT NULL DEFAULT 0,
    total_feedback_count INTEGER NOT NULL DEFAULT 0,
    
    -- Computed metrics
    average_score NUMERIC(3,2) GENERATED ALWAYS AS (
        CASE 
            WHEN total_feedback_count > 0 
            THEN (thumbs_up_count::NUMERIC / total_feedback_count::NUMERIC)
            ELSE NULL
        END
    ) STORED,
    
    -- Timestamps
    first_feedback_at TIMESTAMP WITH TIME ZONE,
    last_feedback_at TIMESTAMP WITH TIME ZONE,
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);
```

---

## 🔄 Implementation Pattern: Dual-Write with Langfuse Authority

### Step 1: Write to Langfuse (Authoritative)

```python
# backend/app/core/annotation_service.py

async def submit_feedback(
    self,
    artifact_id: uuid.UUID,
    trace_id: str | None,
    feedback: FeedbackType,
    comment: str | None = None,
) -> SubmitFeedbackResult:
    """Submit feedback: Langfuse-first, then project to PostgreSQL."""
    
    # 1. WRITE TO LANGFUSE FIRST (source of truth)
    score_value = 1.0 if feedback == "thumbs_up" else 0.0
    
    langfuse_submitted = await self._submit_langfuse_score(
        trace_id=trace_id,
        score_name="user_feedback",
        score_value=score_value,
        comment=comment,
    )
    
    # If Langfuse write fails, return error (Langfuse is authoritative)
    if not langfuse_submitted:
        return {
            "status": "error",
            "message": "Failed to submit feedback to Langfuse",
            "langfuse_submitted": False,
        }
    
    # 2. PROJECT TO POSTGRESQL (read model for fast queries)
    # This is a projection/cache - if it fails, we can rebuild from Langfuse
    try:
        await self._project_feedback_to_db(
            artifact_id=artifact_id,
            trace_id=trace_id,
            feedback=feedback,
            score=score_value,
            comment=comment,
        )
    except Exception as e:
        # Log but don't fail - PostgreSQL projection is just a cache
        logger.warning(
            "feedback_projection_failed",
            artifact_id=str(artifact_id),
            error=str(e),
            message="Langfuse write succeeded, but PostgreSQL projection failed. "
                    "Projection can be rebuilt from Langfuse if needed.",
        )
    
    return {
        "status": "success",
        "message": "Feedback submitted successfully",
        "langfuse_submitted": True,
    }
```

### Step 2: Project to PostgreSQL (Read Model)

```python
# backend/app/core/annotation_service.py

async def _project_feedback_to_db(
    self,
    artifact_id: uuid.UUID,
    trace_id: str,
    feedback: FeedbackType,
    score: float,
    comment: str | None = None,
) -> None:
    """Project feedback to PostgreSQL read model for fast queries.
    
    This is a denormalized projection - the source of truth is Langfuse.
    This table can be rebuilt from Langfuse if needed.
    """
    from app.db.models.feedback_cache import ArtifactFeedbackCache
    from app.db.models.artifact_metrics import ArtifactMetrics
    
    # Insert into cache (idempotent - use ON CONFLICT DO NOTHING)
    feedback_cache = ArtifactFeedbackCache(
        artifact_id=artifact_id,
        trace_id=trace_id,
        score=score,
        feedback_type=feedback,
        comment=comment[:200] if comment else None,  # Truncate for storage
        user_id=None,  # TODO: Add after auth (Issue #421)
    )
    
    self.session.add(feedback_cache)
    
    # Update aggregated metrics (upsert pattern)
    await self.session.execute(
        insert(ArtifactMetrics)
        .values(
            artifact_id=artifact_id,
            thumbs_up_count=1 if feedback == "thumbs_up" else 0,
            thumbs_down_count=1 if feedback == "thumbs_down" else 0,
            total_feedback_count=1,
            first_feedback_at=datetime.now(UTC),
            last_feedback_at=datetime.now(UTC),
        )
        .on_conflict_do_update(
            index_elements=["artifact_id"],
            set_={
                "thumbs_up_count": ArtifactMetrics.thumbs_up_count + (1 if feedback == "thumbs_up" else 0),
                "thumbs_down_count": ArtifactMetrics.thumbs_down_count + (1 if feedback == "thumbs_down" else 0),
                "total_feedback_count": ArtifactMetrics.total_feedback_count + 1,
                "last_feedback_at": datetime.now(UTC),
                "updated_at": datetime.now(UTC),
            }
        )
    )
    
    await self.session.commit()
```

---

## 🔍 Query Patterns: Fast PostgreSQL for Aggregations

### Fast Aggregation Queries (Use PostgreSQL)

```python
# backend/app/api/v1/analytics.py

@router.get("/artifacts/{artifact_id}/feedback/stats")
async def get_feedback_stats(
    artifact_id: uuid.UUID,
    repo: ArtifactMetricsRepository = Depends(get_artifact_metrics_repository),
) -> FeedbackStatsResponse:
    """Get feedback statistics for an artifact (fast PostgreSQL query).
    
    This uses the materialized metrics table for sub-10ms queries.
    Source of truth is Langfuse, but this is the fast read model.
    """
    metrics = await repo.get_metrics(artifact_id)
    
    return FeedbackStatsResponse(
        artifact_id=artifact_id,
        thumbs_up_count=metrics.thumbs_up_count,
        thumbs_down_count=metrics.thumbs_down_count,
        total_feedback_count=metrics.total_feedback_count,
        average_score=metrics.average_score,
        positive_feedback_rate=metrics.average_score,  # Same as average_score for binary feedback
    )
```

### Detailed Trace Queries (Use Langfuse API)

```python
# backend/app/api/v1/analytics.py

@router.get("/artifacts/{artifact_id}/feedback/trace")
async def get_feedback_trace(
    artifact_id: uuid.UUID,
    langfuse_service: LangfuseService = Depends(get_langfuse_service),
    artifact_repo: ArtifactRepository = Depends(get_artifact_repository),
) -> FeedbackTraceResponse:
    """Get detailed feedback trace from Langfuse (source of truth).
    
    Use this for detailed debugging, full context, comments, etc.
    """
    artifact = await artifact_repo.get_artifact_by_id(artifact_id)
    if not artifact or not artifact.trace_id:
        raise HTTPException(404, "Artifact or trace not found")
    
    # Query Langfuse API for full trace details
    trace = await langfuse_service.get_trace(artifact.trace_id)
    
    return FeedbackTraceResponse(
        trace_id=artifact.trace_id,
        scores=trace.get("scores", []),  # All scores (user_feedback, g_eval, etc.)
        observations=trace.get("observations", []),  # Full workflow context
        metadata=trace.get("metadata", {}),
    )
```

---

## 🔄 Sync Strategy: Rebuild Projection from Langfuse

If PostgreSQL projection gets out of sync or is lost, rebuild from Langfuse:

```python
# backend/scripts/sync_feedback_from_langfuse.py

async def rebuild_feedback_cache_from_langfuse():
    """Rebuild PostgreSQL feedback cache from Langfuse (source of truth).
    
    Run this if:
    - PostgreSQL cache is corrupted
    - Need to backfill historical data
    - Migrating from Langfuse-only to Langfuse+PostgreSQL
    """
    langfuse_service = get_langfuse_service()
    if not langfuse_service:
        raise ValueError("Langfuse service not available")
    
    # Get all artifacts with trace_ids
    artifacts = await artifact_repo.list_all_with_trace_ids()
    
    for artifact in artifacts:
        if not artifact.trace_id:
            continue
        
        # Query Langfuse for scores
        trace = await langfuse_service.get_trace(artifact.trace_id)
        user_feedback_scores = [
            score for score in trace.get("scores", [])
            if score.get("name") == "user_feedback"
        ]
        
        # Rebuild cache from Langfuse data
        for score in user_feedback_scores:
            await _project_feedback_to_db(
                artifact_id=artifact.id,
                trace_id=artifact.trace_id,
                feedback="thumbs_up" if score["value"] == 1.0 else "thumbs_down",
                score=score["value"],
                comment=score.get("comment"),
            )
```

---

## ✅ Benefits of This Approach

### 1. **Langfuse-First (Source of Truth)**
- ✅ All feedback written to Langfuse first
- ✅ If Langfuse write fails, entire operation fails (data integrity)
- ✅ PostgreSQL is just a projection/cache

### 2. **Fast Queries (PostgreSQL)**
- ✅ Sub-10ms aggregation queries (vs 200-500ms Langfuse API calls)
- ✅ Materialized metrics table for instant stats
- ✅ Can build dashboards with fast SQL queries

### 3. **Minimal Duplication**
- ✅ Only store denormalized data needed for queries (not full traces)
- ✅ ~100 bytes per feedback entry (vs 5-10KB in Langfuse)
- ✅ Can rebuild from Langfuse if PostgreSQL is lost

### 4. **Vendor Independence**
- ✅ Not locked into Langfuse for analytics queries
- ✅ Can switch observability providers without losing analytics
- ✅ Historical data preserved in PostgreSQL

### 5. **Best of Both Worlds**
- ✅ Langfuse UI for detailed traces, debugging, exploration
- ✅ PostgreSQL for dashboards, reports, product metrics

---

## 📊 What Gets Stored Where

| Data | Langfuse (Source of Truth) | PostgreSQL (Projection) |
|------|---------------------------|------------------------|
| **Full trace context** | ✅ Yes (observations, metadata, timestamps) | ❌ No |
| **All scores** | ✅ Yes (user_feedback, g_eval, etc.) | ⚠️ Only user_feedback |
| **Comments** | ✅ Yes (full text) | ⚠️ Truncated (200 chars) |
| **User ID** | ✅ Yes (when available) | ✅ Yes (when available) |
| **Aggregated metrics** | ❌ No (query on-demand) | ✅ Yes (thumbs_up_count, etc.) |
| **Query performance** | ⚠️ 200-500ms (API calls) | ✅ <10ms (local DB) |

---

## 🚀 Implementation Phases

### Phase 1: Add PostgreSQL Projection Tables
**Effort:** 2-3 days

1. Create `artifact_feedback_cache` table (migration)
2. Create `artifact_metrics` table (migration)
3. Add SQLAlchemy models
4. Add repository methods

### Phase 2: Update Feedback Submission
**Effort:** 1-2 days

1. Add `_project_feedback_to_db()` method to `AnnotationService`
2. Update `submit_feedback()` to dual-write (Langfuse first, then PostgreSQL)
3. Add error handling (fail on Langfuse, log on PostgreSQL)

### Phase 3: Analytics Endpoints
**Effort:** 2-3 days

1. Create `FeedbackStatsRepository` for fast queries
2. Add `GET /api/v1/artifacts/{id}/feedback/stats` endpoint
3. Add `GET /api/v1/analytics/feedback/summary` endpoint (aggregate across artifacts)

### Phase 4: Sync Script (Optional)
**Effort:** 1 day

1. Create `sync_feedback_from_langfuse.py` script
2. Run once to backfill historical data
3. Can be re-run if cache gets corrupted

---

## 🎯 Recommended: Start with Phase 1 + 2

**Minimum Viable Architecture:**
1. ✅ Write to Langfuse (already exists)
2. ✅ Project to PostgreSQL (add projection step)
3. ✅ Fast query endpoints (add stats endpoint)

**Benefits:**
- Langfuse remains source of truth
- Fast analytics queries via PostgreSQL
- Minimal code changes (extend existing `submit_feedback`)
- Can add sync script later if needed

---

## 📝 Migration Path

If you want to migrate existing Langfuse-only feedback:

```bash
# Run sync script to backfill PostgreSQL from Langfuse
poetry run python scripts/sync_feedback_from_langfuse.py

# Verify sync
poetry run python scripts/verify_feedback_sync.py  # Compare counts
```

---

**Conclusion:** This architecture gives you **Langfuse-first** (source of truth) while leveraging **PostgreSQL** for fast analytics queries, with minimal duplication and vendor independence.
