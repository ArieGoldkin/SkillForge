# Database Cleanup - Quick Reference Card

**SkillForge Backend - Production Operations Guide**

---

## Emergency Commands

```bash
# Check system health (read-only, safe)
python scripts/cleanup.py --check

# Preview what will be deleted (dry run)
python scripts/cleanup.py --dry-run

# Execute full cleanup (safe with defaults)
python scripts/cleanup.py --full
```

---

## Common Operations

### Health Check
```bash
cd /Users/yonatangross/coding/SkillForge/backend
python scripts/cleanup.py --check
```

**Exit codes:**
- `0` = Healthy (no issues)
- `1` = Issues found

### Orphan Cleanup
```bash
# Preview orphans
python scripts/cleanup.py --dry-run

# Clean orphans only
python scripts/cleanup.py --orphans

# Include superseded analyses
python scripts/cleanup.py --orphans --include-superseded
```

### TTL Cleanup
```bash
# Clean expired analyses only
python scripts/cleanup.py --ttl

# Defaults: draft=7d, pending=1d, failed=30d
```

### Full Cleanup
```bash
# Standard cleanup
python scripts/cleanup.py --full

# Aggressive cleanup (includes superseded)
python scripts/cleanup.py --full --include-superseded

# Permanent deletion (use with caution!)
python scripts/cleanup.py --full --hard-delete
```

### Generate Report
```bash
python scripts/cleanup.py --report /tmp/cleanup_report.md
cat /tmp/cleanup_report.md
```

---

## Python API Quick Reference

```python
from app.services.cleanup import CleanupService
from app.db.session import get_db

async for db in get_db():
    service = CleanupService(db)

    # Health check
    health = await service.health_check()
    print(f"Healthy: {health['healthy']}")
    print(f"Issues: {health['total_issues']}")

    # Full cleanup
    result = await service.run_full_cleanup(
        include_orphans=True,
        include_expired=True,
        include_superseded=False,
        hard_delete=False,
        dry_run=False,
    )
    print(f"Deleted: {result['summary']['total_items_affected']}")
```

---

## SQL Quick Checks

### Find Orphaned Chunks
```sql
-- Missing parent
SELECT COUNT(*) FROM analysis_chunks ac
LEFT JOIN analyses a ON ac.analysis_id = a.id
WHERE a.id IS NULL;
```

### Find Expired Analyses
```sql
-- Drafts > 7 days
SELECT COUNT(*) FROM analyses
WHERE status = 'draft'
  AND updated_at < NOW() - INTERVAL '7 days';
```

### Check Vector Integrity
```sql
-- Invalid dimensions
SELECT COUNT(*) FROM analysis_chunks
WHERE vector_dims(vector) != 1536;

-- NULL vectors
SELECT COUNT(*) FROM analysis_chunks
WHERE vector IS NULL;
```

### Storage Usage
```sql
-- Top 10 analyses by storage
SELECT a.url, COUNT(ac.id) as chunks,
  pg_size_pretty(SUM(pg_column_size(ac.vector))) as size
FROM analyses a
JOIN analysis_chunks ac ON a.id = ac.analysis_id
GROUP BY a.id, a.url
ORDER BY SUM(pg_column_size(ac.vector)) DESC
LIMIT 10;
```

---

## Cron Schedule (Copy-Paste)

```cron
# SkillForge Database Cleanup Jobs

# Daily health check (2 AM)
0 2 * * * cd /app/backend && python scripts/cleanup.py --check >> /var/log/cleanup-health.log 2>&1

# Weekly orphan cleanup (Sunday 3 AM)
0 3 * * 0 cd /app/backend && python scripts/cleanup.py --orphans >> /var/log/cleanup-orphans.log 2>&1

# Daily TTL cleanup (4 AM)
0 4 * * * cd /app/backend && python scripts/cleanup.py --ttl >> /var/log/cleanup-ttl.log 2>&1

# Monthly full cleanup (1st of month, 5 AM)
0 5 1 * * cd /app/backend && python scripts/cleanup.py --full --include-superseded >> /var/log/cleanup-full.log 2>&1
```

---

## Troubleshooting

### Cleanup Taking Too Long
```bash
# Reduce batch size
python scripts/cleanup.py --full --batch-size 500
```

### High Orphan Count After Cleanup
```sql
-- Check CASCADE constraint
SELECT constraint_name, delete_rule
FROM information_schema.referential_constraints
WHERE constraint_name = 'analysis_chunks_analysis_id_fkey';
-- Should return: delete_rule = 'CASCADE'
```

### Integrity Issues Not Resolving
```python
# Re-check specific issue types
from app.services.cleanup import VectorIntegrityChecker

checker = VectorIntegrityChecker(db)

# Check dimensions
invalid = await checker.check_chunk_vector_dimensions()

# Check NULL vectors
nulls = await checker.check_null_chunk_vectors()

# Check NaN/Inf
issues = await checker.check_invalid_values_in_chunks()
```

---

## Alert Thresholds

| Metric | Warning | Critical | Action |
|--------|---------|----------|--------|
| Orphan chunks | 5,000 | 10,000 | Investigate deletions |
| Expired analyses | 500 | 1,000 | Review TTL policies |
| Integrity issues | 50 | 100 | Check embedding service |
| Cleanup duration | 1800s | 3600s | Reduce batch size |

---

## Migration Status Check

```sql
-- Check if CASCADE migration applied
SELECT constraint_name, delete_rule
FROM information_schema.referential_constraints
WHERE constraint_name = 'analysis_chunks_analysis_id_fkey';

-- Expected output:
-- constraint_name                      | delete_rule
-- -------------------------------------|------------
-- analysis_chunks_analysis_id_fkey    | CASCADE
```

```bash
# Check Alembic migration status
cd /Users/yonatangross/coding/SkillForge/backend
alembic current
# Should include: 20251210_cascade
```

---

## Emergency Procedures

### Stop Runaway Cleanup
```sql
-- Find active cleanup sessions
SELECT pid, query_start, state, query
FROM pg_stat_activity
WHERE query LIKE '%DELETE FROM analysis%'
  OR query LIKE '%DELETE FROM analyses%';

-- Terminate if needed (use with caution!)
SELECT pg_terminate_backend(pid)
FROM pg_stat_activity
WHERE query LIKE '%DELETE FROM analysis%';
```

### Restore from Backup
```bash
# If hard delete was accidental
# 1. Stop application
# 2. Restore from most recent backup
# 3. Re-run migrations
# 4. Restart application
```

### Manual Cleanup (Emergency Only)
```sql
-- CAUTION: Use only if script fails
BEGIN;

-- Delete orphaned chunks
DELETE FROM analysis_chunks
WHERE id IN (
  SELECT ac.id FROM analysis_chunks ac
  LEFT JOIN analyses a ON ac.analysis_id = a.id
  WHERE a.id IS NULL
  LIMIT 1000  -- Batch limit
);

-- Check before committing
SELECT COUNT(*) FROM analysis_chunks ac
LEFT JOIN analyses a ON ac.analysis_id = a.id
WHERE a.id IS NULL;

COMMIT;  -- Or ROLLBACK if something looks wrong
```

---

## Performance Tips

1. **Run cleanup during low-traffic hours** (2-6 AM recommended)
2. **Use dry-run first** to estimate impact
3. **Adjust batch size** based on database load
4. **Vacuum after large deletes**:
   ```sql
   VACUUM ANALYZE analysis_chunks;
   VACUUM ANALYZE analyses;
   ```
5. **Monitor disk I/O** during cleanup

---

## Documentation Links

- **Full Guide**: `/backend/app/services/cleanup/README.md`
- **Executive Summary**: `/backend/app/services/cleanup/CLEANUP_STRATEGY.md`
- **Architecture**: `/docs/ARCHITECTURE.md`
- **Database Models**: `/backend/app/models/`
- **Migrations**: `/backend/alembic/versions/`

---

## Support Contacts

- **Database Issues**: DBA team
- **Application Issues**: Backend team
- **Infrastructure**: DevOps team

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0.0 | 2025-12-10 | Initial implementation |

---

**Last Updated**: December 10, 2025
**Maintained By**: Backend System Architect
