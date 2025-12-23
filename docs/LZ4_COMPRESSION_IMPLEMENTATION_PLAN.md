# LZ4 Compression Implementation Plan for `raw_content`

**Date:** December 22, 2025  
**PostgreSQL Version:** 17 (supports lz4 compression)  
**Issue:** Optimize `raw_content` storage with faster compression

---

## 📋 Executive Summary

Enable LZ4 compression for the `raw_content` column in PostgreSQL 17. This provides:
- **2-3x faster** compression/decompression than default pglz
- **Similar compression ratios** (often better for text)
- **Zero application code changes** (transparent to application)
- **Automatic recompression** of existing data

---

## 🔍 How LZ4 Will Look Like

### 1. Migration File Structure

**File:** `backend/alembic/versions/YYYYMMDDHHMMSS_enable_lz4_compression_raw_content.py`

```python
"""Enable LZ4 compression for raw_content column.

Revision ID: <generated>
Revises: <latest_revision>
Create Date: 2025-12-22

PostgreSQL 17 Feature: LZ4 TOAST Compression
- Faster compression/decompression (2-3x vs pglz)
- Better performance for text content
- Transparent to application layer

Issue: Optimize raw_content storage
"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "<generated>"
down_revision: str | None = "<latest_revision>"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Enable LZ4 compression for raw_content column.
    
    Steps:
    1. Set storage to EXTENDED (required for compression)
    2. Set compression method to lz4
    3. Existing data will be recompressed on next UPDATE
    """
    # Step 1: Set storage to EXTENDED (allows compression)
    # PLAIN = no compression, EXTENDED = TOAST with compression
    op.execute("""
        ALTER TABLE analyses 
        ALTER COLUMN raw_content 
        SET STORAGE EXTENDED;
    """)
    
    # Step 2: Set compression method to lz4
    # Requires PostgreSQL 14+ (we're on 17, so safe)
    op.execute("""
        ALTER TABLE analyses 
        ALTER COLUMN raw_content 
        SET COMPRESSION lz4;
    """)
    
    # Step 3: Force recompression of existing data
    # This updates all rows, triggering compression
    # Note: This is optional but recommended for immediate benefits
    op.execute("""
        UPDATE analyses 
        SET raw_content = raw_content 
        WHERE raw_content IS NOT NULL;
    """)


def downgrade() -> None:
    """Revert to default pglz compression.
    
    Steps:
    1. Reset compression to default (pglz)
    2. Keep EXTENDED storage (still allows compression)
    """
    # Reset to default compression (pglz)
    op.execute("""
        ALTER TABLE analyses 
        ALTER COLUMN raw_content 
        SET COMPRESSION DEFAULT;
    """)
    
    # Optional: Reset storage to PLAIN if you want no compression
    # We keep EXTENDED to maintain compression capability
    # op.execute("""
    #     ALTER TABLE analyses 
    #     ALTER COLUMN raw_content 
    #     SET STORAGE PLAIN;
    # """)
```

### 2. What Happens at Database Level

**Before Migration:**
```sql
-- Current state (default)
raw_content TEXT (STORAGE PLAIN or EXTENDED with pglz)
```

**After Migration:**
```sql
-- New state
raw_content TEXT (STORAGE EXTENDED, COMPRESSION lz4)
```

**PostgreSQL Behavior:**
- Values > 2KB automatically compressed with LZ4
- Compression happens transparently during INSERT/UPDATE
- Decompression happens automatically during SELECT
- No application code changes needed

### 3. Visual Impact

**No visible changes to:**
- Application code (SQLAlchemy models unchanged)
- API responses (same data, just faster to retrieve)
- Test code (same assertions work)
- User experience (transparent optimization)

**Only visible in:**
- Database schema (compression method)
- Performance metrics (faster queries)
- Storage size (potentially smaller)

---

## ⚙️ What It Will Affect

### ✅ **No Impact (Transparent)**

1. **Application Code**
   - SQLAlchemy models: No changes needed
   - Repository methods: No changes needed
   - Service layer: No changes needed
   - API endpoints: No changes needed

2. **Data Access Patterns**
   - `SELECT raw_content FROM analyses` - works identically
   - `UPDATE analyses SET raw_content = ...` - works identically
   - All queries behave the same

3. **Data Integrity**
   - No data loss
   - No schema changes to data types
   - Backward compatible

### ✅ **Positive Impact**

1. **Performance**
   - **2-3x faster** compression when writing large content
   - **2-3x faster** decompression when reading large content
   - Lower CPU usage during compression operations
   - Better performance for `ArtifactStore.load()` operations

2. **Storage Efficiency**
   - Similar or better compression ratios
   - Potentially smaller database size
   - Less I/O for large content

3. **Scalability**
   - Better performance as content sizes grow
   - Handles larger documents more efficiently

### ⚠️ **Potential Considerations**

1. **Migration Time**
   - Recompression of existing data (if we include UPDATE step)
   - For 98 golden dataset analyses: ~1-2 seconds
   - For production with more data: depends on volume

2. **PostgreSQL Version Requirement**
   - Requires PostgreSQL 14+ (we're on 17 ✅)
   - Won't work on older PostgreSQL versions
   - Already satisfied in our setup

3. **Monitoring**
   - Should verify compression is working
   - Can check with: `SELECT pg_column_compression(raw_content) FROM analyses LIMIT 1;`

---

## 🧪 Tests That Need Modification

### ✅ **No Test Changes Required**

**Why?**
- Compression is transparent to application layer
- All data access patterns remain identical
- SQLAlchemy abstracts away storage details
- Tests mock database interactions, not compression

### 📝 **Tests That Verify `raw_content` (No Changes Needed)**

1. **`test_data_persister.py`**
   - ✅ Tests persist/retrieve `raw_content`
   - ✅ No changes needed (compression is transparent)

2. **`test_quality_gate_node.py`**
   - ✅ Tests read `raw_content` from state
   - ✅ No changes needed

3. **`test_orchestrator.py`**
   - ✅ Tests workflow with `raw_content`
   - ✅ No changes needed

4. **`test_analyze_endpoint.py`**
   - ✅ Integration tests for API
   - ✅ No changes needed

5. **`test_analysis.py`**
   - ✅ End-to-end workflow tests
   - ✅ No changes needed

### 🆕 **Optional: New Test for Migration**

**File:** `backend/tests/integration/alembic/test_lz4_compression_migration.py`

```python
"""Integration test for LZ4 compression migration.

This test verifies that:
1. Migration applies successfully
2. Compression is enabled
3. Data can be read/written correctly
"""

import pytest
from sqlalchemy import text

from app.db.session import AsyncSessionLocal


@pytest.mark.asyncio
async def test_lz4_compression_enabled():
    """Verify LZ4 compression is enabled for raw_content."""
    async with AsyncSessionLocal() as session:
        # Check compression method
        result = await session.execute(text("""
            SELECT pg_column_compression(raw_content) as compression
            FROM analyses
            WHERE raw_content IS NOT NULL
            LIMIT 1;
        """))
        
        compression = result.scalar()
        # Should be 'lz4' after migration
        assert compression == 'lz4', f"Expected lz4, got {compression}"


@pytest.mark.asyncio
async def test_raw_content_read_write_with_compression():
    """Verify raw_content can be read/written with LZ4 compression."""
    from app.db.models.analysis import Analysis
    from sqlalchemy import select
    
    async with AsyncSessionLocal() as session:
        # Create test analysis with large content
        test_content = "Test content " * 1000  # ~13KB (will be compressed)
        
        # Write
        analysis = Analysis(
            url="https://test.example.com",
            content_type="article",
            raw_content=test_content,
            status="complete",
        )
        session.add(analysis)
        await session.commit()
        await session.refresh(analysis)
        
        # Read
        result = await session.execute(
            select(Analysis).where(Analysis.id == analysis.id)
        )
        retrieved = result.scalar_one()
        
        # Verify content is identical
        assert retrieved.raw_content == test_content
        
        # Cleanup
        await session.delete(analysis)
        await session.commit()
```

**Note:** This is optional - compression works transparently, so existing tests are sufficient.

---

## 📚 Documentation That Needs Modification

### 1. **Database Schema Documentation**

**File:** `backend/app/db/models/analysis.py`

**Current:**
```python
raw_content = Column(Text)
```

**Updated:**
```python
raw_content = Column(
    Text,
    comment="Extracted text content. Stored with LZ4 compression (PostgreSQL 17 TOAST). "
            "Compression is transparent to application layer."
)
```

### 2. **Migration Documentation**

**File:** `docs/YONATAN_BACKEND_TASKS.md` (or create new migration guide)

**Add section:**
```markdown
### Database Storage Optimization

**LZ4 Compression (PostgreSQL 17)**
- `raw_content` column uses LZ4 compression for faster I/O
- Enabled via migration: `enable_lz4_compression_raw_content`
- Transparent to application layer
- 2-3x faster compression/decompression vs default pglz
```

### 3. **Architecture Documentation**

**File:** `docs/ARCHITECTURE.md`

**Add to Data Layer section:**
```markdown
#### Storage Optimization

**PostgreSQL TOAST Compression:**
- `raw_content` uses LZ4 compression (PostgreSQL 17)
- Automatic compression for values > 2KB
- Transparent to application layer
- Improves performance for large content
```

### 4. **README or Setup Guide**

**File:** `backend/README.md` or `docs/ROADMAP.md`

**Add note:**
```markdown
### Database Features

- PostgreSQL 17 with pgvector extension
- LZ4 compression for large text columns (`raw_content`)
- Automatic TOAST compression for values > 2KB
```

### 5. **ADR (Architecture Decision Record) - Optional but Recommended**

**File:** `docs/architecture-decisions/adr-XXXX-enable-lz4-compression.md`

```markdown
# ADR-XXXX: Enable LZ4 Compression for raw_content

## Status
Accepted

## Context
- PostgreSQL 17 supports LZ4 compression (faster than default pglz)
- `raw_content` column stores extracted text (typically 10-500KB)
- Current compression (pglz) is slower for text content

## Decision
Enable LZ4 compression for `raw_content` column via Alembic migration.

## Consequences
- ✅ 2-3x faster compression/decompression
- ✅ Better performance for ArtifactStore.load() operations
- ✅ Transparent to application layer (no code changes)
- ⚠️ Requires PostgreSQL 14+ (we're on 17, so safe)
- ⚠️ Migration recompresses existing data (minimal impact for our dataset size)
```

---

## 🚀 Implementation Steps

### Step 1: Create Migration

```bash
cd backend
poetry run alembic revision -m "enable_lz4_compression_raw_content"
```

### Step 2: Write Migration Code

Copy the migration template above into the generated file.

### Step 3: Test Migration Locally

```bash
# Apply migration
poetry run alembic upgrade head

# Verify compression is enabled
psql -U dev -d skillforge -c "
SELECT pg_column_compression(raw_content) as compression
FROM analyses
WHERE raw_content IS NOT NULL
LIMIT 1;
"
# Should return: lz4

# Test downgrade
poetry run alembic downgrade -1

# Verify reverted
psql -U dev -d skillforge -c "
SELECT pg_column_compression(raw_content) as compression
FROM analyses
WHERE raw_content IS NOT NULL
LIMIT 1;
"
# Should return: pglz (default)

# Re-apply
poetry run alembic upgrade head
```

### Step 4: Update Documentation

1. Update `analysis.py` model with comment
2. Add note to architecture docs
3. Create ADR (optional)

### Step 5: Run Tests

```bash
# All existing tests should pass
poetry run pytest tests/ -v

# Optional: Add integration test for compression
poetry run pytest tests/integration/alembic/test_lz4_compression_migration.py -v
```

### Step 6: Commit

```bash
git add backend/alembic/versions/*_enable_lz4_compression_raw_content.py
git add backend/app/db/models/analysis.py
git add docs/
git commit -m "feat: enable LZ4 compression for raw_content column

- 2-3x faster compression/decompression
- Transparent to application layer
- PostgreSQL 17 feature
- Migration includes recompression of existing data"
```

---

## 📊 Performance Expectations

### Before (pglz)
- Compression: ~50-100 MB/s
- Decompression: ~200-400 MB/s
- CPU usage: Higher

### After (lz4)
- Compression: ~200-300 MB/s (2-3x faster)
- Decompression: ~500-800 MB/s (2-3x faster)
- CPU usage: Lower

### Real-World Impact
- **ArtifactStore.load()**: Faster when loading large content
- **DataPersister.persist()**: Faster when storing large content
- **Workflow nodes**: Lower latency when accessing raw_content
- **Database backups**: Faster (compressed data)

---

## ✅ Verification Checklist

- [ ] Migration created and tested locally
- [ ] Migration applies successfully (`alembic upgrade head`)
- [ ] Compression verified (`pg_column_compression()` returns 'lz4')
- [ ] Existing tests pass (no changes needed)
- [ ] Optional integration test added
- [ ] Model documentation updated
- [ ] Architecture docs updated
- [ ] ADR created (optional)
- [ ] Migration tested in downgrade (`alembic downgrade -1`)
- [ ] Ready for production deployment

---

## 🔄 Rollback Plan

If issues arise:

1. **Downgrade migration:**
   ```bash
   poetry run alembic downgrade -1
   ```

2. **Verify reverted:**
   ```sql
   SELECT pg_column_compression(raw_content) FROM analyses LIMIT 1;
   -- Should return: pglz (default)
   ```

3. **No data loss** - compression is transparent, data remains intact

---

## 📝 Summary

**What changes:**
- Database column compression method (pglz → lz4)
- Performance (2-3x faster)
- Documentation (add notes about compression)

**What doesn't change:**
- Application code (zero changes)
- Test code (zero changes)
- API contracts (identical)
- Data format (identical)
- User experience (transparent)

**Risk level:** 🟢 **Low**
- Transparent to application
- Reversible migration
- No data loss risk
- PostgreSQL 17 fully supports it
