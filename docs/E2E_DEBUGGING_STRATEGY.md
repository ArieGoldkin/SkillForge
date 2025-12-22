# E2E Test Debugging Strategy

**Based on CI Failure:** https://github.com/ArieGoldkin/SkillForge/actions/runs/20426986413/job/58689291336?pr=457

---

## 🎯 The Real Question: How to Find the Issue Locally

### Why Standard Local Testing Doesn't Work

**Problem:** Running tests against dev environment (`docker-compose.yml`) is **NOT** the same as CI:

1. **Different Database:** Dev uses `skillforge`, CI uses `skillforge_test`
2. **Different Ports:** Dev uses `5173`, CI uses `5174`
3. **Different Seed Data:** Dev may have existing data, CI starts fresh
4. **Different Workflow State:** Dev has workflows enabled, CI disables them
5. **Different Environment Variables:** CI sets specific flags

**Result:** Tests may pass locally but fail in CI (or vice versa).

---

## ✅ The Proper Way: Exact CI Reproduction

### Step-by-Step Local Reproduction

#### 1. **Match CI Environment Exactly**

```bash
# Use the EXACT same docker-compose file CI uses
docker compose -f docker-compose.e2e.yml down -v  # Clean slate

# Start EXACT same services in EXACT same order
export DOCKER_BUILDKIT=1
export COMPOSE_DOCKER_CLI_BUILD=1

docker compose -f docker-compose.e2e.yml up -d --build \
  postgres backend-migrate backend backend-seed frontend-e2e
```

**Why this matters:**
- CI uses `docker-compose.e2e.yml`, not `docker-compose.yml`
- Service order matters (migrations before backend, seed after backend)
- Clean database ensures no state pollution

#### 2. **Wait for Services (Like CI Does)**

```bash
# Mimic CI health check logic
echo "Waiting for backend..."
for i in {1..60}; do
  if curl -fsS http://localhost:8500/api/v1/health >/dev/null 2>&1; then
    echo "✓ Backend healthy after $i attempts"
    break
  fi
  if [ $i -eq 60 ]; then
    echo "✗ Backend health check timed out"
    docker compose -f docker-compose.e2e.yml logs backend
    exit 1
  fi
  sleep 2
done

echo "Waiting for frontend..."
for i in {1..30}; do
  if curl -fsS http://localhost:5174 >/dev/null 2>&1; then
    echo "✓ Frontend ready after $i attempts"
    break
  fi
  if [ $i -eq 30 ]; then
    echo "✗ Frontend health check timed out"
    docker compose -f docker-compose.e2e.yml logs frontend-e2e
    exit 1
  fi
  sleep 2
done
```

**Why this matters:**
- CI waits for health checks before running tests
- Services may not be ready immediately
- Timing issues can cause failures

#### 3. **Verify Seed Data (Critical Step)**

```bash
# Check if seed script actually ran and created data
docker compose -f docker-compose.e2e.yml logs backend-seed

# Verify data exists in database
docker compose -f docker-compose.e2e.yml exec postgres \
  psql -U postgres -d skillforge_test -c \
  "SELECT id, url, status FROM analyses WHERE status='completed';"

# Test API directly (what the test will call)
curl http://localhost:8500/api/v1/library | jq
```

**Why this matters:**
- Seed script may fail silently
- Seed script skips if data already exists
- API may return different format than expected
- Database state must match what tests expect

#### 4. **Run Tests with EXACT CI Environment Variables**

```bash
cd frontend

# Use EXACT same env vars as CI
CI=true \
PLAYWRIGHT_BASE_URL=http://localhost:5174 \
API_BASE_URL=http://localhost:8500 \
E2E_LLM_DISABLED=true \
npx playwright test --project=chromium --reporter=list,html
```

**Why this matters:**
- `CI=true` changes Playwright behavior (retries, workers, etc.)
- `PLAYWRIGHT_BASE_URL` must match E2E frontend port (5174)
- `API_BASE_URL` must match E2E backend port (8500)
- `E2E_LLM_DISABLED` signals lightweight mode to tests

---

## 🔍 Finding the Actual Error

### The 422 Error We Saw

From earlier test run, we saw:
```
Error: Failed to get library: 422
```

**422 = Unprocessable Entity** - This is a **validation error**, not a server error.

### What This Means

The library API endpoint is rejecting the request due to:
1. **Invalid query parameters** - Wrong format or missing required params
2. **Validation error** - Request doesn't match expected schema
3. **API contract mismatch** - Test expects different format than API provides

### How to Debug This

#### Step 1: Test API Directly

```bash
# Test library endpoint with different parameter combinations
curl "http://localhost:8500/api/v1/library" | jq
curl "http://localhost:8500/api/v1/library?limit=10" | jq
curl "http://localhost:8500/api/v1/library?status=completed" | jq

# Check what the API actually expects
curl "http://localhost:8500/docs"  # OpenAPI docs
```

#### Step 2: Check API Response Format

```bash
# What does the API actually return?
curl "http://localhost:8500/api/v1/library" | jq '.'
```

Compare with what test expects:
```typescript
// Test expects:
{
  items: Array<{analysis_id: string, ...}>,
  total: number
}
```

#### Step 3: Check Backend Logs

```bash
# See what error backend is actually returning
docker compose -f docker-compose.e2e.yml logs backend | grep -i "library\|422\|validation"
```

#### Step 4: Check Test Helper Function

```bash
# Look at what getLibrary() is actually sending
# File: frontend/e2e/utils/api-helpers.ts
```

The issue might be:
- Missing required query parameters
- Wrong parameter format
- API schema changed but test not updated

---

## 🎯 Recommended Debugging Workflow

### Phase 1: Reproduce CI Environment

```bash
# 1. Clean start
docker compose -f docker-compose.e2e.yml down -v

# 2. Start services
docker compose -f docker-compose.e2e.yml up -d --build \
  postgres backend-migrate backend backend-seed frontend-e2e

# 3. Wait for health
./scripts/wait_for_e2e_services.sh  # Or manual wait

# 4. Verify seed data
curl http://localhost:8500/api/v1/library | jq
```

### Phase 2: Test API Directly

```bash
# Test each API endpoint the test uses
curl http://localhost:8500/api/v1/health | jq
curl http://localhost:8500/api/v1/library | jq
curl http://localhost:8500/api/v1/library?limit=10 | jq

# If 422 error, check what's wrong
curl -v "http://localhost:8500/api/v1/library?limit=10" 2>&1 | grep -A 10 "< HTTP"
```

### Phase 3: Run Single Test with Debugging

```bash
cd frontend

# Run just the failing test
CI=true \
PLAYWRIGHT_BASE_URL=http://localhost:5174 \
API_BASE_URL=http://localhost:8500 \
E2E_LLM_DISABLED=true \
npx playwright test sse-progress.spec.ts --project=chromium \
  --reporter=list,verbose \
  --trace=on
```

### Phase 4: Inspect Results

```bash
# View HTML report
npx playwright show-report

# Check screenshots
ls -la test-results/*/test-failed-*.png

# Check trace (if enabled)
npx playwright show-trace test-results/*/trace.zip
```

---

## 🔬 Specific Debugging for Current Issue

### The 422 Error on Library Endpoint

**ROOT CAUSE FOUND:** Status Value Mismatch

**The Problem:**
- **Seed script** creates analyses with `status='completed'` (with 'ed')
- **API validation** only accepts `status='complete'` (without 'ed')
- **AnalysisStatus enum** uses `COMPLETE = "complete"` (without 'ed')
- **Test helper** `getCompletedAnalysis()` filters by `status='completed'` (won't match!)

**Evidence:**
```python
# backend/scripts/seed_e2e_fixture.py:50
status='completed'  # ❌ Wrong - has 'ed'

# backend/app/api/v1/analysis/library.py:76
pattern="^(pending|running|complete|failed)$"  # ✅ Expects 'complete'

# backend/app/domains/analysis/schemas/api.py:21
COMPLETE = "complete"  # ✅ Enum uses 'complete'
```

**Impact:**
1. Seed script creates data with wrong status
2. `getCompletedAnalysis()` can't find it (filters by 'completed')
3. Test skips or fails
4. If test calls library API with `status='completed'`, API returns 422 (validation error)

**Most Likely Causes:**

1. **Status Value Mismatch (CONFIRMED):**
   - Seed script uses `'completed'` but should use `'complete'`
   - API validation rejects `'completed'` as invalid
   - Check: `backend/scripts/seed_e2e_fixture.py:50`

2. **Query Parameter Validation:**
   - API expects specific format for `limit`, `offset`, `status`
   - Test helper may be sending wrong format
   - Check: `backend/app/api/v1/analysis/library.py`

3. **API Schema Mismatch:**
   - API response format changed
   - Test expects old format
   - Check: Compare API response vs test expectations

### How to Verify Each

```bash
# 1. Check what status seed script creates
grep -n "status" backend/scripts/seed_e2e_fixture.py
# Should show: status='completed' (WRONG - has 'ed')

# 2. Check what status API expects
grep -A 5 "status.*Query" backend/app/api/v1/analysis/library.py
# Should show: pattern="^(pending|running|complete|failed)$" (expects 'complete')

# 3. Check what status enum uses
grep "COMPLETE" backend/app/domains/analysis/schemas/api.py
# Should show: COMPLETE = "complete" (without 'ed')

# 4. Check database status values (after seed runs)
docker compose -f docker-compose.e2e.yml exec postgres \
  psql -U postgres -d skillforge_test -c \
  "SELECT DISTINCT status FROM analyses;"
# Will show: 'completed' (wrong value)

# 5. Test API with wrong status (should fail)
curl "http://localhost:8500/api/v1/library?status=completed" -v
# Returns: 422 Unprocessable Entity

# 6. Test API with correct status (should work)
curl "http://localhost:8500/api/v1/library?status=complete" -v
# Returns: 200 OK (but no results because seed used 'completed')

# 7. Check what getCompletedAnalysis() filters by
grep -A 10 "getCompletedAnalysis" frontend/e2e/utils/api-helpers.ts
# Shows: filters by status='completed' (won't find 'complete' analyses)
```

---

## 📋 Complete Reproduction Checklist

Before running tests, verify:

- [ ] **E2E stack is running:**
  ```bash
  docker compose -f docker-compose.e2e.yml ps
  ```
  All services should be "Up"

- [ ] **Backend is healthy:**
  ```bash
  curl http://localhost:8500/api/v1/health
  ```
  Should return `{"status":"healthy"}`

- [ ] **Frontend is accessible:**
  ```bash
  curl http://localhost:5174
  ```
  Should return HTML

- [ ] **Seed data exists:**
  ```bash
  curl http://localhost:8500/api/v1/library | jq '.total'
  ```
  Should return `1` or more

- [ ] **API returns valid JSON:**
  ```bash
  curl http://localhost:8500/api/v1/library | jq '.'
  ```
  Should return valid JSON with `items` and `total` fields

- [ ] **Database has correct status:**
  ```bash
  docker compose -f docker-compose.e2e.yml exec postgres \
    psql -U postgres -d skillforge_test -c \
    "SELECT status, COUNT(*) FROM analyses GROUP BY status;"
  ```
  Should show at least one `completed` analysis

- [ ] **Environment variables match CI:**
  ```bash
  echo "CI=$CI"
  echo "PLAYWRIGHT_BASE_URL=$PLAYWRIGHT_BASE_URL"
  echo "API_BASE_URL=$API_BASE_URL"
  echo "E2E_LLM_DISABLED=$E2E_LLM_DISABLED"
  ```

---

## 🎯 Key Insight

**The proper way to find the issue locally is:**

1. **Reproduce CI environment exactly** - Same compose file, same services, same order
2. **Test API directly first** - Don't assume API works, verify it
3. **Check each step individually** - Health → Seed → API → Tests
4. **Compare actual vs expected** - API response format, database state, error messages
5. **Use same environment variables** - CI sets specific flags that affect behavior

**Don't:**
- ❌ Run tests against dev environment and assume it's the same
- ❌ Skip verifying seed data exists
- ❌ Assume API works without testing it directly
- ❌ Ignore 422 errors (they tell you exactly what's wrong)

**Do:**
- ✅ Use `docker-compose.e2e.yml` (not `docker-compose.yml`)
- ✅ Verify each service is healthy before proceeding
- ✅ Test API endpoints directly before running tests
- ✅ Check database state matches expectations
- ✅ Use exact same environment variables as CI

---

**The 422 error is the key** - it means the API is rejecting the request format. Check:
1. What parameters `getLibrary()` is sending
2. What parameters the API actually expects
3. What the API response format is
4. Whether the test helper matches the API contract

