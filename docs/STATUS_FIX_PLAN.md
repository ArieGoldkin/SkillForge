# Status Value Fix Plan - Safe for Dev & E2E

**Root Cause:** Status value inconsistency (`'completed'` vs `'complete'`)  
**Goal:** Fix without breaking dev environment  
**Date:** 2025-12-22

---

## 🎯 Problem Summary

### Current State

**Incorrect Status Value (`'completed'` with 'ed'):**
- ❌ `backend/scripts/seed_e2e_fixture.py` - Creates `status='completed'`
- ❌ `backend/scripts/utils/seed_e2e_fixture.py` - Creates `status='completed'`
- ❌ `backend/scripts/seed_e2e_langfuse_data.py` - Uses `status='completed'`
- ❌ `frontend/e2e/utils/api-helpers.ts` - Filters by `status='completed'`
- ❌ `backend/scripts/load_golden_dataset.py` - Creates `status='completed'` (⚠️ **AFFECTS DEV**)
- ❌ `backend/scripts/load_expanded_fixtures.py` - Creates `status='completed'` (⚠️ **AFFECTS DEV**)
- ❌ Many other golden dataset scripts use `'completed'` (⚠️ **AFFECTS DEV**)

**Correct Status Value (`'complete'` without 'ed'):**
- ✅ `AnalysisStatus.COMPLETE = "complete"` (enum definition)
- ✅ API validation pattern: `^(pending|running|complete|failed)$`
- ✅ All workflow code uses `'complete'`
- ✅ All test code (backend) uses `'complete'`

---

## 🛡️ Safety Strategy

### Principle: Isolate Changes by Environment

**E2E Environment (Safe to Fix Immediately):**
- Uses separate database (`skillforge_test`)
- Isolated from dev
- Can be fixed without risk

**Dev Environment (Needs Careful Handling):**
- May have existing data with `status='completed'`
- Golden dataset scripts load into dev database
- Need to check existing data first
- May need migration script

---

## 📋 Fix Plan

### Phase 1: E2E Environment Fixes (Safe - No Dev Impact)

**Files to Fix:**

1. **`backend/scripts/seed_e2e_fixture.py`**
   - Line 38: Change `status='completed'` → `status='complete'`
   - Line 50: Change `status='completed'` → `status='complete'`
   - **Impact:** Only affects E2E test database
   - **Risk:** ✅ **ZERO** - E2E database is isolated

2. **`backend/scripts/utils/seed_e2e_fixture.py`**
   - Same changes as above
   - **Impact:** Only affects E2E test database
   - **Risk:** ✅ **ZERO** - E2E database is isolated

3. **`backend/scripts/seed_e2e_langfuse_data.py`**
   - Line 251: Change `status='completed'` → `status='complete'`
   - **Impact:** Only affects E2E test database
   - **Risk:** ✅ **ZERO** - E2E database is isolated

4. **`frontend/e2e/utils/api-helpers.ts`**
   - Line 99: Change `status: 'completed'` → `status: 'complete'`
   - **Impact:** Only affects E2E tests
   - **Risk:** ✅ **ZERO** - Test code only

**Verification:**
```bash
# After fixes, verify E2E works
docker compose -f docker-compose.e2e.yml down -v
docker compose -f docker-compose.e2e.yml up -d --build \
  postgres backend-migrate backend backend-seed frontend-e2e

# Check seed creates correct status
docker compose -f docker-compose.e2e.yml exec postgres \
  psql -U postgres -d skillforge_test -c \
  "SELECT status FROM analyses;"
# Should show: 'complete' (not 'completed')

# Test API
curl "http://localhost:8500/api/v1/library?status=complete"
# Should return: 200 OK with data
```

---

### Phase 2: Dev Environment Assessment (Check Before Fixing)

**Files That Affect Dev:**

1. **`backend/scripts/load_golden_dataset.py`**
   - Line 190: Uses `status="completed"`
   - **Impact:** Loads data into **dev database** (`skillforge`)
   - **Risk:** ⚠️ **MEDIUM** - May have existing data with `'completed'`

2. **`backend/scripts/load_expanded_fixtures.py`**
   - Line 143: Uses `status="completed"`
   - **Impact:** Loads data into **dev database** (`skillforge`)
   - **Risk:** ⚠️ **MEDIUM** - May have existing data with `'completed'`

3. **Other Golden Dataset Scripts:**
   - `reconcile_golden_dataset_docs.py`
   - `verify_golden_dataset.py`
   - `backup_golden_dataset.py`
   - All use `'completed'` in queries/filters

**Assessment Steps:**

```bash
# 1. Check if dev database has 'completed' status
docker compose exec postgres \
  psql -U ${POSTGRES_USER} -d ${POSTGRES_DB} -c \
  "SELECT status, COUNT(*) FROM analyses GROUP BY status;"
# Shows: What status values exist in dev

# 2. Check if any analyses use 'completed'
docker compose exec postgres \
  psql -U ${POSTGRES_USER} -d ${POSTGRES_DB} -c \
  "SELECT COUNT(*) FROM analyses WHERE status='completed';"
# Shows: How many need migration

# 3. Check if API can query 'completed' analyses
curl "http://localhost:8500/api/v1/library?status=completed"
# Returns: 422 (validation error) - confirms API doesn't accept it
```

**Decision Tree:**

```
IF dev database has NO 'completed' analyses:
  ✅ Safe to fix all scripts immediately
  ✅ No migration needed

IF dev database HAS 'completed' analyses:
  ⚠️ Need migration script first
  ⚠️ Then fix scripts
  ⚠️ Verify migration worked
```

---

### Phase 3: Dev Environment Fixes (After Assessment)

**Option A: No Existing 'completed' Data (Safest)**

**Files to Fix:**
1. `backend/scripts/load_golden_dataset.py` - Line 190, 266
2. `backend/scripts/load_expanded_fixtures.py` - Line 143
3. `backend/scripts/reconcile_golden_dataset_docs.py` - Line 146
4. All other golden dataset scripts

**Changes:**
- Replace all `'completed'` → `'complete'`
- Use `AnalysisStatus.COMPLETE.value` instead of string literals (best practice)

**Verification:**
```bash
# After fixes, load golden dataset
poetry run python scripts/load_golden_dataset.py

# Verify status is correct
docker compose exec postgres \
  psql -U ${POSTGRES_USER} -d ${POSTGRES_DB} -c \
  "SELECT DISTINCT status FROM analyses;"
# Should show: 'complete' (not 'completed')
```

**Option B: Existing 'completed' Data (Needs Migration)**

**Step 1: Create Migration Script**

```python
# backend/scripts/migrate_completed_to_complete.py
"""Migrate 'completed' status to 'complete' in dev database.

This script safely migrates existing analyses with status='completed'
to status='complete' to match the AnalysisStatus enum.
"""

async def migrate_completed_to_complete():
    async with AsyncSessionLocal() as db:
        # Find all analyses with 'completed' status
        stmt = select(Analysis).where(Analysis.status == "completed")
        result = await db.execute(stmt)
        analyses = result.scalars().all()
        
        print(f"Found {len(analyses)} analyses with 'completed' status")
        
        for analysis in analyses:
            analysis.status = AnalysisStatus.COMPLETE.value
            print(f"Migrated {analysis.id}: 'completed' → 'complete'")
        
        await db.commit()
        print(f"✅ Migrated {len(analyses)} analyses")
```

**Step 2: Run Migration**

```bash
# Backup first!
poetry run python scripts/backup_golden_dataset.py backup

# Run migration
poetry run python scripts/migrate_completed_to_complete.py

# Verify migration
docker compose exec postgres \
  psql -U ${POSTGRES_USER} -d ${POSTGRES_DB} -c \
  "SELECT COUNT(*) FROM analyses WHERE status='completed';"
# Should return: 0
```

**Step 3: Fix Scripts**

Same as Option A - fix all scripts to use `'complete'`

---

### Phase 4: Use Enum Consistently (Best Practice)

**Current Problem:**
- Scripts use string literals: `status='completed'` or `status='complete'`
- Easy to make mistakes
- No type safety

**Solution:**
- Import `AnalysisStatus` enum
- Use `AnalysisStatus.COMPLETE.value` instead of string literals

**Example Fix:**

```python
# BEFORE (error-prone)
status='completed'  # Wrong value
status='complete'   # Correct but string literal

# AFTER (type-safe)
from app.domains.analysis.schemas.api import AnalysisStatus

status=AnalysisStatus.COMPLETE.value  # Always correct, type-safe
```

**Files to Update:**
- All seed scripts
- All golden dataset scripts
- All test fixtures

---

## 🔍 Verification Plan

### Before Making Changes

```bash
# 1. Check dev database status values
docker compose exec postgres \
  psql -U ${POSTGRES_USER} -d ${POSTGRES_DB} -c \
  "SELECT status, COUNT(*) FROM analyses GROUP BY status ORDER BY status;"

# 2. Check E2E database status values
docker compose -f docker-compose.e2e.yml exec postgres \
  psql -U postgres -d skillforge_test -c \
  "SELECT status, COUNT(*) FROM analyses GROUP BY status ORDER BY status;"

# 3. Test API with both status values
curl "http://localhost:8500/api/v1/library?status=completed" -v
curl "http://localhost:8500/api/v1/library?status=complete" -v

# 4. Document findings
# - How many 'completed' analyses exist?
# - Which database (dev or E2E)?
# - Can API query them?
```

### After Phase 1 (E2E Fixes)

```bash
# 1. Clean E2E database
docker compose -f docker-compose.e2e.yml down -v

# 2. Start E2E stack
docker compose -f docker-compose.e2e.yml up -d --build \
  postgres backend-migrate backend backend-seed frontend-e2e

# 3. Verify seed creates correct status
docker compose -f docker-compose.e2e.yml exec postgres \
  psql -U postgres -d skillforge_test -c \
  "SELECT status FROM analyses;"
# Expected: 'complete'

# 4. Test API
curl "http://localhost:8500/api/v1/library?status=complete"
# Expected: 200 OK with data

# 5. Run E2E tests
cd frontend
CI=true PLAYWRIGHT_BASE_URL=http://localhost:5174 \
API_BASE_URL=http://localhost:8500 E2E_LLM_DISABLED=true \
npx playwright test sse-progress.spec.ts --project=chromium
# Expected: Tests pass
```

### After Phase 2/3 (Dev Fixes)

```bash
# 1. Backup dev database (if has data)
poetry run python scripts/backup_golden_dataset.py backup

# 2. Run migration (if needed)
poetry run python scripts/migrate_completed_to_complete.py

# 3. Verify migration
docker compose exec postgres \
  psql -U ${POSTGRES_USER} -d ${POSTGRES_DB} -c \
  "SELECT COUNT(*) FROM analyses WHERE status='completed';"
# Expected: 0

# 4. Test loading golden dataset
poetry run python scripts/load_golden_dataset.py

# 5. Verify loaded data has correct status
docker compose exec postgres \
  psql -U ${POSTGRES_USER} -d ${POSTGRES_DB} -c \
  "SELECT DISTINCT status FROM analyses;"
# Expected: Only 'complete' (no 'completed')

# 6. Test API
curl "http://localhost:8500/api/v1/library?status=complete"
# Expected: 200 OK with data
```

---

## 📊 Risk Assessment

### E2E Environment Fixes

| File | Risk Level | Impact | Mitigation |
|------|------------|--------|------------|
| `seed_e2e_fixture.py` | ✅ **ZERO** | E2E only | Isolated database |
| `utils/seed_e2e_fixture.py` | ✅ **ZERO** | E2E only | Isolated database |
| `seed_e2e_langfuse_data.py` | ✅ **ZERO** | E2E only | Isolated database |
| `frontend/e2e/utils/api-helpers.ts` | ✅ **ZERO** | Tests only | No production impact |

**Action:** ✅ **SAFE TO FIX IMMEDIATELY**

### Dev Environment Fixes

| File | Risk Level | Impact | Mitigation |
|------|------------|--------|------------|
| `load_golden_dataset.py` | ⚠️ **MEDIUM** | Dev database | Check existing data first |
| `load_expanded_fixtures.py` | ⚠️ **MEDIUM** | Dev database | Check existing data first |
| Other golden dataset scripts | ⚠️ **MEDIUM** | Dev database | Check existing data first |

**Action:** ⚠️ **ASSESS FIRST, THEN FIX**

---

## 🎯 Implementation Order

### Step 1: Assessment (Do First)

```bash
# Check dev database
docker compose exec postgres \
  psql -U ${POSTGRES_USER} -d ${POSTGRES_DB} -c \
  "SELECT status, COUNT(*) FROM analyses GROUP BY status;"

# Document findings
# - Has 'completed'? → Need migration
# - No 'completed'? → Safe to fix
```

### Step 2: Fix E2E (Safe - Do Immediately)

1. Fix `backend/scripts/seed_e2e_fixture.py`
2. Fix `backend/scripts/utils/seed_e2e_fixture.py`
3. Fix `backend/scripts/seed_e2e_langfuse_data.py`
4. Fix `frontend/e2e/utils/api-helpers.ts`
5. Test E2E environment

### Step 3: Dev Migration (If Needed)

1. Create migration script
2. Backup dev database
3. Run migration
4. Verify migration

### Step 4: Fix Dev Scripts (After Migration)

1. Fix `backend/scripts/load_golden_dataset.py`
2. Fix `backend/scripts/load_expanded_fixtures.py`
3. Fix other golden dataset scripts
4. Use `AnalysisStatus.COMPLETE.value` (enum)

### Step 5: Verification

1. Test E2E environment
2. Test dev environment
3. Verify API works with both
4. Run CI tests

---

## 🛡️ Safety Guarantees

### What We're NOT Changing

- ✅ **Database schema** - No migrations needed
- ✅ **API endpoints** - No changes to API code
- ✅ **Workflow code** - Already uses correct `'complete'`
- ✅ **Existing dev data** - Only if migration needed (backed up first)

### What We ARE Changing

- ✅ **E2E seed scripts** - Use correct status (isolated)
- ✅ **Test helpers** - Use correct status (tests only)
- ✅ **Golden dataset scripts** - Use correct status (after assessment)
- ✅ **String literals** → **Enum values** (type safety)

### Rollback Plan

**If E2E fixes break:**
```bash
# Revert E2E seed script changes
git checkout HEAD -- backend/scripts/seed_e2e_fixture.py
docker compose -f docker-compose.e2e.yml down -v
docker compose -f docker-compose.e2e.yml up -d --build
```

**If dev fixes break:**
```bash
# Restore from backup
poetry run python scripts/backup_golden_dataset.py restore

# Revert script changes
git checkout HEAD -- backend/scripts/load_golden_dataset.py
```

---

## 📝 Files to Fix (Complete List)

### E2E Environment (Safe - Fix First)

1. ✅ `backend/scripts/seed_e2e_fixture.py` (Lines 38, 50)
2. ✅ `backend/scripts/utils/seed_e2e_fixture.py` (Lines 38, 50)
3. ✅ `backend/scripts/seed_e2e_langfuse_data.py` (Line 251)
4. ✅ `frontend/e2e/utils/api-helpers.ts` (Line 99)

### Dev Environment (Assess First)

5. ⚠️ `backend/scripts/load_golden_dataset.py` (Lines 190, 266)
6. ⚠️ `backend/scripts/load_expanded_fixtures.py` (Line 143)
7. ⚠️ `backend/scripts/reconcile_golden_dataset_docs.py` (Line 146)
8. ⚠️ `backend/scripts/data/load_golden_dataset.py` (Lines 190, 266)
9. ⚠️ `backend/scripts/data/load_expanded_fixtures.py` (Line 143)
10. ⚠️ `backend/scripts/data/reconcile_golden_dataset_docs.py` (Line 146)
11. ⚠️ `backend/scripts/verify_golden_dataset.py` (Multiple lines)
12. ⚠️ `backend/scripts/data/verify_golden_dataset.py` (Multiple lines)
13. ⚠️ `backend/scripts/backup_golden_dataset.py` (Multiple lines)
14. ⚠️ `backend/scripts/data/backup_golden_dataset.py` (Multiple lines)
15. ⚠️ `backend/scripts/regenerate_from_canonical.py` (Line 244)
16. ⚠️ `backend/scripts/validate_golden_dataset_precommit.py` (Line 226)

---

## 🎯 Recommended Approach

### Immediate (Safe)

1. **Fix E2E scripts** - Zero risk, isolated environment
2. **Fix test helpers** - Zero risk, test code only
3. **Test E2E** - Verify fixes work

### After Assessment

4. **Check dev database** - See if 'completed' exists
5. **If no 'completed'** → Fix dev scripts immediately
6. **If has 'completed'** → Create migration, then fix scripts

### Best Practice (Long-term)

7. **Use enum everywhere** - Replace string literals with `AnalysisStatus.COMPLETE.value`
8. **Add validation** - Prevent future mistakes
9. **Document** - Update scripts to use enum

---

## ✅ Success Criteria

### E2E Environment

- [ ] Seed script creates analyses with `status='complete'`
- [ ] API accepts `status='complete'` filter (200 OK)
- [ ] API rejects `status='completed'` filter (422 error)
- [ ] E2E tests pass
- [ ] CI job passes

### Dev Environment

- [ ] No analyses with `status='completed'` (after migration if needed)
- [ ] Golden dataset scripts create `status='complete'`
- [ ] API works correctly with dev data
- [ ] Dev environment functions normally

---

**Status:** 📋 **PLAN COMPLETE** - Ready for implementation after assessment

