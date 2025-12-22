# PostgreSQL 18 Upgrade Plan for SkillForge
**Date:** December 22, 2025  
**Status:** Research Complete - Ready for Implementation  
**Current:** PostgreSQL 17 (pgvector/pgvector:pg17)  
**Target:** PostgreSQL 18 (pgvector/pgvector:pg18-bookworm)

---

## 🎯 Executive Summary

**Verdict: ✅ YES, we can upgrade to PostgreSQL 18**

**Key Findings:**
- ✅ PostgreSQL 18 released September 25, 2025 (stable)
- ✅ pgvector 0.8.1+ compatible with PostgreSQL 18 (0.8.0 had issues, fixed)
- ✅ Docker image available: `pgvector/pgvector:pg18-bookworm`
- ✅ All our features compatible (LZ4, pgvector, tsvector, HNSW indexes)
- ✅ Native UUID v7 support (`uuidv7()` function) - **MAJOR BENEFIT**
- ⚠️ Minor breaking changes (VACUUM behavior, generated columns) - easily handled

**Recommendation:** Upgrade to PostgreSQL 18 for native UUID v7 support and performance improvements.

---

## 🔍 Current State Analysis

### What We're Using

```yaml
Current Setup:
  Database: PostgreSQL 17
  Docker Image: pgvector/pgvector:pg17
  Extensions:
    - pgvector (vector similarity search)
    - Built-in: tsvector, GIN indexes, HNSW indexes
  Features:
    - LZ4 TOAST compression (raw_content column)
    - Vector embeddings (1536 dimensions)
    - Full-text search (tsvector + GIN)
    - HNSW indexes for semantic search
  Python Dependencies:
    - pgvector: ^0.4.2 (SQLAlchemy wrapper)
    - psycopg2-binary: ^2.9.10
    - asyncpg: ^0.31.0
```

### PostgreSQL-Specific Features We Use

1. **pgvector Extension**
   - HNSW indexes for vector similarity
   - IVFFlat indexes for agent_examples
   - Vector cosine operations

2. **Full-Text Search**
   - `tsvector` columns (`search_vector`, `content_tsvector`)
   - `to_tsvector()` functions
   - GIN indexes for fast text search
   - Triggers for auto-updating tsvector

3. **LZ4 Compression**
   - TOAST compression on `raw_content` column
   - PostgreSQL 17+ feature (also in PG 18)

4. **Standard Features**
   - JSONB columns
   - UUID primary keys
   - Foreign keys with CASCADE
   - Timestamps with timezone

---

## ✅ Compatibility Analysis

### ✅ Fully Compatible

| Feature | PG 17 | PG 18 | Status |
|---------|-------|-------|--------|
| **pgvector extension** | ✅ 0.4.x | ✅ 0.8.1+ | Compatible (need 0.8.1+) |
| **LZ4 compression** | ✅ | ✅ | Fully compatible |
| **tsvector/GIN** | ✅ | ✅ | Fully compatible |
| **HNSW indexes** | ✅ | ✅ | Fully compatible |
| **JSONB** | ✅ | ✅ | Fully compatible |
| **UUID types** | ✅ | ✅ | Fully compatible |
| **Python pgvector** | ✅ 0.4.2 | ✅ 0.4.2 | Compatible (wrapper only) |
| **asyncpg** | ✅ 0.31.0 | ✅ 0.31.0 | Compatible |
| **psycopg2** | ✅ 2.9.10 | ✅ 2.9.10 | Compatible |

### ⚠️ Breaking Changes (Minor - Easy to Handle)

#### 1. VACUUM/ANALYZE Behavior Change

**What Changed:**
- PostgreSQL 18 processes child tables of inheritance hierarchies by default
- Previously only parent table was processed

**Impact for SkillForge:** 
- ✅ **NONE** - We don't use table inheritance
- No action needed

**If we did use inheritance:**
```sql
-- Old behavior (PG 17): Only parent vacuumed
VACUUM parent_table;

-- New behavior (PG 18): Parent + children vacuumed
VACUUM parent_table;  -- Now includes children

-- To vacuum only parent (if needed):
VACUUM ONLY parent_table;
```

#### 2. Generated Columns Default to Virtual

**What Changed:**
- Generated columns are now virtual by default (computed on read)
- Previously were stored by default

**Impact for SkillForge:**
- ✅ **NONE** - We don't use generated columns
- No action needed

**If we did use generated columns:**
```sql
-- Virtual (computed on read) - default in PG 18
ALTER TABLE t ADD COLUMN full_name TEXT GENERATED ALWAYS AS (first || ' ' || last) STORED;

-- Explicitly stored (if needed):
ALTER TABLE t ADD COLUMN full_name TEXT GENERATED ALWAYS AS (first || ' ' || last) STORED;
```

#### 3. Data Checksums Enabled by Default

**What Changed:**
- `initdb` now enables data checksums by default
- Better data integrity detection

**Impact for SkillForge:**
- ✅ **POSITIVE** - Better data integrity
- ⚠️ **Migration Note:** When using `pg_upgrade`, both clusters must have matching checksum settings

**Migration Handling:**
```bash
# If upgrading from non-checksum cluster:
initdb --no-data-checksums /path/to/datadir  # Match source
# OR enable checksums on source first (recommended)
```

---

## 🚀 PostgreSQL 18 New Features (Benefits for Us)

### 1. Native UUID v7 Support ⭐ **MAJOR BENEFIT**

```sql
-- PostgreSQL 18 native function
CREATE TABLE analyses (
    id UUID PRIMARY KEY DEFAULT uuidv7()
);
```

**Benefits:**
- ✅ No Python library needed (`uuid-utils`)
- ✅ Database-level generation (better performance)
- ✅ Standard PostgreSQL function (future-proof)
- ✅ Time-ordered UUIDs for better index performance

**Before (Python library):**
```python
from uuid_utils import uuid7
id = Column(PostgresUUID(as_uuid=True), primary_key=True, default=uuid7)
```

**After (PostgreSQL 18):**
```python
# Database handles it - no Python code needed!
id = Column(PostgresUUID(as_uuid=True), primary_key=True, 
            server_default=text("uuidv7()"))
```

### 2. Optimizer Statistics Retention

**What Changed:**
- `pg_upgrade` now retains optimizer statistics during upgrade
- Reduces need for extensive `ANALYZE` post-upgrade

**Benefit:**
- ✅ Faster upgrade process
- ✅ Query performance maintained immediately after upgrade
- ✅ Less downtime for statistics collection

### 3. OAuth Authentication Support

**What Changed:**
- Native OAuth 2.0 authentication support

**Benefit:**
- ✅ Future authentication options (not needed now, but available)

### 4. Performance Improvements

- Better query planner
- Improved parallel query execution
- Enhanced index performance

---

## 📦 Docker Image Availability

### Available Images

```bash
# PostgreSQL 18 with pgvector (Debian Bookworm)
docker pull pgvector/pgvector:pg18-bookworm

# PostgreSQL 18 with pgvector (Debian Trixie)
docker pull pgvector/pgvector:pg18-trixie

# Current (PostgreSQL 17)
docker pull pgvector/pgvector:pg17
```

### pgvector Extension Version

**Important:** The Docker image includes pgvector extension, but we need to verify version:

```sql
-- Check pgvector version after upgrade
SELECT extversion FROM pg_extension WHERE extname = 'vector';
-- Should be 0.8.1 or higher for PG 18 compatibility
```

**Known Issue:**
- pgvector 0.8.0 had compatibility issues with PostgreSQL 18
- Fixed in pgvector 0.8.1+ (released October 2024)
- Docker images should include 0.8.1+ by December 2025

---

## 🔄 Migration Strategy

### Option 1: pg_upgrade (Recommended for Dev)

**Pros:**
- ✅ Fastest method
- ✅ Minimal downtime
- ✅ Retains optimizer statistics (PG 18 feature)
- ✅ Preserves all data

**Cons:**
- ⚠️ Requires matching checksum settings
- ⚠️ More complex than dump/restore

**Steps:**
```bash
# 1. Backup current database
docker exec skillforge-postgres-dev pg_dumpall -U dev > backup.sql

# 2. Stop current container
docker-compose stop postgres

# 3. Update docker-compose.yml
# Change: image: pgvector/pgvector:pg18-bookworm

# 4. Start new container (fresh data directory)
docker-compose up -d postgres

# 5. Restore data
docker exec -i skillforge-postgres-dev psql -U dev < backup.sql

# 6. Verify pgvector extension
docker exec skillforge-postgres-dev psql -U dev -c "SELECT extversion FROM pg_extension WHERE extname = 'vector';"
```

### Option 2: Dump/Restore (Simpler, Recommended for Dev)

**Pros:**
- ✅ Simple and reliable
- ✅ Clean slate (good for dev)
- ✅ Easy to test

**Cons:**
- ⚠️ Requires full backup/restore
- ⚠️ Loses optimizer statistics (but PG 18 will rebuild)

**Steps:**
```bash
# 1. Backup current database
docker exec skillforge-postgres-dev pg_dumpall -U dev > backup_pg17.sql

# 2. Update docker-compose.yml
# Change: image: pgvector/pgvector:pg18-bookworm

# 3. Stop and remove old container
docker-compose stop postgres
docker volume rm skillforge_postgres-dev-data  # WARNING: Deletes data!

# 4. Start new container
docker-compose up -d postgres

# 5. Restore data
docker exec -i skillforge-postgres-dev psql -U dev < backup_pg17.sql

# 6. Run migrations (if needed)
cd backend
poetry run alembic upgrade head

# 7. Verify everything works
docker exec skillforge-postgres-dev psql -U dev -c "\dx"  # List extensions
docker exec skillforge-postgres-dev psql -U dev -c "SELECT version();"  # Check version
```

### Option 3: Fresh Start (Best for Dev/Staging)

**Since we're in dev and can regenerate data:**

```bash
# 1. Update docker-compose.yml
# Change: image: pgvector/pgvector:pg18-bookworm

# 2. Stop and remove old container
docker-compose down postgres
docker volume rm skillforge_postgres-dev-data

# 3. Start new container
docker-compose up -d postgres

# 4. Run migrations (creates fresh schema)
cd backend
poetry run alembic upgrade head

# 5. Restore golden dataset (if needed)
poetry run python scripts/backup_golden_dataset.py restore
```

---

## 📋 Step-by-Step Upgrade Plan

### Phase 1: Preparation (Day 1)

- [ ] **Research Complete** ✅ (This document)
- [ ] Create backup of current database
- [ ] Test upgrade in isolated environment
- [ ] Verify pgvector 0.8.1+ compatibility
- [ ] Update documentation

### Phase 2: Docker Image Update (Day 1)

```yaml
# docker-compose.yml
postgres:
  image: pgvector/pgvector:pg18-bookworm  # Changed from pg17
  # ... rest of config unchanged
```

### Phase 3: Database Migration (Day 1)

**Option A: Fresh Start (Recommended for Dev)**
```bash
# Stop services
docker-compose down postgres

# Remove volume (WARNING: Deletes data!)
docker volume rm skillforge_postgres-dev-data

# Start with PG 18
docker-compose up -d postgres

# Run migrations
cd backend
poetry run alembic upgrade head

# Verify
docker exec skillforge-postgres-dev psql -U dev -c "SELECT version();"
```

**Option B: Preserve Data (If needed)**
```bash
# Backup
docker exec skillforge-postgres-dev pg_dumpall -U dev > backup_pg17.sql

# Upgrade (follow Option 2 steps above)
# ... restore backup ...
```

### Phase 4: Verification (Day 1)

- [ ] Verify PostgreSQL version: `SELECT version();` → Should show 18.x
- [ ] Verify pgvector extension: `SELECT extversion FROM pg_extension WHERE extname = 'vector';` → Should be 0.8.1+
- [ ] Test vector search: Run retrieval smoke tests
- [ ] Test full-text search: Verify tsvector queries work
- [ ] Test LZ4 compression: Verify raw_content compression
- [ ] Run full test suite: `pytest tests/ -v`

### Phase 5: UUID v7 Migration (Day 2)

Once PostgreSQL 18 is confirmed working:

- [ ] Update models to use `uuidv7()` server default
- [ ] Create migration to update default for new records
- [ ] Test UUID v7 generation
- [ ] Update documentation

---

## 🧪 Testing Checklist

### Pre-Upgrade Tests

- [ ] All tests pass on PostgreSQL 17
- [ ] Backup created successfully
- [ ] Golden dataset backed up

### Post-Upgrade Tests

- [ ] **Database Version**
  ```sql
  SELECT version();  -- Should show PostgreSQL 18.x
  ```

- [ ] **Extensions**
  ```sql
  SELECT extname, extversion FROM pg_extension;
  -- Should show: vector | 0.8.1 (or higher)
  ```

- [ ] **Vector Search**
  ```python
  # Run retrieval smoke tests
  pytest tests/smoke/retrieval/ -v
  ```

- [ ] **Full-Text Search**
  ```sql
  SELECT * FROM analyses 
  WHERE search_vector @@ to_tsquery('english', 'test');
  ```

- [ ] **LZ4 Compression**
  ```sql
  SELECT pg_column_compression(raw_content) FROM analyses LIMIT 1;
  -- Should return: lz4
  ```

- [ ] **HNSW Indexes**
  ```sql
  SELECT indexname, indexdef 
  FROM pg_indexes 
  WHERE indexdef LIKE '%hnsw%';
  -- Should show HNSW indexes
  ```

- [ ] **Application Tests**
  ```bash
  # Full test suite
  pytest tests/ -v
  
  # Integration tests
  pytest tests/integration/ -v
  
  # Smoke tests
  pytest tests/smoke/ -v
  ```

---

## ⚠️ Risks & Mitigation

### Risk 1: pgvector Compatibility

**Risk:** pgvector 0.8.0 had issues with PostgreSQL 18  
**Mitigation:** 
- ✅ Use pgvector 0.8.1+ (included in Docker images)
- ✅ Verify extension version after upgrade
- ✅ Test vector search immediately

### Risk 2: Data Loss During Migration

**Risk:** Accidental data loss during upgrade  
**Mitigation:**
- ✅ Full backup before upgrade
- ✅ Test upgrade in isolated environment first
- ✅ For dev: Fresh start is acceptable (can regenerate)

### Risk 3: Breaking Changes

**Risk:** Unknown breaking changes affecting our code  
**Mitigation:**
- ✅ Comprehensive testing checklist
- ✅ Run full test suite after upgrade
- ✅ Monitor application logs for errors

### Risk 4: Performance Regression

**Risk:** Query performance worse on PostgreSQL 18  
**Mitigation:**
- ✅ PG 18 retains optimizer statistics (faster upgrade)
- ✅ Run `ANALYZE` after upgrade if needed
- ✅ Monitor query performance metrics

---

## 📊 Comparison: Before vs After

### Current (PostgreSQL 17)

```yaml
Database: PostgreSQL 17
Docker: pgvector/pgvector:pg17
UUID Generation: Python uuid.uuid4() (random)
pgvector: 0.4.x (extension in Docker)
Features:
  - LZ4 compression ✅
  - Vector search ✅
  - Full-text search ✅
  - HNSW indexes ✅
```

### After Upgrade (PostgreSQL 18)

```yaml
Database: PostgreSQL 18
Docker: pgvector/pgvector:pg18-bookworm
UUID Generation: Native uuidv7() (time-ordered) ⭐
pgvector: 0.8.1+ (extension in Docker)
Features:
  - LZ4 compression ✅
  - Vector search ✅
  - Full-text search ✅
  - HNSW indexes ✅
  - Native UUID v7 ⭐ NEW
  - Better query planner ⭐
  - OAuth auth support (future) ⭐
```

---

## 🎯 Decision Matrix

| Factor | Weight | PG 17 | PG 18 | Score PG 17 | Score PG 18 |
|--------|--------|-------|-------|-------------|-------------|
| **Current Stability** | 15% | 5/5 | 4/5 | 0.75 | 0.6 |
| **UUID v7 Support** | 25% | 0/5 | 5/5 | 0 | 1.25 |
| **Performance** | 20% | 4/5 | 5/5 | 0.8 | 1.0 |
| **Future-Proof** | 20% | 3/5 | 5/5 | 0.6 | 1.0 |
| **Migration Effort** | 10% | 5/5 | 3/5 | 0.5 | 0.3 |
| **Risk Level** | 10% | 5/5 | 4/5 | 0.5 | 0.4 |
| **TOTAL** | 100% | - | - | **3.15** | **4.55** |

**Winner: PostgreSQL 18** (4.55 vs 3.15)

---

## ✅ Final Recommendation

### For SkillForge (December 2025)

**Upgrade to PostgreSQL 18** with the following approach:

1. **Immediate:** Update Docker image to `pgvector/pgvector:pg18-bookworm`
2. **Fresh Start:** Since we're in dev, use fresh database (can regenerate data)
3. **Verify:** Run full test suite to confirm compatibility
4. **Migrate UUIDs:** Update models to use native `uuidv7()` function

### Implementation Priority

- **High:** Upgrade to PostgreSQL 18 (enables UUID v7)
- **High:** Migrate to UUID v7 using native `uuidv7()` function
- **Medium:** Test and verify all features work
- **Low:** Performance tuning (if needed)

### Why Upgrade Now?

1. ✅ **Native UUID v7** - No Python library needed, better performance
2. ✅ **We're in dev** - Perfect time to upgrade (no production risk)
3. ✅ **Future-proof** - Latest stable PostgreSQL version
4. ✅ **Low risk** - All our features are compatible
5. ✅ **Performance** - Better query planner and optimizer

---

## 📚 References

- **PostgreSQL 18 Release Notes:** https://www.postgresql.org/docs/release/18/
- **pgvector GitHub:** https://github.com/pgvector/pgvector
- **pgvector 0.8.1 Release:** https://github.com/pgvector/pgvector/releases/tag/v0.8.1
- **Docker Image Tags:** https://hub.docker.com/r/pgvector/pgvector/tags
- **UUID v7 RFC 9562:** https://www.rfc-editor.org/rfc/rfc9562
- **PostgreSQL 18 UUID v7:** https://www.postgresql.org/docs/18/functions-uuid.html

---

## 🎨 ASCII Art Summary

```
┌─────────────────────────────────────────────────────────────┐
│         PostgreSQL 17 → 18 Upgrade Path                      │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│  Current State:                                               │
│  ┌─────────────────────────────────────────────────────┐   │
│  │  PostgreSQL 17 ████████████                         │   │
│  │  UUID v4 (random) ████████████                      │   │
│  │  Python library needed ████████████                │   │
│  │  pgvector 0.4.x ████████████                         │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                               │
│  Upgrade Path:                                                │
│  ┌─────────────────────────────────────────────────────┐   │
│  │  1. Update docker-compose.yml                      │   │
│  │     image: pgvector/pgvector:pg18-bookworm          │   │
│  │                                                       │   │
│  │  2. Fresh start (dev environment)                   │   │
│  │     docker-compose down postgres                    │   │
│  │     docker volume rm skillforge_postgres-dev-data   │   │
│  │     docker-compose up -d postgres                  │   │
│  │                                                       │   │
│  │  3. Run migrations                                    │   │
│  │     alembic upgrade head                            │   │
│  │                                                       │   │
│  │  4. Verify                                           │   │
│  │     SELECT version(); → PostgreSQL 18.x            │   │
│  │     SELECT extversion FROM pg_extension... → 0.8.1+ │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                               │
│  After Upgrade:                                              │
│  ┌─────────────────────────────────────────────────────┐   │
│  │  PostgreSQL 18 ████████████████████                  │   │
│  │  UUID v7 (time-ordered) ████████████████████ ⭐      │   │
│  │  Native uuidv7() function ████████████████████ ⭐   │   │
│  │  pgvector 0.8.1+ ████████████████████                │   │
│  │  Better performance ████████████████████ ⭐          │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                               │
│  Benefits:                                                    │
│  ✅ Native UUID v7 (no Python library)                      │
│  ✅ Better query performance                                 │
│  ✅ Future-proof (latest stable)                             │
│  ✅ All features compatible                                   │
│  ✅ Low risk (dev environment)                              │
└─────────────────────────────────────────────────────────────┘
```

---

**Status:** Ready for implementation  
**Next Steps:** 
1. Update `docker-compose.yml` to use `pgvector/pgvector:pg18-bookworm`
2. Test upgrade in isolated environment
3. Execute upgrade plan
4. Migrate to UUID v7 using native `uuidv7()` function

**Estimated Time:** 2-4 hours (including testing)
