# Database Cleanup Strategy for SkillForge Embedding Pipeline

**Version:** 1.0
**Date:** December 10, 2025
**Status:** Production Ready

---

## Table of Contents

1. [Overview](#overview)
2. [Architecture](#architecture)
3. [Cleanup Routines](#cleanup-routines)
4. [Usage Examples](#usage-examples)
5. [SQL Queries](#sql-queries)
6. [Scheduled Jobs](#scheduled-jobs)
7. [Monitoring](#monitoring)
8. [Migration Guide](#migration-guide)

---

## Overview

The SkillForge embedding pipeline stores:
- **Analyses table**: Analysis records with metadata and embeddings (1536-dim vectors)
- **Analysis_chunks table**: Chunk-level embeddings with hierarchical metadata

This cleanup system provides:

1. **Orphan Cleanup**: Remove chunks where parent analysis is deleted/superseded
2. **Integrity Checks**: Detect corrupted vectors (NaN, Inf, dimension mismatches)
3. **TTL Expiration**: Remove old draft analyses with configurable retention policies

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                        CleanupService                               │
│                     (Orchestration Layer)                           │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  ┌────────────────┐  ┌──────────────────┐  ┌─────────────────┐   │
│  │ OrphanCleaner  │  │ IntegrityChecker │  │   TTLCleaner    │   │
│  │                │  │                  │  │                 │   │
│  │ • Missing      │  │ • Dimensions     │  │ • Draft: 7d     │   │
│  │   parent       │  │ • NULL vectors   │  │ • Failed: 30d   │   │
│  │ • Failed       │  │ • NaN/Inf        │  │ • Pending: 1d   │   │
│  │   analysis     │  │ • Zero vectors   │  │ • Cascade       │   │
│  │ • Superseded   │  │ • Normalization  │  │                 │   │
│  └────────────────┘  └──────────────────┘  └─────────────────┘   │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

### Design Decisions

**1. Batch Processing**
- Default batch size: 1000 records
- Prevents memory exhaustion on large datasets
- Provides progress logging

**2. Soft Delete vs Hard Delete**
- Soft delete: Mark as deleted (requires migration for `is_deleted` column)
- Hard delete: Permanent removal (currently implemented)
- Grace period: 7 days before hard delete

**3. Cascade Delete**
- Foreign key: `analysis_chunks.analysis_id → analyses.id ON DELETE CASCADE`
- Automatic chunk deletion when parent analysis is deleted
- Migration: `20251210_add_cascade_delete.py`

---

## Cleanup Routines

### 1. Orphan Cleanup

Orphaned chunks are chunks whose parent analysis has been:
- Deleted from the analyses table
- Superseded by a newer analysis of the same URL
- Marked as failed/error for extended period

#### Detection Methods

**Missing Parent (Critical)**
```python
# Find chunks where parent analysis no longer exists
# Uses LEFT JOIN to efficiently find chunks with NULL parent
orphan_ids = await cleaner.find_orphans_missing_parent()
```

**Failed Analysis (Medium)**
```python
# Find chunks from failed analyses older than 7 days
# These are unlikely to be retried
orphan_ids = await cleaner.find_orphans_failed_analysis(
    failed_threshold_days=7
)
```

**Superseded Analysis (Low)**
```python
# Find chunks from older versions of re-analyzed URLs
# Keeps only the most recent analysis per URL
orphan_ids = await cleaner.find_orphans_superseded_analysis()
```

#### Deletion Strategies

**Safe Deletion (Recommended)**
```python
await cleaner.delete_orphans_batch(
    orphan_ids,
    hard_delete=False  # Soft delete
)
```

**Permanent Deletion (Caution)**
```python
await cleaner.delete_orphans_batch(
    orphan_ids,
    hard_delete=True  # Permanent
)
```

---

### 2. Integrity Checks

Vector integrity checks detect data corruption and quality issues.

#### Check Types

**1. Dimension Mismatch**
```python
# Expected: 1536 dimensions (OpenAI text-embedding-3-small)
invalid_ids = await checker.check_chunk_vector_dimensions()
```

**2. NULL Vectors**
```python
# Chunks should always have embeddings
null_ids = await checker.check_null_chunk_vectors()
```

**3. Invalid Values (NaN, Inf)**
```python
# Detect NaN/Inf in vector components
issues = await checker.check_invalid_values_in_chunks()
# Returns: [(chunk_id, "Contains 5 NaN values"), ...]
```

**4. Zero Vectors**
```python
# Detect all-zero vectors (embedding failure)
zero_ids = await checker.check_zero_vectors_in_chunks()
```

**5. Non-Normalized Vectors**
```python
# Check L2 norm ≈ 1.0 (required for cosine similarity)
issues = await checker.check_vector_normalization(tolerance=1e-5)
# Returns: [(chunk_id, 0.876), ...]  # Actual norm
```

#### Comprehensive Check

```python
report = await checker.run_all_checks()
# Returns:
# {
#     "chunk_dimension_issues": [uuid1, uuid2, ...],
#     "null_chunk_vectors": [uuid3, ...],
#     "invalid_values": [(uuid4, "NaN"), ...],
#     "zero_vectors": [uuid5, ...],
#     "non_normalized_vectors": [(uuid6, 0.95), ...]
# }
```

---

### 3. TTL-Based Expiration

Time-To-Live policies automatically clean up old analyses by status.

#### Default Policies

| Status | TTL | Rationale |
|--------|-----|-----------|
| `draft` | 7 days | User abandoned |
| `pending` | 1 day | Likely stuck workflow |
| `failed` | 30 days | Give time for debugging |
| `error` | 30 days | Same as failed |
| `complete` | Never | Keep indefinitely |

#### Customization

```python
cleaner = TTLCleaner(session)

# Extend draft retention to 14 days
cleaner.set_ttl_policy('draft', 14)

# Keep completed analyses indefinitely
cleaner.set_ttl_policy('complete', None)
```

#### Cascade Behavior

When an analysis is deleted, **all chunks cascade automatically** via foreign key constraint:

```sql
-- Migration: 20251210_add_cascade_delete.py
ALTER TABLE analysis_chunks
DROP CONSTRAINT analysis_chunks_analysis_id_fkey;

ALTER TABLE analysis_chunks
ADD CONSTRAINT analysis_chunks_analysis_id_fkey
FOREIGN KEY (analysis_id) REFERENCES analyses(id)
ON DELETE CASCADE;
```

---

## Usage Examples

### Python API

**1. Health Check (Read-Only)**
```python
from app.services.cleanup import CleanupService
from app.db.session import get_db

async def check_health():
    async for db in get_db():
        service = CleanupService(db)
        health = await service.health_check()

        if not health['healthy']:
            print(f"Found {health['total_issues']} issues")
            print(f"  • Orphans: {health['orphan_chunks']}")
            print(f"  • Expired: {health['expired_analyses']}")
            print(f"  • Integrity: {health['integrity_issues']}")
```

**2. Dry Run (Preview)**
```python
async def preview_cleanup():
    async for db in get_db():
        service = CleanupService(db)
        result = await service.run_full_cleanup(dry_run=True)

        summary = result['summary']
        print(f"Would delete:")
        print(f"  • {summary['orphans_cleaned']} chunks")
        print(f"  • {summary['analyses_expired']} analyses")
```

**3. Execute Cleanup**
```python
async def execute_cleanup():
    async for db in get_db():
        service = CleanupService(db)
        result = await service.run_full_cleanup(
            include_orphans=True,
            include_expired=True,
            include_superseded=False,  # Be conservative
            hard_delete=False,  # Soft delete
            dry_run=False,
        )

        print(f"Cleaned up {result['summary']['total_items_affected']} items")
```

**4. Generate Report**
```python
async def generate_report():
    async for db in get_db():
        service = CleanupService(db)
        report = await service.generate_cleanup_report_markdown()

        with open('cleanup_report.md', 'w') as f:
            f.write(report)
```

### Command-Line Script

```bash
# Navigate to backend directory
cd /Users/yonatangross/coding/SkillForge/backend

# Health check
python scripts/cleanup.py --check

# Preview cleanup (dry run)
python scripts/cleanup.py --dry-run

# Execute orphan cleanup
python scripts/cleanup.py --orphans

# Execute TTL cleanup
python scripts/cleanup.py --ttl

# Full cleanup
python scripts/cleanup.py --full

# Full cleanup with superseded analyses
python scripts/cleanup.py --full --include-superseded

# Generate report
python scripts/cleanup.py --report cleanup_report.md

# Use hard delete (permanent)
python scripts/cleanup.py --full --hard-delete

# Custom batch size
python scripts/cleanup.py --orphans --batch-size 500
```

---

## SQL Queries

### Manual Inspection Queries

**1. Find Orphaned Chunks (Missing Parent)**
```sql
-- Chunks where parent analysis no longer exists
SELECT ac.id, ac.analysis_id, ac.created_at
FROM analysis_chunks ac
LEFT JOIN analyses a ON ac.analysis_id = a.id
WHERE a.id IS NULL;
```

**2. Find Orphaned Chunks (Failed Analysis)**
```sql
-- Chunks from analyses in failed/error status for > 7 days
SELECT ac.id, a.status, a.updated_at
FROM analysis_chunks ac
JOIN analyses a ON ac.analysis_id = a.id
WHERE a.status IN ('failed', 'error')
  AND a.updated_at < NOW() - INTERVAL '7 days';
```

**3. Find Superseded Analyses**
```sql
-- Analyses that have been superseded by newer versions
WITH ranked_analyses AS (
  SELECT
    id,
    url,
    created_at,
    ROW_NUMBER() OVER (PARTITION BY url ORDER BY created_at DESC) as row_num
  FROM analyses
  WHERE status = 'complete'
)
SELECT id, url, created_at
FROM ranked_analyses
WHERE row_num > 1;
```

**4. Find Expired Analyses (Draft > 7 days)**
```sql
-- Draft analyses older than 7 days
SELECT id, url, status, updated_at
FROM analyses
WHERE status = 'draft'
  AND updated_at < NOW() - INTERVAL '7 days';
```

**5. Check Vector Dimensions**
```sql
-- Chunks with incorrect vector dimensions (should be 1536)
SELECT id, vector_dims(vector) as dims
FROM analysis_chunks
WHERE vector_dims(vector) != 1536;
```

**6. Find NULL Vectors**
```sql
-- Chunks with NULL vectors (should always have embeddings)
SELECT id, analysis_id, created_at
FROM analysis_chunks
WHERE vector IS NULL;
```

**7. Count Chunks by Granularity**
```sql
-- Distribution of chunk granularities
SELECT granularity, COUNT(*) as count
FROM analysis_chunks
GROUP BY granularity;
```

**8. Storage Usage by Analysis**
```sql
-- Disk usage by analysis (approximate)
SELECT
  a.id,
  a.url,
  a.status,
  COUNT(ac.id) as chunk_count,
  pg_size_pretty(
    pg_column_size(a.content_embedding) +
    SUM(pg_column_size(ac.vector))
  ) as storage_size
FROM analyses a
LEFT JOIN analysis_chunks ac ON a.analysis_id = ac.id
GROUP BY a.id
ORDER BY SUM(pg_column_size(ac.vector)) DESC
LIMIT 20;
```

### Cleanup Queries (Use with Caution)

**1. Delete Orphaned Chunks (Hard Delete)**
```sql
-- WARNING: Permanent deletion
DELETE FROM analysis_chunks
WHERE id IN (
  SELECT ac.id
  FROM analysis_chunks ac
  LEFT JOIN analyses a ON ac.analysis_id = a.id
  WHERE a.id IS NULL
);
```

**2. Delete Expired Draft Analyses**
```sql
-- Cascades to chunks via ON DELETE CASCADE
DELETE FROM analyses
WHERE status = 'draft'
  AND updated_at < NOW() - INTERVAL '7 days';
```

**3. Delete Failed Analyses Older Than 30 Days**
```sql
DELETE FROM analyses
WHERE status IN ('failed', 'error')
  AND updated_at < NOW() - INTERVAL '30 days';
```

---

## Scheduled Jobs

### Recommended Cron Schedule

**1. Daily Health Check (2 AM)**
```cron
0 2 * * * cd /app/backend && python scripts/cleanup.py --check >> /var/log/cleanup-health.log 2>&1
```

**2. Weekly Orphan Cleanup (Sunday 3 AM)**
```cron
0 3 * * 0 cd /app/backend && python scripts/cleanup.py --orphans >> /var/log/cleanup-orphans.log 2>&1
```

**3. Daily TTL Cleanup (4 AM)**
```cron
0 4 * * * cd /app/backend && python scripts/cleanup.py --ttl >> /var/log/cleanup-ttl.log 2>&1
```

**4. Monthly Full Cleanup (1st of month, 5 AM)**
```cron
0 5 1 * * cd /app/backend && python scripts/cleanup.py --full --include-superseded >> /var/log/cleanup-full.log 2>&1
```

**5. Weekly Report Generation (Monday 6 AM)**
```cron
0 6 * * 1 cd /app/backend && python scripts/cleanup.py --report /var/reports/cleanup_$(date +\%Y\%m\%d).md
```

### Docker Compose (Scheduled Service)

```yaml
services:
  cleanup:
    image: skillforge-backend:latest
    command: python scripts/cleanup.py --full
    environment:
      - DATABASE_URL=${DATABASE_URL}
    depends_on:
      - db
    restart: "no"  # Run once
```

### Kubernetes CronJob

```yaml
apiVersion: batch/v1
kind: CronJob
metadata:
  name: skillforge-cleanup
spec:
  schedule: "0 4 * * *"  # Daily at 4 AM
  jobTemplate:
    spec:
      template:
        spec:
          containers:
          - name: cleanup
            image: skillforge-backend:latest
            command: ["python", "scripts/cleanup.py", "--full"]
            env:
            - name: DATABASE_URL
              valueFrom:
                secretKeyRef:
                  name: skillforge-secrets
                  key: database-url
          restartPolicy: OnFailure
```

---

## Monitoring

### Metrics to Track

**1. Orphan Chunk Count**
```python
counts = await cleaner.count_orphans()
# Emit metric: orphan_chunks_total = counts['total']
```

**2. Expired Analysis Count**
```python
counts = await ttl_cleaner.count_expired_by_status()
# Emit metric: expired_analyses_total = counts['total']
```

**3. Integrity Issue Count**
```python
report = await checker.run_all_checks()
issue_count = sum(len(v) for v in report.values() if isinstance(v, list))
# Emit metric: integrity_issues_total = issue_count
```

**4. Cleanup Execution Time**
```python
import time
start = time.time()
await service.run_full_cleanup(dry_run=False)
duration = time.time() - start
# Emit metric: cleanup_duration_seconds = duration
```

### Alerts

**1. High Orphan Count**
```
Alert: orphan_chunks_total > 10000
Action: Investigate parent analysis deletion patterns
```

**2. High Integrity Issue Count**
```
Alert: integrity_issues_total > 100
Action: Check embedding generation service
```

**3. Cleanup Failure**
```
Alert: cleanup_duration_seconds > 3600 (1 hour)
Action: Check database performance, reduce batch size
```

---

## Migration Guide

### Step 1: Apply CASCADE Delete Migration

```bash
cd backend
alembic upgrade head
```

This applies migration `20251210_add_cascade_delete.py` which adds:
```sql
ON DELETE CASCADE
```
to the `analysis_chunks.analysis_id` foreign key.

### Step 2: Test in Development

```bash
# Health check
python scripts/cleanup.py --check

# Dry run
python scripts/cleanup.py --dry-run

# Generate report
python scripts/cleanup.py --report dev_cleanup_report.md
```

### Step 3: Production Rollout

**Phase 1: Monitoring Only (Week 1)**
```bash
# Daily health checks (no cleanup)
python scripts/cleanup.py --check
```

**Phase 2: Soft Cleanup (Week 2-3)**
```bash
# Start with orphan cleanup only
python scripts/cleanup.py --orphans
```

**Phase 3: Full Cleanup (Week 4+)**
```bash
# Enable full cleanup
python scripts/cleanup.py --full
```

### Step 4: Schedule Cron Jobs

Add to crontab:
```bash
crontab -e
```

Paste recommended schedule from [Scheduled Jobs](#scheduled-jobs).

---

## Troubleshooting

### Issue: Cleanup Taking Too Long

**Cause:** Large batch size or too many items

**Solution:**
```bash
# Reduce batch size
python scripts/cleanup.py --full --batch-size 500

# Or clean up in stages
python scripts/cleanup.py --orphans  # First
python scripts/cleanup.py --ttl      # Then
```

### Issue: High Orphan Count After Cleanup

**Cause:** Ongoing analysis deletion without cascade

**Solution:**
- Ensure migration `20251210_add_cascade_delete.py` is applied
- Check foreign key constraint:
  ```sql
  SELECT constraint_name, table_name
  FROM information_schema.table_constraints
  WHERE constraint_name = 'analysis_chunks_analysis_id_fkey';
  ```

### Issue: Integrity Issues Not Resolving

**Cause:** Embedding service generating corrupt vectors

**Solution:**
1. Check OpenAI API status
2. Verify embedding model version
3. Re-generate embeddings for affected chunks:
   ```python
   invalid_ids = await checker.check_invalid_values_in_chunks()
   # Re-run embedding workflow for these analyses
   ```

---

## API Reference

### CleanupService

```python
class CleanupService:
    async def run_full_cleanup(
        self,
        include_orphans: bool = True,
        include_expired: bool = True,
        include_superseded: bool = False,
        hard_delete: bool = False,
        dry_run: bool = False,
    ) -> dict[str, dict]

    async def health_check(self) -> dict[str, bool | int]

    async def generate_cleanup_report_markdown(
        self,
        include_recommendations: bool = True,
    ) -> str

    async def schedule_cleanup(
        self,
        cleanup_type: str = "full",  # 'full', 'orphans', 'ttl', 'health'
    ) -> dict
```

### OrphanCleaner

```python
class OrphanCleaner:
    async def find_orphans_missing_parent(self) -> list[uuid.UUID]

    async def find_orphans_failed_analysis(
        self,
        failed_threshold_days: int = 7,
    ) -> list[uuid.UUID]

    async def find_orphans_superseded_analysis(self) -> list[uuid.UUID]

    async def delete_orphans_batch(
        self,
        orphan_ids: list[uuid.UUID],
        hard_delete: bool = False,
    ) -> int

    async def cleanup_all_orphans(
        self,
        hard_delete: bool = False,
        include_superseded: bool = False,
    ) -> dict[str, int]

    async def count_orphans(self) -> dict[str, int]
```

### VectorIntegrityChecker

```python
class VectorIntegrityChecker:
    async def check_chunk_vector_dimensions(self) -> list[uuid.UUID]

    async def check_null_chunk_vectors(self) -> list[uuid.UUID]

    async def check_invalid_values_in_chunks(
        self,
        check_batch_size: int = 100,
    ) -> list[tuple[uuid.UUID, str]]

    async def check_zero_vectors_in_chunks(self) -> list[uuid.UUID]

    async def check_vector_normalization(
        self,
        tolerance: float = 1e-5,
    ) -> list[tuple[uuid.UUID, float]]

    async def run_all_checks(self) -> dict[str, list]

    async def generate_integrity_report_markdown(self) -> str
```

### TTLCleaner

```python
class TTLCleaner:
    def set_ttl_policy(self, status: str, days: int | None) -> None

    async def find_expired_analyses(
        self,
        status: str | None = None,
        dry_run: bool = True,
    ) -> list[tuple[uuid.UUID, str, datetime]]

    async def delete_expired_analyses(
        self,
        status: str | None = None,
        cascade_to_chunks: bool = True,
    ) -> dict[str, int]

    async def count_expired_by_status(self) -> dict[str, int]

    async def cleanup_with_preview(
        self,
        status: str | None = None,
        confirm: bool = False,
    ) -> dict[str, int | dict]

    async def extend_ttl_for_analysis(
        self,
        analysis_id: uuid.UUID,
        extension_days: int = 7,
    ) -> bool

    async def get_ttl_status_report(self) -> dict[str, dict]
```

---

## Performance Considerations

### Database Indexes

**Required indexes for efficient cleanup:**

```sql
-- Already exists: analysis_chunks.analysis_id (foreign key index)
CREATE INDEX IF NOT EXISTS ix_analysis_chunks_analysis_id
ON analysis_chunks (analysis_id);

-- Already exists: analysis_chunks.hash (deduplication)
CREATE INDEX IF NOT EXISTS ix_analysis_chunks_hash
ON analysis_chunks (hash);

-- Add if missing: analyses.status + updated_at (TTL cleanup)
CREATE INDEX IF NOT EXISTS ix_analyses_status_updated
ON analyses (status, updated_at);

-- Add if missing: analyses.url (superseded analysis detection)
CREATE INDEX IF NOT EXISTS ix_analyses_url
ON analyses (url);
```

### Batch Size Tuning

| Dataset Size | Recommended Batch Size |
|--------------|------------------------|
| < 10K chunks | 1000 (default) |
| 10K - 100K | 500 |
| 100K - 1M | 250 |
| > 1M | 100 |

### Vacuum After Large Deletes

```sql
-- Reclaim disk space after cleanup
VACUUM ANALYZE analysis_chunks;
VACUUM ANALYZE analyses;
```

---

## Future Enhancements

1. **Soft Delete Column**
   - Add `is_deleted` column to `analysis_chunks`
   - Implement grace period before hard delete
   - Migration: `backend/alembic/versions/YYYYMMDD_add_is_deleted.py`

2. **Cleanup Audit Log**
   - Track cleanup operations in `cleanup_audit` table
   - Record: timestamp, operation, items_deleted, user

3. **Vector Re-generation**
   - Automatic re-embedding for corrupt vectors
   - Integration with embedding workflow

4. **Storage Monitoring**
   - Track storage usage by analysis
   - Alert on high disk usage
   - Automated cleanup triggers

5. **Admin Dashboard**
   - Web UI for cleanup operations
   - Real-time health monitoring
   - Interactive reports

---

## References

- **Database Schema**: `/backend/app/models/`
- **Migrations**: `/backend/alembic/versions/`
- **Repository Pattern**: `/backend/app/db/repositories/`
- **Architecture Docs**: `/docs/ARCHITECTURE.md`
- **Current Status**: `/docs/CURRENT_STATUS.md`

---

**Maintained by:** Backend System Architect
**Last Updated:** December 10, 2025
**Version:** 1.0.0
