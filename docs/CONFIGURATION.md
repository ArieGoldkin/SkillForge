# ⚙️ SkillForge Configuration (Source of Truth)

**Purpose:** This file is the canonical reference for **ports, URLs, and environment variables** used in SkillForge. Other docs should link here instead of duplicating values.

---

## 🔌 Local development ports & URLs

### Docker Compose (recommended dev setup)

- **Backend API**: `http://localhost:8500`
  - Swagger UI: `http://localhost:8500/docs`
  - Health: `http://localhost:8500/api/v1/health`
- **PostgreSQL (host access)**: `localhost:5437`
  - Database: `skillforge`
  - User: `dev`
  - Password: `devpass`

**Source of truth:** `docker-compose.yml`

### Frontend dev server

- **Frontend**: `http://localhost:5173`

**Source of truth:** `frontend/vite.config.ts`

---

## 🌐 Frontend environment variables

### Backend URL

- **`VITE_API_URL`**: Base URL for the backend API (used by `fetch()` in the frontend).
  - Default in code: `http://localhost:8500`

Examples:

```env
# frontend/.env.local
VITE_API_URL=http://localhost:8500
```

Notes:
- If you rely on the Vite dev proxy (`/api` → backend), you may not need this env var for local dev, but the app still supports it and uses it as a base for direct calls.

**Source of truth:** `frontend/src/services/api.service.ts`, `frontend/vite.config.ts`

---

## 🦙 Ollama (Local LLM - Recommended for Dev)

**Default for development: Use Ollama for $0 LLM costs.**

### Quick Start
```bash
# Start Ollama
ollama serve &

# Pull required models (one-time)
ollama pull deepseek-r1:70b      # Reasoning (42GB)
ollama pull qwen2.5-coder:32b    # Coding (19GB)
ollama pull nomic-embed-text     # Embeddings (274MB)
```

### Enable Ollama
Create `backend/.env.local` (gitignored):
```env
OLLAMA_ENABLED=true
OLLAMA_HOST=http://localhost:11434
```

### Ollama Environment Variables
| Variable | Default | Description |
|----------|---------|-------------|
| `OLLAMA_ENABLED` | `false` | Enable local Ollama inference |
| `OLLAMA_HOST` | `http://localhost:11434` | Ollama server URL |
| `OLLAMA_MODEL_REASONING` | `deepseek-r1:70b` | Model for complex reasoning |
| `OLLAMA_MODEL_CODING` | `qwen2.5-coder:32b` | Model for code tasks |
| `OLLAMA_MODEL_EMBED` | `nomic-embed-text` | Model for embeddings |

### Cost Structure
```
Dev (Ollama)  → $0/month
CI (Ollama)   → $0/month (93% cost reduction - Issue #606)
Production    → Cloud APIs (pay per use)
```

**Source of truth:** `backend/app/core/config.py` (lines 715-770)

---

## 🧩 Backend environment variables (high-level)

Backend env vars are loaded from `backend/.env` (see `backend/.env.example`).
For local overrides, use `backend/.env.local` (gitignored).

Commonly used variables:
- **`DATABASE_URL`**: DB connection string
  - In Docker Compose container: `postgresql+asyncpg://dev:devpass@postgres:5432/skillforge`
  - On host (if running backend locally while Postgres is in Docker): typically `postgresql+asyncpg://dev:devpass@localhost:5437/skillforge`
- **`API_V1_PREFIX`**: API prefix (default: `/api/v1`)
- **`PORT`**: backend port (Docker Compose sets `8500`)
- **`CORS_ORIGINS`**: allowed origins for frontend (JSON list)

**Source of truth:** `backend/.env.example`, `docker-compose.yml`

---

## 📦 Versions (source of truth)

- Backend dependencies: `backend/pyproject.toml`
- Frontend dependencies: `frontend/package.json`

Key “headline” versions (verify in the files above):
- **LangGraph**: `^1.0.4` (backend)
- **FastAPI**: `^0.124.0` (backend)
- **React**: `19.2.1` (frontend)


