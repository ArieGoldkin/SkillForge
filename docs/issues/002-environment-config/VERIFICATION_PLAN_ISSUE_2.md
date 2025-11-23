# Development Environment Verification Plan - Issue #2

## Overview

Comprehensive verification plan to test Issue #2 implementation (Environment Config & Logging) in a Docker Desktop development environment. The backend runs standalone (not in Docker) while PostgreSQL and Ollama run in Docker containers.

**IMPORTANT:** This plan checks for existing services (reporter-accuracy project) and avoids port conflicts.

## Current Setup Analysis

**Existing Infrastructure:**
- `docker-compose.ci.yml` exists for CI/CD (full stack)
- `backend/Dockerfile` exists for production builds
- No `docker-compose.yml` for local development (needs creation)
- Backend designed to run standalone with Poetry
- Docker Desktop used for PostgreSQL + Ollama services only

**Existing Services Detected:**
- Ollama running on host: port 11434 (already in use)
- PostgreSQL containers: postgres-test (port 5433), postgres (port 5436)
- Various reporter-accuracy services on ports 8000-9005
- Redis on port 6379

**Conflict Resolution:**
- Use existing Ollama on port 11434 (no Docker container needed)
- Create new PostgreSQL container on port 5437 (avoids reporter-accuracy ports: 5433, 5436)
- Backend uses port 8500 (currently free, outside reporter-accuracy range 8000-9005)

**Issue #2 Changes to Verify:**
1. Config caching with `@lru_cache()` decorator
2. Structured logging with stdlib integration
3. Request ID middleware with proper cleanup
4. Environment variable loading from `.env`
5. Production validation in config

## Prerequisites Check

### 1. System Requirements
- [ ] Docker Desktop installed and running
- [ ] Python 3.13 installed (`python3.13 --version`)
- [ ] Poetry installed (`poetry --version`)
- [ ] Port 8500 available (backend) - **CHECK FIRST**
- [ ] Port 5432 available (PostgreSQL) - **CHECK FIRST**
- [ ] Ollama already running on port 11434 - **USE EXISTING**

### 2. Existing Services Check

**2.1 Check Port Availability**
```bash
# Check if ports are available
lsof -i :8500  # Backend port
lsof -i :5437  # PostgreSQL port (using 5437 to avoid reporter-accuracy ports 5433, 5436)
lsof -i :11434 # Ollama port (expect it to be in use)
```

- [ ] Port 8500 is free (if not, use different port in .env)
- [ ] Port 5437 is free (avoids reporter-accuracy ports: 5433, 5436)
- [ ] Ollama running on port 11434 (verify with: `curl http://localhost:11434/api/tags`)

**2.2 Verify Ollama Connection**
```bash
# Test existing Ollama
curl http://localhost:11434/api/tags
```

- [ ] Ollama responds correctly
- [ ] Can list available models

**2.3 Check Existing PostgreSQL Containers**
```bash
# Check existing PostgreSQL containers
docker ps --filter "name=postgres" --format "{{.Names}}\t{{.Ports}}"
```

- [ ] Identify existing PostgreSQL containers
- [ ] Decide: Use existing OR create new on port 5432

## Verification Steps

### Phase 1: Environment Setup

**1.1 Check Existing Services First**

```bash
# Check what's already running
docker ps --format "table {{.Names}}\t{{.Ports}}"
lsof -i -P | grep LISTEN | grep -E ":(8500|5432|11434)"
```

**1.2 Create docker-compose.yml for Local Development**

Create `docker-compose.yml` at project root for local dev services:

**Option A: If port 5432 is free (create new PostgreSQL)**
```yaml
version: '3.8'

services:
  postgres:
    image: pgvector/pgvector:pg17
    container_name: skillforge-postgres-dev
    environment:
      POSTGRES_USER: dev
      POSTGRES_PASSWORD: devpass
      POSTGRES_DB: skillforge
    ports:
      - "5432:5432"
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U dev"]
      interval: 10s
      timeout: 5s
      retries: 5
    volumes:
      - postgres-dev-data:/var/lib/postgresql/data

# NOTE: Ollama not included - using existing service on host (port 11434)

volumes:
  postgres-dev-data:
```

**Option B: If port 5432 is taken (use alternative port)**
```yaml
version: '3.8'

services:
  postgres:
    image: pgvector/pgvector:pg17
    container_name: skillforge-postgres-dev
    environment:
      POSTGRES_USER: dev
      POSTGRES_PASSWORD: devpass
      POSTGRES_DB: skillforge
    ports:
      - "5437:5432"  # Using 5437 to avoid conflicts with reporter-accuracy (5433, 5436)
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U dev"]
      interval: 10s
      timeout: 5s
      retries: 5
    volumes:
      - postgres-dev-data:/var/lib/postgresql/data

# NOTE: Ollama not included - using existing service on host (port 11434)
# Update .env DATABASE_URL to use port 5437 if using this option

volumes:
  postgres-dev-data:
```

**1.3 Update .env for Existing Ollama**

If using existing Ollama on host (port 11434), ensure `.env` has:
```bash
OLLAMA_BASE_URL=http://localhost:11434
```

No Docker container needed for Ollama.

**1.2 Create .env File**

- [ ] Copy `.env.example` to `.env`: `cp backend/.env.example backend/.env`
- [ ] Verify `.env` file exists and is not in git (check `.gitignore`)

**1.3 Install Dependencies**

- [ ] Navigate to backend: `cd backend`
- [ ] Install Poetry dependencies: `poetry install`
- [ ] Verify installation: `poetry show pydantic-settings structlog`

### Phase 2: Docker Services Startup

**2.1 Verify Existing Ollama (Skip Docker Container)**

```bash
# Test existing Ollama on host
curl http://localhost:11434/api/tags
```

- [ ] Ollama responds with JSON
- [ ] API accessible from host
- [ ] Note: No Docker container needed for Ollama

**2.2 Start PostgreSQL Service Only**

- [ ] Start PostgreSQL service: `docker-compose up -d postgres`
- [ ] Verify container running: `docker-compose ps`
  - Expected: `skillforge-postgres-dev` - Up (healthy)
  - Note: Ollama not in docker-compose (using existing)

**2.3 Verify PostgreSQL Connection**

```bash
# Test PostgreSQL connection
docker exec -it skillforge-postgres-dev psql -U dev -d skillforge -c "SELECT version();"
```

- [ ] Connection successful
- [ ] PostgreSQL version displayed
- [ ] Verify port: Check if using 5432 or alternative (5434)

**2.4 Verify No Port Conflicts**

```bash
# Verify no conflicts with reporter-accuracy services
lsof -i :8500  # Should be empty
lsof -i :5437  # Should show skillforge-postgres-dev only (avoids reporter-accuracy ports)
```

- [ ] Port 8500 free for backend
- [ ] PostgreSQL port configured correctly (no conflicts)

### Phase 3: Backend Application Verification

**3.1 Verify Config Loading**

- [ ] Start backend: `cd backend && poetry run uvicorn app.main:app --reload`
- [ ] Check startup logs for config loading:
  - Expected: `application_startup` log with environment and log_level
  - Expected: No config errors

**3.2 Test Config Caching**

- [ ] Verify `get_settings()` is cached (check imports)
- [ ] Multiple imports should reuse same instance
- [ ] Test helper methods: `settings.is_development()` should return True

**3.3 Verify Structured Logging**

- [ ] Check log format in console:
  - Expected: Structured logs with request_id (when requests made)
  - Expected: ConsoleRenderer format in development (human-readable)
  - Expected: ISO timestamp format

**3.4 Test Request ID Middleware**

- [ ] Make request: `curl http://localhost:8500/api/v1/health`
- [ ] Verify response header: `X-Request-ID` exists
- [ ] Verify logs include request_id in all log entries
- [ ] Test with existing header: `curl -H "X-Request-ID: test-123" http://localhost:8500/api/v1/health`
  - Expected: Response uses provided request ID (test-123)

**3.5 Test Context Cleanup**

- [ ] Make multiple requests rapidly: `for i in {1..10}; do curl http://localhost:8500/api/v1/health; done`
- [ ] Check logs: Each request should have unique request_id
- [ ] Verify no context leakage: Request IDs should not appear in wrong logs

### Phase 4: Endpoint Verification

**4.1 Root Endpoint**

```bash
curl http://localhost:8500/
```

- [ ] Status code: 200 OK
- [ ] Response: `{"message": "SkillForge API", "version": "0.1.0", "docs": "/docs"}`
- [ ] Response header: `X-Request-ID` present

**4.2 Health Check Endpoint**

```bash
curl http://localhost:8500/api/v1/health
```

- [ ] Status code: 200 OK
- [ ] Response includes: `status: "healthy"`, `version`, `environment: "development"`
- [ ] Response header: `X-Request-ID` present
- [ ] Logs show: `request_completed` with process_time_ms

**4.3 OpenAPI Docs**

- [ ] Visit: http://localhost:8500/docs
- [ ] Page loads without errors
- [ ] API documentation visible
- [ ] Health endpoint listed

**4.4 OpenAPI JSON Schema**

```bash
curl http://localhost:8500/openapi.json | jq '.info'
```

- [ ] Valid JSON response
- [ ] Info section includes title, version, description

### Phase 5: Logging Verification

**5.1 Startup Logs**

- [ ] Verify startup log format:
  - Expected: `application_startup` event
  - Expected: Includes `environment` and `log_level` fields
  - Expected: Structured format (not plain text)

**5.2 Request Logs**

- [ ] Make several requests and verify logs:
  - Expected: Each request logged with `request_completed`
  - Expected: Includes `method`, `path`, `status_code`, `process_time_ms`
  - Expected: All logs include `request_id` field

**5.3 Error Logging**

- [ ] Test invalid endpoint: `curl http://localhost:8500/invalid`
- [ ] Verify error log format:
  - Expected: Structured error log
  - Expected: Includes request_id
  - Expected: Includes error details

**5.4 Log Format Verification**

- [ ] Check log output format in development:
  - Expected: Human-readable console format (ConsoleRenderer)
  - Expected: Colored output if terminal supports
  - Expected: ISO timestamp format

### Phase 6: Production Environment Simulation

**6.1 Test Production Config Validation**

- [ ] Set `ENVIRONMENT=production` in `.env` (without `DATABASE_URL`)
- [ ] Restart backend
- [ ] Expected: ValidationError raised about missing `DATABASE_URL`
- [ ] Revert: Set `ENVIRONMENT=development`

**6.2 Test Production Logging Format**

- [ ] Temporarily change log format in `logging.py`:
  - Set `ENVIRONMENT=production` in code (for test only)
  - Restart backend
  - Expected: JSON format logs (JSONRenderer)
  - Revert changes

### Phase 7: Integration Testing

**7.1 Multiple Concurrent Requests**

```bash
# Test concurrent requests
for i in {1..20}; do
  curl -s http://localhost:8500/api/v1/health > /dev/null &
done
wait
```

- [ ] All requests complete successfully
- [ ] No context leakage in logs
- [ ] Each request has unique request_id

**7.2 Long-Running Test**

- [ ] Leave backend running for 5 minutes
- [ ] Make periodic requests
- [ ] Check logs: No memory leaks, no context accumulation
- [ ] Verify: Request IDs remain unique

### Phase 8: Edge Cases

**8.1 Missing Environment Variables**

- [ ] Test with missing `.env` file (rename temporarily)
- [ ] Expected: Default values used from config.py
- [ ] Restore `.env` file

**8.2 Invalid Log Level**

- [ ] Set `LOG_LEVEL=INVALID` in `.env`
- [ ] Restart backend
- [ ] Expected: ValueError with helpful message
- [ ] Restore: `LOG_LEVEL=DEBUG`

**8.3 Invalid Environment**

- [ ] Set `ENVIRONMENT=invalid` in `.env`
- [ ] Restart backend
- [ ] Expected: ValidationError with allowed values
- [ ] Restore: `ENVIRONMENT=development`

## Success Criteria

### All Verification Steps Must Pass:

- [ ] Docker services start and remain healthy
- [ ] Backend starts without errors
- [ ] Config loads correctly from `.env`
- [ ] Config caching works (no repeated loading)
- [ ] Structured logging outputs correctly formatted logs
- [ ] Request ID middleware adds `X-Request-ID` header to all responses
- [ ] Request ID middleware extracts existing `X-Request-ID` from headers
- [ ] Context variables properly cleaned up (no leakage)
- [ ] All endpoints respond correctly
- [ ] Health check returns expected format
- [ ] Production validation catches missing required variables
- [ ] Log format changes between dev (console) and prod (JSON)
- [ ] Concurrent requests work without context leakage
- [ ] Error handling works correctly

## Test Commands Summary

```bash
# 1. Check existing services and port availability
docker ps --format "table {{.Names}}\t{{.Ports}}"
lsof -i :8500 -i :5432 -i :11434

# 2. Verify existing Ollama (no Docker container needed)
curl http://localhost:11434/api/tags

# 3. Start PostgreSQL service only (uses port 5437 to avoid conflicts)
docker-compose up -d postgres

# 4. Verify containers (should only see postgres)
docker-compose ps

# 5. Test PostgreSQL
docker exec -it skillforge-postgres-dev psql -U dev -d skillforge -c "SELECT version();"

# 6. Verify .env configuration
cd backend
cat .env | grep -E "(OLLAMA_BASE_URL|DATABASE_URL|PORT)"

# 7. Start backend (standalone, not in Docker)
poetry run uvicorn app.main:app --reload

# 8. Test endpoints
curl http://localhost:8500/
curl http://localhost:8500/api/v1/health
curl -H "X-Request-ID: test-123" http://localhost:8500/api/v1/health

# 9. Verify logs (check terminal output)
# Should see structured logs with request_id

# 10. Stop PostgreSQL service only (Ollama stays running)
docker-compose down
```

## Issues to Check For

**Common Problems:**
1. Port conflicts (8500, 5432 already in use by reporter-accuracy)
2. Docker Desktop not running
3. `.env` file missing or misconfigured
4. Poetry dependencies not installed
5. Config validation errors on startup
6. Logging setup failures
7. Context variable leakage in async code
8. **Ollama port conflict** - Port 11434 already in use (expected - use existing)

**Conflict Resolution:**
- **Port 11434:** Ollama already running on host - use existing, don't create Docker container
- **Port 5437:** Using port 5437 for PostgreSQL to avoid reporter-accuracy ports (5433, 5436)
- **Port 8500:** Backend port (free, outside reporter-accuracy range 8000-9005)
- **Other ports:** Reporter-accuracy uses 8000-9005 and 5433/5436, all avoided

**Error Indicators:**
- Backend fails to start: Check config validation, port conflicts
- No logs: Check logging setup
- Missing request IDs: Check middleware registration
- Context leakage: Check finally block in middleware
- Port conflicts: Change ports in docker-compose.yml or .env
- **Ollama connection fails:** Verify existing Ollama on port 11434, update OLLAMA_BASE_URL if needed

## Cleanup

After verification:
- [ ] Stop backend (Ctrl+C)
- [ ] Stop PostgreSQL service only: `docker-compose down`
- [ ] **DO NOT stop Ollama** - it's shared with reporter-accuracy project
- [ ] Remove volumes if needed: `docker-compose down -v` (only postgres volume)
- [ ] Restore any test changes to `.env`
- [ ] Verify reporter-accuracy services still running: `docker ps | grep -E "(postgres-test|api-gateway)"`

## Documentation Updates Needed

If verification successful, document:
- [ ] Update `backend/README.md` with Docker Desktop setup steps
- [ ] Add `docker-compose.yml` to repository
- [ ] Document verification process for future reference
