# Test Environment Implementation Plan

**Goal:** Implement 2-environment approach (Dev + Test), remove redundant E2E files, utilize Langfuse UI backups  
**Date:** 2025-12-22  
**Status:** 📋 **PLAN READY** - Ready for implementation

---

## 🎯 Quick Summary

**What We're Doing:**
1. ✅ Create `docker-compose.test.yml` (full dev mirror with Langfuse)
2. ✅ Remove E2E files (docker-compose.e2e.yml, seed scripts, etc.)
3. ✅ Use existing Langfuse backup scripts to restore config
4. ✅ Update Playwright to use test environment
5. ✅ Update GitHub Actions to use test environment

**Result:**
- 2 environments: Dev (development) + Test (all testing)
- Test environment = single source for all tests (integration, API, E2E/Playwright)
- Langfuse config restored from existing backups (`backend/data/langfuse_backups/`)
- Clean codebase (no redundant E2E files)

---

## 🗑️ Files to Delete (E2E Cleanup)

| File | Reason |
|------|--------|
| `docker-compose.e2e.yml` | Redundant - E2E tests use test environment |
| `docker-compose.e2e-langfuse.yml` | Redundant - test environment includes Langfuse |
| `backend/scripts/seed_e2e_fixture.py` | Redundant - use golden dataset instead |
| `backend/scripts/utils/seed_e2e_fixture.py` | Redundant - duplicate |
| `backend/scripts/seed_e2e_langfuse_data.py` | Redundant - use Langfuse backup restore |
| `backend/scripts/verify_langfuse_e2e.py` | Redundant - E2E-specific verification |

---

## 📦 Langfuse Backup Strategy

**Existing Backups (Already Available):**
- Location: `backend/data/langfuse_backups/`
- Contents:
  - `prompts_backup.json` - All Langfuse prompts
  - `datasets_backup.json` - Dataset configurations
  - `score_configs_backup.json` - Score config definitions
  - `llm_connections_backup.json` - LLM connection configs
  - `backup_metadata.json` - Backup metadata/timestamp

**Restore Process:**
1. Test environment starts Langfuse services
2. `langfuse-restore` service runs after Langfuse is healthy
3. Executes existing scripts:
   - `backup_langfuse.py restore` - Restores prompts, datasets, configs
   - `setup_langfuse_score_configs.py` - Sets up score configs
   - `setup_langfuse_annotation_queue.py` - Sets up annotation queue
4. Test environment now matches dev Langfuse setup exactly

**No New Code Needed** - All restore scripts already exist!

---

## 🎯 Overview

```
┌─────────────────────────────────────────────────────────────┐
│  BEFORE (3 environments - redundant)                        │
├─────────────────────────────────────────────────────────────┤
│  • Dev environment (docker-compose.yml)                      │
│  • Test environment (docker-compose.test.yml) - NEW         │
│  • E2E environment (docker-compose.e2e.yml) - REDUNDANT     │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│  AFTER (2 environments - clean)                             │
├─────────────────────────────────────────────────────────────┤
│  • Dev environment (docker-compose.yml)                     │
│  • Test environment (docker-compose.test.yml)               │
│    → Used for ALL testing (integration, API, E2E/Playwright)│
└─────────────────────────────────────────────────────────────┘
```

---

## 📋 Implementation Steps

### Phase 1: Create Test Environment (docker-compose.test.yml)

**File:** `docker-compose.test.yml`

**Strategy:** Extend `docker-compose.yml` with test-specific overrides

**Key Changes:**
- Container names: `skillforge-{service}-test`
- Database: `skillforge-test`
- Ports: 5438, 6381, 8501, 5174, 3001 (offset by 1 from dev)
- Network: `skillforge-test_default`
- Volumes: `{service}-test-data`
- Environment: `ENVIRONMENT=test`
- Seed service: Loads golden dataset via `load_golden_dataset.py`

**Services Included:**
- ✅ PostgreSQL (skillforge-test database)
- ✅ Redis (redis-test)
- ✅ Backend (backend-test)
- ✅ Frontend (frontend-test)
- ✅ Langfuse Web (langfuse-web-test)
- ✅ Langfuse DB (langfuse-db-test)
- ✅ Langfuse Worker (langfuse-worker-test)
- ✅ Langfuse Redis (langfuse-redis-test)
- ✅ Langfuse Minio (langfuse-minio-test)
- ✅ Langfuse Clickhouse (langfuse-clickhouse-test)
- ✅ Backend Seed (loads golden dataset)

---

### Phase 2: Remove E2E Files

**Files to Delete:**
1. ❌ `docker-compose.e2e.yml` - Redundant, E2E tests use test env
2. ❌ `docker-compose.e2e-langfuse.yml` - Redundant
3. ❌ `backend/scripts/seed_e2e_fixture.py` - Minimal seed, use golden dataset instead
4. ❌ `backend/scripts/utils/seed_e2e_fixture.py` - Duplicate
5. ❌ `backend/scripts/seed_e2e_langfuse_data.py` - Use Langfuse backup restore instead
6. ❌ `backend/scripts/verify_langfuse_e2e.py` - E2E-specific, not needed

**Keep (but update):**
- ✅ `frontend/e2e/` - Playwright tests (update to use test environment)
- ✅ `.github/workflows/e2e-tests.yml` - Update to use test environment

---

### Phase 3: Update Playwright Configuration

**File:** `frontend/playwright.config.ts`

**Changes:**
- Update `baseURL` to use test environment: `http://localhost:5174`
- Update `API_BASE_URL` to use test environment: `http://localhost:8501`
- Remove E2E-specific environment variables
- Use test environment for all Playwright tests

---

### Phase 4: Update GitHub Actions Workflow

**File:** `.github/workflows/e2e-tests.yml`

**Changes:**
- Replace `docker-compose.e2e.yml` with `docker-compose.test.yml`
- Update ports: 5438, 6381, 8501, 5174, 3001
- Update environment variables to use test environment
- Remove E2E-specific job names (rename to `test-lightweight`, `test-full`)

---

### Phase 5: Utilize Langfuse UI Backups

**Existing Backup Scripts (Already Available):**
- ✅ `backend/scripts/backup_langfuse.py` - Backs up/restores prompts, datasets, score configs, LLM connections
- ✅ `backend/scripts/backup_langfuse_evaluators.py` - Backs up evaluator configurations
- ✅ `backend/scripts/setup_langfuse_score_configs.py` - Sets up score configs (G-Eval, quality metrics)
- ✅ `backend/scripts/setup_langfuse_annotation_queue.py` - Sets up annotation queue

**Backup Location:**
- `backend/data/langfuse_backups/` - Contains all Langfuse UI configurations
- Version controlled JSON files
- Can be restored to any Langfuse instance

**Integration Strategy:**
1. **Restore Langfuse config in test environment** after Langfuse services start
2. **Use existing backup scripts** - no new code needed
3. **Ensure test environment matches dev** Langfuse setup exactly

**New Service in docker-compose.test.yml:**
```yaml
langfuse-restore:
  build:
    context: ./backend
    dockerfile: Dockerfile
  container_name: skillforge-langfuse-restore-test
  depends_on:
    langfuse-web:
      condition: service_healthy
    langfuse-db:
      condition: service_healthy
  environment:
    LANGFUSE_PUBLIC_KEY: ${LANGFUSE_PUBLIC_KEY}
    LANGFUSE_SECRET_KEY: ${LANGFUSE_SECRET_KEY}
    LANGFUSE_HOST: http://langfuse-web:3000
  volumes:
    - ./backend/data/langfuse_backups:/app/data/langfuse_backups:ro
  command: >
    sh -c "
      echo 'Restoring Langfuse configurations from backups...' &&
      python -m scripts.backup_langfuse restore &&
      python -m scripts.backup_langfuse_evaluators restore &&
      python -m scripts.setup_langfuse_score_configs &&
      python -m scripts.setup_langfuse_annotation_queue &&
      echo 'Langfuse configuration restored'
    "
  restart: "no"
```

**Note:** Backup files are in `backend/data/langfuse_backups/` - mount as read-only volume

---

### Phase 6: Update Test Scripts

**Files to Update:**
1. `frontend/package.json` - Add test environment scripts
2. `backend/scripts/load_golden_dataset.py` - Ensure works with test environment
3. Update any E2E-specific references to use test environment

**New npm Scripts:**
```json
{
  "scripts": {
    "test:env:up": "docker compose -f docker-compose.test.yml up -d",
    "test:env:down": "docker compose -f docker-compose.test.yml down",
    "test:env:logs": "docker compose -f docker-compose.test.yml logs -f",
    "test:integration": "PLAYWRIGHT_BASE_URL=http://localhost:5174 API_BASE_URL=http://localhost:8501 playwright test --project=chromium",
    "test:e2e": "PLAYWRIGHT_BASE_URL=http://localhost:5174 API_BASE_URL=http://localhost:8501 playwright test --project=chromium"
  }
}
```

---

## 🗑️ Files to Delete (E2E Redundancy Cleanup)

```
❌ docker-compose.e2e.yml                    # Redundant - use test env
❌ docker-compose.e2e-langfuse.yml           # Redundant - use test env
❌ backend/scripts/seed_e2e_fixture.py       # Redundant - use golden dataset
❌ backend/scripts/utils/seed_e2e_fixture.py # Redundant - duplicate
❌ backend/scripts/seed_e2e_langfuse_data.py # Redundant - use backup restore
❌ backend/scripts/verify_langfuse_e2e.py    # Redundant - E2E-specific
```

**Rationale:**
- E2E tests run against test environment (full dev mirror)
- Golden dataset provides better test data than minimal seed
- Langfuse backups restore all configs (better than minimal seed)
- No need for separate E2E environment

---

## 📝 Files to Create

```
✅ docker-compose.test.yml (extends docker-compose.yml)
✅ .env.test (test environment variables)
```

**Note:** No new Langfuse restore script needed - use existing:
- `backend/scripts/backup_langfuse.py restore`
- `backend/scripts/backup_langfuse_evaluators.py` (backup only, restore via UI or API)
- `backend/scripts/setup_langfuse_score_configs.py`
- `backend/scripts/setup_langfuse_annotation_queue.py`

---

## 🔄 Files to Update

```
✅ frontend/playwright.config.ts (use test environment ports)
✅ .github/workflows/e2e-tests.yml (use docker-compose.test.yml)
✅ frontend/package.json (add test environment scripts)
✅ docs/TEST_ENV_MIRROR_PLAN.md (implementation details)
```

---

## 🚀 Implementation Order

### Step 1: Create Test Environment (docker-compose.test.yml)
- Extend docker-compose.yml
- Override ports, container names, database
- Add seed service (golden dataset)
- Add Langfuse restore service

### Step 2: Create .env.test
- Copy from .env
- Update ports and database name
- Set ENVIRONMENT=test

### Step 3: Update Playwright Config
- Change baseURL to test environment
- Update API_BASE_URL
- Remove E2E-specific config

### Step 4: Update GitHub Actions
- Replace docker-compose.e2e.yml with docker-compose.test.yml
- Update ports and environment variables
- Rename jobs appropriately

### Step 5: Delete E2E Files (Cleanup)
- Remove docker-compose.e2e.yml
- Remove docker-compose.e2e-langfuse.yml
- Remove backend/scripts/seed_e2e_fixture.py
- Remove backend/scripts/utils/seed_e2e_fixture.py
- Remove backend/scripts/seed_e2e_langfuse_data.py
- Remove backend/scripts/verify_langfuse_e2e.py
- Update .gitignore if needed

### Step 6: Integrate Langfuse Restore
- Add langfuse-restore service to docker-compose.test.yml
- Mount backup directory as read-only volume
- Run existing restore scripts (backup_langfuse.py restore, etc.)
- Ensure Langfuse services are healthy before restore

### Step 7: Update npm Scripts
- Add test environment management scripts
- Update test execution scripts

### Step 8: Test & Verify
- Start test environment
- Verify all services start
- Verify golden dataset loads
- Verify Langfuse config restored
- Run Playwright tests against test environment

---

## ✅ Success Criteria

- [ ] Test environment mirrors dev exactly (all services including Langfuse)
- [ ] Test environment uses different ports (no conflicts with dev)
- [ ] Golden dataset loads successfully in test environment
- [ ] Langfuse config restored from backups
- [ ] Playwright tests run against test environment
- [ ] GitHub Actions updated to use test environment
- [ ] All E2E-specific files removed
- [ ] Can run dev + test simultaneously without conflicts

---

## 📊 Migration Checklist

### Before Implementation
- [ ] Backup current E2E test results
- [ ] Document current E2E workflow behavior
- [ ] Verify Langfuse backups exist and are valid

### During Implementation
- [ ] Create docker-compose.test.yml
- [ ] Create .env.test
- [ ] Update Playwright config
- [ ] Update GitHub Actions
- [ ] Create Langfuse restore integration
- [ ] Update npm scripts

### After Implementation
- [ ] Delete E2E files
- [ ] Test locally (dev + test simultaneously)
- [ ] Test Playwright against test environment
- [ ] Update CI workflow
- [ ] Verify CI passes
- [ ] Update documentation

---

## 🔍 Verification Steps

```bash
# 1. Start test environment
docker compose -f docker-compose.test.yml up -d

# 2. Verify all services running
docker compose -f docker-compose.test.yml ps
# Expected: All services healthy (postgres, redis, backend, frontend, langfuse-*)

# 3. Verify database seeded (golden dataset)
docker compose -f docker-compose.test.yml exec postgres \
  psql -U dev -d skillforge-test -c \
  "SELECT COUNT(*) FROM analyses WHERE status='complete';"
# Expected: 98 (golden dataset)

# 4. Verify Langfuse accessible and configured
curl http://localhost:3001/api/public/health
# Expected: 200 OK

# Check Langfuse config restored
docker compose -f docker-compose.test.yml logs langfuse-restore
# Expected: "Langfuse configuration restored"

# 5. Verify backend healthy
curl http://localhost:8501/api/v1/health
# Expected: 200 OK

# 6. Verify frontend accessible
curl http://localhost:5174
# Expected: 200 OK

# 7. Run Playwright tests against test environment
cd frontend
PLAYWRIGHT_BASE_URL=http://localhost:5174 \
API_BASE_URL=http://localhost:8501 \
npx playwright test --project=chromium
# Expected: All tests pass

# 8. Verify dev environment still works (isolation test)
docker compose up -d
docker compose ps
# Expected: Dev environment starts independently, no conflicts
```

---

## 🎯 Key Benefits

1. **Simplified:** 2 environments instead of 3
2. **Consistent:** All tests use same environment
3. **Complete:** Test environment mirrors dev exactly
4. **Langfuse Ready:** Uses existing UI backups/configs
5. **Clean:** Removed redundant E2E files

---

**Status:** 📋 **PLAN READY** - Ready for implementation

