# Test Environment Mirror Plan - Dev-like E2E Setup

**Goal:** Create a test environment that mirrors dev but is isolated for testing  
**Pattern:** `skillforge-test` mirrors `skillforge-dev` (including Langfuse)  
**Date:** 2025-12-22

**Implementation Plan:** See `docs/TEST_ENV_IMPLEMENTATION_PLAN.md` for step-by-step implementation

---

## 🎯 Strategy Summary

**Two Environments Only (Logical Approach):**

**1. Dev Environment (Development):**
- ✅ Full stack for daily development work
- ✅ Manual data management
- ✅ Ports: 5437, 6380, 8500, 5173, 3000

**2. Test Environment (All Testing - Including E2E):**
- ✅ Full dev mirror with ALL services (Postgres, Redis, Backend, Frontend, **Langfuse**)
- ✅ Golden dataset (98 analyses) - mirrors dev data
- ✅ Use for: **ALL testing** - Integration tests, API tests, **E2E/Playwright tests**, manual testing, CI
- ✅ Ports: 5438, 6381, 8501, 5174, 3001
- ✅ **E2E tests run against this environment** (no separate E2E needed)

**Key Insight:** 
- **2 environments only:** Dev (development) + Test (all testing including E2E)
- Test environment is the **single source of truth** for all testing
- E2E tests are just Playwright tests that run against the test environment
- No need for separate E2E environment - it's redundant

---

## 🎯 Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                    DEVELOPMENT ENVIRONMENT                       │
│                    (docker-compose.yml)                          │
├─────────────────────────────────────────────────────────────────┤
│                                                                   │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐          │
│  │  PostgreSQL  │  │    Redis     │  │   Backend    │          │
│  │  skillforge  │  │  redis-dev   │  │ backend-dev  │          │
│  │  :5437       │  │  :6380       │  │  :8500       │          │
│  └──────────────┘  └──────────────┘  └──────────────┘          │
│                                                                   │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐          │
│  │   Frontend   │  │   Langfuse   │  │   Langfuse   │          │
│  │ frontend-dev │  │   Web/DB     │  │   Worker     │          │
│  │  :5173       │  │  :3000       │  │              │          │
│  └──────────────┘  └──────────────┘  └──────────────┘          │
│                                                                   │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│                    TEST ENVIRONMENT (ALL TESTING)                │
│              (docker-compose.test.yml)                          │
│              FULL DEV MIRROR - INCLUDES E2E/PLAYWRIGHT          │
├─────────────────────────────────────────────────────────────────┤
│                                                                   │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐          │
│  │  PostgreSQL  │  │    Redis     │  │   Backend    │          │
│  │ skillforge-  │  │  redis-test  │  │ backend-test │          │
│  │    test      │  │  :6381       │  │  :8501       │          │
│  │  :5438       │  │              │  │              │          │
│  └──────────────┘  └──────────────┘  └──────────────┘          │
│                                                                   │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐          │
│  │   Frontend   │  │   Langfuse   │  │   Langfuse   │          │
│  │ frontend-test│  │   Web/DB     │  │   Worker     │          │
│  │  :5174       │  │  :3001       │  │              │          │
│  └──────────────┘  └──────────────┘  └──────────────┘          │
│                                                                   │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐          │
│  │   Langfuse   │  │   Langfuse   │  │   Seed       │          │
│  │   Clickhouse │  │   Minio      │  │   (Golden    │          │
│  │              │  │  :9001       │  │   Dataset)   │          │
│  └──────────────┘  └──────────────┘  └──────────────┘          │
│                                                                   │
│  USED FOR: Integration tests, API tests, E2E/Playwright tests   │
│                                                                   │
│  NOTE: E2E environment (docker-compose.e2e.yml) is REDUNDANT    │
│        → E2E tests run against TEST environment                  │
│        → No separate E2E environment needed                     │
│                                                                   │
└─────────────────────────────────────────────────────────────────┘
```

---

## 📋 Best Practices

### 1. **Environment Isolation**

```
┌─────────────────────────────────────────────────────────────┐
│  ISOLATION LAYERS                                            │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│  Layer 1: Network Isolation                                  │
│  ┌─────────────────────────────────────────────────────┐   │
│  │  Dev:    skillforge_default network                 │   │
│  │  Test:   skillforge-test_default network             │   │
│  │  E2E:    skillforge-e2e_default network              │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                               │
│  Layer 2: Database Isolation                                 │
│  ┌─────────────────────────────────────────────────────┐   │
│  │  Dev:    skillforge (database)                       │   │
│  │  Test:   skillforge-test (database)                  │   │
│  │  E2E:    skillforge_test (database)                  │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                               │
│  Layer 3: Volume Isolation                                   │
│  ┌─────────────────────────────────────────────────────┐   │
│  │  Dev:    postgres-dev-data                           │   │
│  │  Test:   postgres-test-data                           │   │
│  │  E2E:    postgres-e2e-data                            │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                               │
│  Layer 4: Port Isolation                                     │
│  ┌─────────────────────────────────────────────────────┐   │
│  │  Dev:    5437, 6380, 8500, 5173, 3000               │   │
│  │  Test:   5438, 6381, 8501, 5174, 3001               │   │
│  │  E2E:    5432, 8500, 5174 (CI ports)                 │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                               │
└─────────────────────────────────────────────────────────────┘
```

### 2. **Service Naming Convention**

```
┌─────────────────────────────────────────────────────────────┐
│  NAMING PATTERN                                              │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│  Dev Environment:                                             │
│  ┌─────────────────────────────────────────────────────┐   │
│  │  Container: skillforge-{service}-dev                 │   │
│  │  Database:  skillforge                               │   │
│  │  Network:   skillforge_default                       │   │
│  │  Volume:    {service}-dev-data                       │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                               │
│  Test Environment:                                            │
│  ┌─────────────────────────────────────────────────────┐   │
│  │  Container: skillforge-{service}-test                │   │
│  │  Database:  skillforge-test                          │   │
│  │  Network:   skillforge-test_default                  │   │
│  │  Volume:    {service}-test-data                      │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                               │
│  E2E Environment:                                             │
│  ┌─────────────────────────────────────────────────────┐   │
│  │  Container: skillforge-{service}-e2e                 │   │
│  │  Database:  skillforge_test                          │   │
│  │  Network:   skillforge-e2e_default                   │   │
│  │  Volume:    {service}-e2e-data                       │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                               │
└─────────────────────────────────────────────────────────────┘
```

### 3. **Configuration Hierarchy**

```
┌─────────────────────────────────────────────────────────────┐
│  CONFIGURATION SOURCES (Priority Order)                      │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│  1. Environment Variables (Highest Priority)                 │
│     ┌─────────────────────────────────────────────────┐   │
│     │  .env.test                                       │   │
│     │  docker-compose.test.yml environment:            │   │
│     │    - DATABASE_URL                                │   │
│     │    - REDIS_URL                                   │   │
│     │    - ENVIRONMENT=test                            │   │
│     └─────────────────────────────────────────────────┘   │
│                                                               │
│  2. Docker Compose Overrides                                │
│     ┌─────────────────────────────────────────────────┐   │
│     │  docker-compose.test.yml                         │   │
│     │    - extends: docker-compose.yml (base config)   │   │
│     │    - overrides: test-specific settings           │   │
│     └─────────────────────────────────────────────────┘   │
│                                                               │
│  3. Base Configuration (Lowest Priority)                    │
│     ┌─────────────────────────────────────────────────┐   │
│     │  docker-compose.yml                             │   │
│     │    - Common service definitions                 │   │
│     │    - Shared volumes/networks                    │   │
│     └─────────────────────────────────────────────────┘   │
│                                                               │
└─────────────────────────────────────────────────────────────┘
```

### 4. **Data Lifecycle**

```
┌─────────────────────────────────────────────────────────────┐
│  TEST DATA LIFECYCLE                                         │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│  ┌──────────┐      ┌──────────┐      ┌──────────┐          │
│  │   Setup  │ ───> │   Run    │ ───> │  Cleanup │          │
│  │  Phase   │      │  Phase   │      │  Phase   │          │
│  └──────────┘      └──────────┘      └──────────┘          │
│       │                 │                 │                  │
│       ▼                 ▼                 ▼                  │
│  ┌─────────────────────────────────────────────────────┐   │
│  │  1. Start containers                                 │   │
│  │  2. Run migrations                                  │   │
│  │  3. Seed test data                                  │   │
│  │  4. Verify readiness                                │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                               │
│  ┌─────────────────────────────────────────────────────┐   │
│  │  1. Run tests                                        │   │
│  │  2. Tests can modify data                           │   │
│  │  3. Each test run gets fresh state                  │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                               │
│  ┌─────────────────────────────────────────────────────┐   │
│  │  1. Stop containers                                  │   │
│  │  2. Remove volumes (optional)                       │   │
│  │  3. Cleanup network/volumes                         │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                               │
└─────────────────────────────────────────────────────────────┘
```

---

## 🏗️ Proposed Structure

### File Organization

```
docker-compose.yml              # Dev environment
docker-compose.test.yml         # Test environment (mirrors dev, used for ALL testing)
# docker-compose.e2e.yml        # DEPRECATED - E2E tests use test environment

.env                            # Dev environment variables
.env.test                       # Test environment variables (used for E2E too)

scripts/
  ├── load_golden_dataset.py    # Test seed (full - 98 analyses, used for all testing)
  └── setup_test_env.sh         # Test environment setup script
```

### Service Comparison

```
┌─────────────────────────────────────────────────────────────────┐
│  SERVICE COMPARISON                                              │
├─────────────────────────────────────────────────────────────────┤
│                                                                   │
│  Service          │  Dev        │  Test (All Testing)           │
│  ──────────────────────────────────────────────────────────────│
│  PostgreSQL       │  ✅ :5437   │  ✅ :5438                     │
│  Redis            │  ✅ :6380   │  ✅ :6381                     │
│  Backend          │  ✅ :8500   │  ✅ :8501                     │
│  Frontend         │  ✅ :5173   │  ✅ :5174                     │
│  Langfuse Web     │  ✅ :3000   │  ✅ :3001                     │
│  Langfuse DB      │  ✅         │  ✅                           │
│  Langfuse Worker  │  ✅         │  ✅                           │
│  Langfuse Redis   │  ✅         │  ✅                           │
│  Langfuse Minio   │  ✅         │  ✅                           │
│  Langfuse Clickhouse│  ✅       │  ✅                           │
│  Seed Script      │  ❌         │  ✅ (golden dataset)          │
│                                                                   │
│  Test Types:      │  N/A        │  Integration, API, E2E       │
│                                                                   │
└─────────────────────────────────────────────────────────────────┘
```

---

## 🔧 Implementation Strategy

### Option 1: Extend Base Compose (Recommended)

```yaml
# docker-compose.test.yml
name: skillforge-test

services:
  # Extend base services with test overrides
  postgres:
    extends:
      file: docker-compose.yml
      service: postgres
    container_name: skillforge-postgres-test
    environment:
      POSTGRES_DB: skillforge-test
    ports:
      - "5438:5432"
    volumes:
      - postgres-test-data:/var/lib/postgresql/data

  redis:
    extends:
      file: docker-compose.yml
      service: redis
    container_name: skillforge-redis-test
    ports:
      - "6381:6379"
    volumes:
      - redis-test-data:/data

  backend:
    extends:
      file: docker-compose.yml
      service: backend
    container_name: skillforge-backend-test
    environment:
      DATABASE_URL: postgresql+asyncpg://dev:devpass@postgres:5432/skillforge-test
      ENVIRONMENT: test
      REDIS_URL: redis://:${REDIS_PASSWORD}@redis:6379
      LANGFUSE_HOST: http://langfuse-web:3000
    ports:
      - "8501:8500"
    depends_on:
      - postgres
      - redis
      - langfuse-web

  frontend:
    extends:
      file: docker-compose.yml
      service: frontend
    container_name: skillforge-frontend-test
    ports:
      - "5174:5173"
    environment:
      VITE_API_URL: http://localhost:8501

  # Langfuse services (full stack like dev)
  langfuse-db:
    extends:
      file: docker-compose.yml
      service: langfuse-db
    container_name: skillforge-langfuse-db-test

  langfuse-redis:
    extends:
      file: docker-compose.yml
      service: langfuse-redis
    container_name: skillforge-langfuse-redis-test

  langfuse-clickhouse:
    extends:
      file: docker-compose.yml
      service: langfuse-clickhouse
    container_name: skillforge-langfuse-clickhouse-test

  langfuse-minio:
    extends:
      file: docker-compose.yml
      service: langfuse-minio
    container_name: skillforge-langfuse-minio-test
    ports:
      - "9001:9000"

  langfuse-web:
    extends:
      file: docker-compose.yml
      service: langfuse-web
    container_name: skillforge-langfuse-web-test
    ports:
      - "3001:3000"

  langfuse-worker:
    extends:
      file: docker-compose.yml
      service: langfuse-worker
    container_name: skillforge-langfuse-worker-test

  # Test seed service (loads golden dataset)
  backend-seed:
    build:
      context: ./backend
      dockerfile: Dockerfile
    container_name: skillforge-backend-seed-test
    depends_on:
      backend:
        condition: service_healthy
    environment:
      DATABASE_URL: postgresql+asyncpg://dev:devpass@postgres:5432/skillforge-test
    command: ["python", "-m", "scripts.load_golden_dataset"]
    restart: "no"
```

### Option 2: Standalone Compose (More Control)

```yaml
# docker-compose.test.yml
name: skillforge-test

# Copy dev compose but with test-specific values
# Full control, no inheritance
```

### Option 3: Override Pattern (Flexible)

```yaml
# docker-compose.test.yml
name: skillforge-test

# Use override files
# docker-compose -f docker-compose.yml -f docker-compose.test.yml up
```

---

## 📊 Data Seeding Strategy

```
┌─────────────────────────────────────────────────────────────┐
│  SEEDING APPROACHES                                          │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│  Test Environment (Proposed - Used for ALL Testing):        │
│  ┌─────────────────────────────────────────────────────┐   │
│  │  Full seed:                                          │   │
│  │  - Golden dataset (98 analyses)                      │   │
│  │  - All artifacts                                     │   │
│  │  - All chunks with embeddings                        │   │
│  │  - Langfuse traces (if needed)                       │   │
│  │  - Mirrors dev environment exactly                   │   │
│  │  - Used for: Integration, API, E2E/Playwright      │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                               │
│  Dev Environment:                                            │
│  ┌─────────────────────────────────────────────────────┐   │
│  │  Manual seed:                                        │   │
│  │  - Developer controls                               │   │
│  │  - Can load golden dataset                          │   │
│  │  - Can create custom data                           │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                               │
└─────────────────────────────────────────────────────────────┘
```

---

## 🚀 Usage Patterns

### Development Workflow

```bash
# Dev environment (your daily work)
docker compose up -d
# → skillforge-dev containers
# → Ports: 5437, 6380, 8500, 5173, 3000

# Test environment (ALL testing - integration, API, E2E)
docker compose -f docker-compose.test.yml up -d
# → skillforge-test containers
# → Ports: 5438, 6381, 8501, 5174, 3001
```

### Test Execution

```bash
# Start test environment (for all testing)
docker compose -f docker-compose.test.yml up -d

# Run integration/API tests
npm run test:integration
# → Uses TEST environment (http://localhost:8501)

# Run E2E/Playwright tests
npm run test:e2e
# → Uses TEST environment (http://localhost:5174, http://localhost:8501)

# All tests use the same test environment!
```

### Playwright Configuration

```typescript
// frontend/playwright.config.ts
// E2E tests target TEST environment
const baseURL = process.env.PLAYWRIGHT_BASE_URL || 'http://localhost:5174';
const apiURL = process.env.API_BASE_URL || 'http://localhost:8501';
```

---

## 🔒 Isolation Guarantees

```
┌─────────────────────────────────────────────────────────────┐
│  ISOLATION CHECKLIST                                         │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│  ✅ Separate Docker networks                                 │
│  ✅ Separate database instances                              │
│  ✅ Separate volume storage                                  │
│  ✅ Separate port bindings                                   │
│  ✅ Separate environment variables                           │
│  ✅ No shared state between environments                     │
│  ✅ Can run dev + test simultaneously                       │
│                                                               │
└─────────────────────────────────────────────────────────────┘
```

---

## 📝 Environment Variables

```
┌─────────────────────────────────────────────────────────────┐
│  ENV VAR COMPARISON                                          │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│  Dev (.env):                                                 │
│  ┌─────────────────────────────────────────────────────┐   │
│  │  DATABASE_URL=postgresql+asyncpg://.../skillforge   │   │
│  │  REDIS_URL=redis://redis:6379                        │   │
│  │  ENVIRONMENT=development                             │   │
│  │  CORS_ORIGINS=["http://localhost:5173"]             │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                               │
│  Test (.env.test):                                           │
│  ┌─────────────────────────────────────────────────────┐   │
│  │  DATABASE_URL=postgresql+asyncpg://.../skillforge-test│ │
│  │  REDIS_URL=redis://redis:6379                        │   │
│  │  ENVIRONMENT=test                                    │   │
│  │  CORS_ORIGINS=["http://localhost:5174"]             │   │
│  │  SKIP_WORKFLOW=true (optional)                      │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                               │
│  Test (.env.test) - Used for E2E too:                       │
│  ┌─────────────────────────────────────────────────────┐   │
│  │  DATABASE_URL=postgresql+asyncpg://.../skillforge-test│ │
│  │  ENVIRONMENT=test                                     │   │
│  │  CORS_ORIGINS=["http://localhost:5174"]              │   │
│  │  SKILLFORGE_E2E_DISABLE_WORKFLOW=true (optional)     │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                               │
└─────────────────────────────────────────────────────────────┘
```

---

## 🎯 Two Environments Only (Simplified)

```
┌─────────────────────────────────────────────────────────────┐
│  DEV vs TEST ENVIRONMENTS                                    │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│  Dev Environment (Development):                              │
│  ┌─────────────────────────────────────────────────────┐   │
│  │  Purpose: Daily development work                    │   │
│  │  Data:    Manual management                          │   │
│  │  Services: Full stack (Postgres, Redis, Backend,     │   │
│  │            Frontend, Langfuse)                      │   │
│  │  Ports:   5437, 6380, 8500, 5173, 3000             │   │
│  │  Use:     Development, debugging, manual testing    │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                               │
│  Test Environment (All Testing - Including E2E):           │
│  ┌─────────────────────────────────────────────────────┐   │
│  │  Purpose: ALL testing (integration, API, E2E)      │   │
│  │  Data:    Golden dataset (98 analyses)              │   │
│  │  Services: Full dev mirror (ALL services)            │   │
│  │  Ports:   5438, 6381, 8501, 5174, 3001            │   │
│  │  Use:     Integration tests, API tests,            │   │
│  │           E2E/Playwright tests, CI                 │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                               │
│  KEY INSIGHT:                                                │
│  ┌─────────────────────────────────────────────────────┐   │
│  │  • E2E tests are just Playwright tests              │   │
│  │  • They run against TEST environment                │   │
│  │  • No separate E2E environment needed                │   │
│  │  • Test environment = single source for all testing │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                               │
└─────────────────────────────────────────────────────────────┘
```

---

## ✅ Benefits

1. **True Dev Mirroring**
   - Test environment matches dev exactly
   - Same services (including Langfuse), same configuration
   - Same data structure (golden dataset)

2. **Isolation**
   - Can run dev + test simultaneously
   - No port conflicts
   - No data interference

3. **CI Parity**
   - Test locally what CI runs
   - Same environment = fewer surprises
   - Faster feedback loop

4. **Complete Testing**
   - Test with full dataset (98 analyses)
   - Test with Langfuse observability
   - Test all integrations (Redis, Langfuse, etc.)

5. **E2E Simplification**
   - E2E becomes lightweight Playwright-only
   - Use test env for anything requiring full stack
   - Clear separation: browser tests vs integration tests

---

## 📋 Implementation Checklist

- [ ] Create `docker-compose.test.yml` (extends dev, includes Langfuse)
- [ ] Create `.env.test` file (mirrors dev with test ports)
- [ ] Use existing `scripts/load_golden_dataset.py` for seeding
- [ ] Create `scripts/setup_test_env.sh` helper
- [ ] Update Playwright config to use test environment ports (5174, 8501)
- [ ] Update E2E test scripts to target test environment
- [ ] Add npm scripts: `test:integration`, `test:e2e` (both use test env)
- [ ] Verify isolation (can run dev + test simultaneously)
- [ ] Test data seeding works (golden dataset loads)
- [ ] Verify all services start correctly (including Langfuse)
- [ ] Test Langfuse integration in test environment
- [ ] Run E2E tests against test environment (verify they work)
- [ ] **Consider deprecating `docker-compose.e2e.yml`** (if test env works for E2E)

---

**Status:** 📋 **PLAN COMPLETE** - Ready for implementation review

