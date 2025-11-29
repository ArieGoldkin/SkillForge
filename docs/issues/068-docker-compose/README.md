# Issue #68: Docker Compose Configuration

**Status:** ✅ **COMPLETE**  
**Assignee:** Yonatan  
**Points:** 3  
**GitHub:** [#68](https://github.com/ArieGoldkin/SkillForge/issues/68)  
**Sprint:** Sprint 1: Backend Foundation  
**Completed:** November 29, 2025

---

## 📋 Overview

Create Docker Compose configuration for PostgreSQL with PGVector extension and Backend service with proper environment variables, health checks, and data persistence.

---

## ✅ Implementation Summary

### Docker Compose Configuration

Created `docker-compose.yml` at project root with complete service definitions:

**Services:**
1. **PostgreSQL with PGVector** (`postgres`)
   - Image: `pgvector/pgvector:pg17`
   - Port: `5437:5432` (to avoid conflicts)
   - Health checks configured
   - Data persistence via named volume

2. **Backend Service** (`backend`)
   - Builds from `./backend/Dockerfile`
   - Hot-reload support for development
   - Automatic database migrations on startup
   - Health checks configured
   - Environment variables from `./backend/.env`

### File Structure

```
SkillForge/
├── docker-compose.yml          # Main Docker Compose configuration
├── docker-compose.ci.yml       # CI-specific configuration
└── backend/
    ├── Dockerfile              # Backend service Dockerfile
    └── .env                    # Environment variables (not committed)
```

### Service Configuration Details

#### PostgreSQL Service
- **Image:** `pgvector/pgvector:pg17`
- **Container:** `skillforge-postgres-dev`
- **Port:** `5437:5432` (external:internal)
- **Database:** `skillforge`
- **User:** `dev` / Password: `devpass`
- **Health Check:** `pg_isready -U dev` (every 10s)
- **Volume:** `postgres-dev-data` (persistent storage)

#### Backend Service
- **Build Context:** `./backend`
- **Container:** `skillforge-backend-dev`
- **Port:** `8500:8500`
- **Environment:**
  - Loads from `./backend/.env` via `env_file`
  - Overrides `DATABASE_URL` for container-internal connection
  - Development defaults for `ENVIRONMENT`, `LOG_LEVEL`
- **Health Check:** `curl -f http://localhost:8500/api/v1/health` (every 10s)
- **Volumes:**
  - `./backend/app:/app/app:ro` (code hot-reload)
  - `./backend/alembic:/app/alembic:ro` (migrations)
  - `./backend/alembic.ini:/app/alembic.ini:ro` (migration config)
- **Startup Command:**
  - Waits for PostgreSQL
  - Runs migrations (`alembic upgrade head`)
  - Starts uvicorn with reload

### Dependencies

- **Backend depends on PostgreSQL:** Uses `depends_on` with `condition: service_healthy`
- **Startup order:** PostgreSQL starts first, backend waits for health check

---

## ✅ Verification

### Acceptance Criteria

- [x] docker-compose.yml file created
- [x] PostgreSQL service with PGVector extension
- [x] Backend service with proper environment variables
- [x] Health checks configured
- [x] Volumes for data persistence

### Manual Testing

```bash
# Start services
docker-compose up -d

# Verify services are running
docker-compose ps

# Check PostgreSQL health
docker-compose exec postgres pg_isready -U dev

# Check backend health
curl http://localhost:8500/api/v1/health

# View logs
docker-compose logs backend
docker-compose logs postgres

# Stop services
docker-compose down

# Stop and remove volumes
docker-compose down -v
```

### Service Verification

- ✅ PostgreSQL starts successfully
- ✅ PGVector extension available
- ✅ Backend connects to PostgreSQL
- ✅ Migrations run automatically on startup
- ✅ Health checks pass
- ✅ Hot-reload works (code changes trigger restart)
- ✅ Data persists across container restarts

---

## 🚀 Usage

### Start Services

```bash
# Start in background
docker-compose up -d

# Start with logs
docker-compose up

# Rebuild and start
docker-compose up -d --build
```

### Stop Services

```bash
# Stop services (keeps volumes)
docker-compose down

# Stop and remove volumes (clean slate)
docker-compose down -v
```

### View Logs

```bash
# All services
docker-compose logs

# Specific service
docker-compose logs backend
docker-compose logs postgres

# Follow logs
docker-compose logs -f backend
```

### Execute Commands

```bash
# Run migrations manually
docker-compose exec backend alembic upgrade head

# Access PostgreSQL shell
docker-compose exec postgres psql -U dev -d skillforge

# Access backend shell
docker-compose exec backend /bin/bash
```

---

## 🔧 Technical Details

### Health Checks

**PostgreSQL:**
- Command: `pg_isready -U dev`
- Interval: 10 seconds
- Timeout: 5 seconds
- Retries: 5

**Backend:**
- Command: `curl -f http://localhost:8500/api/v1/health`
- Interval: 10 seconds
- Timeout: 5 seconds
- Retries: 5
- Start period: 30 seconds (allows time for startup)

### Volume Management

- **Named volume:** `postgres-dev-data`
- **Purpose:** Persist PostgreSQL data across container restarts
- **Location:** Managed by Docker (typically `/var/lib/docker/volumes/`)

### Network Configuration

- Services communicate via Docker's default bridge network
- Backend connects to PostgreSQL using service name: `postgres:5432`
- External access via published ports

### Environment Variables

Backend service loads variables from:
1. `./backend/.env` file (via `env_file`)
2. Explicit `environment:` overrides (for container-internal connections)

---

## 📝 Related Issues

- Issue #1: FastAPI Project Structure (backend setup)
- Issue #3: Database Schema & Migrations (migrations run on startup)
- Issue #69: Create Setup Script (uses this Docker Compose config)

---

## 🔗 GitHub Issue

[View Issue #68 on GitHub](https://github.com/ArieGoldkin/SkillForge/issues/68)

---

**Last Updated:** November 29, 2025



