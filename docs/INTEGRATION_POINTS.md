# 🔗 SkillForge - Integration Points & Coordination Protocol

**Version:** 1.0
**Last Updated:** November 20, 2025
**Team:** Arie (Frontend) + Yonatan (Backend)

---

## 📋 Table of Contents

1. [Communication Protocol](#communication-protocol)
2. [Integration Calendar](#integration-calendar)
3. [API Contract Definitions](#api-contract-definitions)
4. [Shared Type Definitions](#shared-type-definitions)
5. [Testing Strategy](#testing-strategy)
6. [Troubleshooting Guide](#troubleshooting-guide)

---

## 🤝 Communication Protocol

### Daily Async Standup (15 minutes)

**Time:** 9:00 AM (or start of work day)
**Format:** Written update in shared doc/Slack

**Template:**
```
📅 Date: [YYYY-MM-DD]
👤 Developer: [Arie/Yonatan]
📊 Sprint: [Sprint X, Day Y]

✅ Yesterday:
- Completed Task X.Y.Z: [Brief description]
- ...

🎯 Today:
- Working on Task X.Y.Z: [Brief description]
- ...

🚫 Blockers:
- [None / Description of blocker]
- Blocked by: [Other developer's task] - Need by: [time]

💬 Questions:
- [Any clarifications needed]
```

**Response Time:** Both developers should respond/acknowledge within 2 hours.

---

### Weekly Integration Checkpoint (1 hour)

**Time:** Friday 3:00 PM
**Format:** Video call or detailed written review

**Agenda:**
1. **Demo completed work** (10 min each)
2. **Review next sprint integration points** (15 min)
3. **Discuss blockers/risks** (15 min)
4. **Update task priorities** (10 min)

---

### Emergency Protocol (>4 Hours Blocked)

**If you're blocked for more than 4 hours:**

1. **Immediate notification:** Ping other developer in Slack/Discord
2. **Document blocker** in shared tracking doc:
   ```
   🚨 BLOCKER: [Task X.Y.Z]
   Blocked by: [Dependency]
   Impact: [What you can't proceed with]
   Workaround: [What you're doing instead]
   Unblocked by: [Date/time needed]
   ```
3. **Pair programming session:** Schedule 30-min call to resolve
4. **Escalate if needed:** Bring to PM if blocker can't be resolved in 1 day

---

## 🎯 Backend Implementation Patterns

### API Endpoint Pattern

**Repository-Based Endpoints:**
```python
# app/api/v1/analyze.py
from fastapi import Depends, APIRouter
from app.db.repositories.analysis import get_analysis_repository, IAnalysisRepository
from app.schemas.analysis import AnalyzeRequest, AnalyzeResponse

router = APIRouter(prefix="/api/v1", tags=["analyze"])

@router.post("/analyze", response_model=AnalyzeResponse)
async def create_analysis(
    request: AnalyzeRequest,
    repo: IAnalysisRepository = Depends(get_analysis_repository)
) -> AnalyzeResponse:
    """Create new analysis from URL."""
    analysis = await repo.create(
        url=request.url,
        content_type=request.content_type
    )
    return AnalyzeResponse.from_orm(analysis)
```

**SSE Endpoint Pattern:**
```python
from sse_starlette.sse import EventSourceResponse
from app.services.event_broadcaster import broadcaster

@router.get("/analyze/{analysis_id}/stream")
async def stream_analysis_progress(
    analysis_id: uuid.UUID,
    request: Request
) -> EventSourceResponse:
    """Stream real-time analysis progress via SSE."""
    
    async def event_generator():
        async for event in broadcaster.subscribe(f"workflow:{analysis_id}"):
            yield {
                "event": event["type"],
                "data": json.dumps(event)
            }
    
    return EventSourceResponse(event_generator())
```

**Note:** Full SSE event schema documented in `docs/issues/040-sse-endpoint/SSE_SCHEMA.md`

### LangGraph Workflow Pattern (v1.0 Functional API)

**SSE Instrumentation in Nodes:**
```python
from langgraph.func import entrypoint, task
from app.services.event_broadcaster import broadcaster

@task
async def extract_content(url: str, analysis_id: str) -> dict:
    """Extract content with SSE events."""
    # Emit start event
    await broadcaster.publish(
        f"workflow:{analysis_id}",
        {"type": "progress", "stage": "extraction", "status": "running"}
    )
    
    # Do work
    content = await jina_reader.extract(url)
    
    # Emit complete event
    await broadcaster.publish(
        f"workflow:{analysis_id}",
        {"type": "progress", "stage": "extraction", "status": "complete"}
    )
    
    return {"content": content}

@entrypoint(checkpointer=checkpointer)
async def analysis_workflow(url: str, analysis_id: str) -> dict:
    """Main workflow with SSE instrumentation."""
    result = extract_content(url, analysis_id).result()
    return result
```

---

## 📅 Integration Calendar

### Sprint 1: Foundation (Weeks 1-2)

#### 🔗 Integration Point 1: API Contract Definition (Day 3)

**Participants:** Arie + Yonatan
**Duration:** 1 hour
**Location:** Video call + shared doc

**Pre-work:**
- **Yonatan:** Draft OpenAPI spec for `/api/v1/analyze` endpoint
  - Use Pydantic schemas for request/response validation
  - Include error response schemas (400, 404, 500)
  - Document SSE endpoint separately
- **Arie:** Review user stories, list required frontend data

**Agenda:**
1. **Yonatan presents API design** (15 min)
   - Request/response schemas
   - Error codes
   - SSE event format
2. **Arie reviews from frontend perspective** (15 min)
   - Are all UI needs met?
   - Any missing fields?
   - Naming conventions clear?
3. **Agreement & lock contract** (20 min)
   - Document final contract in `docs/API_CONTRACT.md`
   - Generate TypeScript types for Arie
4. **Action items** (10 min)
   - Yonatan: Implement endpoint
   - Arie: Create mock responses

**Outputs:**
- [ ] `docs/API_CONTRACT.md` created with:
  - Request/response schemas (Pydantic models)
  - Error codes and messages
  - SSE event schemas
  - Example requests/responses
- [ ] `frontend/src/types/api.ts` generated from OpenAPI spec
- [ ] Both developers agree on contract (no changes without discussion)

**Backend Implementation Notes:**
- Use repository pattern: `Depends(get_analysis_repository)`
- Validate with Pydantic schemas
- Return proper HTTP status codes
- Log all requests with structlog (include analysis_id in context)

**Post-meeting:**
- Yonatan implements endpoint following contract exactly
- Arie creates mocks following contract exactly
- Any deviations require immediate discussion

---

#### 🔗 Integration Point 2: First End-to-End Test (Day 10)

**Participants:** Arie + Yonatan
**Duration:** 30 minutes
**Goal:** Verify frontend → backend connection works

**Testing Steps:**
1. **Yonatan:** Start backend server
   ```bash
   cd backend
   uvicorn app.main:app --reload
   ```
2. **Arie:** Start frontend dev server
   ```bash
   cd frontend
   npm run dev
   ```
3. **Both:** Test submission flow
   - Submit URL from frontend
   - Verify backend receives request
   - Check response matches contract
   - Verify CORS works
4. **Document issues** in shared tracking doc
5. **Fix critical bugs immediately** (anything that blocks further work)

**Success Criteria:**
- [ ] Frontend can submit URL to backend
- [ ] Backend returns analysis_id
- [ ] No CORS errors
- [ ] Response matches TypeScript types

---

### Sprint 2: Analysis Pipeline (Weeks 3-4)

#### 🔗 Integration Point 3: SSE Schema Lock (Day 1)

**Participants:** Yonatan → Arie (async)
**Duration:** 30 minutes
**Blocker:** Arie cannot build progress UI without this

**Deliverable:** Yonatan provides SSE event schema

**Backend Implementation Pattern:**
```python
# Yonatan implements SSE events in LangGraph nodes
# Event types match schema exactly:

# 1. Progress events (from each workflow stage)
await emit_streaming_event(
    "progress",
    analysis_id=analysis_id,
    stage="extraction",  # or "supervisor_routing", "tech_comparison", etc.
    status="running",    # or "pending", "complete", "failed"
    details={"word_count": 5234}  # Optional stage-specific data
)

# 2. Complete event (when analysis finishes)
await emit_streaming_event(
    "complete",
    analysis_id=analysis_id,
    stage="artifact_generation",
    status="complete",
    details={"artifact_id": "abc123..."}
)

# 3. Error events (on failures)
await emit_streaming_event(
    "error",
    analysis_id=analysis_id,
    stage="extraction",
    status="failed",
    details={"error": "URL not found (404)"}
)
```

**Format:**
```typescript
// Yonatan creates this file: docs/SSE_SCHEMA.md

## SSE Event Types

### Event: "progress"
```json
{
  "stage": "extraction" | "supervisor_routing" | "tech_comparison" | ...,
  "status": "pending" | "running" | "complete" | "failed",
  "details": {
    "word_count": 5234,  // Optional: stage-specific data
    "agent": "tech_comparator"  // Optional: which agent is running
  },
  "timestamp": "2025-11-20T10:30:05Z"
}
```

### Event: "complete"
```json
{
  "stage": "artifact_generation",
  "status": "complete",
  "details": {
    "artifact_id": "abc123..."
  },
  "timestamp": "2025-11-20T10:35:00Z"
}
```

### Event: "error"
```json
{
  "stage": "extraction",
  "status": "failed",
  "details": {
    "error": "URL not found (404)"
  },
  "timestamp": "2025-11-20T10:30:10Z"
}
```
```

**Post-delivery:**
- Arie creates TypeScript types from schema
- Arie implements `useSSE` hook with these events
- Yonatan implements SSE endpoint emitting these events

---

#### 🔗 Integration Point 4: Live SSE Testing (Day 8)

**Participants:** Arie + Yonatan
**Duration:** 30 minutes

**Test Scenarios:**
1. **Happy path:** Submit URL → see all stages → complete
2. **Error handling:** Submit invalid URL → see error event
3. **Connection loss:** Kill backend mid-analysis → frontend handles gracefully
4. **Multiple connections:** Open 3 analyses simultaneously

**Debugging Tools:**
- Backend logs (structlog JSON)
- Frontend Network tab (EventSource)
- Database queries (check `analysis_progress` table)

---

### Sprint 3: Artifact Viewer (Weeks 5-6)

#### 🔗 Integration Point 5: Artifact Schema (Day 2)

**Participants:** Yonatan → Arie (async)
**Duration:** 15 minutes

**Deliverable:** Yonatan provides artifact structure

```typescript
// docs/ARTIFACT_SCHEMA.md

interface Artifact {
  id: string
  analysis_id: string
  markdown_content: string  // Full markdown
  version: number
  metadata: {
    topics: string[]        // ["React", "Performance"]
    complexity: "beginner" | "intermediate" | "advanced"
    word_count: number
  }
  download_count: number
  created_at: string
}
```

**Post-delivery:**
- Arie builds `MarkdownPreview` component
- Arie implements download handler
- Yonatan implements `/api/v1/artifacts/{id}/download` endpoint

---

#### 🔗 Integration Point 6: Markdown Preview Test (Day 7)

**Participants:** Arie + Yonatan
**Duration:** 30 minutes

**Test Cases:**
1. Verify all markdown sections render correctly
2. Test code block syntax highlighting (Python, TypeScript, Bash)
3. Verify tables, lists, headings format properly
4. Test download with correct filename
5. Test copy-to-clipboard for prompts

---

### Sprint 4: Tutoring (Weeks 7-8)

#### 🔗 Integration Point 7: Tutoring API Contract (Day 1)

**Participants:** Arie + Yonatan
**Duration:** 45 minutes

**Endpoints to Define:**
1. `POST /api/v1/tutor/sessions` - Start session
2. `POST /api/v1/tutor/sessions/{id}/messages` - Send message
3. `GET /api/v1/tutor/sessions/{id}` - Get history
4. `PATCH /api/v1/tutor/sessions/{id}` - Complete session

**Document in:** `docs/API_CONTRACT.md` (append to existing)

---

#### 🔗 Integration Point 8: Chat Integration Test (Day 6)

**Participants:** Arie + Yonatan
**Duration:** 1 hour

**Test Full Conversation Flow:**
1. Start tutoring session from completed analysis
2. Send 5 user messages
3. Verify tutor responses are contextual
4. Exit session
5. Resume session
6. Verify history persists

---

### Sprint 5: Library (Weeks 9-10)

#### 🔗 Integration Point 9: Search API Contract (Day 1)

**Endpoint:** `GET /api/v1/library`

**Query Parameters:**
- `search`: string (keyword search)
- `content_type`: "all" | "article" | "video" | "repo"
- `topics`: string[] (comma-separated)
- `sort`: "recent" | "popular"
- `limit`: number (default: 20)
- `offset`: number (default: 0)

**Response:** Paginated list of analyses

---

#### 🔗 Integration Point 10: Search Accuracy Test (Day 7)

**Test Queries:**
- "React hooks" → Should find React-related analyses
- "LangGraph supervisor" → Should find LangGraph analyses
- "performance optimization" → Semantic search test

---

### Sprint 6: Content Expansion (Week 11)

#### 🔗 Integration Point 11: YouTube & GitHub Schema (Day 1)

**YouTube Analysis:**
```typescript
interface YouTubeAnalysis extends Analysis {
  metadata: {
    video_duration: string  // "15:32"
    thumbnail_url: string
    channel: string
  }
}
```

**GitHub Analysis:**
```typescript
interface GitHubAnalysis extends Analysis {
  metadata: {
    language: string
    stars: number
    last_updated: string
    file_structure: string[]
  }
}
```

---

### Sprint 7: Production (Weeks 12-13)

#### 🔗 Integration Point 12: Staging Environment Setup (Day 1)

**Backend:** Deploy to staging server (Railway/Render)
**Frontend:** Deploy to Vercel preview

**Test full flow** on staging:
1. Submit analysis (all 3 content types)
2. View progress
3. Download artifact
4. Start tutoring
5. Search library

---

#### 🔗 Integration Point 13: Production Deployment (Day 10)

**Coordinated deployment:**
1. **Yonatan:** Deploy backend to production
2. **Yonatan:** Run database migrations
3. **Arie:** Update frontend env vars (VITE_API_BASE_URL)
4. **Arie:** Deploy frontend to Vercel
5. **Both:** Smoke test all features
6. **Both:** Monitor error tracking (Sentry)

---

## 📝 API Contract Definitions

### Shared Error Format

**All endpoints use consistent error responses:**

```typescript
interface APIError {
  error: {
    code: string          // "INVALID_URL", "NOT_FOUND", etc.
    message: string       // Human-readable error
    details?: object      // Optional extra context
  }
}
```

**HTTP Status Codes:**
- `200` - Success
- `201` - Created
- `400` - Bad Request (validation error)
- `404` - Not Found
- `422` - Unprocessable Entity (semantic validation)
- `429` - Too Many Requests (rate limit)
- `500` - Internal Server Error

---

### Content Type Detection Logic

**Backend detects content type from URL:**
```python
def detect_content_type(url: str) -> str:
    if "youtube.com" in url or "youtu.be" in url:
        return "video"
    elif "github.com" in url:
        return "repo"
    else:
        return "article"
```

**Frontend displays corresponding icon:**
```typescript
const CONTENT_TYPE_ICONS = {
  article: '📄',
  video: '🎥',
  repo: '💻',
}
```

---

## 🔤 Shared Type Definitions

### TypeScript Types (Frontend)

Yonatan generates these from Pydantic schemas:

```typescript
// frontend/src/types/api.ts

export type ContentType = 'article' | 'video' | 'repo'
export type AnalysisStatus = 'pending' | 'extracting' | 'analyzing' | 'complete' | 'failed'
export type StageStatus = 'pending' | 'running' | 'complete' | 'failed'

export interface Analysis {
  id: string
  url: string
  content_type: ContentType
  title: string | null
  status: AnalysisStatus
  created_at: string
  artifact_id: string | null
}

export interface SSEProgressEvent {
  stage: string
  status: StageStatus
  details?: Record<string, any>
  timestamp: string
}

export interface Artifact {
  id: string
  analysis_id: string
  markdown_content: string
  version: number
  metadata: {
    topics: string[]
    complexity: 'beginner' | 'intermediate' | 'advanced'
    word_count: number
  }
  download_count: number
  created_at: string
}

export interface TutoringSession {
  id: string
  analysis_id: string
  status: 'active' | 'completed' | 'abandoned'
  started_at: string
  completed_at: string | null
}

export interface TutoringMessage {
  id: string
  session_id: string
  role: 'user' | 'assistant'
  content: string
  created_at: string
}
```

### Python Models (Backend)

```python
# app/schemas/shared.py
from enum import Enum

class ContentType(str, Enum):
    ARTICLE = "article"
    VIDEO = "video"
    REPO = "repo"

class AnalysisStatus(str, Enum):
    PENDING = "pending"
    EXTRACTING = "extracting"
    ANALYZING = "analyzing"
    COMPLETE = "complete"
    FAILED = "failed"
```

---

## 🧪 Testing Strategy

### Unit Tests

**Frontend (Arie):**
- Components with React Testing Library
- Hooks (useSSE, useClipboard, etc.)
- Utility functions
- **Target:** >70% coverage

**Backend (Yonatan):**
- Service functions (extraction, embeddings)
- LangGraph nodes (mocked LLM calls)
- Database operations (use test DB)
- **Target:** >70% coverage

---

### Integration Tests

**API Integration (Arie + Yonatan):**
- Use VCR.py to record HTTP interactions
- Mock expensive operations (LLM calls, Jina API)
- Test full request/response cycle

**Example:**
```python
# backend/tests/test_analyze_endpoint.py
import pytest
from httpx import AsyncClient
from app.main import app

@pytest.mark.asyncio
async def test_create_analysis():
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.post(
            "/api/v1/analyze",
            json={"url": "https://example.com/article"}
        )
        assert response.status_code == 201
        data = response.json()
        assert "analysis_id" in data
        assert "sse_endpoint" in data
```

---

### E2E Tests (Both)

**Playwright tests covering:**
1. Submit URL → View progress → Download artifact
2. Start tutoring → Send messages → Exit session
3. Search library → Filter results → Open analysis
4. Error handling (invalid URL, network failure)

**Run before every deployment:**
```bash
# Frontend
npm run test:e2e

# Backend
pytest tests/e2e/
```

---

### Manual Testing Checklist

**Before marking sprint complete:**

- [ ] Submit analysis for all 3 content types (article, video, repo)
- [ ] Test on mobile viewport (responsive design)
- [ ] Test with slow network (Chrome DevTools throttling)
- [ ] Test error states (kill backend, invalid URLs)
- [ ] Test browser compatibility (Chrome, Firefox, Safari)
- [ ] Check accessibility (keyboard navigation, screen reader)

---

## 🐛 Troubleshooting Guide

### Issue: CORS Errors

**Symptoms:** Frontend can't connect to backend

**Frontend sees:** `Access-Control-Allow-Origin` error in console

**Solution:**
1. **Yonatan:** Verify CORS middleware in `app/main.py`
   ```python
   app.add_middleware(
       CORSMiddleware,
       allow_origins=["http://localhost:5173"],
       allow_credentials=True,
       allow_methods=["*"],
       allow_headers=["*"],
   )
   ```
2. **Arie:** Verify API URL in `.env.local`:
   ```
   VITE_API_BASE_URL=http://localhost:8000
   ```

---

### Issue: SSE Connection Fails

**Symptoms:** No progress updates in UI

**Debug Steps:**
1. **Arie:** Check browser Network tab → EventSource connection
2. **Yonatan:** Check backend logs for SSE connection
3. **Both:** Verify analysis_id matches in URL
4. **Yonatan:** Check `analysis_progress` table has records

**Common Causes:**
- Analysis doesn't exist (404)
- Database query error
- Event format doesn't match TypeScript types

---

### Issue: TypeScript Type Errors

**Symptoms:** Arie sees type errors after Yonatan changes API

**Solution:**
1. **Yonatan:** Update `docs/API_CONTRACT.md` with changes
2. **Yonatan:** Regenerate TypeScript types
3. **Yonatan:** Notify Arie in standup
4. **Arie:** Pull latest types, update components

---

### Issue: Database Migration Conflicts

**Symptoms:** Alembic migration fails

**Solution:**
1. **Yonatan:** Check current migration state: `alembic current`
2. **Yonatan:** Review conflicting migrations
3. **Yonatan:** Resolve manually or create new migration
4. **Both:** Coordinate on shared schema changes

---

### Issue: Ollama Model Not Found

**Symptoms:** Backend LLM calls fail

**Solution:**
```bash
docker exec -it ollama ollama list
# If model missing:
docker exec -it ollama ollama pull llama3.1:8b
```

---

## 📞 Escalation Path

**If blocker can't be resolved between developers:**

1. **Document blocker** in shared doc with:
   - Impact (what's blocked)
   - Attempted solutions
   - Recommendation

2. **Bring to PM** (if available)

3. **Make architectural decision jointly:**
   - Both developers align on solution
   - Document in `docs/ARCHITECTURE_DECISIONS.md`
   - Proceed with implementation

---

## ✅ Integration Checklist

**After each integration point, verify:**

- [ ] Both developers tested the integration
- [ ] API contract followed exactly
- [ ] TypeScript types match backend schemas
- [ ] No console errors in browser
- [ ] No errors in backend logs
- [ ] Tests pass (if applicable)
- [ ] Documentation updated (if API changed)

---

## 📊 Success Metrics

**Track these weekly:**

- **Integration velocity:** # integration points completed on time
- **Blocker resolution time:** Average hours to unblock
- **Bug escape rate:** # bugs found in integration testing vs. E2E
- **API contract changes:** # times contract was modified (goal: minimize)

---

**Document Maintained By:** Both (Arie + Yonatan)
**Review:** Before each integration point
**Update:** Immediately after integration issues arise
