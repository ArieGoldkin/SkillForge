# E2E Test Failure - Root Cause: Status Value Mismatch

**CI Run:** https://github.com/ArieGoldkin/SkillForge/actions/runs/20426986413/job/58689291336?pr=457  
**Error:** `Failed to get library: 422`  
**Date:** 2025-12-22

---

## 🎯 Root Cause Identified

### The Problem: Status Value Inconsistency

**Three different status values are being used:**

1. **Seed Script** (`backend/scripts/seed_e2e_fixture.py:50`):
   ```python
   status='completed'  # ❌ Has 'ed' suffix
   ```

2. **API Validation** (`backend/app/api/v1/analysis/library.py:76`):
   ```python
   pattern="^(pending|running|complete|failed)$"  # ✅ Expects 'complete' (no 'ed')
   ```

3. **AnalysisStatus Enum** (`backend/app/domains/analysis/schemas/api.py:21`):
   ```python
   COMPLETE = "complete"  # ✅ Uses 'complete' (no 'ed')
   ```

4. **Test Helper** (`frontend/e2e/utils/api-helpers.ts:99`):
   ```typescript
   const library = await getLibrary(request, { status: 'completed', limit: 20 });
   // ❌ Filters by 'completed' (with 'ed')
   ```

---

## 🔍 How This Causes the Failure

### Failure Chain

1. **Seed script runs** → Creates analysis with `status='completed'`
2. **Test calls `getCompletedAnalysis()`** → Tries to filter by `status='completed'`
3. **API receives request** → Validates `status='completed'` against pattern
4. **Validation fails** → Pattern only accepts `'complete'` (no 'ed')
5. **API returns 422** → Unprocessable Entity (validation error)
6. **Test fails** → `Failed to get library: 422`

### Why It's Hard to Find Locally

**If you test against dev environment:**
- Dev database may have analyses with `status='complete'` (correct)
- Test might work because data exists with correct status
- But CI fails because seed script creates wrong status

**If you don't check the actual error:**
- 422 error is a validation error, not a server error
- Easy to miss if you don't test API directly
- Error message doesn't clearly say "status value invalid"

---

## ✅ Proper Way to Find This Locally

### Step 1: Reproduce CI Environment Exactly

```bash
# Use E2E compose file (not dev)
docker compose -f docker-compose.e2e.yml down -v
docker compose -f docker-compose.e2e.yml up -d --build \
  postgres backend-migrate backend backend-seed frontend-e2e
```

### Step 2: Check What Status Seed Script Creates

```bash
# Check seed script
grep -n "status" backend/scripts/seed_e2e_fixture.py
# Shows: status='completed' (WRONG)

# Check database after seed runs
docker compose -f docker-compose.e2e.yml exec postgres \
  psql -U postgres -d skillforge_test -c \
  "SELECT id, status FROM analyses;"
# Shows: status = 'completed' (wrong value in DB)
```

### Step 3: Test API Directly (This Reveals the Issue)

```bash
# Test with wrong status (what test helper uses)
curl "http://localhost:8500/api/v1/library?status=completed" -v
# Returns: 422 Unprocessable Entity
# Error: "status" does not match pattern "^(pending|running|complete|failed)$"

# Test with correct status
curl "http://localhost:8500/api/v1/library?status=complete" -v
# Returns: 200 OK, but {"items":[],"total":0} (no data because seed used 'completed')
```

### Step 4: Check API Validation Pattern

```bash
# Check what API expects
grep -A 5 "status.*Query" backend/app/api/v1/analysis/library.py
# Shows: pattern="^(pending|running|complete|failed)$"
# Only accepts: 'complete' (no 'ed')
```

### Step 5: Check What Test Helper Uses

```bash
# Check test helper
grep -A 3 "getCompletedAnalysis" frontend/e2e/utils/api-helpers.ts
# Shows: status: 'completed' (WRONG - should be 'complete')
```

---

## 🔧 The Fix (Not Implementing, Just Documenting)

### Fix 1: Seed Script (Primary Fix)

**File:** `backend/scripts/seed_e2e_fixture.py`

**Change:**
```python
# Line 38: Check for 'complete' (not 'completed')
res = await conn.execute(text("SELECT COUNT(*) FROM analyses WHERE status='complete'"))

# Line 50: Use 'complete' (not 'completed')
VALUES (:id, :url, :content_type, :title, 'complete', NOW(), NOW())
```

### Fix 2: Test Helper (Secondary Fix)

**File:** `frontend/e2e/utils/api-helpers.ts`

**Change:**
```typescript
// Line 99: Use 'complete' (not 'completed')
const library = await getLibrary(request, { status: 'complete', limit: 20 });
```

---

## 📊 Verification Steps

### After Fixes

```bash
# 1. Clean and restart
docker compose -f docker-compose.e2e.yml down -v
docker compose -f docker-compose.e2e.yml up -d --build \
  postgres backend-migrate backend backend-seed frontend-e2e

# 2. Verify seed creates correct status
docker compose -f docker-compose.e2e.yml exec postgres \
  psql -U postgres -d skillforge_test -c \
  "SELECT status FROM analyses;"
# Should show: 'complete' (not 'completed')

# 3. Test API with correct status
curl "http://localhost:8500/api/v1/library?status=complete"
# Should return: 200 OK with data

# 4. Run tests
cd frontend
CI=true PLAYWRIGHT_BASE_URL=http://localhost:5174 \
API_BASE_URL=http://localhost:8500 E2E_LLM_DISABLED=true \
npx playwright test sse-progress.spec.ts --project=chromium
# Should pass
```

---

## 🎯 Key Lessons

### Why This Was Hard to Find

1. **Status inconsistency** - Three different values used in different places
2. **422 error is subtle** - Validation error, not obvious server error
3. **Local vs CI difference** - Dev environment may have correct status values
4. **No direct API testing** - Tests fail without testing API first

### How to Prevent This

1. **Use enum consistently** - Always use `AnalysisStatus.COMPLETE.value` instead of string literals
2. **Test API directly** - Before running E2E tests, verify API works
3. **Check seed data** - Verify seed script creates data with correct values
4. **Reproduce CI exactly** - Use same compose file, same environment variables

---

## 🔍 Proper Local Reproduction Method

**The correct way to find this issue:**

```bash
# 1. Start E2E stack (exact CI environment)
docker compose -f docker-compose.e2e.yml up -d --build \
  postgres backend-migrate backend backend-seed frontend-e2e

# 2. Wait for services
sleep 10  # Or use proper health checks

# 3. Test API directly FIRST (this reveals the issue)
curl "http://localhost:8500/api/v1/library?status=completed" -v
# This immediately shows: 422 error with validation message

# 4. Check what status exists in database
docker compose -f docker-compose.e2e.yml exec postgres \
  psql -U postgres -d skillforge_test -c "SELECT status FROM analyses;"

# 5. Compare with what API expects
grep "pattern" backend/app/api/v1/analysis/library.py | grep status

# 6. Now you've found the mismatch!
```

**The key insight:** Test the API directly before running tests. The 422 error tells you exactly what's wrong.

