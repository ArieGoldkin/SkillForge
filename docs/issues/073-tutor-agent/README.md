# Issue #73: Tutor Agent LangGraph Workflow

**Status:** 🚧 **IN PROGRESS**  
**Assignee:** Yonatan  
**Points:** 13 pts (broken into 3 phases)  
**GitHub:** [#73](https://github.com/ArieGoldkin/SkillForge/issues/73)  
**Sprint:** Sprint 4: Interactive Tutoring

---

## 📋 Overview

Implement Socratic Tutor Agent using LangGraph StateGraph API - an interactive, curriculum-based tutoring system that helps users master topics from completed analyses. The tutor provides personalized, adaptive instruction using Socratic methodology with multi-turn conversations.

**Key Features:**
- Personalized curriculum generation (2-4 sections, 2-3 lessons each)
- Socratic questioning (adaptive based on user level)
- LLM-based understanding assessment
- Adaptive re-explanation with hints
- Section reviews and final challenges
- Real-world application guidance

---

## 🏗️ Architecture

### State Machine Flow

```
                    ┌─────────────────┐
                    │      START      │
                    │  (User Request)│
                    └────────┬────────┘
                             │
                             ▼
                    ┌─────────────────┐
                    │ GENERATE        │
                    │ SYLLABUS        │◄──┐
                    │ (From Analysis) │   │
                    └────────┬────────┘   │
                             │            │
                             ▼            │
                    ┌─────────────────┐   │
                    │ DELIVER         │   │
                    │ LESSON          │   │
                    │ (Section 0)     │   │
                    └────────┬────────┘   │
                             │            │
                             ▼            │
                    ┌─────────────────┐   │
                    │ ASK SOCRATIC    │   │
                    │ QUESTION        │   │
                    └────────┬────────┘   │
                             │            │
                             ▼            │
                    ┌─────────────────┐   │
                    │ ASSESS          │   │
                    │ READINESS       │   │
                    │ (LLM Evaluation)│   │
                    └────────┬────────┘   │
                             │            │
                    ┌────────┴────────┐  │
                    │                  │  │
              ┌─────▼─────┐    ┌──────▼──────┐
              │  READY?   │    │  NOT READY   │
              │   YES     │    │              │
              └─────┬─────┘    └──────┬───────┘
                    │                 │
        ┌───────────┴──────────┐      │
        │                      │      │
   ┌────▼────┐         ┌──────▼──────┐
   │  LAST   │         │  REPHRASE   │
   │ LESSON? │         │  EXPLAIN    │
   └────┬────┘         └──────┬──────┘
        │                    │
   ┌────┴────┐               │
   │   NO    │               │
   └────┬────┘               │
        │                    │
        ▼                    │
   ┌─────────────────┐       │
   │ NEXT LESSON     │───────┘
   └─────────────────┘
        │
        ▼
   ┌─────────────────┐
   │ CONDUCT         │
   │ SECTION REVIEW │
   └────────┬────────┘
        │
   ┌────┴────┐
   │  LAST   │
   │SECTION? │
   └────┬────┘
        │
   ┌────┴────┐
   │   NO    │
   └────┬────┘
        │
        ▼
   ┌─────────────────┐
   │ FINAL           │
   │ CHALLENGE       │
   └────────┬────────┘
        │
        ▼
   ┌─────────────────┐
   │ GUIDE           │
   │ REFLECTION      │
   └────────┬────────┘
        │
        ▼
   ┌─────────────────┐
   │      END        │
   └─────────────────┘
```

### System Architecture

```
┌──────────────┐         ┌──────────────┐         ┌──────────────┐
│   Frontend  │         │  FastAPI     │         │  PostgreSQL  │
│   (React)   │◄───────►│   Backend    │◄───────►│   Database   │
│             │  REST   │              │  Async  │              │
│             │  + SSE  │              │  ORM    │              │
└──────────────┘         └──────┬───────┘         └──────┬───────┘
                                 │                        │
                    ┌────────────▼────────────┐          │
                    │  LangGraph StateGraph   │          │
                    │   Tutor Workflow        │          │
                    │                         │          │
                    │  ┌──────────────────┐  │          │
                    │  │ PostgresSaver     │◄─┘          │
                    │  │ Checkpointer     │             │
                    │  └──────────────────┘             │
                    │                                    │
                    │  ┌──────────────────┐             │
                    │  │ Event Broadcaster│             │
                    │  │ (SSE Events)    │             │
                    │  └──────────────────┘             │
                    └────────────┬─────────────────────┘
                                 │
                    ┌────────────▼────────────┐
                    │   OpenAI API            │
                    │   (LLM + Embeddings)    │
                    └─────────────────────────┘
```

### Key Differences from Analysis Agents

| Aspect | Analysis Agents | Tutor Agent |
|--------|----------------|-------------|
| Interaction | Single pass | Multi-turn conversation |
| State | Stateless | Persistent session |
| Output | Structured JSON | Streaming natural language |
| Flow | Linear parallel | Cyclic until mastery |
| Duration | ~30 seconds | 10-60 minutes |
| Checkpointing | Per analysis | Per session (multi-turn) |

---

## 📁 File Structure

```
backend/app/workflows/tutor/
├── __init__.py              # Exports: tutor_workflow, TutorState
├── graph_builder.py         # StateGraph definition & compilation
├── state.py                 # TutorState TypedDict
├── config.py                # TUTOR_CONFIG constants
├── context.py               # Sliding window + summarization
│
├── nodes/
│   ├── __init__.py
│   ├── generate_syllabus.py    # Phase 1: Create curriculum
│   ├── deliver_lesson.py       # Phase 1: Teach concept
│   ├── ask_socratic.py         # Phase 1: Generate questions
│   ├── assess_readiness.py     # Phase 1: LLM evaluation
│   ├── rephrase_explain.py     # Phase 2: Adaptive re-explanation
│   ├── conduct_review.py       # Phase 3: Section quiz
│   ├── final_challenge.py      # Phase 3: Integrative problem
│   └── guide_reflection.py     # Phase 3: Real-world applications
│
├── tasks/
│   ├── __init__.py
│   ├── syllabus_generation.py  # LLM prompt for syllabus
│   ├── lesson_delivery.py     # LLM prompt for lessons
│   └── context_management.py  # Sliding window logic
│
└── schemas/
    ├── __init__.py
    ├── state.py                # Message, TutorPhase enum
    ├── syllabus.py             # Syllabus, Section, Lesson models
    ├── assessment.py           # ReadinessAssessment
    └── api.py                  # Request/Response schemas

backend/app/db/repositories/
└── tutor_repository.py         # CRUD for sessions/messages

backend/app/api/v1/
└── tutor.py                    # FastAPI router

backend/app/models/
└── tutoring.py                 # TutoringSession, TutoringMessage (UPDATE)
```

---

## 🎯 Implementation Phases

### Phase 1: Core Loop (5 pts)

**Goal**: Basic tutoring flow from syllabus to lesson delivery with Socratic questioning

**Components**:
1. Database migration (add missing fields to `tutoring_sessions`)
2. State schema (TutorState TypedDict + Pydantic models)
3. Repository (CRUD operations)
4. Graph builder (StateGraph with 4 core nodes)
5. Core nodes (generate_syllabus, deliver_lesson, ask_socratic, assess_readiness)
6. API endpoints (POST/GET/PATCH)
7. Unit tests (≥80% coverage)

### Phase 2: Adaptive Features (5 pts)

**Goal**: Adaptive re-explanation, context management, and understanding tracking

**Components**:
1. rephrase_explain node (max 3 attempts)
2. Context management (sliding window + summarization)
3. Understanding tracking (scores per concept, attempt tracking)
4. Tasks module (LLM prompt engineering)

### Phase 3: Completion Flow (3 pts)

**Goal**: Section reviews, final challenge, and reflection

**Components**:
1. conduct_review node (section quiz)
2. final_challenge node (integrative problem)
3. guide_reflection node (real-world applications)
4. Session completion logic
   - **Resume Session Logic (US-2.3)**: When user returns, `GET /api/v1/tutor/sessions/{id}` loads full conversation history from `tutoring_messages` table, restores StateGraph checkpoint state, allows user to continue from where they left off
   - **Exit Session Logic (US-2.4)**: `PATCH /api/v1/tutor/sessions/{id}` marks session as "completed" or "abandoned", sets `completed_at` timestamp, saves final state to checkpoint

---

## 🧪 Testing Strategy

### Unit Tests

**Location**: `tests/unit/workflows/tutor/`

- `test_graph_builder.py` - StateGraph compilation, routing logic
- `test_nodes/test_generate_syllabus.py` - Syllabus generation (mocked LLM)
- `test_nodes/test_deliver_lesson.py` - Lesson delivery (mocked LLM)
- `test_nodes/test_ask_socratic.py` - Question generation (mocked LLM)
- `test_nodes/test_assess_readiness.py` - Readiness assessment (mocked LLM)
- `test_nodes/test_rephrase_explain.py` - Re-explanation (mocked LLM)
- `test_nodes/test_conduct_review.py` - Section review (mocked LLM)
- `test_nodes/test_final_challenge.py` - Final challenge (mocked LLM)
- `test_nodes/test_guide_reflection.py` - Reflection guidance (mocked LLM)
- `test_repository.py` - CRUD operations
- `test_context.py` - Sliding window, summarization

### Integration Tests

**Location**: `tests/integration/workflows/tutor/`

- `test_conversation_flow.py` - Full 5+ turn conversation
  - Test routing logic end-to-end
  - Test SSE streaming response
  - Test session persistence across restarts
  - Test completion flow

### Coverage Requirements

- **Target**: ≥80% backend coverage (hard block)
- **Unit tests**: 100% pass rate
- **Integration tests**: Full conversation flow passes

---

## 📊 Data Flow

```
User → POST /sessions → Repository → DB (Create Session)
     → GET /sessions/{id}/stream → SSE Connection
     → POST /sessions/{id}/messages → Repository → DB (Save Message)
     → StateGraph Workflow → Node Execution
     → SSE Events → Frontend (Real-time Updates)
     → Repository → DB (Update Session State)
```

---

## 🔧 Technical Details

### Database Schema

**Existing Models** (need migration):
- `TutoringSession` - Basic structure exists
- `TutoringMessage` - Basic structure exists

**Migration Required**:
- Add `syllabus JSONB`
- Add `current_section INT DEFAULT 0`
- Add `current_lesson INT DEFAULT 0`
- Add `current_phase VARCHAR(50) DEFAULT 'syllabus_generation'`
- Add `user_level VARCHAR(20) DEFAULT 'intermediate'`
- Add `understanding_scores JSONB DEFAULT '{}'`
- Add `conversation_summary TEXT`

### StateGraph Pattern

**Reference**: `app/workflows/graph_builder.py`

```python
graph = StateGraph(TutorState)
graph.add_node("node_name", node_function)
graph.set_entry_point("first_node")
graph.add_edge("node1", "node2")
graph.add_conditional_edges("node", route_function, {"key": "target_node"})
return graph.compile(checkpointer=checkpointer)
```

### SSE Integration

**Reference**: `app/services/sse_helpers.py`

```python
await emit_streaming_event(
    "progress",
    session_id=session_id,
    stage="syllabus_generation",
    status="running",
)
```

### Repository Pattern

**Reference**: `app/db/repositories/analysis_repository.py`

- Protocol interface (`ITutorRepository`)
- Implementation (`TutorRepository`)
- Dependency injection (`get_tutor_repository()`)

---

## ✅ Acceptance Criteria

### Phase 1: Core Loop
- [ ] Database migration created and tested (reversible)
- [ ] TutorState TypedDict defined
- [ ] Pydantic models (Syllabus, Section, Lesson, Message) created
- [ ] Repository interface and implementation
  - `create_session()` - Create new tutoring session
  - `get_session()` - Get session with messages (for resume)
  - `save_message()` - Save user/assistant messages
  - `update_session_state()` - Update session progress
- [ ] Graph builder with 4 core nodes
- [ ] All 4 core nodes implemented with SSE events
- [ ] API endpoints:
  - `POST /api/v1/tutor/sessions` - Start session (US-2.1)
  - `POST /api/v1/tutor/sessions/{id}/messages` - Send message (US-2.2)
  - `GET /api/v1/tutor/sessions/{id}` - Get session + history (US-2.3 resume)
  - `PATCH /api/v1/tutor/sessions/{id}` - Update session status (US-2.4 exit)
- [ ] Router registered in main.py
- [ ] Unit tests (≥80% coverage)
- [ ] Integration test: Basic flow

### Phase 2: Adaptive Features
- [ ] rephrase_explain node
- [ ] Context management (sliding window)
- [ ] Conversation summarization
- [ ] Understanding scores tracking
- [ ] Attempt tracking logic
- [ ] Tasks module
- [ ] Unit tests for Phase 2

### Phase 3: Completion Flow
- [ ] conduct_review node
- [ ] final_challenge node
- [ ] guide_reflection node
- [ ] Session completion logic:
  - Resume session: Load checkpoint state, restore conversation history, continue workflow
  - Exit session: Mark as completed/abandoned, save final checkpoint, update `completed_at`
- [ ] Graph builder updated
- [ ] Unit tests for Phase 3
- [ ] Integration test: Full flow (including resume/exit scenarios)

### Quality Gates
- [ ] All tests pass (100% pass rate)
- [ ] Coverage ≥80% (pytest --cov)
- [ ] No linting errors (ruff check)
- [ ] No type errors (mypy app)
- [ ] Code formatted (ruff format)
- [ ] All docstrings added
- [ ] Migration tested (upgrade + downgrade)
- [ ] Frontend integration verified
- [ ] SSE streaming verified end-to-end

---

## 🔗 Dependencies

- ✅ Issue #72 (Artifact Generation) - **COMPLETE** - provides analysis context
- ✅ SSE infrastructure (`app/services/sse_helpers.py`) - **EXISTS**
- ✅ Database models (`app/models/tutoring.py`) - **EXISTS** (needs migration)
- ✅ LangGraph v1.0.4 - **INSTALLED**
- ✅ LangChain v1.1.0 - **INSTALLED**
- ✅ PostgreSQL with PGVector - **CONFIGURED**

---

## 📝 Implementation Notes

### LangGraph Pattern
- Use **StateGraph API** (not Functional API)
- Reference: `app/workflows/graph_builder.py`
- Pattern: `StateGraph(TutorState)` with nodes, edges, conditional routing

### File Structure
- Follow current pattern: `app/workflows/tutor/` (matches `app/workflows/analysis.py`)
- Repository: `app/db/repositories/tutor_repository.py`
- API: `app/api/v1/tutor.py`

### Code Quality Standards
- File size limits: Source ≤200 lines, Repository ≤150 lines, Tests ≤300 lines
- Function complexity: Max 5 params, max 4 nesting, max 15 cyclomatic
- Type hints: All functions typed, NO `Any`
- Testing: ≥80% coverage (hard block)

---

## 🚀 Usage

### Start Tutoring Session

```bash
POST /api/v1/tutor/sessions
{
  "analysis_id": "uuid",
  "user_level": "intermediate"
}

Response:
{
  "session_id": "uuid",
  "status": "active",
  "sse_endpoint": "/api/v1/tutor/sessions/{id}/stream"
}
```

### Send Message (SSE Streaming)

```bash
POST /api/v1/tutor/sessions/{id}/messages
{
  "content": "User message"
}

SSE Stream:
data: {"type": "chunk", "content": "Let me explain..."}
data: {"type": "done", "phase": "lesson_delivery", "progress": {"section": 1, "lesson": 2}}
```

### Resume Session (US-2.3)

```bash
GET /api/v1/tutor/sessions/{id}

Response:
{
  "session_id": "uuid",
  "status": "active",
  "syllabus": {...},
  "current_section": 1,
  "current_lesson": 2,
  "messages": [
    {"role": "user", "content": "...", "created_at": "..."},
    {"role": "assistant", "content": "...", "created_at": "..."}
  ]
}

# Frontend loads conversation history and continues from checkpoint
```

### Exit Session (US-2.4)

```bash
PATCH /api/v1/tutor/sessions/{id}
{
  "status": "completed"  # or "abandoned"
}

Response:
{
  "session_id": "uuid",
  "status": "completed",
  "completed_at": "2025-11-29T10:30:00Z"
}
```

---

## 📚 References

- Issue #73: [GitHub Issue](https://github.com/ArieGoldkin/SkillForge/issues/73)
- LangGraph StateGraph: https://langchain-ai.github.io/langgraph/
- Reference Implementation: `backend/app/workflows/graph_builder.py`
- Reference Implementation: `backend/app/workflows/analysis.py`
- Socratic Method: https://en.wikipedia.org/wiki/Socratic_method

---

**Last Updated:** November 29, 2025  
**Status:** Planning Complete - Ready for Implementation
