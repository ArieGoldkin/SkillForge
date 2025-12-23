# E2E Test Local Reproduction Guide

**Purpose:** Reproduce CI failures locally with exact same environment  
**CI Run:** https://github.com/ArieGoldkin/SkillForge/actions/runs/20426986413/job/58689291336?pr=457

---

## 🔍 Understanding the CI Environment

### CI Execution Flow

```
1. Build E2E Stack
   ├─ postgres (skillforge_test database)
   ├─ backend-migrate (alembic upgrade head)
   ├─ backend (SKILLFORGE_E2E_DISABLE_WORKFLOW=true)
   ├─ backend-seed (runs seed_e2e_fixture.py)
   └─ frontend-e2e (Vite on port 5174)

2. Wait for Health Checks
   ├─ Backend: http://localhost:8500/api/v1/health
   └─ Frontend: http://localhost:5174

3. Run Playwright Tests
   └─ Environment:
      - CI=true
      - PLAYWRIGHT_BASE_URL=http://localhost:5174
      - API_BASE_URL=http://localhost:8500
      - E2E_LLM_DISABLED=true
```

### Key Differences from Dev Environment

| Aspect | Dev Environment | E2E Environment (CI) |
|--------|------------------|----------------------|
| **Database** | `skillforge` | `skillforge_test` |
| **Frontend Port** | `5173` | `5174` |
| **Seed Data** | Optional | Required (runs automatically) |
| **Workflow** | Enabled | Disabled (`SKILLFORGE_E2E_DISABLE_WORKFLOW=true`) |
| **Environment** | `development` | `e2e` |
| **CI Flag** | Not set | `CI=true` |

---

## 🎯 Proper Local Reproduction Method

### Method 1: Exact CI Reproduction (Recommended)

**This matches CI exactly:**

```bash
# 1. Clean up any existing E2E containers
docker compose -f docker-compose.e2e.yml down -v

# 2. Build and start E2E stack (exact CI command)
export DOCKER_BUILDKIT=1
export COMPOSE_DOCKER_CLI_BUILD=1

docker compose -f docker-compose.e2e.yml up -d --build \
  postgres backend-migrate backend backend-seed frontend-e2e

# 3. Wait for services (mimic CI health checks)
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

# 4. Verify seed data was created
echo "Checking seed data..."
docker compose -f docker-compose.e2e.yml exec backend \
  poetry run python -c "
import asyncio
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine
import os

async def check():
    engine = create_async_engine(os.environ['DATABASE_URL'])
    async with engine.begin() as conn:
        res = await conn.execute(text(\"SELECT COUNT(*) FROM analyses WHERE status='completed'\"))
        count = int(res.scalar() or 0)
        print(f'Completed analyses: {count}')
    await engine.dispose()

asyncio.run(check())
"

# 5. Run tests with EXACT CI environment variables
cd frontend
CI=true \
PLAYWRIGHT_BASE_URL=http://localhost:5174 \
API_BASE_URL=http://localhost:8500 \
E2E_LLM_DISABLED=true \
npx playwright test --project=chromium

# 6. Check results
npx playwright show-report
```

### Method 2: Quick Verification Script

**Create a script to automate the above:**

```bash
#!/bin/bash
# scripts/reproduce_e2e_ci.sh

set -e

echo "🧹 Cleaning up existing E2E stack..."
docker compose -f docker-compose.e2e.yml down -v

echo "🏗️  Building and starting E2E stack..."
export DOCKER_BUILDKIT=1
export COMPOSE_DOCKER_CLI_BUILD=1

docker compose -f docker-compose.e2e.yml up -d --build \
  postgres backend-migrate backend backend-seed frontend-e2e

echo "⏳ Waiting for services to be healthy..."
./scripts/wait_for_e2e_services.sh

echo "✅ Services ready. Running tests..."
cd frontend
CI=true \
PLAYWRIGHT_BASE_URL=http://localhost:5174 \
API_BASE_URL=http://localhost:8500 \
E2E_LLM_DISABLED=true \
npx playwright test --project=chromium --reporter=list,html

echo "📊 Test results available at: frontend/playwright-report/index.html"
```

### Method 3: Debug Mode (Step-by-Step)

**For detailed debugging:**

```bash
# 1. Start stack
docker compose -f docker-compose.e2e.yml up -d --build \
  postgres backend-migrate backend backend-seed frontend-e2e

# 2. Check backend logs
docker compose -f docker-compose.e2e.yml logs backend

# 3. Check seed script logs
docker compose -f docker-compose.e2e.yml logs backend-seed

# 4. Verify database state
docker compose -f docker-compose.e2e.yml exec postgres \
  psql -U postgres -d skillforge_test -c "SELECT id, url, status FROM analyses;"

# 5. Test API directly
curl http://localhost:8500/api/v1/health
curl http://localhost:8500/api/v1/library

# 6. Test frontend
curl http://localhost:5174

# 7. Run single test with verbose output
cd frontend
CI=true \
PLAYWRIGHT_BASE_URL=http://localhost:5174 \
API_BASE_URL=http://localhost:8500 \
E2E_LLM_DISABLED=true \
npx playwright test sse-progress.spec.ts --project=chromium --reporter=list,verbose

# 8. Run with UI mode (see what's happening)
CI=true \
PLAYWRIGHT_BASE_URL=http://localhost:5174 \
API_BASE_URL=http://localhost:8500 \
E2E_LLM_DISABLED=true \
npx playwright test sse-progress.spec.ts --project=chromium --ui
```

---

## 🔬 Debugging Checklist

### Before Running Tests

- [ ] **E2E stack is running:**
  ```bash
  docker compose -f docker-compose.e2e.yml ps
  ```
  Should show: `postgres`, `backend`, `frontend-e2e` all "Up"

- [ ] **Backend is healthy:**
  ```bash
  curl http://localhost:8500/api/v1/health
  ```
  Should return: `{"status":"healthy",...}`

- [ ] **Frontend is accessible:**
  ```bash
  curl http://localhost:5174
  ```
  Should return: HTML content

- [ ] **Seed data exists:**
  ```bash
  curl http://localhost:8500/api/v1/library
  ```
  Should return: `{"items":[...],"total":1}` (at least 1 item)

- [ ] **Database has seed data:**
  ```bash
  docker compose -f docker-compose.e2e.yml exec postgres \
    psql -U postgres -d skillforge_test -c \
    "SELECT COUNT(*) FROM analyses WHERE status='completed';"
  ```
  Should return: `count >= 1`

### During Test Execution

- [ ] **Check test output for:**
  - Seed data availability messages
  - Skip conditions being triggered
  - Actual error messages (not just "test failed")

- [ ] **Monitor backend logs:**
  ```bash
  docker compose -f docker-compose.e2e.yml logs -f backend
  ```

- [ ] **Check browser (if using --headed):**
  - Is library page loading?
  - Are cards visible?
  - Does navigation work?

### After Test Failure

- [ ] **View Playwright report:**
  ```bash
  cd frontend && npx playwright show-report
  ```

- [ ] **Check screenshots:**
  ```bash
  ls -la frontend/test-results/*/test-failed-*.png
  ```

- [ ] **Review error context:**
  ```bash
  cat frontend/test-results/*/error-context.md
  ```

- [ ] **Check API responses:**
  ```bash
  # Test library endpoint
  curl http://localhost:8500/api/v1/library | jq
  
  # Test analysis endpoint (use ID from seed)
  curl http://localhost:8500/api/v1/analyze/<analysis-id> | jq
  ```

---

## 🐛 Common Issues & Solutions

### Issue 1: Seed Data Not Available

**Symptoms:**
- Test skips with "No seed data available"
- Library API returns `{"items":[],"total":0}`

**Debug:**
```bash
# Check if seed script ran
docker compose -f docker-compose.e2e.yml logs backend-seed

# Check database directly
docker compose -f docker-compose.e2e.yml exec postgres \
  psql -U postgres -d skillforge_test -c \
  "SELECT id, url, status, created_at FROM analyses ORDER BY created_at DESC LIMIT 5;"
```

**Solution:**
- Seed script may have skipped if data already exists
- Manually run seed: `docker compose -f docker-compose.e2e.yml exec backend poetry run python -m scripts.seed_e2e_fixture`
- Or clear database and restart: `docker compose -f docker-compose.e2e.yml down -v && docker compose -f docker-compose.e2e.yml up -d`

### Issue 2: Port Conflicts

**Symptoms:**
- `Error: bind: address already in use`
- Tests can't connect to services

**Debug:**
```bash
# Check what's using ports
lsof -i :5174  # Frontend
lsof -i :8500  # Backend
lsof -i :5432  # Postgres (inside container)
```

**Solution:**
- Stop dev environment: `docker compose down`
- Or use different ports in E2E compose file

### Issue 3: CORS Errors

**Symptoms:**
- Browser console shows CORS errors
- API calls fail with CORS headers missing

**Debug:**
```bash
# Check backend CORS config
docker compose -f docker-compose.e2e.yml exec backend \
  env | grep CORS_ORIGINS
```

**Solution:**
- Ensure `CORS_ORIGINS` includes `http://localhost:5174`
- Check backend logs for CORS errors

### Issue 4: Test Timeout

**Symptoms:**
- Tests timeout waiting for elements
- "Timeout 5000ms exceeded" errors

**Debug:**
- Run with `--headed` to see what's happening
- Check if frontend is actually rendering
- Verify API responses are correct

**Solution:**
- Increase timeouts in test
- Check if elements actually exist in UI
- Verify selectors are correct

---

## 📊 Comparison: Local vs CI

### What's the Same

✅ Docker Compose file (`docker-compose.e2e.yml`)  
✅ Service startup order  
✅ Environment variables (when set correctly)  
✅ Database schema (migrations)  
✅ Seed script execution  

### What Might Differ

⚠️ **Docker versions** - CI uses GitHub Actions runners  
⚠️ **Network latency** - Local may be faster  
⚠️ **Resource limits** - CI runners have different limits  
⚠️ **Timing** - Race conditions may appear differently  
⚠️ **Browser versions** - Playwright browsers may differ  

### Ensuring Exact Match

```bash
# Use same Playwright version as CI
cd frontend
npm list @playwright/test

# Use same Node version (check .nvmrc or package.json)
node --version

# Use same Docker Compose version
docker compose version
```

---

## 🎯 Recommended Workflow

### For Debugging CI Failures

1. **Reproduce locally first:**
   ```bash
   # Use Method 1 (exact CI reproduction)
   ./scripts/reproduce_e2e_ci.sh
   ```

2. **If it passes locally but fails in CI:**
   - Check CI logs for specific error
   - Compare environment differences
   - Check timing/race conditions
   - Verify seed data timing

3. **If it fails both locally and CI:**
   - Use Method 3 (debug mode)
   - Check each step individually
   - Verify API responses
   - Check database state

4. **Fix and verify:**
   ```bash
   # Make fix
   # Re-run reproduction script
   ./scripts/reproduce_e2e_ci.sh
   ```

---

## 📝 Quick Reference Commands

```bash
# Start E2E stack
docker compose -f docker-compose.e2e.yml up -d --build \
  postgres backend-migrate backend backend-seed frontend-e2e

# Check status
docker compose -f docker-compose.e2e.yml ps

# View logs
docker compose -f docker-compose.e2e.yml logs -f backend
docker compose -f docker-compose.e2e.yml logs backend-seed

# Run tests
cd frontend
CI=true PLAYWRIGHT_BASE_URL=http://localhost:5174 \
API_BASE_URL=http://localhost:8500 E2E_LLM_DISABLED=true \
npx playwright test --project=chromium

# Clean up
docker compose -f docker-compose.e2e.yml down -v

# Check database
docker compose -f docker-compose.e2e.yml exec postgres \
  psql -U postgres -d skillforge_test -c "SELECT * FROM analyses;"
```

---

## 🔍 Finding the Actual Error

### From CI Logs

1. **Check the "Run Playwright E2E tests" step:**
   - Look for actual test failure messages
   - Check which test failed
   - Look for error stack traces

2. **Check "Collect Docker logs on failure" step:**
   - Backend errors
   - Frontend errors
   - Database connection issues

3. **Download artifacts:**
   - `playwright-report-lightweight` - HTML report
   - `playwright-results-lightweight` - Screenshots/videos

### From Local Run

```bash
# Run with maximum verbosity
CI=true PLAYWRIGHT_BASE_URL=http://localhost:5174 \
API_BASE_URL=http://localhost:8500 E2E_LLM_DISABLED=true \
npx playwright test --project=chromium --reporter=list,verbose

# Or with trace
CI=true PLAYWRIGHT_BASE_URL=http://localhost:5174 \
API_BASE_URL=http://localhost:8500 E2E_LLM_DISABLED=true \
npx playwright test --project=chromium --trace=on
```

---

**Key Insight:** The most reliable way to find the issue is to reproduce the **exact CI environment** locally using Method 1, then use Method 3 for detailed debugging when issues are found.

