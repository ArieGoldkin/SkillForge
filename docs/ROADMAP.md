# 🗺️ SkillForge Development Roadmap

**Version:** 1.0
**Last Updated:** November 23, 2025
**Project Type:** Research-to-Implementation Pipeline with AI Tutoring

---

## 📋 Table of Contents

1. [Project Overview](#project-overview)
2. [Architecture Summary](#architecture-summary)
3. [Tech Stack](#tech-stack)
4. [Development Phases](#development-phases)
5. [Detailed Task Breakdown](#detailed-task-breakdown)
6. [Dependencies & Prerequisites](#dependencies--prerequisites)
7. [Success Metrics](#success-metrics)
8. [Risk Management](#risk-management)

---

## 🎯 Project Overview

### Vision
SkillForge is an intelligent learning integration platform that analyzes technical content (articles, videos, research papers), generates actionable markdown artifacts for AI coding agents, and provides Socratic tutoring to deeply understand concepts.

### Core Value Proposition
- **Automated Research Analysis**: Multi-agent pipeline extracts insights from URLs
- **AI-Ready Artifacts**: Generates markdown files optimized for Claude Code/Cursor/other AI coding assistants
- **Deep Learning Mode**: Socratic tutoring for concept mastery
- **Searchable Knowledge Base**: Library of analyzed content with full-text search

### Target Users
- Developers learning new technologies
- Engineering teams evaluating technical approaches
- AI-assisted coding practitioners (Claude Code, Cursor, etc.)

### Success Criteria
- ✅ Analyze any technical URL in <5 minutes
- ✅ Generate comprehensive, actionable markdown artifacts
- ✅ Provide interactive tutoring sessions with context awareness
- ✅ Maintain searchable library with >95% retrieval accuracy

---

## 🏗️ Architecture Summary

### System Components

```
┌──────────────────────────────────────────────────────────┐
│                       FRONTEND                           │
│              React 19 + Vite (Vercel)                    │
│         ┌─────────────┬─────────────┬─────────────┐     │
│         │   Analyze   │   Tutor     │   Library   │     │
│         │   Module    │   Module    │   Module    │     │
│         └─────────────┴─────────────┴─────────────┘     │
│                          ↕ (SSE + REST)                  │
└──────────────────────────────────────────────────────────┘
                             ↕
┌──────────────────────────────────────────────────────────┐
│                    BACKEND (Python)                      │
│                FastAPI + LangGraph                       │
│                                                          │
│  ┌────────────────────────────────────────────────────┐ │
│  │           LangGraph Workflows                      │ │
│  │                                                    │ │
│  │  Analysis Pipeline:                               │ │
│  │  Extract → Supervisor → Sub-Agents → Aggregate   │ │
│  │                                                    │ │
│  │  Tutor Pipeline:                                  │ │
│  │  Init → Socratic Response → Assess → Loop        │ │
│  └────────────────────────────────────────────────────┘ │
│                                                          │
│  ┌────────────────────────────────────────────────────┐ │
│  │         Content Extraction Services                │ │
│  │  • Jina AI Reader (articles/web)                  │ │
│  │  • youtube-transcript-api (videos)                │ │
│  │  • GitHub API (repositories)                      │ │
│  └────────────────────────────────────────────────────┘ │
└──────────────────────────────────────────────────────────┘
                             ↕
┌──────────────────────────────────────────────────────────┐
│                   DATA LAYER                             │
│              PostgreSQL + PGVector                       │
│                                                          │
│  • Analyses (URLs, content, metadata)                   │
│  • Agent Findings (sub-agent outputs)                   │
│  • Artifacts (generated markdown files)                 │
│  • Tutoring Sessions (chat history)                     │
│  • Vector Embeddings (semantic search)                  │
└──────────────────────────────────────────────────────────┘
```

### Data Flow

**Analysis Pipeline:**
1. User submits URL
2. Backend validates & extracts content (Jina AI / YouTube API / GitHub API)
3. Supervisor agent analyzes content type → routes to specialized sub-agents
4. Sub-agents run in parallel (8 specialists: Tech Comparator, Integration Feasibility, Security Auditor, etc.)
5. Aggregator synthesizes findings into coherent narrative
6. Artifact Generator creates markdown file
7. All data persisted to PGVector
8. Frontend receives SSE updates throughout process

**Tutoring Pipeline:**
1. User selects analyzed content → enters tutoring mode
2. Tutor loads full analysis context
3. Socratic dialogue loop: Question → User Response → Assessment → Next Question
4. All messages stored in tutoring_messages table
5. (Future) Insights can update original artifact

---

## 🛠️ Tech Stack

### Backend (Python 3.13)

**Framework & Core:**
- `fastapi>=0.121.2` - Modern async web framework (latest with CVE fixes)
- `starlette>=0.49.3` - ASGI framework (CVE fixes included)
- `uvicorn[standard]>=0.32.0` - ASGI server
- `pydantic>=2.10.3` - Data validation
- `pydantic-settings>=2.6.1` - Configuration management

**LangChain/LangGraph v1.0 (November 2025):**
- `langgraph>=1.0.0` - **v1.0 stable** - Agent orchestration with Functional API
- `langchain>=1.0.0` - **v1.0 stable** - Core framework with create_agent
- `langchain-core>=1.0.0` - **v1.0 stable** - Foundation library
- `langchain-community>=1.0.0` - **v1.0 stable** - Community integrations
- `langgraph-checkpoint>=3.0.0` - Advanced checkpointing (PostgreSQL, time-travel)
- `langsmith>=1.0.0` - Observability & tracing (v1.0 compatible)

**LLM Providers:**
- `langchain-openai>=1.0.0` - OpenAI models (staging/prod, v1.0 compatible)
- `langchain-anthropic>=1.0.0` - Claude models (optional, v1.0 compatible)
- `langchain-ollama>=1.0.0` - Ollama integration (v1.0 compatible)
- `ollama>=0.4.3` - Local models (dev environment)

**Database:**
- `psycopg[binary,pool]==3.2.3` - PostgreSQL driver
- `pgvector>=0.4.1` - Vector similarity search (latest)
- `sqlalchemy==2.0.36` - ORM
- `alembic==1.13.3` - Database migrations

**Content Extraction:**
- `httpx[brotli,zstd]>=0.28.1` - Async HTTP client with compression
- `youtube-transcript-api==0.6.2` - YouTube transcripts
- `pygithub==2.5.0` - GitHub API wrapper
- `beautifulsoup4==4.12.3` - HTML parsing
- `playwright==1.48.0` - Browser automation (fallback)

**Utilities:**
- `tenacity==9.0.0` - Retry logic
- `structlog==24.4.0` - Structured logging
- `orjson>=3.9.7` - Fast JSON serialization
- `sse-starlette==2.1.3` - Server-Sent Events
- `python-dotenv==1.0.1` - Environment variables

### Frontend (React 19)

**Core:**
- `react@19.0.0` - Latest with resource preloading APIs
- `react-dom@19.0.0` - DOM bindings
- `vite@6.0.3` - Build tool
- `typescript@5.7.2` - Type safety

**State & Data:**
- `@tanstack/react-query@5.62.7` - Server state management
- `zustand@5.0.2` - Client state management

**UI Components:**
- `tailwindcss@3.4.15` - Utility-first CSS
- `@radix-ui/react-dialog@1.1.2` - Accessible modals
- `@radix-ui/react-tabs@1.1.1` - Tab components
- `@radix-ui/react-select@2.1.2` - Select dropdowns
- `lucide-react@0.460.0` - Icon library

**Content:**
- `react-markdown@9.0.1` - Markdown rendering
- `remark-gfm@4.0.0` - GitHub Flavored Markdown

**Utilities:**
- `clsx@2.1.1` - Conditional classes
- `tailwind-merge@2.5.5` - Merge Tailwind classes

### Infrastructure

**Development:**
- Docker Compose (PostgreSQL + PGVector + Ollama)
- Ollama models: `llama3.1:8b` (LLM), `nomic-embed-text` (embeddings)

**Production:**
- Frontend: Vercel
- Backend: TBD (Railway/Render/AWS)
- Database: Managed PostgreSQL with PGVector
- LLM: OpenAI GPT-4 Turbo or Claude 3.5 Sonnet

---

## 📦 Dependency Management

### pyproject.toml + Poetry (Recommended)

**Why pyproject.toml over requirements.txt:**
- ✅ **PEP 518 Standard** - Official Python packaging standard
- ✅ **Unified Configuration** - Metadata, dependencies, tools in one file
- ✅ **Rich Metadata** - Project name, version, authors, license
- ✅ **Tool Integration** - Works with Poetry, Hatch, uv, pip
- ✅ **Optional Dependencies** - Dev, test, docs groups
- ✅ **Build System** - Specifies build backend
- ✅ **Modern Tools** - Poetry, uv use it natively

**Setup:**
```bash
# Install Poetry
curl -sSL https://install.python-poetry.org | python3 -

# Initialize project
poetry init

# Add dependencies
poetry add fastapi langgraph langchain

# Add dev dependencies
poetry add --group dev pytest black ruff mypy

# Install
poetry install
```

**pyproject.toml Template:**
```toml
[tool.poetry]
name = "skillforge-backend"
version = "0.1.0"
description = "SkillForge Backend API"
authors = ["SkillForge Team"]
package-mode = false  # Application, not a package

[tool.poetry.dependencies]
python = "^3.13"
fastapi = "^0.121.2"
starlette = "^0.49.3"
uvicorn = {extras = ["standard"], version = "^0.32.0"}
pydantic = "^2.10.3"
pydantic-settings = "^2.6.1"
python-dotenv = "^1.0.1"

# LangGraph v1.0
langgraph = "^1.0.0"
langgraph-checkpoint = "^3.0.0"

# LangChain v1.0
langchain = "^1.0.0"
langchain-core = "^1.0.0"
langchain-community = "^1.0.0"

# LLM Providers
langchain-openai = "^1.0.0"
langchain-anthropic = "^1.0.0"
langchain-ollama = "^1.0.0"
ollama = "^0.4.3"

# Database
psycopg = {extras = ["binary", "pool"], version = "^3.2.3"}
pgvector = "^0.4.1"
sqlalchemy = {extras = ["asyncio"], version = "^2.0.36"}
alembic = "^1.13.3"

# HTTP & Utilities
httpx = {extras = ["brotli", "zstd"], version = "^0.28.1"}
sse-starlette = "^2.1.3"
structlog = "^24.4.0"
tenacity = "^9.0.0"
orjson = "^3.9.7"

# Content Extraction
youtube-transcript-api = "^0.6.2"
pygithub = "^2.5.0"
beautifulsoup4 = "^4.12.3"
playwright = "^1.48.0"

# Observability
langsmith = "^1.0.0"

[tool.poetry.group.dev.dependencies]
pytest = "^8.3.4"
pytest-asyncio = "^0.25.1"
pytest-cov = "^5.0.0"
black = "^24.8.0"
ruff = "^0.6.9"
mypy = "^1.13.0"
isort = "^5.13.2"

[build-system]
requires = ["poetry-core"]
build-backend = "poetry.core.masonry.api"
```

**For Deployment:**
Generate `requirements.txt` from lock file when needed:
```bash
poetry export -f requirements.txt --output requirements.txt --without-hashes
```

---

## 🚀 LangGraph v1.0 Features

### Functional API (@entrypoint, @task)

**New Pattern for Workflows:**
```python
from langgraph.func import entrypoint, task
from langgraph.checkpoint.postgres import PostgresSaver

checkpointer = PostgresSaver.from_conn_string(DATABASE_URL)

@task
def extract_content(url: str) -> str:
    """Extract content from URL."""
    return content

@entrypoint(checkpointer=checkpointer)
def analysis_workflow(url: str, previous: dict | None = None) -> dict:
    """Main analysis workflow using Functional API."""
    content = extract_content(url).result()
    return {"content": content}
```

**Benefits:**
- ✅ Simpler syntax than StateGraph
- ✅ Built-in checkpointing
- ✅ Parallel execution with futures
- ✅ Human-in-the-loop support

### create_agent (LangChain v1.0)

**Replaces deprecated `create_react_agent`:**
```python
from langchain.agents import create_agent
from langchain.chat_models import init_chat_model

model = init_chat_model("ollama:llama3.1:8b")

agent = create_agent(
    model,
    tools=[tool1, tool2],
    middleware=[...]  # Optional middleware
)
```

**Benefits:**
- ✅ Cleaner interface
- ✅ Middleware customization
- ✅ Built on LangGraph v1.0

### Advanced Checkpointing

**PostgreSQL Persistence:**
```python
from langgraph.checkpoint.postgres import PostgresSaver

checkpointer = PostgresSaver.from_conn_string(DATABASE_URL)
```

**Features:**
- ✅ Time-travel debugging
- ✅ Subgraph state inspection
- ✅ Checkpoint listing
- ✅ Production-ready persistence

---

## 🎯 Backend Development Standards

### Code Quality Standards

**File Size Limits:**
- Source files: 200 lines maximum (refactor when approaching)
- Repository files: 150 lines maximum
- Service files: 200 lines maximum
- Test files: 300 lines maximum

**Function Complexity:**
- Maximum parameters: 5 per function
- Maximum nesting depth: 4 levels
- Maximum cyclomatic complexity: 15

**Async Repository Pattern (Mandatory):**
```python
# ✅ GOOD: Repository interface dependency injection
async def list_analyses(repo: IAnalysisRepository = Depends(get_analysis_repository)):
    return await repo.list_active()

# ❌ BAD: Direct Session access
async def list_analyses(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Analysis))
    return result.scalars().all()
```

**Structured Logging:**
```python
import structlog
logger = structlog.get_logger()

# ✅ GOOD: Structured logging with context
logger.info(
    "workflow_stage_complete",
    analysis_id=analysis_id,
    stage="extraction",
    duration_ms=1234
)
```

**Alembic Migrations:**
- Always reversible (`upgrade()` + `downgrade()`)
- Index names: `ix_<table>_<column>`
- Test locally: `alembic upgrade head` + `alembic downgrade -1`

**Quality Gates:**
- Backend coverage: ≥80% (hard block)
- Type errors: 0 (mypy strict)
- Linting: 0 warnings (ruff)
- Tests: 100% pass rate

---

## 📅 Development Phases

### **Phase 1: Foundation (Weeks 1-2)** ⚡ PRIORITY
**Goal:** Establish core infrastructure and basic analysis capability

**Deliverables:**
- ✅ Backend scaffolding (FastAPI app structure)
- ✅ Database schema + migrations (PGVector tables)
- ✅ Frontend scaffolding (React 19 + Vite)
- ✅ Content extraction for articles (Jina AI Reader)
- ✅ Basic analysis workflow (no sub-agents yet)
- ✅ Docker Compose dev environment

**Definition of Done:**
- User can submit article URL → backend extracts text → stores in PGVector
- Frontend displays extraction progress via SSE
- All services run via `docker-compose up`

---

### **Phase 2: Multi-Agent Analysis Pipeline (Weeks 3-4)** 🤖
**Goal:** Implement full LangGraph orchestration with sub-agents

**Deliverables:**
- ✅ LangGraph supervisor pattern implementation
- ✅ 3 core sub-agents (Tech Comparator, Integration Feasibility, Implementation Planner)
- ✅ 5 additional sub-agents (Security, Performance, Code Quality, Trends, Dependencies)
- ✅ Aggregator node (synthesizes findings)
- ✅ Artifact generator (markdown output)
- ✅ SSE progress updates for each stage
- ✅ Markdown download endpoint

**Definition of Done:**
- User submits URL → receives comprehensive markdown artifact in <5 minutes
- Artifact includes: Executive Summary, Key Findings, Architecture Recommendations, Implementation Plan, Claude Code-ready prompts
- All agent findings persisted to database with embeddings

---

### **Phase 3: Tutoring System (Weeks 5-6)** 🎓
**Goal:** Interactive Socratic learning mode

**Deliverables:**
- ✅ Tutor agent LangGraph workflow
- ✅ Context loading from analysis
- ✅ Socratic dialogue implementation (system prompt engineering)
- ✅ Understanding assessment logic
- ✅ Tutoring UI (separate chat interface)
- ✅ Session persistence (tutoring_sessions + tutoring_messages tables)

**Definition of Done:**
- User can click "Teach Me" on any analysis → enters interactive chat
- Tutor asks progressive questions, adapts to user responses
- Conversation history persists across browser sessions
- User can exit/resume tutoring sessions

---

### **Phase 4: Library & Search (Weeks 7-8)** 📚
**Goal:** Searchable knowledge base with filtering

**Deliverables:**
- ✅ Full-text search (PostgreSQL `tsvector` + PGVector semantic search)
- ✅ Library UI with filters (content type, date, topics)
- ✅ Topic extraction & auto-tagging
- ✅ Sorting (recent, most downloaded)
- ✅ Pagination
- ✅ Markdown preview in library

**Definition of Done:**
- User can search "React Server Components" → finds all relevant analyses
- Filters work correctly (e.g., "only videos from last month")
- Library loads instantly (<500ms) for up to 1000 analyses

---

### **Phase 5: Content Source Expansion (Week 9)** 📹
**Goal:** Support YouTube videos and GitHub repositories

**Deliverables:**
- ✅ YouTube transcript extraction (youtube-transcript-api)
- ✅ GitHub repo analysis (basic structure + README)
- ✅ Content type detection & routing
- ✅ Specialized prompts for video vs article vs repo

**Definition of Done:**
- User can submit YouTube tutorial URL → receives transcript-based analysis
- User can submit GitHub repo URL → receives architecture analysis
- All content types use same artifact template

---

### **Phase 6: Polish & Production (Weeks 10-11)** 🚀
**Goal:** Production-ready deployment

**Deliverables:**
- ✅ Error boundaries & loading states
- ✅ Toast notifications for user feedback
- ✅ Markdown preview with syntax highlighting (Prism.js)
- ✅ Copy-to-clipboard for Claude Code prompts
- ✅ Unit tests for critical paths (>70% coverage)
- ✅ E2E tests (Playwright - 10 core flows)
- ✅ Production deployment (Vercel frontend + backend host)
- ✅ Monitoring & logging (Sentry, Prometheus)

**Definition of Done:**
- All features work on production domains
- <5% error rate in production
- P95 latency <3 seconds for analysis
- Lighthouse score >90

---

### **Phase 7: Future Enhancements (Post-MVP)** 🔮
**Not in initial scope, but planned:**

- **GitHub Integration:** Analyze user's repos for skill utilization
- **Artifact Updates from Tutoring:** Insights from tutoring refine original markdown
- **Collaborative Features:** Share analyses with team
- **API Access:** Developers can integrate SkillForge via REST API
- **Browser Extension:** One-click analysis from any webpage
- **MCP Server:** Direct integration with Claude Code CLI

---

## 📝 Detailed Task Breakdown

### Phase 1: Foundation (Weeks 1-2)

#### **1.1 Backend Scaffolding (3 days)**
- [x] **1.1.1** Create FastAPI project structure ✅
  - `app/main.py` - FastAPI app initialization
  - `app/api/v1/` - API route modules
  - `app/core/config.py` - Settings with Pydantic
  - `app/db/` - Database connection & session management
  - `app/models/` - SQLAlchemy models
  - `app/schemas/` - Pydantic request/response schemas
- [x] **1.1.2** Setup environment configuration ✅
  - `.env.example` - Template for environment variables
  - `app/core/config.py` - Load settings from environment
  - Validation for required variables (DATABASE_URL, OLLAMA_BASE_URL, etc.)
- [x] **1.1.3** Implement logging & error handling ✅
  - `app/core/logging.py` - Structured logging with structlog
  - Global exception handlers in `main.py`
  - Request ID tracking middleware
- [x] **1.1.4** Write basic health check endpoint ✅
  - `GET /api/v1/health` - Returns status, database connectivity, Ollama connectivity

**Acceptance Criteria:**
- `uvicorn app.main:app --reload` starts server successfully
- `/health` endpoint returns 200 with all systems operational
- Logs show structured JSON output

---

#### **1.2 Database Schema & Migrations (4 days)**
- [x] **1.2.1** Install & configure Alembic ✅
  - `alembic init alembic`
  - Configure `alembic.ini` with SQLAlchemy async
  - Setup `env.py` to load models
- [x] **1.2.2** Create SQLAlchemy models ✅
  - `app/models/analysis.py` - `Analysis` model (url, content, status, embeddings)
  - `app/models/agent_finding.py` - `AgentFinding` model (analysis_id FK, agent_type, findings)
  - `app/models/artifact.py` - `Artifact` model (analysis_id FK, markdown_content)
  - `app/models/tutoring.py` - `TutoringSession`, `TutoringMessage` models
  - `app/models/progress.py` - `AnalysisProgress` model (for SSE tracking)
- [x] **1.2.3** Enable PGVector extension ✅
  - Create custom migration with `CREATE EXTENSION IF NOT EXISTS vector;`
  - Add vector column types to models (`Vector(768)` for nomic-embed-text)
- [x] **1.2.4** Write initial migration ✅
  - `alembic revision --autogenerate -m "Initial schema"`
  - Review generated migration SQL
  - Test `alembic upgrade head`
- [x] **1.2.5** Create database utilities ✅
  - `app/db/session.py` - AsyncSession factory
  - `app/db/base.py` - Base class for models
  - CRUD utilities for common operations

**Acceptance Criteria:**
- `alembic upgrade head` runs without errors
- All tables created in PostgreSQL
- PGVector extension enabled
- Can insert/query records via SQLAlchemy

---

#### **1.3 Frontend Scaffolding (3 days)**
- [ ] **1.3.1** Initialize Vite + React 19 project
  - `npm create vite@latest frontend -- --template react-ts`
  - Update React to v19: `npm install --save-exact react@^19.0.0 react-dom@^19.0.0`
  - Configure `vite.config.ts` (proxy API calls to backend)
- [ ] **1.3.2** Setup Tailwind CSS + Radix UI
  - `npx tailwindcss init -p`
  - Configure `tailwind.config.js` with colors, fonts
  - Install Radix UI primitives (Dialog, Tabs, Select)
  - Create `components/ui/` folder for styled primitives
- [ ] **1.3.3** Configure routing
  - Install `react-router-dom@7.9.4` (latest)
  - Setup routes: `/` (home), `/analyze/:id` (analysis view), `/tutor/:sessionId`, `/library`
  - Create layout component with navigation
- [ ] **1.3.4** Setup state management
  - Configure TanStack Query (`QueryClient`, `QueryClientProvider`)
  - Create Zustand store for global UI state
  - Setup SSE client utility (`hooks/useSSE.ts`)
- [ ] **1.3.5** Create basic page shells
  - `pages/Home.tsx` - Landing with module cards
  - `pages/Analyze.tsx` - URL input form
  - `pages/Library.tsx` - Empty state
  - `pages/Tutor.tsx` - Chat interface skeleton

**Acceptance Criteria:**
- `npm run dev` starts frontend on http://localhost:5173
- Navigation between routes works
- Tailwind classes render correctly
- API calls proxied to backend

---

#### **1.4 Content Extraction - Jina AI (3 days)** ✅ COMPLETE
- [x] **1.4.1** Research & obtain Jina AI API key ✅
  - Sign up at https://jina.ai
  - Test API with curl: `curl https://r.jina.ai/YOUR_URL`
  - Document rate limits & pricing
- [x] **1.4.2** Create extraction service ✅
  - `app/services/extraction/jina_reader.py`
  - Implement `extract_article(url: str) -> dict`
  - Parse Jina response (title, content, metadata)
  - Error handling (invalid URLs, timeouts, 404s)
- [x] **1.4.3** Content type detection ✅
  - `app/services/extraction/content_type.py`
  - Detects content type (article/video/repo)
  - Used by extraction service
- [x] **1.4.4** Add retry logic with Tenacity ✅
  - Retry on network errors (max 3 attempts)
  - Exponential backoff (1s, 2s, 4s)
  - Integrated in JinaReader service
- [x] **1.4.5** Write tests ✅
  - Unit tests for `jina_reader.py` (mock httpx)
  - Integration tests with real Jina API
  - Extended tests for multiple scenarios
  - 100% coverage on extraction services

**Acceptance Criteria:**
- `POST /api/v1/analyze` with article URL returns `analysis_id`
- Extracted content stored in `analyses.raw_content`
- Extraction completes in <10 seconds for typical articles
- Errors logged with context

---

#### **1.5 Basic Analysis Workflow (3 days)**
- [x] **1.5.0** Schema migration to Vector(768) ✅
- [x] **1.5.1** Install Ollama & pull models ✅
  - Pulled `nomic-embed-text` model
  - Verified model availability via health check
- [x] **1.5.2** Create embedding service ✅
  - `app/services/embeddings.py` (209 lines)
  - Implemented `generate_embedding(text: str) -> list[float]`
  - Uses `nomic-embed-text` via Ollama (768 dimensions)
  - Dimension handling (truncate/pad) following reporter-accuracy pattern
  - L2 normalization for cosine similarity search
  - Comprehensive tests (15 tests, 100% pass rate)
- [ ] **1.5.3** Create basic LangGraph workflow
  - `app/workflows/analysis.py`
  - Define `AnalysisState` TypedDict
  - Implement single node: `extract_and_embed`
  - No sub-agents yet - just extraction → embedding → done
- [ ] **1.5.4** Integrate workflow with API
  - `POST /api/v1/analyze` triggers LangGraph execution
  - Run workflow in background task (FastAPI BackgroundTasks)
  - Update `analyses.status` from "extracting" → "complete"
- [ ] **1.5.5** Add SSE endpoint for progress
  - `GET /api/v1/analyze/{analysis_id}/stream` (SSE)
  - Stream `AnalysisProgress` updates as they occur
  - Event types: `extraction`, `embedding`, `complete`, `error`

**Acceptance Criteria:**
- Submit article URL → backend extracts → generates embedding → stores in PGVector
- Frontend can connect to SSE endpoint and receive real-time updates
- Analysis completes end-to-end in <30 seconds

---

#### **1.6 Docker Compose Dev Environment (2 days)**
- [ ] **1.6.1** Create `docker-compose.yml`
  - Service: `postgres` (pgvector/pgvector:pg17)
  - Service: `ollama` (ollama/ollama:latest)
  - Service: `backend` (build from `./backend/Dockerfile`)
  - Service: `frontend` (build from `./frontend/Dockerfile` - dev mode)
  - Networks & volumes configuration
- [ ] **1.6.2** Write Dockerfiles
  - `backend/Dockerfile` - Multi-stage build (Python 3.11)
  - `frontend/Dockerfile.dev` - Node 20 with Vite dev server
- [ ] **1.6.3** Create setup scripts
  - `scripts/setup.sh` - One-command environment setup
    - Checks Docker installation
    - Copies `.env.example` → `.env`
    - Runs `docker-compose up -d`
    - Runs Alembic migrations
    - Pulls Ollama models
- [ ] **1.6.4** Write developer documentation
  - `docs/DEVELOPMENT.md` - Setup instructions
  - Environment variable reference
  - Common troubleshooting (port conflicts, DB connection issues)

**Acceptance Criteria:**
- `./scripts/setup.sh` brings up entire stack on fresh machine
- All services healthy: `docker-compose ps` shows all "Up"
- Can access frontend (http://localhost:5173) and backend (http://localhost:8000/docs)

---

### Phase 2: Multi-Agent Analysis Pipeline (Weeks 3-4)

#### **2.1 LangGraph Supervisor Pattern (4 days)**
- [ ] **2.1.1** Design state schema for multi-agent workflow
  - Update `AnalysisState` TypedDict with new fields:
    - `supervisor_decision: dict` - Which agents to invoke + priority
    - `agent_findings: list[dict]` - Outputs from all sub-agents
    - `aggregated_insights: dict` - Combined findings
- [ ] **2.1.2** Implement Supervisor node
  - `app/workflows/nodes/supervisor.py`
  - LLM call (Ollama llama3.1:8b) analyzes extracted content
  - Returns: `{"agents": ["tech_comparator", "security_auditor", ...], "priority": [0.9, 0.7, ...]}`
  - Logic: Route based on content keywords, length, domain
- [ ] **2.1.3** Implement dynamic routing with LangGraph `send()` API
  - Use `Send` from `langgraph.constants` for parallel execution
  - Map supervisor decisions to sub-agent nodes
  - Handle cases where 0 agents or all 8 agents are selected
- [ ] **2.1.4** Create sub-agent registry
  - `app/workflows/agents/registry.py`
  - Maps agent names → node functions
  - Validates agent existence before routing
- [ ] **2.1.5** Write tests
  - Unit test supervisor logic (mock LLM)
  - Integration test full routing (ensure parallel execution)

**Acceptance Criteria:**
- Supervisor correctly identifies relevant agents for different content types
- Sub-agents invoked in parallel via `send()`
- State updates include supervisor_decision

---

#### **2.2 Core Sub-Agents Implementation (5 days)**

##### **2.2.1 Tech Comparator Agent**
- [ ] Create `app/workflows/agents/tech_comparator.py`
- [ ] Define specialized prompt template
  - "You are a Technical Comparison Specialist..."
  - Task: Identify primary tech → compare to alternatives → create table
- [ ] Implement `run_tech_comparator(state: AnalysisState) -> dict`
  - LLM call with content + prompt
  - Parse response (JSON format)
  - Return findings: `{"primary_tech": "...", "alternatives": [...], "comparison": {...}}`
- [ ] Store findings in `agent_findings` table

##### **2.2.2 Integration Feasibility Agent**
- [ ] Create `app/workflows/agents/integration_feasibility.py`
- [ ] Prompt: "Analyze how this tech integrates with modern stacks (Next.js, FastAPI, etc.)"
- [ ] Output: `{"compatibility": {...}, "migration_effort": "low/medium/high", "breaking_changes": [...]}`

##### **2.2.3 Implementation Planner Agent**
- [ ] Create `app/workflows/agents/implementation_planner.py`
- [ ] Prompt: "Create step-by-step implementation guide"
- [ ] Output: `{"prerequisites": [...], "steps": [{step: 1, action: "...", files: [...]}], "testing_strategy": "..."}`

**Acceptance Criteria (for all 3 agents):**
- Each agent returns structured JSON
- Findings stored in database with `agent_type` field
- Execution completes in <30 seconds per agent

---

##### **2.2.4 Additional 5 Sub-Agents (staggered implementation)**
- [ ] Security Auditor (`security_auditor.py`)
  - Identifies security implications (OWASP risks, auth concerns)
- [ ] Performance Analyst (`performance_analyst.py`)
  - Evaluates performance trade-offs (latency, memory, scaling)
- [ ] Code Quality Critic (`code_quality_critic.py`)
  - Checks for antipatterns, best practices, maintainability
- [ ] Trend Validator (`trend_validator.py`)
  - Assesses if tech is 2025-aligned or legacy
- [ ] Dependency Mapper (`dependency_mapper.py`)
  - Lists required libraries, version conflicts

**Strategy:** Implement these incrementally, one per day, reusing the pattern from core 3 agents.

---

#### **2.3 Aggregator Node (3 days)**
- [ ] **2.3.1** Create `app/workflows/nodes/aggregator.py`
- [ ] **2.3.2** Implement `aggregate_findings(state: AnalysisState) -> dict`
  - LLM call with all agent findings as input
  - Prompt: "Synthesize these findings into a cohesive narrative..."
  - Remove redundancy, resolve contradictions
  - Return: `{"executive_summary": "...", "key_findings": [...], "synthesis": {...}}`
- [ ] **2.3.3** Handle cases where agents disagree
  - Prioritize findings from higher-priority agents
  - Flag contradictions in output
- [ ] **2.3.4** Store aggregated insights in state

**Acceptance Criteria:**
- Aggregator produces readable, non-redundant summary
- Executive summary is 2-3 sentences
- Key findings are bullet points (3-7 items)

---

#### **2.4 Artifact Generator (4 days)**
- [ ] **2.4.1** Design markdown template
  - Create `app/templates/artifact_template.md` (Jinja2)
  - Sections: Executive Summary, Key Findings, Technical Analysis, Implementation Plan, Claude Code Prompt, Considerations, References
- [ ] **2.4.2** Create `app/workflows/nodes/artifact_generator.py`
- [ ] **2.4.3** Implement `generate_artifact(state: AnalysisState) -> str`
  - Populate template with aggregated insights + sub-agent findings
  - Format code blocks with syntax highlighting hints
  - Generate "Claude Code Prompt" section (copyable prompt)
- [ ] **2.4.4** Store artifact in `artifacts` table
  - Link to analysis via `analysis_id`
  - Set version=1 (for future updates)
  - Extract metadata (topics, complexity score)
- [ ] **2.4.5** Create download endpoint
  - `GET /api/v1/artifacts/{artifact_id}/download`
  - Returns markdown with proper headers (`Content-Disposition: attachment`)

**Acceptance Criteria:**
- Generated markdown is well-formatted and comprehensive (2000-4000 words)
- "Claude Code Prompt" section is actionable (can be copy-pasted)
- Download endpoint returns correct filename (e.g., `react-19-streaming-guide.md`)

---

#### **2.5 End-to-End Pipeline Integration (3 days)**
- [ ] **2.5.1** Connect all nodes in LangGraph workflow
  - `Extract → Supervisor → Sub-Agents (parallel) → Aggregator → Artifact Generator → END`
  - Add conditional edges for error handling
- [ ] **2.5.2** Update SSE endpoint to stream all stages
  - Events: `extraction`, `supervisor_routing`, `tech_comparison`, `integration_feasibility`, ..., `aggregation`, `artifact_generation`, `complete`
  - Each event includes progress percentage
- [ ] **2.5.3** Frontend progress UI
  - Display live updates as analysis progresses
  - Show checkmarks for completed stages
  - Handle error states (retry button)
- [ ] **2.5.4** End-to-end testing
  - Submit 5 different URLs (React article, LangGraph tutorial, Python video, GitHub repo, blog post)
  - Verify all produce valid artifacts
  - Measure total processing time (<5 minutes)

**Acceptance Criteria:**
- Full pipeline runs without errors for diverse content types
- Frontend shows real-time progress for all 8+ stages
- Artifacts downloadable immediately after completion

---

### Phase 3: Tutoring System (Weeks 5-6)

#### **3.1 Tutor Agent LangGraph Workflow (4 days)**
- [ ] **3.1.1** Design `TutorState` schema
  - Fields: `session_id`, `analysis_context`, `conversation_history`, `current_topic`, `user_understanding_level`, `socratic_strategy`
- [ ] **3.1.2** Create `app/workflows/tutor.py`
- [ ] **3.1.3** Implement `initialize_tutor` node
  - Load full analysis from database
  - Extract available topics (from agent findings)
  - Return initial greeting message
- [ ] **3.1.4** Implement `socratic_response` node
  - System prompt: Your provided Socratic tutoring instructions
  - Analyze user message → generate next question or explanation
  - Adapt complexity based on `user_understanding_level`
- [ ] **3.1.5** Implement `assess_understanding` node
  - LLM evaluates user's response for comprehension signals
  - Updates `user_understanding_level`: "novice" → "intermediate" → "advanced"
  - Adjusts `socratic_strategy`: "scaffolding", "challenging", "synthesizing"

**Acceptance Criteria:**
- Tutor workflow initializes with analysis context
- Socratic responses are contextual and pedagogically sound
- Assessment accurately categorizes user understanding

---

#### **3.2 Tutoring API Endpoints (3 days)**
- [ ] **3.2.1** Create tutoring session endpoint
  - `POST /api/v1/tutor/sessions` - Body: `{"analysis_id": "...", "topic": "..."}`
  - Creates `TutoringSession` record with status="active"
  - Runs `initialize_tutor` node
  - Returns: `{"session_id": "...", "initial_message": "...", "available_topics": [...]}`
- [ ] **3.2.2** Create message endpoint
  - `POST /api/v1/tutor/sessions/{session_id}/messages` - Body: `{"content": "..."}`
  - Stores user message in `tutoring_messages` table
  - Runs `socratic_response` → `assess_understanding` nodes
  - Returns assistant message: `{"message_id": "...", "content": "...", "metadata": {...}}`
- [ ] **3.2.3** Create session retrieval endpoint
  - `GET /api/v1/tutor/sessions/{session_id}`
  - Returns full conversation history + metadata

**Acceptance Criteria:**
- Can create tutoring session from any analysis
- Messages persist correctly with role (user/assistant)
- Conversation history retrievable

---

#### **3.3 Tutoring Frontend UI (5 days)**
- [ ] **3.3.1** Create `TutorChat` component
  - Message list (scrollable, auto-scroll to bottom)
  - Input field with "Send" button
  - Typing indicator while assistant responds
- [ ] **3.3.2** Implement topic selection
  - Modal/dialog showing available topics from analysis
  - User selects topic → initializes session
- [ ] **3.3.3** Add session management
  - "Exit Tutoring" button → marks session as completed
  - "Resume Session" if navigating away and returning
- [ ] **3.3.4** Style chat interface
  - Distinguish user vs assistant messages (different colors/alignment)
  - Add avatar icons (user icon, AI tutor icon)
  - Markdown rendering in assistant messages
- [ ] **3.3.5** Add keyboard shortcuts
  - Enter to send message
  - Shift+Enter for new line

**Acceptance Criteria:**
- Chat interface is responsive and accessible
- Markdown in assistant messages renders correctly
- Can exit and resume sessions

---

#### **3.4 Tutoring Session Persistence (2 days)**
- [ ] **3.4.1** Store all messages to database immediately after sending
- [ ] **3.4.2** Load conversation history on session resume
- [ ] **3.4.3** Add session status tracking
  - "active", "completed", "abandoned" (no activity for 24h)
- [ ] **3.4.4** Create background job to mark abandoned sessions

**Acceptance Criteria:**
- Conversation persists across browser sessions
- Can resume from exactly where user left off

---

### Phase 4: Library & Search (Weeks 7-8)

#### **4.1 Full-Text Search (4 days)**
- [ ] **4.1.1** Add PostgreSQL full-text search
  - Create `tsvector` column on `analyses` table: `search_vector`
  - Create GIN index: `CREATE INDEX idx_search_vector ON analyses USING GIN(search_vector);`
  - Update trigger to auto-populate `search_vector` on insert/update
- [ ] **4.1.2** Implement search query builder
  - `app/services/search.py`
  - Function: `search_analyses(query: str, filters: dict) -> list[Analysis]`
  - Combine full-text search with PGVector semantic search
  - Ranking: 70% keyword relevance, 30% semantic similarity
- [ ] **4.1.3** Create search endpoint
  - `GET /api/v1/library?search=...&content_type=...&sort=...&limit=...&offset=...`
  - Returns paginated results with total count
- [ ] **4.1.4** Test search accuracy
  - Test queries: "React hooks", "LangGraph supervisor", "streaming SSR"
  - Verify relevant results appear in top 5

**Acceptance Criteria:**
- Search returns results in <500ms for 1000+ analyses
- Semantic search catches synonyms (e.g., "AI agent" matches "LLM workflow")

---

#### **4.2 Topic Extraction & Tagging (3 days)**
- [ ] **4.2.1** Create topic extraction service
  - `app/services/topics.py`
  - LLM call: "Extract 3-5 main topics from this content..."
  - Returns: `["React", "Server Components", "Performance"]`
- [ ] **4.2.2** Add topics to artifact metadata
  - Store in `artifacts.metadata` JSONB field: `{"topics": [...], "complexity": "intermediate"}`
  - Populate during artifact generation
- [ ] **4.2.3** Create topic filter in Library UI
  - Multi-select dropdown (Radix Select)
  - Filter results by selected topics

**Acceptance Criteria:**
- Topics accurately represent content (manual review of 20 analyses)
- Topic filter works correctly in UI

---

#### **4.3 Library Frontend (5 days)**
- [ ] **4.3.1** Create `Library` page component
  - Search input with debounce (500ms)
  - Filter dropdowns (content type, topics)
  - Sort selector (recent, popular)
  - Results grid (card layout)
- [ ] **4.3.2** Create `AnalysisCard` component
  - Displays: Title, URL, topics (tags), date, download button
  - Click card → opens analysis detail view
- [ ] **4.3.3** Implement pagination
  - Load 20 results per page
  - "Load More" button (infinite scroll optional)
- [ ] **4.3.4** Add markdown preview modal
  - Click "Preview" on card → opens modal with rendered markdown
  - Syntax highlighting for code blocks (Prism.js)
- [ ] **4.3.5** Optimize performance
  - Virtualized list for 100+ results (react-window)
  - Image lazy loading

**Acceptance Criteria:**
- Library loads <1s for 100 analyses
- Search, filter, sort all work seamlessly
- Preview modal renders markdown correctly with syntax highlighting

---

### Phase 5: Content Source Expansion (Week 9)

#### **5.1 YouTube Transcript Extraction (3 days)**
- [ ] **5.1.1** Create `app/services/extraction/youtube_extractor.py`
- [ ] **5.1.2** Implement `extract_youtube(url: str) -> dict`
  - Use `youtube-transcript-api`
  - Parse video ID from URL
  - Fetch transcript (handle multiple language options)
  - Return: `{"title": "...", "transcript": "...", "duration": "...", "metadata": {...}}`
- [ ] **5.1.3** Handle errors
  - No transcript available (some videos)
  - Auto-generated vs manual captions (prefer manual)
  - Age-restricted videos
- [ ] **5.1.4** Update content type detection
  - Regex for YouTube URLs: `youtube.com/watch?v=...` or `youtu.be/...`
  - Route to `extract_youtube()`
- [ ] **5.1.5** Customize artifact template for videos
  - Add "Video Duration" field
  - Include timestamps in "Key Findings" (e.g., "[12:34] Speaker explains X")

**Acceptance Criteria:**
- Can analyze YouTube tutorial URLs
- Transcript-based analysis is coherent
- Artifact includes video-specific metadata

---

#### **5.2 GitHub Repository Analysis (4 days)**
- [ ] **5.2.1** Create `app/services/extraction/github_extractor.py`
- [ ] **5.2.2** Implement `extract_github(url: str) -> dict`
  - Use `pygithub` library
  - Fetch README.md content
  - Get repo metadata (stars, language, contributors)
  - Analyze file structure (top-level directories)
  - Return: `{"title": "...", "readme": "...", "structure": [...], "metadata": {...}}`
- [ ] **5.2.3** Specialized prompts for repos
  - Tech Comparator: "Identify the tech stack of this repo..."
  - Implementation Planner: "How to integrate this repo's patterns..."
- [ ] **5.2.4** Update content type detection
  - Regex for GitHub URLs: `github.com/[org]/[repo]`
- [ ] **5.2.5** Handle private repos gracefully
  - Return error: "This repo is private. Analysis requires public access."

**Acceptance Criteria:**
- Can analyze public GitHub repos
- Artifact includes architecture analysis + tech stack identification

---

### Phase 6: Polish & Production (Weeks 10-11)

#### **6.1 Error Handling & UX Polish (4 days)**
- [ ] **6.1.1** Add error boundaries in React
  - Top-level boundary in `App.tsx`
  - Per-route boundaries for isolated failures
  - Fallback UI with "Retry" button
- [ ] **6.1.2** Implement toast notifications
  - Library: `sonner` or custom with Radix Toast
  - Success: "Analysis complete!"
  - Error: "Failed to extract content. Please try again."
- [ ] **6.1.3** Add loading states
  - Skeleton screens for Library cards
  - Spinner for analysis in progress
  - Disabled buttons during submission
- [ ] **6.1.4** Markdown preview with syntax highlighting
  - Install Prism.js
  - Configure for Python, JavaScript, TypeScript, Bash
  - Add copy button to code blocks
- [ ] **6.1.5** Copy-to-clipboard for Claude Code prompts
  - Button in artifact view: "Copy Prompt"
  - Toast confirmation: "Copied to clipboard!"

**Acceptance Criteria:**
- No crashes from unhandled errors
- All async actions have loading states
- Code blocks render beautifully with syntax highlighting

---

#### **6.2 Testing (5 days)**
- [ ] **6.2.1** Backend unit tests
  - Test all extraction services (mock external APIs)
  - Test each LangGraph node (mock LLM calls)
  - Test database CRUD operations
  - Target: >70% coverage
- [ ] **6.2.2** Frontend unit tests
  - Test components with React Testing Library
  - Test hooks (useSSE, useTutoring, etc.)
  - Test utility functions
- [ ] **6.2.3** Integration tests
  - Test full analysis pipeline (use VCR.py to record HTTP interactions)
  - Test tutoring flow end-to-end
- [ ] **6.2.4** E2E tests with Playwright
  - 10 critical flows:
    1. Analyze article URL
    2. Download artifact
    3. Start tutoring session
    4. Search library
    5. Filter by content type
    6. Analyze YouTube video
    7. Analyze GitHub repo
    8. Resume tutoring session
    9. Copy Claude Code prompt
    10. Error handling (invalid URL)
- [ ] **6.2.5** Performance testing
  - Load test: 100 concurrent analysis requests
  - Database query performance (<100ms for library search)
  - Frontend Lighthouse audit (>90 score)

**Acceptance Criteria:**
- All tests pass in CI
- E2E tests cover happy paths + major error cases
- No performance regressions

---

#### **6.3 Production Deployment (4 days)**
- [ ] **6.3.1** Frontend deployment (Vercel)
  - Create Vercel project from GitHub repo
  - Configure environment variables (VITE_API_BASE_URL)
  - Setup custom domain (optional)
  - Enable preview deployments for PRs
- [ ] **6.3.2** Backend deployment
  - Choose host: Railway, Render, AWS ECS, or DigitalOcean App Platform
  - Create production `Dockerfile`
  - Configure environment variables (DATABASE_URL, OPENAI_API_KEY, etc.)
  - Setup health check endpoint for monitoring
- [ ] **6.3.3** Database setup
  - Provision managed PostgreSQL (Neon, Supabase, or AWS RDS)
  - Enable PGVector extension
  - Run migrations: `alembic upgrade head`
  - Setup daily backups
- [ ] **6.3.4** Switch to production LLM
  - Update `OPENAI_API_KEY` in backend env
  - Change model from Ollama to `gpt-4-turbo-preview` or `claude-3-5-sonnet`
  - Update embedding model to `text-embedding-3-large`

**Acceptance Criteria:**
- Frontend accessible at production URL
- Backend API responds at production domain
- Database migrations applied successfully
- LLM calls work with OpenAI/Anthropic

---

#### **6.4 Monitoring & Logging (3 days)**
- [ ] **6.4.1** Setup Sentry
  - Install `sentry-sdk` in backend
  - Install `@sentry/react` in frontend
  - Configure error reporting (DSNs in env)
  - Test by triggering intentional error
- [ ] **6.4.2** Add Prometheus metrics (optional)
  - Install `prometheus-client` in backend
  - Expose `/metrics` endpoint
  - Track: request count, latency, error rate, LLM token usage
- [ ] **6.4.3** Structured logging
  - Ensure all logs are JSON (already using structlog)
  - Send logs to aggregator (e.g., Axiom, Better Stack)
- [ ] **6.4.4** Create monitoring dashboard
  - Track: API uptime, P95 latency, error rate, analysis completion rate
  - Alerts: Error rate >5%, latency >5s

**Acceptance Criteria:**
- Errors appear in Sentry within 1 minute
- Can query logs by request_id or analysis_id
- Monitoring dashboard shows key metrics

---

## 🔧 Dependencies & Prerequisites

### Development Environment
- **Docker Desktop** (v24+) - For local services
- **Python** 3.11+ - Backend runtime
- **Node.js** 20+ - Frontend runtime
- **PostgreSQL Client** (psql) - Database access
- **Git** - Version control

### External Services (Free Tiers Available)
- **Jina AI** - Article extraction (500 requests/month free)
- **OpenAI** (Production) - LLM calls ($5-20/month estimated)
- **Vercel** - Frontend hosting (free for personal projects)
- **Neon/Supabase** - Managed PostgreSQL with PGVector (free tier: 3GB)
- **Sentry** - Error monitoring (5k events/month free)

### Optional Tools
- **LangSmith** - LangChain observability (debugging workflows)
- **Playwright** - E2E testing
- **Postman/Bruno** - API testing

---

## 📊 Success Metrics

### Performance
- **Analysis Completion Time:** <5 minutes (P95)
- **API Response Time:** <500ms (P95) for non-LLM endpoints
- **Database Query Time:** <100ms for library search
- **Frontend Load Time:** <2s (Lighthouse score >90)

### Reliability
- **Uptime:** >99.5% (allow for maintenance windows)
- **Error Rate:** <5% (some URLs may fail extraction)
- **Retry Success Rate:** >80% (failed analyses succeed on retry)

### Quality
- **Artifact Completeness:** 100% include all required sections
- **Markdown Validity:** 100% render correctly in viewers
- **Tutoring Coherence:** >90% user satisfaction (manual review)

### Usage (Post-Launch)
- **Analyses per Week:** 50+ (first month target)
- **Tutoring Sessions Started:** 30% of analyses
- **Artifacts Downloaded:** 70% of completed analyses

---

## ⚠️ Risk Management

### Technical Risks

**Risk 1: LLM Rate Limits**
- **Probability:** High (especially with 8 sub-agents)
- **Impact:** Analysis failures, slow processing
- **Mitigation:**
  - Implement exponential backoff with Tenacity
  - Add queueing system (Celery + Redis) for high load
  - Cache LLM responses for repeated content
  - Use batch processing where possible

**Risk 2: Content Extraction Failures**
- **Probability:** Medium (paywalls, JS-heavy sites)
- **Impact:** Cannot analyze certain URLs
- **Mitigation:**
  - Fallback to Playwright for JS rendering
  - Clear error messages to user ("This site requires login")
  - Manual content paste option (future feature)

**Risk 3: Database Performance Degradation**
- **Probability:** Medium (as data grows)
- **Impact:** Slow library searches
- **Mitigation:**
  - Regular VACUUM and ANALYZE on PostgreSQL
  - Add composite indexes on common query patterns
  - Implement query caching (Redis)

**Risk 4: PGVector Compatibility Issues**
- **Probability:** Low (mature extension)
- **Impact:** Cannot store embeddings
- **Mitigation:**
  - Use latest PGVector version (0.3.5+)
  - Test migrations on staging environment first
  - Have rollback plan (Alembic downgrade)

### Business/Product Risks

**Risk 5: Poor Artifact Quality**
- **Probability:** Medium (depends on LLM prompt quality)
- **Impact:** Users don't trust/use outputs
- **Mitigation:**
  - Extensive prompt engineering with examples
  - Manual review of first 50 artifacts
  - User feedback mechanism ("Was this helpful?")

**Risk 6: Low Tutoring Engagement**
- **Probability:** Medium (users may prefer just artifacts)
- **Impact:** Underutilized feature
- **Mitigation:**
  - Add "Teach Me" CTA prominently in UI
  - Showcase tutoring examples in onboarding
  - Track analytics (drop-off points in conversations)

**Risk 7: Scope Creep**
- **Probability:** High (many possible features)
- **Impact:** Delayed launch
- **Mitigation:**
  - Strict adherence to Phase 1-6 scope
  - Move all "nice-to-haves" to Phase 7
  - Weekly sprint reviews with stakeholders

---

## 📅 Timeline Summary

| Phase | Duration | Key Milestone |
|-------|----------|---------------|
| **Phase 1: Foundation** | Weeks 1-2 | Basic analysis pipeline working |
| **Phase 2: Multi-Agent** | Weeks 3-4 | Full 8-agent workflow + artifacts |
| **Phase 3: Tutoring** | Weeks 5-6 | Interactive Socratic learning |
| **Phase 4: Library** | Weeks 7-8 | Searchable knowledge base |
| **Phase 5: Expansion** | Week 9 | YouTube + GitHub support |
| **Phase 6: Production** | Weeks 10-11 | Live deployment |
| **Total** | **11 weeks** | **MVP Launch** |

---

## 🚀 Next Steps

### Immediate Actions (This Week)
1. **Setup Development Environment**
   - Run `./scripts/setup.sh` (to be created in Phase 1.6)
   - Verify all services start correctly
2. **Backend Scaffolding**
   - Create FastAPI project structure (Phase 1.1)
   - Write health check endpoint
3. **Database Schema**
   - Design models (Phase 1.2)
   - Create initial Alembic migration

### Project Management Integration
This roadmap is designed to be imported into your project management system. Each task includes:
- **Task ID** (e.g., 1.1.1, 2.3.4)
- **Acceptance Criteria** (definition of done)
- **Dependencies** (implied by phase ordering)

**Recommended PM Tool:** Linear, Jira, or GitHub Projects

**Sprint Structure:**
- 2-week sprints aligned with phases
- Daily standups (async acceptable)
- Sprint demos at end of each phase

---

## 📚 Additional Documentation

- **Architecture Decisions:** See `/docs/ARCHITECTURE.md` (to be created)
- **API Reference:** See `/docs/API.md` (to be created)
- **Developer Guide:** See `/docs/DEVELOPMENT.md` (Phase 1.6)
- **Deployment Guide:** See `/docs/DEPLOYMENT.md` (Phase 6.3)

---

**Document Version:** 1.0
**Last Updated:** November 23, 2025
**Maintained By:** Project Team
**Review Cycle:** Weekly during active development
