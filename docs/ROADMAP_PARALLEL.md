# 🚀 SkillForge - Parallel Development Roadmap

**Version:** 2.0 (Parallel-Optimized)
**Last Updated:** November 20, 2025
**Team:** Arie (Frontend Specialist) + Yonatan (Backend Specialist)
**Timeline:** 11 weeks (6 sprints of 2 weeks, 1 sprint of 1 week)

---

## 📋 Table of Contents

1. [Team Allocation Strategy](#team-allocation-strategy)
2. [Sprint Planning Grid](#sprint-planning-grid)
3. [Task Dependency Graph](#task-dependency-graph)
4. [Detailed Task Breakdown with Ownership](#detailed-task-breakdown-with-ownership)
5. [Risk Assessment & Bottlenecks](#risk-assessment--bottlenecks)
6. [Communication Protocol](#communication-protocol)
7. [Integration Points](#integration-points)

---

## 🎯 Team Allocation Strategy

### Developer Profiles

**Arie (Frontend Specialist)**
- **Primary Stack:** React 19, TypeScript, Vite, Tailwind, TanStack Query
- **Secondary Skills:** Can handle API integration, basic backend debugging
- **Focus Areas:** UI/UX, real-time updates (SSE), state management, accessibility

**Yonatan (Backend Specialist)**
- **Primary Stack:** Python 3.13, FastAPI 0.121.2+, LangGraph v1.0, LangChain v1.0, PostgreSQL, PGVector
- **Secondary Skills:** Can handle frontend debugging, API documentation
- **Focus Areas:** LangGraph workflows, LLM integration, database design, content extraction
- **Backend Patterns:** Async repository pattern, SSE instrumentation, structured logging, reversible migrations

### Work Distribution Principles

1. **Maximize Parallelism:** Both developers have independent work at all times
2. **Clear API Contracts:** Define interfaces early so both sides can proceed
3. **Mock-First Development:** Frontend uses mocked APIs until backend ready
4. **Daily Sync Points:** 15-min standup to align on blockers/dependencies
5. **Flexible Full-Stack:** Either can jump to other side if blocked >1 day

---

## 📅 Sprint Planning Grid

### Sprint 1: Foundation - Week 1-2 (Phase 1)

| Developer | Tasks | Story Points | Status |
|-----------|-------|--------------|--------|
| **Yonatan (Backend)** | 1.1.1-1.1.4: Backend scaffolding<br>1.2.1-1.2.5: Database schema + migrations<br>1.4.1-1.4.5: Jina AI content extraction<br>1.5.1-1.5.2: Embedding service<br>1.6.1-1.6.4: Docker Compose setup | **21 pts**<br>(5 + 8 + 5 + 3) | Sprint 1 |
| **GitHub** | [Milestone #1](https://github.com/ArieGoldkin/SkillForge/milestone/1) | [Issues #1-5](https://github.com/ArieGoldkin/SkillForge/issues?q=is%3Aissue+milestone%3A%22Sprint+1%3A+Backend+Foundation%22) | ✅ Created |
| **Arie (Frontend)** | 1.3.1-1.3.5: Frontend scaffolding<br>Create mock API responses<br>Design component library<br>Implement URL input form | **13 pts**<br>(8 + 3 + 2) | Sprint 1 |
| **Integration Point** | API Contract Definition (Day 3) | - | 🔗 |

**Sprint Goal:** Development environment running end-to-end with mocked workflows

**Dependencies:**
- **Day 1-2:** Both work independently (no dependencies)
- **Day 3:** API contract meeting → Define `/api/v1/analyze` schema
- **Day 4-10:** Continue in parallel with contract locked

---

### Sprint 2: Analysis Pipeline Foundation - Week 3-4 (Phase 2 Part 1)

| Developer | Tasks | Story Points | Status |
|-----------|-------|--------------|--------|
| **Yonatan (Backend)** | 1.5.3-1.5.5: Basic LangGraph workflow + SSE<br>2.1.1-2.1.5: Supervisor pattern implementation<br>2.2.1-2.2.3: First 3 core sub-agents | **21 pts**<br>(5 + 8 + 8) | Sprint 2 |
| **Arie (Frontend)** | Build real-time progress UI (SSE client)<br>Create Analysis view page<br>Implement loading states<br>Add error boundaries | **13 pts**<br>(5 + 5 + 3) | Sprint 2 |
| **Integration Point** | SSE Event Schema (Day 1)<br>Test with live backend (Day 8) | - | 🔗 |

**Sprint Goal:** Frontend displays live analysis progress from real backend workflow

**Dependencies:**
- **Blocker:** Arie needs SSE schema from Yonatan by Day 1
- **Integration:** Day 8 - Test SSE connection with real events

---

### Sprint 3: Multi-Agent Complete - Week 5-6 (Phase 2 Part 2)

| Developer | Tasks | Story Points | Status |
|-----------|-------|--------------|--------|
| **Yonatan (Backend)** | 2.2.4: Additional 5 sub-agents (1/day)<br>2.3.1-2.3.4: Aggregator node<br>2.4.1-2.4.3: Artifact generator (logic) | **20 pts**<br>(8 + 5 + 7) | Sprint 3 |
| **Arie (Frontend)** | 2.4.5: Artifact download UI<br>2.5.3: Progress UI refinements<br>Markdown preview component<br>Copy-to-clipboard functionality<br>Agent status cards | **13 pts**<br>(3 + 3 + 5 + 2) | Sprint 3 |
| **Integration Point** | Artifact schema (Day 2)<br>Download endpoint (Day 7) | - | 🔗 |

**Sprint Goal:** Full 8-agent pipeline generating downloadable markdown artifacts

**Dependencies:**
- **Blocker:** Arie needs artifact structure by Day 2 for preview component
- **Parallel:** Yonatan implements agents, Arie builds UI simultaneously

---

### Sprint 4: Tutoring System - Week 7-8 (Phase 3)

| Developer | Tasks | Story Points | Status |
|-----------|-------|--------------|--------|
| **Yonatan (Backend)** | 3.1.1-3.1.5: Tutor LangGraph workflow<br>3.2.1-3.2.3: Tutoring API endpoints<br>3.4.1-3.4.4: Session persistence | **21 pts**<br>(8 + 8 + 5) | Sprint 4 |
| **Arie (Frontend)** | 3.3.1-3.3.5: Chat UI component<br>Topic selection modal<br>Session management<br>Markdown rendering in chat | **13 pts**<br>(8 + 3 + 2) | Sprint 4 |
| **Integration Point** | Tutoring API schema (Day 1)<br>WebSocket vs REST decision (Day 1)<br>Live chat test (Day 6) | - | 🔗 |

**Sprint Goal:** Interactive Socratic tutoring working end-to-end

**Dependencies:**
- **Blocker:** Arie needs API schema + decision on SSE vs REST for chat
- **Integration:** Day 6 - Test full chat flow with real backend

---

### Sprint 5: Library & Search - Week 9-10 (Phase 4)

| Developer | Tasks | Story Points | Status |
|-----------|-------|--------------|--------|
| **Yonatan (Backend)** | 4.1.1-4.1.4: Full-text + vector search<br>4.2.1-4.2.2: Topic extraction<br>Pagination logic<br>Performance optimization | **20 pts**<br>(8 + 5 + 5 + 2) | Sprint 5 |
| **Arie (Frontend)** | 4.3.1-4.3.5: Library page UI<br>Search input with debounce<br>Filter components<br>Pagination UI<br>Analysis card component | **13 pts**<br>(8 + 2 + 3) | Sprint 5 |
| **Integration Point** | Search API contract (Day 1)<br>Performance testing (Day 9) | - | 🔗 |

**Sprint Goal:** Searchable library with <500ms query time for 1000+ items

**Dependencies:**
- **Blocker:** Arie needs search API response structure by Day 1
- **Parallel:** Both implement search features simultaneously

---

### Sprint 6: Content Expansion - Week 11 (Phase 5)

| Developer | Tasks | Story Points | Status |
|-----------|-------|--------------|--------|
| **Yonatan (Backend)** | 5.1.1-5.1.5: YouTube extraction<br>5.2.1-5.2.5: GitHub extraction<br>Content type routing logic | **13 pts**<br>(5 + 5 + 3) | Sprint 6 |
| **Arie (Frontend)** | UI for content type detection<br>Video-specific UI elements<br>Repo-specific UI elements<br>URL validation enhancements | **8 pts**<br>(3 + 2 + 3) | Sprint 6 |
| **Integration Point** | Content type enum (Day 1)<br>Test new extractors (Day 5) | - | 🔗 |

**Sprint Goal:** Support article + YouTube + GitHub URLs

**Note:** Arie has lighter load this sprint - can help with testing or start Phase 6 polish work early

---

### Sprint 7: Production Polish - Week 12-13 (Phase 6)

| Developer | Tasks | Story Points | Status |
|-----------|-------|--------------|--------|
| **Yonatan (Backend)** | 6.2.1: Backend unit tests<br>6.2.3: Integration tests<br>6.3.2-6.3.3: Backend deployment + DB setup<br>6.4.1-6.4.4: Monitoring setup | **21 pts**<br>(8 + 5 + 5 + 3) | Sprint 7 |
| **Arie (Frontend)** | 6.1.1-6.1.5: Error handling + UX polish<br>6.2.2: Frontend unit tests<br>6.2.4: E2E tests (Playwright)<br>6.3.1: Vercel deployment | **21 pts**<br>(8 + 5 + 5 + 3) | Sprint 7 |
| **Integration Point** | Production deployment coordination (Day 8-10)<br>E2E test suite (Day 7) | - | 🔗 |

**Sprint Goal:** Production deployment with monitoring and >70% test coverage

**Dependencies:**
- **Blocker:** E2E tests require backend staging environment
- **Coordination:** Deploy frontend first (Vercel), then backend, then integrate

---

## 🌳 Task Dependency Graph

```mermaid
graph TD
    %% Sprint 1
    A[1.1 Backend Scaffolding] --> B[1.2 Database Schema]
    B --> C[1.4 Content Extraction]
    B --> D[1.5 Embeddings Service]
    E[1.3 Frontend Scaffolding] --> F[Mock API Layer]

    A -.API Contract.-> E

    %% Sprint 2
    D --> G[1.5.3 Basic LangGraph]
    G --> H[2.1 Supervisor Pattern]
    F --> I[Real-time Progress UI]
    H -.SSE Schema.-> I

    %% Sprint 3
    H --> J[2.2 Sub-Agents 1-3]
    J --> K[2.2.4 Sub-Agents 4-8]
    K --> L[2.3 Aggregator]
    L --> M[2.4 Artifact Generator]
    I --> N[2.5 Progress UI]
    M -.Artifact Schema.-> O[Artifact Download UI]

    %% Sprint 4
    B --> P[3.4 Session Persistence]
    M --> Q[3.1 Tutor Workflow]
    Q --> R[3.2 Tutoring API]
    R -.API Schema.-> S[3.3 Chat UI]
    P --> R

    %% Sprint 5
    B --> T[4.1 Search Implementation]
    M --> U[4.2 Topic Extraction]
    T -.Search API.-> V[4.3 Library UI]
    U --> T

    %% Sprint 6
    C --> W[5.1 YouTube Extraction]
    C --> X[5.2 GitHub Extraction]
    W -.Content Types.-> Y[Content Type UI]
    X -.Content Types.-> Y

    %% Sprint 7
    Z[All Backend] --> AA[6.2.1 Backend Tests]
    AB[All Frontend] --> AC[6.2.2 Frontend Tests]
    AA --> AD[6.2.4 E2E Tests]
    AC --> AD
    AD --> AE[6.3 Deployment]

    style A fill:#e1f5ff
    style E fill:#ffe1f5
    style H fill:#e1f5ff
    style I fill:#ffe1f5
    style M fill:#e1f5ff
    style O fill:#ffe1f5
    style R fill:#e1f5ff
    style S fill:#ffe1f5
    style T fill:#e1f5ff
    style V fill:#ffe1f5

    %% Legend
    classDef backend fill:#e1f5ff,stroke:#0077cc
    classDef frontend fill:#ffe1f5,stroke:#cc0077
```

**Legend:**
- 🔵 Blue boxes = Backend tasks (Yonatan)
- 🔴 Pink boxes = Frontend tasks (Arie)
- Solid lines = Hard dependencies (blocking)
- Dotted lines = Integration points (contract needed)

---

## 📝 Detailed Task Breakdown with Ownership

### Phase 1: Foundation (Weeks 1-2)

#### 1.1 Backend Scaffolding [BACKEND - Yonatan]

| Task ID | Task | Story Points | Dependencies | Acceptance Criteria |
|---------|------|--------------|--------------|---------------------|
| 1.1.1 | Create FastAPI project structure | 2 | None | `uvicorn app.main:app --reload` starts server |
| 1.1.2 | Setup environment configuration | 1 | 1.1.1 | `.env.example` exists, settings load correctly |
| 1.1.3 | Implement logging & error handling | 1 | 1.1.1 | Structured JSON logs output |
| 1.1.4 | Write basic health check endpoint | 1 | 1.1.1 | `/health` returns 200 with DB/Ollama status |

**Arie Involvement:** None (fully independent)

---

#### 1.2 Database Schema & Migrations [BACKEND - Yonatan]

| Task ID | Task | Story Points | Dependencies | Acceptance Criteria |
|---------|------|--------------|--------------|---------------------|
| 1.2.1 | Install & configure Alembic | 1 | 1.1.1 | `alembic upgrade head` runs |
| 1.2.2 | Create SQLAlchemy models | 3 | 1.2.1 | All 8 models defined (`Analysis`, `AgentFinding`, `Artifact`, `TutoringSession`, `TutoringMessage`, `AnalysisProgress`) |
| 1.2.3 | Enable PGVector extension | 1 | 1.2.1 | Migration includes `CREATE EXTENSION vector;` |
| 1.2.4 | Write initial migration | 2 | 1.2.2, 1.2.3 | All tables created, PGVector columns work |
| 1.2.5 | Create database utilities | 1 | 1.2.4 | AsyncSession factory, CRUD helpers |

**Arie Involvement:** Review schema on Day 4 to understand data models for UI planning

---

#### 1.3 Frontend Scaffolding [FRONTEND - Arie]

| Task ID | Task | Story Points | Dependencies | Acceptance Criteria |
|---------|------|--------------|--------------|---------------------|
| 1.3.1 | Initialize Vite + React 19 project | 2 | None | `npm run dev` starts on port 5173 |
| 1.3.2 | Setup Tailwind CSS + Radix UI | 2 | 1.3.1 | Styles render, Radix components work |
| 1.3.3 | Configure routing | 1 | 1.3.1 | Routes defined: `/`, `/analyze/:id`, `/tutor/:sessionId`, `/library` |
| 1.3.4 | Setup state management | 2 | 1.3.1 | TanStack Query configured, Zustand store created |
| 1.3.5 | Create basic page shells | 1 | 1.3.3 | All 4 pages render with navigation |

**Yonatan Involvement:** Provide API base URL pattern on Day 3

---

#### 1.4 Content Extraction - Jina AI [BACKEND - Yonatan]

| Task ID | Task | Story Points | Dependencies | Acceptance Criteria |
|---------|------|--------------|--------------|---------------------|
| 1.4.1 | Research & obtain Jina AI API key | 1 | None | API key in `.env`, tested with curl |
| 1.4.2 | Create extraction service | 2 | 1.1.1 | `extract_article(url)` returns dict |
| 1.4.3 | Create extraction endpoint | 1 | 1.2.5, 1.4.2 | `POST /api/v1/analyze` accepts URL, creates Analysis record |
| 1.4.4 | Add retry logic with Tenacity | 1 | 1.4.3 | Max 3 retries with exponential backoff |
| 1.4.5 | Write tests | 0 (deferred) | - | (Move to Sprint 7) |

**Arie Involvement:** None initially. On Day 7, integrate UI form with this endpoint.

---

#### 1.5 Basic Analysis Workflow [BACKEND - Yonatan]

| Task ID | Task | Story Points | Dependencies | Acceptance Criteria |
|---------|------|--------------|--------------|---------------------|
| 1.5.1 | Install Ollama & pull models | 1 | 1.6.1 (Docker Compose) | `llama3.1:8b` and `nomic-embed-text` available |
| 1.5.2 | Create embedding service | 2 | 1.5.1 | `generate_embedding(text)` returns 768-dim vector |
| 1.5.3 | Create basic LangGraph workflow | 3 | 1.4.3, 1.5.2 | Single-node workflow: extract → embed → done |
| 1.5.4 | Integrate workflow with API | 2 | 1.5.3 | `POST /api/v1/analyze` triggers workflow in background |
| 1.5.5 | Add SSE endpoint for progress | 2 | 1.5.4 | `GET /api/v1/analyze/{id}/stream` emits SSE events |

**Arie Involvement:**
- **Day 5:** Get SSE event schema from Yonatan
- **Day 6-7:** Implement SSE client (`hooks/useSSE.ts`)

---

#### 1.6 Docker Compose Dev Environment [BACKEND - Yonatan]

| Task ID | Task | Story Points | Dependencies | Acceptance Criteria |
|---------|------|--------------|--------------|---------------------|
| 1.6.1 | Create `docker-compose.yml` | 1 | None | All 4 services defined (postgres, ollama, backend, frontend) |
| 1.6.2 | Write Dockerfiles | 1 | 1.6.1 | Multi-stage builds work |
| 1.6.3 | Create setup scripts | 1 | 1.6.2 | `./scripts/setup.sh` brings up entire stack |
| 1.6.4 | Write developer documentation | 0 | - | (Inline in setup script comments) |

**Arie Involvement:** Test setup script on Day 8, report any frontend issues

---

#### SPRINT 1 INTEGRATION MILESTONE (Day 10)

**Integration Test:**
1. Arie submits URL via frontend form
2. Backend extracts content (Jina AI)
3. Frontend receives SSE updates
4. Database shows `Analysis` record with embedding

**Success Criteria:** End-to-end flow works, even if slow/rough UI

---

### Phase 2: Multi-Agent Analysis Pipeline (Weeks 3-4)

#### 2.1 LangGraph Supervisor Pattern [BACKEND - Yonatan]

| Task ID | Task | Story Points | Dependencies | Acceptance Criteria |
|---------|------|--------------|--------------|---------------------|
| 2.1.1 | Design state schema for multi-agent | 2 | 1.5.3 | `AnalysisState` TypedDict updated |
| 2.1.2 | Implement Supervisor node | 3 | 2.1.1 | LLM returns agent selection JSON |
| 2.1.3 | Implement dynamic routing with `send()` | 2 | 2.1.2 | Parallel execution works via `Send` |
| 2.1.4 | Create sub-agent registry | 1 | None | Agent name → function mapping |
| 2.1.5 | Write tests | 0 (deferred) | - | (Move to Sprint 7) |

**Arie Involvement:** None (Yonatan works independently)

---

#### 2.2 Core Sub-Agents Implementation [BACKEND - Yonatan]

| Task ID | Task | Story Points | Dependencies | Acceptance Criteria |
|---------|------|--------------|--------------|---------------------|
| 2.2.1 | Tech Comparator Agent | 2 | 2.1.4 | Returns structured comparison JSON |
| 2.2.2 | Integration Feasibility Agent | 2 | 2.1.4 | Returns compatibility assessment |
| 2.2.3 | Implementation Planner Agent | 2 | 2.1.4 | Returns step-by-step guide |
| 2.2.4 | Additional 5 agents (staggered) | 8 | 2.1.4 | Security, Performance, Code Quality, Trend, Dependency agents complete |

**Arie Involvement:**
- **Day 3:** Review agent finding structure to design UI cards
- **Day 5:** Start building agent status display components

---

#### 2.3 Aggregator Node [BACKEND - Yonatan]

| Task ID | Task | Story Points | Dependencies | Acceptance Criteria |
|---------|------|--------------|--------------|---------------------|
| 2.3.1 | Create aggregator node | 2 | 2.2.4 | Aggregator function exists |
| 2.3.2 | Implement synthesis logic | 2 | 2.3.1 | LLM produces non-redundant summary |
| 2.3.3 | Handle contradictions | 1 | 2.3.2 | Conflicts flagged in output |
| 2.3.4 | Store aggregated insights | 0 | - | (Part of 2.3.2) |

**Arie Involvement:** Design UI for displaying executive summary (can start Day 4)

---

#### 2.4 Artifact Generator [FULL-STACK]

| Task ID | Task | Story Points | Owner | Dependencies | Acceptance Criteria |
|---------|------|--------------|-------|--------------|---------------------|
| 2.4.1 | Design markdown template | 1 | Yonatan | None | Jinja2 template with all sections |
| 2.4.2 | Create artifact generator node | 3 | Yonatan | 2.3.4, 2.4.1 | Workflow generates markdown |
| 2.4.3 | Store artifact in database | 1 | Yonatan | 2.4.2 | `artifacts` table populated |
| 2.4.4 | Extract metadata (topics, complexity) | 2 | Yonatan | 2.4.3 | JSONB metadata field filled |
| 2.4.5 | Create download endpoint | 1 | Yonatan | 2.4.3 | `GET /api/v1/artifacts/{id}/download` works |
| 2.4.6 | Frontend download button | 1 | Arie | 2.4.5 | Button triggers download with correct filename |

**Integration Point (Day 17):** Arie tests download flow with real backend

---

#### 2.5 End-to-End Pipeline Integration [FULL-STACK]

| Task ID | Task | Story Points | Owner | Dependencies | Acceptance Criteria |
|---------|------|--------------|-------|--------------|---------------------|
| 2.5.1 | Connect all nodes in LangGraph | 2 | Yonatan | 2.4.4 | Full graph executes: Extract → Supervisor → Sub-Agents → Aggregator → Artifact → END |
| 2.5.2 | Update SSE endpoint for all stages | 2 | Yonatan | 2.5.1 | 12+ event types emitted |
| 2.5.3 | Frontend progress UI | 3 | Arie | 2.5.2 | Live updates show all stages with checkmarks |
| 2.5.4 | End-to-end testing | 3 | Both | 2.5.3 | 5 diverse URLs analyzed successfully in <5 min |

**SPRINT 2-3 INTEGRATION MILESTONE (Day 28):**
Submit article URL → receive comprehensive markdown artifact with all 8 agent findings

---

### Phase 3: Tutoring System (Weeks 5-6)

#### 3.1 Tutor Agent LangGraph Workflow [BACKEND - Yonatan]

| Task ID | Task | Story Points | Dependencies | Acceptance Criteria |
|---------|------|--------------|--------------|---------------------|
| 3.1.1 | Design `TutorState` schema | 1 | None | TypedDict defined |
| 3.1.2 | Create tutor workflow file | 1 | 3.1.1 | `app/workflows/tutor.py` exists |
| 3.1.3 | Implement `initialize_tutor` node | 2 | 3.1.2, 1.2.2 | Loads analysis context, returns greeting |
| 3.1.4 | Implement `socratic_response` node | 3 | 3.1.3 | Generates contextual questions |
| 3.1.5 | Implement `assess_understanding` node | 1 | 3.1.4 | Categorizes user level (novice/intermediate/advanced) |

**Arie Involvement:** None until Day 4 (waits for API schema)

---

#### 3.2 Tutoring API Endpoints [BACKEND - Yonatan]

| Task ID | Task | Story Points | Dependencies | Acceptance Criteria |
|---------|------|--------------|--------------|---------------------|
| 3.2.1 | Create session creation endpoint | 2 | 3.1.5 | `POST /api/v1/tutor/sessions` works |
| 3.2.2 | Create message endpoint | 3 | 3.2.1 | `POST /api/v1/tutor/sessions/{id}/messages` returns assistant response |
| 3.2.3 | Create session retrieval endpoint | 1 | 3.2.1 | `GET /api/v1/tutor/sessions/{id}` returns history |

**Arie Involvement:**
- **Day 1:** Receive API schema document from Yonatan
- **Day 2-6:** Build chat UI with mocked responses
- **Day 7:** Integrate with real API

---

#### 3.3 Tutoring Frontend UI [FRONTEND - Arie]

| Task ID | Task | Story Points | Dependencies | Acceptance Criteria |
|---------|------|--------------|--------------|---------------------|
| 3.3.1 | Create `TutorChat` component | 3 | 3.2.2 (API schema) | Message list + input field render |
| 3.3.2 | Implement topic selection | 2 | 3.2.1 (API schema) | Modal shows available topics |
| 3.3.3 | Add session management | 2 | 3.2.3 | Can exit/resume sessions |
| 3.3.4 | Style chat interface | 1 | 3.3.1 | User/assistant messages styled differently |
| 3.3.5 | Add keyboard shortcuts | 0 | - | (Built into 3.3.1) |

**Yonatan Involvement:** None (Arie works independently after schema received)

---

#### 3.4 Tutoring Session Persistence [BACKEND - Yonatan]

| Task ID | Task | Story Points | Dependencies | Acceptance Criteria |
|---------|------|--------------|--------------|---------------------|
| 3.4.1 | Store messages to database | 1 | 3.2.2 | `tutoring_messages` table populated |
| 3.4.2 | Load conversation history | 1 | 3.4.1 | Resuming session shows all previous messages |
| 3.4.3 | Add session status tracking | 1 | 3.2.1 | Status: active/completed/abandoned |
| 3.4.4 | Background job for abandoned sessions | 2 | 3.4.3 | Cron job marks sessions abandoned after 24h |

**SPRINT 4 INTEGRATION MILESTONE (Day 42):**
User clicks "Teach Me" → selects topic → has multi-turn Socratic conversation → exits → resumes later

---

### Phase 4: Library & Search (Weeks 7-8)

#### 4.1 Full-Text Search [BACKEND - Yonatan]

| Task ID | Task | Story Points | Dependencies | Acceptance Criteria |
|---------|------|--------------|--------------|---------------------|
| 4.1.1 | Add PostgreSQL full-text search | 2 | 1.2.4 | `search_vector` column + GIN index created |
| 4.1.2 | Implement search query builder | 3 | 4.1.1 | Hybrid keyword + semantic search works |
| 4.1.3 | Create search endpoint | 2 | 4.1.2 | `GET /api/v1/library?search=...` returns paginated results |
| 4.1.4 | Test search accuracy | 1 | 4.1.3 | Top 5 results relevant for test queries |

**Arie Involvement:**
- **Day 1:** Receive search API response schema
- **Day 2-8:** Build library UI in parallel

---

#### 4.2 Topic Extraction & Tagging [BACKEND - Yonatan]

| Task ID | Task | Story Points | Dependencies | Acceptance Criteria |
|---------|------|--------------|--------------|---------------------|
| 4.2.1 | Create topic extraction service | 2 | None | LLM extracts 3-5 topics |
| 4.2.2 | Add topics to artifact metadata | 1 | 4.2.1, 2.4.4 | `artifacts.metadata.topics` array populated |
| 4.2.3 | Create topic filter logic | 2 | 4.2.2 | Search endpoint accepts `topics[]` filter |

**Arie Involvement:** Build topic filter UI component (Day 5-6)

---

#### 4.3 Library Frontend [FRONTEND - Arie]

| Task ID | Task | Story Points | Dependencies | Acceptance Criteria |
|---------|------|--------------|--------------|---------------------|
| 4.3.1 | Create `Library` page component | 3 | 4.1.3 (API schema) | Search + filters + results grid render |
| 4.3.2 | Create `AnalysisCard` component | 2 | 4.1.3 | Card shows title, URL, topics, date, download button |
| 4.3.3 | Implement pagination | 2 | 4.1.3 | "Load More" loads next 20 results |
| 4.3.4 | Add markdown preview modal | 2 | 2.4.3 | Modal displays rendered markdown |
| 4.3.5 | Optimize performance | 2 | 4.3.3 | Virtualized list for 100+ results |

**Yonatan Involvement:** None (Arie works independently with API contract)

---

**SPRINT 5 INTEGRATION MILESTONE (Day 56):**
User searches "React hooks" → finds 10 results → filters by "Video" → previews markdown → downloads artifact

---

### Phase 5: Content Source Expansion (Week 9)

#### 5.1 YouTube Transcript Extraction [BACKEND - Yonatan]

| Task ID | Task | Story Points | Dependencies | Acceptance Criteria |
|---------|------|--------------|--------------|---------------------|
| 5.1.1 | Create YouTube extractor service | 2 | 1.4.2 | `extract_youtube(url)` returns transcript dict |
| 5.1.2 | Implement transcript fetching | 2 | 5.1.1 | `youtube-transcript-api` works |
| 5.1.3 | Handle errors (no transcript, etc.) | 1 | 5.1.2 | Clear error messages |
| 5.1.4 | Update content type detection | 0 | - | (Part of 5.1.1) |
| 5.1.5 | Customize artifact template | 0 | - | (Template already flexible) |

**Arie Involvement:** Add video icon to UI (Day 3)

---

#### 5.2 GitHub Repository Analysis [BACKEND - Yonatan]

| Task ID | Task | Story Points | Dependencies | Acceptance Criteria |
|---------|------|--------------|--------------|---------------------|
| 5.2.1 | Create GitHub extractor service | 2 | 1.4.2 | `extract_github(url)` returns repo dict |
| 5.2.2 | Implement README fetching | 2 | 5.2.1 | `pygithub` fetches README |
| 5.2.3 | Specialized prompts for repos | 1 | 5.2.2 | Tech stack identified correctly |
| 5.2.4 | Update content type detection | 0 | - | (Part of 5.2.1) |
| 5.2.5 | Handle private repos | 0 | - | (Part of 5.2.1 error handling) |

**Arie Involvement:** Add repo icon to UI (Day 5)

---

**SPRINT 6 INTEGRATION MILESTONE (Day 63):**
Submit YouTube URL → transcript analyzed → artifact generated
Submit GitHub URL → README analyzed → architecture summary generated

**Note:** Arie has lighter load in Sprint 6. Options:
1. Start Phase 6 polish work early (error boundaries, toasts)
2. Help Yonatan with integration testing
3. Design improvements / accessibility audit

---

### Phase 6: Polish & Production (Weeks 10-11)

#### 6.1 Error Handling & UX Polish [FRONTEND - Arie]

| Task ID | Task | Story Points | Dependencies | Acceptance Criteria |
|---------|------|--------------|--------------|---------------------|
| 6.1.1 | Add error boundaries in React | 2 | None | Top-level + per-route boundaries |
| 6.1.2 | Implement toast notifications | 2 | None | Success/error toasts display |
| 6.1.3 | Add loading states | 2 | None | Skeleton screens + spinners |
| 6.1.4 | Markdown preview with syntax highlighting | 1 | 4.3.4 | Prism.js highlights code |
| 6.1.5 | Copy-to-clipboard for prompts | 1 | 2.4.6 | "Copy Prompt" button works |

**Yonatan Involvement:** None (Arie works independently)

---

#### 6.2 Testing [FULL-STACK]

| Task ID | Task | Story Points | Owner | Dependencies | Acceptance Criteria |
|---------|------|--------------|-------|--------------|---------------------|
| 6.2.1 | Backend unit tests | 5 | Yonatan | None | >70% coverage for services + workflows |
| 6.2.2 | Frontend unit tests | 3 | Arie | None | >60% coverage for components + hooks |
| 6.2.3 | Integration tests | 3 | Yonatan | 6.2.1 | Full pipeline tests with VCR.py |
| 6.2.4 | E2E tests with Playwright | 5 | Arie | 6.2.1, 6.2.2 | 10 critical flows pass |
| 6.2.5 | Performance testing | 2 | Yonatan | 6.2.3 | P95 latency <3s, can handle 100 concurrent requests |

**Integration Point (Day 5):** Arie needs staging backend for E2E tests

---

#### 6.3 Production Deployment [FULL-STACK]

| Task ID | Task | Story Points | Owner | Dependencies | Acceptance Criteria |
|---------|------|--------------|-------|--------------|---------------------|
| 6.3.1 | Frontend deployment (Vercel) | 2 | Arie | 6.2.4 | Frontend live at production URL |
| 6.3.2 | Backend deployment | 3 | Yonatan | 6.2.3 | Backend live with health check passing |
| 6.3.3 | Database setup | 2 | Yonatan | None | Managed PostgreSQL with PGVector |
| 6.3.4 | Switch to production LLM | 1 | Yonatan | 6.3.2 | Using OpenAI GPT-4 Turbo or Claude 3.5 Sonnet |

**Coordination:** Deploy in sequence: DB (Day 8) → Backend (Day 9) → Frontend (Day 10)

---

#### 6.4 Monitoring & Logging [BACKEND - Yonatan]

| Task ID | Task | Story Points | Dependencies | Acceptance Criteria |
|---------|------|--------------|--------------|---------------------|
| 6.4.1 | Setup Sentry | 1 | 6.3.1, 6.3.2 | Errors reported to Sentry |
| 6.4.2 | Add Prometheus metrics | 1 | 6.3.2 | `/metrics` endpoint exposed |
| 6.4.3 | Structured logging to aggregator | 1 | 6.3.2 | Logs queryable by request_id |
| 6.4.4 | Create monitoring dashboard | 0 | - | (Use Sentry/Prometheus default UIs) |

**Arie Involvement:** Add Sentry to frontend (Day 2)

---

**SPRINT 7 INTEGRATION MILESTONE (Day 77):**
Production deployment complete, monitoring active, E2E tests passing against production

---

## ⚠️ Risk Assessment & Bottlenecks

### Critical Path Analysis

**Longest Dependency Chain (59 days):**
```
Backend Scaffolding (2d) → Database Schema (4d) → Content Extraction (3d) →
Basic Workflow (3d) → Supervisor (4d) → Sub-Agents (5d) → Aggregator (3d) →
Artifact Generator (4d) → Tutor Workflow (4d) → Search Implementation (4d) →
Testing (5d) → Deployment (3d)
```

**Potential Bottlenecks:**

### 1. SSE Integration (Sprint 2, Day 5)
**Risk:** Arie blocked if SSE schema delayed
**Mitigation:**
- Yonatan delivers SSE schema by end of Day 4 (hard deadline)
- Arie can mock SSE events if schema late, refactor later
- Daily check-in on Day 4: "Is schema ready?"

### 2. Sub-Agent Implementation (Sprint 3, Days 1-5)
**Risk:** Yonatan implementing 8 agents serially takes longer than estimated
**Mitigation:**
- Arie can help with agent prompts/testing if Yonatan falls behind
- Reduce to 6 agents if needed (Security + Trends optional for MVP)
- Parallel agent development: Yonatan does 5, Arie helps with 3 (Arie can write Python)

### 3. Artifact Generator Template (Sprint 3, Day 7)
**Risk:** Complex markdown template takes longer than 1 day
**Mitigation:**
- Start with simple template (just headings + agent outputs)
- Arie helps with Jinja2 template formatting (has web dev experience)
- Iterate on template in Sprint 4-5 (not blocking)

### 4. Tutoring API Schema Delay (Sprint 4, Day 1)
**Risk:** Arie blocked if Yonatan doesn't deliver schema on time
**Mitigation:**
- Yonatan writes OpenAPI spec on Day 0 (before Sprint 4 starts)
- Arie reviews schema during Sprint 3 retrospective
- Use contract-first development (schema → implementation)

### 5. Search Performance Issues (Sprint 5, Day 9)
**Risk:** Query time >500ms with 1000+ records
**Mitigation:**
- Yonatan profiles queries on Day 7, optimizes indexes
- Arie implements optimistic UI updates (instant feedback)
- Add Redis caching if PostgreSQL too slow (1-day spike)

### 6. E2E Test Environment (Sprint 7, Day 5)
**Risk:** Arie needs staging backend for Playwright tests, Yonatan not ready
**Mitigation:**
- Yonatan deploys staging backend by Day 3 (2 days before E2E starts)
- Arie can run E2E against local Docker Compose if staging delayed
- Use feature flags to disable unreliable features in E2E

### 7. Production Deployment Coordination (Sprint 7, Days 8-10)
**Risk:** Frontend deployed before backend ready → 500 errors
**Mitigation:**
- Deploy in sequence: DB → Backend → Frontend (not parallel)
- Use Vercel preview deployments to test against staging backend
- Keep old backend running during migration (blue-green deployment)

---

### Mitigation Strategy Summary

| Risk Category | Likelihood | Impact | Mitigation Owner |
|--------------|------------|--------|-----------------|
| API Schema Delays | Medium | High | Yonatan (publish early) |
| Complex Backend Tasks | High | Medium | Both (pair programming) |
| Integration Issues | Medium | High | Both (daily sync) |
| Performance Problems | Low | Medium | Yonatan (early profiling) |
| Deployment Failures | Medium | High | Yonatan (staging env) |

**Escape Hatch:** If either developer blocked >1 day, they switch to help the other (full-stack flexibility)

---

## 📞 Communication Protocol

### Daily Standup (15 minutes, Async OK)

**Format:**
1. **Yesterday:** What I completed
2. **Today:** What I'm working on
3. **Blockers:** What I'm waiting for

**Example (Arie, Day 17):**
```
Yesterday: Built agent status cards UI (2.5.3)
Today: Implementing download button (2.4.6)
Blockers: Need artifact download endpoint - is it ready? [tags Yonatan]
```

### Integration Checkpoints

**Sprint Boundaries (Days 14, 28, 42, 56, 63, 77):**
- 1-hour pair testing session
- Both developers test end-to-end flow
- Document any bugs in shared tracker
- Retrospective: What worked? What blocked us?

### API Contract Reviews

**Timing:** Day 3 of each sprint that introduces new endpoints
**Attendees:** Both developers
**Duration:** 30 minutes
**Deliverable:** OpenAPI spec committed to repo

**Example Agenda (Sprint 4, Day 3):**
1. Review `/api/v1/tutor/sessions` schema (5 min)
2. Review `/api/v1/tutor/sessions/{id}/messages` schema (5 min)
3. Arie asks clarifying questions (10 min)
4. Yonatan commits spec to `/docs/api/tutoring.yaml` (5 min)
5. Both agree on error codes + responses (5 min)

### Emergency Protocol

**If blocked >4 hours:**
1. Post in shared Slack/Discord channel
2. Tag the other developer
3. Propose workaround (mock data, skip feature, etc.)
4. If no response in 2 hours → implement workaround, revisit later

---

## 🔗 Integration Points

### 1. API Contracts (OpenAPI Specs)

**Location:** `/docs/api/`
**Files:**
- `analyze.yaml` - Analysis endpoints (Sprint 1)
- `artifacts.yaml` - Artifact download (Sprint 3)
- `tutoring.yaml` - Tutoring endpoints (Sprint 4)
- `library.yaml` - Search/library endpoints (Sprint 5)

**Process:**
1. Yonatan writes spec BEFORE implementing endpoint
2. Commits to repo
3. Arie generates TypeScript types from spec (openapi-generator)
4. Both develop in parallel using contract

### 2. Shared Type Definitions

**Backend (`app/schemas/`):**
```python
# Pydantic schemas for API requests/responses
class AnalysisCreate(BaseModel):
    url: str

class AnalysisResponse(BaseModel):
    id: UUID
    url: str
    status: Literal["pending", "extracting", "analyzing", "complete", "failed"]
    created_at: datetime
```

**Frontend (`src/types/`):**
```typescript
// Generated from OpenAPI spec
export interface AnalysisResponse {
  id: string;
  url: string;
  status: "pending" | "extracting" | "analyzing" | "complete" | "failed";
  created_at: string;
}
```

**Sync Mechanism:**
- Yonatan updates Pydantic schemas → OpenAPI spec regenerated → Arie pulls latest types
- Use `pydantic-to-typescript` or `datamodel-code-generator` for automation

### 3. Database Schema Documentation

**Arie's Read-Only Access:**
- Yonatan provides Entity-Relationship Diagram (ERD) after Sprint 1
- Arie reviews to understand data model for UI planning
- Use `eralchemy` to auto-generate ERD from SQLAlchemy models

### 4. SSE Event Format

**Location:** `/docs/sse-events.md`
**Example:**
```typescript
type SSEEvent =
  | { type: "extraction", progress: number, message: string }
  | { type: "supervisor_routing", agents: string[] }
  | { type: "tech_comparison", findings: object }
  | { type: "complete", artifact_id: string }
  | { type: "error", error: string };
```

**Process:**
1. Yonatan defines event types in Sprint 2, Day 1
2. Arie implements TypeScript types + event handlers
3. Both test with real backend on Day 7

### 5. Mock Data for Frontend Development

**Location:** `/frontend/src/mocks/`
**Files:**
- `analysisResponse.mock.ts` - Sample API responses
- `sseEvents.mock.ts` - Sample SSE event stream
- `artifacts.mock.md` - Sample markdown artifact

**Process:**
- Arie creates mocks based on API contracts
- Uses mocks for UI development when backend not ready
- Replaces with real API calls during integration

### 6. Environment Variables

**Shared `.env.example`:**
```bash
# Backend
DATABASE_URL=postgresql://user:pass@localhost:5432/skillforge
OLLAMA_BASE_URL=http://localhost:11434
JINA_API_KEY=your_jina_key

# Frontend
VITE_API_BASE_URL=http://localhost:8000
```

**Process:**
- Both developers keep `.env.example` updated
- Sync at start of each sprint
- Avoid surprises with missing env vars

---

## 📊 Story Points Calibration

### Story Point Scale

| Points | Meaning | Example | Time Estimate |
|--------|---------|---------|---------------|
| 1 | Trivial | Add environment variable | 1-2 hours |
| 2 | Simple | Create basic API endpoint | 2-4 hours |
| 3 | Moderate | Implement LangGraph node with LLM call | 4-8 hours |
| 5 | Complex | Full UI page with state management | 1-2 days |
| 8 | Very Complex | Multi-agent workflow orchestration | 2-3 days |

### Velocity Tracking

**Sprint Capacity:**
- **Yonatan:** 20-21 points per 2-week sprint
- **Arie:** 13-21 points per 2-week sprint (lighter in Sprints 1-6 due to backend dependencies)

**Why the difference?**
- Backend work (LangGraph, LLM integration) is more complex → higher points
- Frontend work (UI components) is faster but depends on backend readiness
- Sprint 7: Both at 21 points (equal workload for testing/deployment)

---

## 🎯 Sprint Goals (Summary)

| Sprint | Week | Goal | Success Metric |
|--------|------|------|----------------|
| **1** | 1-2 | Development environment working | `docker-compose up` → all services healthy |
| **2** | 3-4 | Multi-agent pipeline foundation | 3 agents producing findings |
| **3** | 5-6 | Complete 8-agent artifact generation | Download comprehensive markdown file |
| **4** | 7-8 | Interactive Socratic tutoring | Multi-turn conversation with context |
| **5** | 9-10 | Searchable library | Find relevant analyses in <500ms |
| **6** | 11 | YouTube + GitHub support | All 3 content types work |
| **7** | 12-13 | Production deployment | Live URL with monitoring |

---

## 🚦 Go/No-Go Criteria (Sprint Gates)

### Sprint 1 → Sprint 2 Gate
- [ ] Docker Compose brings up all services
- [ ] Backend health check returns 200
- [ ] Frontend displays analysis form
- [ ] Can submit URL and see database record created
- [ ] **Blocker:** SSE endpoint not working → Fix before Sprint 2

### Sprint 2 → Sprint 3 Gate
- [ ] Supervisor routes to at least 1 sub-agent
- [ ] Frontend displays live SSE updates
- [ ] LangGraph state persists across nodes
- [ ] **Blocker:** Sub-agents not producing JSON → Fix before Sprint 3

### Sprint 3 → Sprint 4 Gate
- [ ] All 8 agents produce findings
- [ ] Aggregator synthesizes findings
- [ ] Can download markdown artifact
- [ ] Artifact is well-formatted (manual review)
- [ ] **Blocker:** Artifact generator broken → Fix before Sprint 4

### Sprint 4 → Sprint 5 Gate
- [ ] Can start tutoring session from analysis
- [ ] Tutor generates Socratic questions
- [ ] Conversation history persists
- [ ] **Blocker:** Tutor LLM responses incoherent → Fix prompts before Sprint 5

### Sprint 5 → Sprint 6 Gate
- [ ] Library search returns results in <500ms
- [ ] Filters work correctly
- [ ] Can preview markdown in modal
- [ ] **Blocker:** Search performance >1s → Add indexes before Sprint 6

### Sprint 6 → Sprint 7 Gate
- [ ] YouTube extractor works for 5 test videos
- [ ] GitHub extractor works for 5 test repos
- [ ] **Blocker:** Extractors fail >50% of time → Debug before Sprint 7

### Sprint 7 → Production Gate
- [ ] All E2E tests pass
- [ ] >70% test coverage (backend), >60% (frontend)
- [ ] Production database migrated
- [ ] Monitoring shows <5% error rate
- [ ] **Blocker:** P95 latency >5s → Optimize before launch

---

## 📈 Progress Tracking Dashboard

**Recommended Tool:** Linear, Jira, or GitHub Projects

**Columns:**
1. **Backlog** - All tasks from this roadmap
2. **Ready** - Dependencies met, can start anytime
3. **In Progress** - Currently being worked on (max 3 per developer)
4. **Code Review** - Waiting for other developer to review
5. **Integration Testing** - Testing with real backend/frontend
6. **Done** - Acceptance criteria met

**Labels:**
- `backend` (blue) - Yonatan's tasks
- `frontend` (pink) - Arie's tasks
- `full-stack` (purple) - Requires coordination
- `blocked` (red) - Waiting on dependency
- `sprint-N` - Sprint number

**Metrics to Track:**
- Velocity (points completed per sprint)
- Cycle time (days from "Ready" → "Done")
- Blocked time (days tasks spend in "blocked" state)
- Integration test pass rate

---

## 🔄 Retrospective Template

**End of Each Sprint (30 minutes):**

1. **What went well?** (5 min)
   - Example: "API contracts helped us work in parallel"
2. **What didn't go well?** (5 min)
   - Example: "SSE schema delayed, Arie blocked for 1 day"
3. **What should we improve?** (10 min)
   - Example: "Publish API schemas 2 days before sprint starts"
4. **Action items for next sprint** (10 min)
   - Example: "Yonatan: Write tutoring API spec by Day 0"

**Document in:** `/docs/retrospectives/sprint-N.md`

---

## 🎓 Key Learnings for Parallel Development

### Do's ✅
1. **Define API contracts early** (Day 1 of sprint, not Day 5)
2. **Mock liberally** (Frontend doesn't wait for backend)
3. **Integrate frequently** (Daily if possible, at least twice per sprint)
4. **Communicate blockers immediately** (Don't wait for standup)
5. **Review each other's PRs** (Catch integration issues early)

### Don'ts ❌
1. **Don't change API contracts mid-sprint** (Breaks frontend)
2. **Don't skip integration testing** (Unit tests aren't enough)
3. **Don't let one developer get blocked >1 day** (Pair up or switch tasks)
4. **Don't deploy backend/frontend separately** (Causes version mismatches)
5. **Don't skip retrospectives** (Miss opportunities to improve)

---

## 📚 Additional Resources

### For Arie (Frontend)
- **React 19 Docs:** https://react.dev
- **TanStack Query Guide:** https://tanstack.com/query/latest
- **SSE Client Tutorial:** https://developer.mozilla.org/en-US/docs/Web/API/EventSource
- **Playwright E2E Testing:** https://playwright.dev

### For Yonatan (Backend)
- **LangGraph Docs:** https://langchain-ai.github.io/langgraph/
- **FastAPI Best Practices:** https://fastapi.tiangolo.com
- **PGVector Guide:** https://github.com/pgvector/pgvector
- **Ollama API Docs:** https://github.com/ollama/ollama/blob/main/docs/api.md

### For Both
- **API Contract First Design:** https://swagger.io/resources/articles/adopting-an-api-first-approach/
- **Parallel Development Patterns:** https://martinfowler.com/articles/branching-patterns.html

---

## 🚀 Ready to Start?

### Week 1, Day 1 Checklist

**Yonatan:**
- [ ] Clone repo, create `backend/` directory
- [ ] Initialize FastAPI project (Task 1.1.1)
- [ ] Create `.env.example` with database URL
- [ ] Push initial commit

**Arie:**
- [ ] Clone repo, create `frontend/` directory
- [ ] Initialize Vite + React 19 project (Task 1.3.1)
- [ ] Install Tailwind CSS (Task 1.3.2)
- [ ] Push initial commit

**Both:**
- [ ] 15-min kickoff meeting
  - Agree on Git workflow (feature branches, PR reviews)
  - Set daily standup time (async or sync)
  - Share preferred communication channels
- [ ] Schedule API contract review for Day 3

**Let's build SkillForge! 🔨🧠**

---

**Document Version:** 2.0 (Parallel-Optimized)
**Maintained By:** Arie + Yonatan
**Review Cycle:** End of each sprint
**Last Updated:** November 20, 2025
