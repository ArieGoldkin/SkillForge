# Database Cleanup Strategy - Executive Summary

**Document:** SkillForge Embedding Pipeline Cleanup
**Author:** Backend System Architect
**Date:** December 10, 2025
**Status:** Implementation Complete

---

## Quick Start

```bash
# Navigate to backend
cd /Users/yonatangross/coding/SkillForge/backend

# Health check (read-only)
python scripts/cleanup.py --check

# Preview cleanup (dry run)
python scripts/cleanup.py --dry-run

# Execute cleanup
python scripts/cleanup.py --full
```

---

## Architecture Overview

### Data Model

```
analyses (parent)
├── id: UUID (PK)
├── status: draft | pending | complete | failed | error
├── content_embedding: Vector(1536)
└── chunks: analysis_chunks[] (ON DELETE CASCADE)

analysis_chunks (child)
├── id: UUID (PK)
├── analysis_id: UUID (FK → analyses.id) CASCADE
├── granularity: coarse | fine | summary
├── vector: Vector(1536) NOT NULL
└── hash: String(128) (deduplication)
```

### Three-Pillar Strategy

```
┌────────────────────────────────────────────────────────────┐
│ 1. ORPHAN CLEANUP                                          │
│    Remove chunks with deleted/failed/superseded parent     │
│    • Missing parent (LEFT JOIN)                            │
│    • Failed analysis > 7 days                              │
│    • Superseded analysis (ROW_NUMBER window)               │
├────────────────────────────────────────────────────────────┤
│ 2. INTEGRITY CHECKS                                        │
│    Detect corrupted vectors (read-only)                    │
│    • Dimension mismatch (expected 1536)                    │
│    • NULL vectors                                          │
│    • NaN/Inf values                                        │
│    • Zero vectors                                          │
│    • Non-normalized (L2 norm ≠ 1.0)                        │
├────────────────────────────────────────────────────────────┤
│ 3. TTL EXPIRATION                                          │
│    Remove old drafts with cascade to chunks                │
│    • draft: 7 days                                         │
│    • pending: 1 day (stuck)                                │
│    • failed/error: 30 days                                 │
│    • complete: never expire                                │
└────────────────────────────────────────────────────────────┘
```

---

## Implementation Files

### Python Services

```
backend/app/services/cleanup/
├── __init__.py                  # Package exports
├── cleanup_service.py           # Main orchestrator
├── orphan_cleanup.py            # Orphan detection & removal
├── integrity_checks.py          # Vector validation
├── ttl_cleanup.py               # TTL-based expiration
├── README.md                    # Full documentation (8000+ words)
└── CLEANUP_STRATEGY.md          # This file
```

### Scripts & Migrations

```
backend/scripts/
└── cleanup.py                   # CLI tool (executable)

backend/alembic/versions/
└── 20251210_add_cascade_delete.py  # ON DELETE CASCADE migration
```

---

## Key Design Decisions

### 1. Batch Processing

**Problem:** Large datasets cause memory exhaustion

**Solution:**
- Default batch size: 1000 records
- Configurable via `--batch-size` flag
- Progress logging per batch
- Commit after each batch

**Example:**
```python
for i in range(0, len(orphan_ids), batch_size):
    batch = orphan_ids[i : i + batch_size]
    # Process batch
    await session.commit()
```

### 2. Cascade Delete

**Problem:** Manual chunk deletion is error-prone

**Solution:**
- Foreign key constraint with `ON DELETE CASCADE`
- Automatic chunk cleanup when parent deleted
- Database-enforced consistency

**Migration:**
```sql
ALTER TABLE analysis_chunks
DROP CONSTRAINT analysis_chunks_analysis_id_fkey;

ALTER TABLE analysis_chunks
ADD CONSTRAINT analysis_chunks_analysis_id_fkey
FOREIGN KEY (analysis_id) REFERENCES analyses(id)
ON DELETE CASCADE;
```

### 3. Soft vs Hard Delete

**Current:** Hard delete (permanent)
**Future:** Soft delete with `is_deleted` column
**Grace Period:** 7 days before hard delete

**Trade-offs:**
- Hard delete: Immediate space reclamation, irreversible
- Soft delete: Safer, allows recovery, requires additional storage

---

## SQL Query Reference

### Orphan Detection

**1. Missing Parent (LEFT JOIN)**
```sql
SELECT ac.id
FROM analysis_chunks ac
LEFT JOIN analyses a ON ac.analysis_id = a.id
WHERE a.id IS NULL;
```

**2. Failed Analysis > 7 Days**
```sql
SELECT ac.id
FROM analysis_chunks ac
JOIN analyses a ON ac.analysis_id = a.id
WHERE a.status IN ('failed', 'error')
  AND a.updated_at < NOW() - INTERVAL '7 days';
```

**3. Superseded Analysis (Window Function)**
```sql
WITH ranked AS (
  SELECT id, url,
    ROW_NUMBER() OVER (PARTITION BY url ORDER BY created_at DESC) as rn
  FROM analyses WHERE status = 'complete'
)
SELECT ac.id
FROM analysis_chunks ac
WHERE ac.analysis_id IN (SELECT id FROM ranked WHERE rn > 1);
```

### Integrity Checks

**1. Dimension Mismatch**
```sql
SELECT id, vector_dims(vector) as dims
FROM analysis_chunks
WHERE vector_dims(vector) != 1536;
```

**2. NULL Vectors**
```sql
SELECT id FROM analysis_chunks WHERE vector IS NULL;
```

**3. Storage Usage**
```sql
SELECT a.id, COUNT(ac.id) as chunks,
  pg_size_pretty(
    pg_column_size(a.content_embedding) +
    SUM(pg_column_size(ac.vector))
  ) as storage
FROM analyses a
LEFT JOIN analysis_chunks ac ON a.id = ac.analysis_id
GROUP BY a.id
ORDER BY SUM(pg_column_size(ac.vector)) DESC;
```

### TTL Cleanup

**1. Expired Drafts**
```sql
DELETE FROM analyses
WHERE status = 'draft'
  AND updated_at < NOW() - INTERVAL '7 days';
-- Chunks cascade automatically
```

**2. Stuck Pending**
```sql
DELETE FROM analyses
WHERE status = 'pending'
  AND updated_at < NOW() - INTERVAL '1 day';
```

---

## Usage Patterns

### 1. Development/Testing

```bash
# Health check
python scripts/cleanup.py --check

# Dry run
python scripts/cleanup.py --dry-run

# Orphans only
python scripts/cleanup.py --orphans

# Generate report
python scripts/cleanup.py --report cleanup_report.md
```

### 2. Production Deployment

```bash
# Phase 1: Monitoring (Week 1)
python scripts/cleanup.py --check

# Phase 2: Conservative cleanup (Week 2-3)
python scripts/cleanup.py --orphans

# Phase 3: Full cleanup (Week 4+)
python scripts/cleanup.py --full
```

### 3. Scheduled Cron Jobs

```cron
# Daily health check (2 AM)
0 2 * * * cd /app && python scripts/cleanup.py --check

# Weekly orphan cleanup (Sunday 3 AM)
0 3 * * 0 cd /app && python scripts/cleanup.py --orphans

# Daily TTL cleanup (4 AM)
0 4 * * * cd /app && python scripts/cleanup.py --ttl

# Monthly full cleanup (1st, 5 AM)
0 5 1 * * cd /app && python scripts/cleanup.py --full --include-superseded
```

---

## API Examples

### Python API (Programmatic)

**Health Check**
```python
from app.services.cleanup import CleanupService
from app.db.session import get_db

async for db in get_db():
    service = CleanupService(db)
    health = await service.health_check()

    if not health['healthy']:
        print(f"Issues: {health['total_issues']}")
```

**Full Cleanup**
```python
result = await service.run_full_cleanup(
    include_orphans=True,
    include_expired=True,
    include_superseded=False,
    hard_delete=False,
    dry_run=False,
)

print(f"Deleted {result['summary']['total_items_affected']} items")
```

**Custom TTL Policy**
```python
from app.services.cleanup import TTLCleaner

cleaner = TTLCleaner(db)
cleaner.set_ttl_policy('draft', 14)  # Extend to 14 days
cleaner.set_ttl_policy('complete', None)  # Never expire

stats = await cleaner.delete_expired_analyses()
```

**Integrity Report**
```python
from app.services.cleanup import VectorIntegrityChecker

checker = VectorIntegrityChecker(db)
report = await checker.run_all_checks()

# Check for dimension issues
if report['chunk_dimension_issues']:
    print(f"Found {len(report['chunk_dimension_issues'])} dimension mismatches")

# Check for NaN/Inf
for chunk_id, issue in report['invalid_values']:
    print(f"Chunk {chunk_id}: {issue}")
```

---

## Monitoring & Alerts

### Key Metrics

| Metric | Threshold | Action |
|--------|-----------|--------|
| `orphan_chunks_total` | > 10,000 | Investigate deletion patterns |
| `expired_analyses_total` | > 1,000 | Check TTL policies |
| `integrity_issues_total` | > 100 | Check embedding service |
| `cleanup_duration_seconds` | > 3,600 | Reduce batch size |

### Health Status

```python
health = await service.health_check()

# Emit metrics
emit('orphan_chunks', health['orphan_chunks'])
emit('expired_analyses', health['expired_analyses'])
emit('integrity_issues', health['integrity_issues'])

# Alert if unhealthy
if not health['healthy']:
    alert(f"Cleanup health check failed: {health['total_issues']} issues")
```

---

## Performance Considerations

### Database Indexes

**Required for efficient cleanup:**

```sql
-- Already exists
CREATE INDEX ix_analysis_chunks_analysis_id ON analysis_chunks (analysis_id);
CREATE INDEX ix_analysis_chunks_hash ON analysis_chunks (hash);

-- Add if missing
CREATE INDEX ix_analyses_status_updated ON analyses (status, updated_at);
CREATE INDEX ix_analyses_url ON analyses (url);
```

### Batch Size Tuning

| Dataset Size | Batch Size |
|--------------|------------|
| < 10K | 1000 |
| 10K-100K | 500 |
| 100K-1M | 250 |
| > 1M | 100 |

### Vacuum After Cleanup

```sql
VACUUM ANALYZE analysis_chunks;
VACUUM ANALYZE analyses;
```

---

## Deployment Checklist

- [ ] **Migration Applied**
  ```bash
  cd backend
  alembic upgrade 20251210_cascade
  ```

- [ ] **Verify CASCADE Constraint**
  ```sql
  SELECT constraint_name, delete_rule
  FROM information_schema.referential_constraints
  WHERE constraint_name = 'analysis_chunks_analysis_id_fkey';
  -- Should return: delete_rule = 'CASCADE'
  ```

- [ ] **Test Health Check**
  ```bash
  python scripts/cleanup.py --check
  ```

- [ ] **Run Dry Run**
  ```bash
  python scripts/cleanup.py --dry-run
  ```

- [ ] **Schedule Cron Jobs**
  ```bash
  crontab -e
  # Add recommended schedule
  ```

- [ ] **Setup Monitoring**
  - Track orphan count
  - Track integrity issues
  - Alert on high counts

- [ ] **Document Runbooks**
  - Orphan cleanup procedure
  - Integrity issue resolution
  - TTL policy changes

---

## Troubleshooting

### Issue: Cleanup Too Slow

**Symptoms:** Cleanup takes > 1 hour

**Solution:**
```bash
# Reduce batch size
python scripts/cleanup.py --full --batch-size 500

# Or split into stages
python scripts/cleanup.py --orphans
python scripts/cleanup.py --ttl
```

### Issue: High Orphan Count

**Symptoms:** Orphans > 10,000 after cleanup

**Cause:** CASCADE not working

**Solution:**
```sql
-- Check constraint
SELECT constraint_name, delete_rule
FROM information_schema.referential_constraints
WHERE constraint_name = 'analysis_chunks_analysis_id_fkey';

-- Re-apply migration if needed
```

### Issue: Integrity Failures

**Symptoms:** Many NaN/Inf values

**Cause:** Embedding service issues

**Solution:**
1. Check OpenAI API status
2. Verify embedding model
3. Re-generate embeddings:
   ```python
   invalid_ids = await checker.check_invalid_values_in_chunks()
   # Re-run embedding workflow for these chunks
   ```

---

## Future Enhancements

1. **Soft Delete Implementation**
   - Add `is_deleted BOOLEAN` column
   - Grace period before hard delete
   - Recovery mechanism

2. **Cleanup Audit Log**
   - Track all cleanup operations
   - Record: timestamp, user, items deleted

3. **Vector Re-generation**
   - Automatic re-embedding for corrupt vectors
   - Integration with embedding workflow

4. **Storage Monitoring**
   - Track disk usage trends
   - Automated cleanup triggers

5. **Admin Dashboard**
   - Web UI for cleanup operations
   - Real-time health monitoring

---

## Resources

- **Full Documentation**: `/backend/app/services/cleanup/README.md` (comprehensive)
- **Script Usage**: `python scripts/cleanup.py --help`
- **Architecture**: `/docs/ARCHITECTURE.md`
- **Database Models**: `/backend/app/models/`
- **Migrations**: `/backend/alembic/versions/`

---

## Summary

This cleanup strategy provides:

✅ **Orphan Detection**: 3 methods (missing parent, failed analysis, superseded)
✅ **Integrity Checks**: 5 vector validation checks
✅ **TTL Expiration**: Configurable retention policies
✅ **Batch Processing**: Efficient for large datasets
✅ **Cascade Delete**: Database-enforced consistency
✅ **CLI Tool**: Easy-to-use script with dry-run
✅ **Python API**: Programmatic access for automation
✅ **SQL Queries**: Manual inspection and cleanup
✅ **Monitoring**: Health checks and metrics
✅ **Documentation**: Comprehensive guides

**Total Implementation:**
- 4 Python service classes
- 1 CLI script
- 1 database migration
- 2 documentation files (8000+ words)
- 20+ SQL query examples
- Full API reference

**Ready for production deployment.**

---

**Maintained by:** Backend System Architect
**Version:** 1.0.0
**Last Updated:** December 10, 2025
