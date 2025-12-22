# Test Environment E2E Setup - Complete ✅

## Overview

The test environment is fully configured and ready for E2E testing. All services are running on separate ports from the dev environment to allow parallel testing.

## Test Environment Ports

| Service | Port | URL |
|---------|------|-----|
| Frontend | 5174 | http://localhost:5174 |
| Backend | 8501 | http://localhost:8501 |
| Langfuse Web | 3001 | http://localhost:3001 |
| PostgreSQL | 5438 | localhost:5438 |
| Redis | 6381 | localhost:6381 |

## Configuration Files

### Backend
- **`.env.test`** - Backend test environment configuration
  - Contains Langfuse keys, database URLs, etc.
  - Gitignored (sensitive data)

### Frontend
- **`.env.test`** - Frontend test environment configuration
  - Contains API URLs, Langfuse credentials for E2E tests
  - Gitignored (sensitive data)
- **`.env.test.example`** - Template file (committed to git)
  - Copy this to `.env.test` and fill in credentials

## Running E2E Tests

### Prerequisites
1. Test environment must be running:
   ```bash
   docker compose -f docker-compose.test.yml up -d
   ```

2. Frontend `.env.test` must be configured:
   ```bash
   cd frontend
   cp .env.test.example .env.test
   # Edit .env.test and add your Langfuse credentials
   ```

### Run Tests

**Option 1: Using npm script (recommended)**
```bash
cd frontend
npm run test:e2e
```

This automatically:
- Loads `.env.test` file
- Sets all required environment variables
- Runs Playwright tests against test environment

**Option 2: Direct Playwright command**
```bash
cd frontend
npm run test:e2e:direct
```

**Option 3: Custom test file**
```bash
cd frontend
./scripts/run-e2e-tests.sh e2e/specs/home.spec.ts
```

## Test Scripts

| Script | Description |
|--------|-------------|
| `npm run test:e2e` | Run all E2E tests (loads .env.test) |
| `npm run test:e2e:direct` | Run tests with inline env vars |
| `npm run test:env:up` | Start test environment |
| `npm run test:env:down` | Stop test environment |
| `npm run test:env:logs` | View test environment logs |
| `npm run test:env:restart` | Restart test environment |

## Environment Variables

### Required for E2E Tests

These are loaded from `frontend/.env.test`:

- `VITE_API_BASE_URL` - Backend API URL (default: http://localhost:8501)
- `LANGFUSE_URL` - Langfuse UI URL (default: http://localhost:3001)
- `LANGFUSE_EMAIL` - Langfuse login email (required for Langfuse tests)
- `LANGFUSE_PASSWORD` - Langfuse login password (required for Langfuse tests)
- `PLAYWRIGHT_BASE_URL` - Frontend URL for Playwright (default: http://localhost:5174)
- `API_BASE_URL` - Backend API URL for Playwright (default: http://localhost:8501)

## Langfuse Configuration

### Annotation Queue
- **Queue Name**: SkillForge Review Queue
- **Queue ID**: Automatically detected and stored in `backend/.env.test`
- **Score Config**: `# quality_avg`

The annotation queue is automatically set up when:
1. Langfuse restore service runs (on container startup)
2. Or manually via: `cd backend && ENVIRONMENT=test poetry run python scripts/setup_langfuse_annotation_queue.py`

## Verification

### Check Services
```bash
# Check all services are running
docker compose -f docker-compose.test.yml ps

# Verify backend health
curl http://localhost:8501/api/v1/health

# Verify frontend
curl http://localhost:5174

# Verify Langfuse
curl http://localhost:3001/api/public/health
```

### List Available Tests
```bash
cd frontend
npm run test:e2e -- --list
```

## Test Categories

### Available E2E Tests
- `home.spec.ts` - Home page URL submission
- `analysis.spec.ts` - Analysis progress tracking
- `artifact.spec.ts` - Artifact preview and download
- `tutor.spec.ts` - Tutor session flow
- `library.spec.ts` - Library search and filtering
- `langfuse-feedback.spec.ts` - Langfuse integration tests
- `full-workflow-13-stages.spec.ts` - Complete workflow test
- `error-handling.spec.ts` - Error scenarios
- `responsive.spec.ts` - Mobile/responsive design
- `sse-progress.spec.ts` - SSE event handling

## Troubleshooting

### Tests fail to connect
1. Verify test environment is running: `docker compose -f docker-compose.test.yml ps`
2. Check service health endpoints (see Verification section)
3. Verify `.env.test` has correct URLs

### Langfuse tests fail
1. Verify Langfuse credentials in `frontend/.env.test`
2. Check Langfuse is accessible: `curl http://localhost:3001/api/public/health`
3. Verify annotation queue exists in Langfuse UI

### Port conflicts
- Test environment uses ports 5174, 8501, 3001 (offset by 1 from dev)
- If conflicts occur, check what's using those ports:
  ```bash
  lsof -i :5174
  lsof -i :8501
  lsof -i :3001
  ```

## Next Steps

1. ✅ Test environment configured
2. ✅ E2E test runner script created
3. ✅ Environment files set up
4. ✅ Langfuse annotation queue created
5. 🎯 **Ready to run E2E tests!**

Run your first test:
```bash
cd frontend
npm run test:e2e -- e2e/specs/home.spec.ts
```

