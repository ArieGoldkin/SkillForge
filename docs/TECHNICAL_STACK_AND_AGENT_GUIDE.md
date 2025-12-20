# Health Coach Agent System - Technical Implementation Guide

> **Purpose**: Complete blueprint for building a multi-agent Health Coach system using LangGraph, FastAPI, and React.
> **Based on**: SkillForge architecture patterns (production-tested multi-agent content analysis system)
> **Target**: Claude Code AI agents building similar systems

---

## Executive Summary

This guide provides everything needed to build an intelligent Health Coach agent system that:
- Analyzes user health data, symptoms, and goals
- Routes to specialized health agents (Nutrition, Exercise, Sleep, etc.)
- Synthesizes personalized health plans
- Streams real-time progress to users

**Architecture**: LangGraph StateGraph with supervisor-worker pattern, PostgreSQL + pgvector for data/embeddings, React 19 frontend with SSE streaming.

---

## 1. Technology Stack

### Backend
| Component | Technology | Purpose |
|-----------|------------|---------|
| Runtime | Python 3.11+ | Core language |
| API Framework | FastAPI | Async REST API |
| Agent Orchestration | **LangGraph 1.0** | Multi-agent workflow engine |
| LLM Abstraction | LangChain | Provider-agnostic LLM calls |
| Database | PostgreSQL 15+ | Primary data store |
| Vector Search | pgvector | Semantic search for personalization |
| Embeddings | OpenAI text-embedding-3-small | 1536-dim vectors |
| LLM | OpenAI GPT-4 / Claude | Agent reasoning |
| Observability | Langfuse | Tracing & debugging |
| Package Mgmt | Poetry | Dependencies |

### Frontend
| Component | Technology | Purpose |
|-----------|------------|---------|
| Framework | React 19 | UI framework |
| Language | TypeScript 5.x | Type safety |
| Routing | TanStack Router | File-based routing |
| Server State | React Query | API caching |
| Client State | Zustand | Lightweight state |
| UI Components | Radix UI + shadcn/ui | Accessible components |
| Styling | TailwindCSS | Utility-first CSS |
| Real-time | Server-Sent Events (SSE) | Progress streaming |

---

## 2. System Architecture

### 2.1 High-Level Flow

```
┌─────────────────────────────────────────────────────────────────┐
│                  Health Coach Agent System                       │
├─────────────────────────────────────────────────────────────────┤
│                                                                   │
│  [User Input] ───► INTAKE ───┬───────────────────┬               │
│   - Symptoms                 │                   │               │
│   - Health goals             ▼                   ▼               │
│   - Biometrics          TRIAGE            DATA_ANALYZER          │
│   - Medications             │                    │               │
│                             │                    │               │
│                        ▼    ▼    ▼    ▼         │               │
│                 ┌─────────────────────────┐      │               │
│                 │   SPECIALIST AGENTS     │      │               │
│                 │   (Parallel Execution)  │      │               │
│                 │                         │      │               │
│                 │  • Nutrition Coach      │      │               │
│                 │  • Exercise Planner     │      │               │
│                 │  • Sleep Optimizer      │      │               │
│                 │  • Stress Manager       │      │               │
│                 │  • Symptom Checker      │      │               │
│                 │  • Medication Reviewer  │      │               │
│                 └─────────────────────────┘      │               │
│                             │                    │               │
│                             └──────┬─────────────┘               │
│                                    ▼                             │
│                             SAFETY_CHECK                         │
│                                    │                             │
│                                    ▼                             │
│                             SYNTHESIZER                          │
│                                    │                             │
│                                    ▼                             │
│                          PLAN_GENERATOR                          │
│                                    │                             │
│                                    ▼                             │
│                    [Personalized Health Plan]                    │
│                                                                   │
└─────────────────────────────────────────────────────────────────┘
```

### 2.2 Project Structure

```
health-coach/
├── backend/
│   ├── app/
│   │   ├── main.py                    # FastAPI entry point
│   │   ├── core/
│   │   │   ├── config.py              # Environment settings
│   │   │   ├── model_factory.py       # LLM initialization
│   │   │   └── langfuse_config.py    # Tracing setup
│   │   ├── workflows/
│   │   │   ├── graph_builder.py       # LangGraph workflow
│   │   │   ├── state.py               # State TypedDict
│   │   │   ├── nodes/
│   │   │   │   ├── intake.py          # User data processing
│   │   │   │   ├── triage.py          # Supervisor routing
│   │   │   │   ├── safety_check.py    # Medical safety validation
│   │   │   │   ├── synthesizer.py     # Combine agent findings
│   │   │   │   └── plan_generator.py  # Generate health plan
│   │   │   └── agents/
│   │   │       ├── base.py            # Agent utilities
│   │   │       ├── nutrition_coach.py
│   │   │       ├── exercise_planner.py
│   │   │       ├── sleep_optimizer.py
│   │   │       ├── stress_manager.py
│   │   │       ├── symptom_checker.py
│   │   │       └── medication_reviewer.py
│   │   ├── models/
│   │   │   ├── user_profile.py        # User data model
│   │   │   ├── health_plan.py         # Generated plans
│   │   │   └── health_memory.py       # RAG memory for context
│   │   ├── services/
│   │   │   ├── embeddings.py          # Vector generation
│   │   │   └── sse_helpers.py         # SSE streaming
│   │   └── api/v1/
│   │       ├── health.py              # Health plan endpoints
│   │       └── users.py               # User management
│   ├── alembic/                       # Database migrations
│   └── pyproject.toml
│
├── frontend/
│   ├── src/
│   │   ├── features/
│   │   │   ├── intake/                # Health questionnaire
│   │   │   ├── progress/              # Real-time analysis view
│   │   │   ├── plan/                  # Health plan display
│   │   │   └── history/               # Past plans
│   │   ├── hooks/
│   │   │   └── useSSE.ts              # SSE connection hook
│   │   ├── stores/
│   │   │   └── sseStore.ts            # SSE state
│   │   └── services/
│   │       └── api.service.ts         # API client
│   └── package.json
│
└── docker-compose.yml
```

---

## 3. Backend Implementation

### 3.1 State Definition

```python
# backend/app/workflows/state.py
from typing import TypedDict, Annotated
import operator

class HealthCoachState(TypedDict, total=False):
    """Central state passed through the LangGraph workflow."""

    # === User Identity ===
    session_id: str
    user_id: str

    # === User Profile ===
    age: int
    gender: str
    health_goals: list[str]           # ["weight_loss", "better_sleep", "stress_reduction"]
    medical_conditions: list[str]     # ["diabetes_type_2", "hypertension"]
    medications: list[str]            # ["metformin", "lisinopril"]
    allergies: list[str]              # ["peanuts", "penicillin"]
    dietary_restrictions: list[str]   # ["vegetarian", "gluten_free"]

    # === Input Data ===
    symptoms: list[str]               # ["fatigue", "headache", "poor_sleep"]
    symptom_duration: str             # "3_days", "1_week", "chronic"
    biometrics: dict                  # {"weight_kg": 80, "blood_pressure": "130/85"}
    activity_log: list[dict]          # Recent exercise data
    sleep_data: dict                  # Sleep tracker data
    stress_level: int                 # 1-10 scale

    # === Triage Decision ===
    triage_decision: dict             # {urgency, specialists_needed, reasoning}

    # === Agent Findings (REDUCER PATTERN) ===
    # operator.add automatically merges parallel agent outputs
    specialist_findings: Annotated[list[dict], operator.add]

    # === Safety Check ===
    safety_check: dict                # {is_safe, red_flags, requires_human_review}

    # === Output ===
    synthesized_insights: dict
    health_plan: dict
    recommendations: list[dict]
    follow_up_schedule: dict
```

**Key Pattern**: `Annotated[list[dict], operator.add]` - This reducer pattern allows parallel agents to each return `{"specialist_findings": [their_result]}` and LangGraph automatically concatenates them.

### 3.2 LangGraph Workflow Builder

```python
# backend/app/workflows/graph_builder.py
from langgraph.graph import StateGraph, START, END
from langgraph.types import Send

from app.workflows.state import HealthCoachState
from app.workflows.nodes.intake import intake_node
from app.workflows.nodes.triage import triage_node, route_to_specialists
from app.workflows.nodes.safety_check import safety_check_node
from app.workflows.nodes.synthesizer import synthesizer_node
from app.workflows.nodes.plan_generator import plan_generator_node
from app.workflows.agents.nutrition_coach import nutrition_coach_node
from app.workflows.agents.exercise_planner import exercise_planner_node
from app.workflows.agents.sleep_optimizer import sleep_optimizer_node
from app.workflows.agents.stress_manager import stress_manager_node
from app.workflows.agents.symptom_checker import symptom_checker_node
from app.workflows.agents.medication_reviewer import medication_reviewer_node


def build_health_coach_graph() -> StateGraph:
    """Build the Health Coach LangGraph workflow."""

    graph = StateGraph(HealthCoachState)

    # ==================== NODES ====================

    # Stage 1: Intake & Triage (parallel)
    graph.add_node("intake", intake_node)
    graph.add_node("triage", triage_node)

    # Stage 2: Specialist Agents (dynamically routed)
    graph.add_node("nutrition_coach", nutrition_coach_node)
    graph.add_node("exercise_planner", exercise_planner_node)
    graph.add_node("sleep_optimizer", sleep_optimizer_node)
    graph.add_node("stress_manager", stress_manager_node)
    graph.add_node("symptom_checker", symptom_checker_node)
    graph.add_node("medication_reviewer", medication_reviewer_node)

    # Stage 3: Safety & Synthesis
    graph.add_node("safety_check", safety_check_node)
    graph.add_node("synthesizer", synthesizer_node)

    # Stage 4: Plan Generation
    graph.add_node("plan_generator", plan_generator_node)

    # ==================== EDGES ====================

    # Entry point
    graph.add_edge(START, "intake")
    graph.add_edge("intake", "triage")

    # Triage routes to specialists dynamically using Send API
    graph.add_conditional_edges(
        "triage",
        route_to_specialists,  # Returns list[Send] for parallel execution
        [
            "nutrition_coach",
            "exercise_planner",
            "sleep_optimizer",
            "stress_manager",
            "symptom_checker",
            "medication_reviewer",
        ]
    )

    # All specialists converge to safety check
    for agent in [
        "nutrition_coach", "exercise_planner", "sleep_optimizer",
        "stress_manager", "symptom_checker", "medication_reviewer"
    ]:
        graph.add_edge(agent, "safety_check")

    # Safety → Synthesis → Plan → End
    graph.add_edge("safety_check", "synthesizer")
    graph.add_edge("synthesizer", "plan_generator")
    graph.add_edge("plan_generator", END)

    return graph


def compile_health_coach_workflow(checkpointer=None):
    """Compile the workflow with optional checkpointing."""
    graph = build_health_coach_graph()

    return graph.compile(
        checkpointer=checkpointer,  # PostgresSaver for persistence
        interrupt_before=["safety_check"],  # Optional human-in-the-loop
    )
```

### 3.3 Triage Supervisor (Agent Routing)

```python
# backend/app/workflows/nodes/triage.py
from pydantic import BaseModel, Field
from langgraph.types import Send

from app.core.model_factory import get_chat_model
from app.workflows.state import HealthCoachState


class TriageResult(BaseModel):
    """Structured output for triage decisions."""
    urgency: str = Field(
        description="Urgency level: 'routine', 'elevated', 'urgent', 'emergency'"
    )
    specialists_needed: list[str] = Field(
        description="List of specialist agents to invoke"
    )
    reasoning: str = Field(
        description="Brief explanation of routing decision"
    )
    red_flags: list[str] = Field(
        default=[],
        description="Symptoms requiring immediate medical attention"
    )


TRIAGE_PROMPT = """You are a medical triage AI assistant. Your role is to:
1. Assess the urgency of the user's health concerns
2. Determine which specialist agents should be consulted
3. Identify any red flags requiring human medical review

Available specialists:
- nutrition_coach: Diet, meal planning, supplements, hydration
- exercise_planner: Fitness routines, activity recommendations
- sleep_optimizer: Sleep quality, sleep hygiene, circadian rhythm
- stress_manager: Mental wellness, relaxation techniques, work-life balance
- symptom_checker: Symptom analysis, potential causes, when to see a doctor
- medication_reviewer: Drug interactions, side effects, timing

IMPORTANT: Always include symptom_checker if any symptoms are reported.
IMPORTANT: Always include medication_reviewer if medications are listed.

Urgency levels:
- routine: General wellness, no concerning symptoms
- elevated: Mild symptoms, multiple health goals
- urgent: Concerning symptoms, needs prompt attention
- emergency: Severe symptoms, recommend immediate medical care

Red flags (always escalate):
- Chest pain, difficulty breathing, sudden severe headache
- Signs of stroke (FAST: Face drooping, Arm weakness, Speech difficulty, Time to call 911)
- Severe allergic reactions, uncontrolled bleeding
- Suicidal thoughts or self-harm ideation
"""


async def triage_node(state: HealthCoachState) -> dict:
    """Assess urgency and determine which specialists to consult."""

    model = get_chat_model().with_structured_output(TriageResult)

    user_context = f"""
User Profile:
- Age: {state.get('age', 'Unknown')}
- Health Goals: {', '.join(state.get('health_goals', []))}
- Medical Conditions: {', '.join(state.get('medical_conditions', []))}
- Medications: {', '.join(state.get('medications', []))}

Current Concerns:
- Symptoms: {', '.join(state.get('symptoms', []))}
- Symptom Duration: {state.get('symptom_duration', 'Unknown')}
- Stress Level: {state.get('stress_level', 'Unknown')}/10

Biometrics: {state.get('biometrics', {})}
"""

    result = await model.ainvoke([
        {"role": "system", "content": TRIAGE_PROMPT},
        {"role": "user", "content": user_context}
    ])

    return {"triage_decision": result.model_dump()}


async def route_to_specialists(state: HealthCoachState) -> list[Send]:
    """Route to selected specialists using LangGraph Send API for parallelism."""

    triage = state.get("triage_decision", {})
    specialists = triage.get("specialists_needed", [])

    # Emergency handling - skip to safety check
    if triage.get("urgency") == "emergency":
        return [Send("safety_check", state)]

    # Build Send objects for parallel execution
    sends = []
    for specialist in specialists:
        # Each agent receives the full state
        sends.append(Send(specialist, state))

    return sends
```

### 3.4 Specialist Agent Example

```python
# backend/app/workflows/agents/nutrition_coach.py
from pydantic import BaseModel, Field
from langchain_core.messages import SystemMessage, HumanMessage

from app.core.model_factory import get_chat_model
from app.workflows.state import HealthCoachState


class NutritionPlan(BaseModel):
    """Structured nutrition recommendations."""
    daily_calories: int = Field(description="Recommended daily calorie intake")
    macros: dict = Field(
        description="Macronutrient breakdown: {protein_g, carbs_g, fat_g}"
    )
    meal_timing: dict = Field(
        description="Recommended meal schedule: {breakfast, lunch, dinner, snacks}"
    )
    foods_to_emphasize: list[str] = Field(
        description="Foods to include more of"
    )
    foods_to_limit: list[str] = Field(
        description="Foods to reduce or avoid"
    )
    hydration_goal_oz: int = Field(
        description="Daily water intake goal in ounces"
    )
    supplements: list[str] = Field(
        default=[],
        description="Recommended supplements (if any)"
    )
    special_considerations: str = Field(
        description="Notes based on conditions/medications"
    )
    reasoning: str = Field(
        description="Explanation for recommendations"
    )


NUTRITION_COACH_PROMPT = """You are an expert nutrition coach AI. Provide personalized
dietary recommendations based on the user's health profile.

Consider:
- Health goals (weight loss, muscle gain, energy, etc.)
- Medical conditions (adjust for diabetes, hypertension, etc.)
- Medications (watch for food-drug interactions)
- Dietary restrictions and allergies
- Activity level and biometrics

Be specific with recommendations. Avoid generic advice.
Always explain WHY you're making each recommendation.

IMPORTANT: If the user has medical conditions or takes medications,
note any relevant food-drug or food-condition interactions.
"""


async def nutrition_coach_node(state: HealthCoachState) -> dict:
    """Generate personalized nutrition recommendations."""

    model = get_chat_model().with_structured_output(NutritionPlan)

    user_context = f"""
User Profile:
- Age: {state.get('age')} | Gender: {state.get('gender')}
- Health Goals: {state.get('health_goals')}
- Medical Conditions: {state.get('medical_conditions')}
- Medications: {state.get('medications')}
- Allergies: {state.get('allergies')}
- Dietary Restrictions: {state.get('dietary_restrictions')}

Biometrics:
{state.get('biometrics')}

Activity Level: Based on {state.get('activity_log', 'no data')}
Stress Level: {state.get('stress_level')}/10
"""

    result = await model.ainvoke([
        SystemMessage(content=NUTRITION_COACH_PROMPT),
        HumanMessage(content=user_context)
    ])

    # Return as list for reducer pattern
    return {
        "specialist_findings": [{
            "agent": "nutrition_coach",
            "findings": result.model_dump(),
            "confidence": 0.85
        }]
    }
```

### 3.5 Safety Check Node

```python
# backend/app/workflows/nodes/safety_check.py
from pydantic import BaseModel, Field

from app.core.model_factory import get_chat_model
from app.workflows.state import HealthCoachState


class SafetyCheckResult(BaseModel):
    """Safety validation result."""
    is_safe: bool = Field(
        description="Whether recommendations are safe to provide"
    )
    requires_human_review: bool = Field(
        description="Whether a human medical professional should review"
    )
    red_flags: list[str] = Field(
        default=[],
        description="Any concerning findings"
    )
    modifications_needed: list[str] = Field(
        default=[],
        description="Recommended changes to agent outputs"
    )
    disclaimer_level: str = Field(
        description="'standard', 'enhanced', or 'medical_referral'"
    )


SAFETY_CHECK_PROMPT = """You are a medical safety reviewer. Your job is to:

1. Review all specialist agent recommendations
2. Check for dangerous advice or contraindications
3. Identify any red flags that require human medical review
4. Ensure recommendations are appropriate given medications/conditions

Red flags requiring human review:
- Recommendations that conflict with known medications
- Advice that could worsen medical conditions
- Exercise recommendations unsafe for the user's health status
- Dietary advice that could cause dangerous blood sugar changes
- Any mention of serious symptoms

ALWAYS err on the side of caution. When in doubt, flag for human review.
"""


async def safety_check_node(state: HealthCoachState) -> dict:
    """Validate all recommendations for safety."""

    model = get_chat_model().with_structured_output(SafetyCheckResult)

    # Compile all specialist findings
    findings_summary = "\n\n".join([
        f"**{f['agent']}**:\n{f['findings']}"
        for f in state.get("specialist_findings", [])
    ])

    context = f"""
User Medical Context:
- Conditions: {state.get('medical_conditions')}
- Medications: {state.get('medications')}
- Allergies: {state.get('allergies')}

Triage Assessment:
{state.get('triage_decision')}

Specialist Recommendations to Review:
{findings_summary}
"""

    result = await model.ainvoke([
        {"role": "system", "content": SAFETY_CHECK_PROMPT},
        {"role": "user", "content": context}
    ])

    return {"safety_check": result.model_dump()}
```

### 3.6 Database Models

```python
# backend/app/models/user_profile.py
from sqlalchemy import Column, String, Integer, DateTime, ForeignKey, Text
from sqlalchemy.dialects.postgresql import UUID, JSONB
from pgvector.sqlalchemy import Vector
import uuid

from app.db.base import Base


class UserProfile(Base):
    __tablename__ = "user_profiles"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String(255), unique=True, index=True)

    # Demographics
    age = Column(Integer)
    gender = Column(String(20))

    # Health data (stored as JSONB for flexibility)
    health_goals = Column(JSONB, default=[])
    medical_conditions = Column(JSONB, default=[])
    medications = Column(JSONB, default=[])
    allergies = Column(JSONB, default=[])
    dietary_restrictions = Column(JSONB, default=[])

    # Embedding for personalized recommendations
    profile_embedding = Column(Vector(1536))

    created_at = Column(DateTime, server_default="now()")
    updated_at = Column(DateTime, onupdate="now()")


class HealthPlan(Base):
    __tablename__ = "health_plans"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("user_profiles.id"))
    session_id = Column(String(50), index=True)

    # Plan content
    plan_type = Column(String(20))  # daily, weekly, monthly
    specialist_findings = Column(JSONB)  # Raw agent outputs
    synthesized_plan = Column(JSONB)     # Final plan
    recommendations = Column(JSONB)

    # Safety
    safety_check = Column(JSONB)
    disclaimer = Column(Text)

    # Metadata
    urgency_level = Column(String(20))
    created_at = Column(DateTime, server_default="now()")


class HealthMemory(Base):
    """RAG memory for personalized context."""
    __tablename__ = "health_memory"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("user_profiles.id"))

    memory_type = Column(String(50))  # past_plan, feedback, preference
    content = Column(Text)
    embedding = Column(Vector(1536))  # For semantic retrieval

    relevance_score = Column(Integer, default=0)  # Updated based on usage
    created_at = Column(DateTime, server_default="now()")
```

### 3.7 API Endpoints

```python
# backend/app/api/v1/health.py
from fastapi import APIRouter, BackgroundTasks
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

router = APIRouter(prefix="/v1/health", tags=["health"])


class HealthAssessmentRequest(BaseModel):
    user_id: str | None = None
    health_goals: list[str]
    symptoms: list[str] = []
    symptom_duration: str | None = None
    biometrics: dict = {}
    stress_level: int | None = None


class HealthAssessmentResponse(BaseModel):
    session_id: str
    sse_endpoint: str
    status: str


@router.post("/assess", response_model=HealthAssessmentResponse)
async def create_health_assessment(
    request: HealthAssessmentRequest,
    background_tasks: BackgroundTasks
):
    """Start a new health assessment workflow."""
    import uuid

    session_id = str(uuid.uuid4())

    # Start workflow in background
    background_tasks.add_task(
        run_health_workflow,
        session_id=session_id,
        request=request
    )

    return HealthAssessmentResponse(
        session_id=session_id,
        sse_endpoint=f"/v1/health/{session_id}/stream",
        status="processing"
    )


@router.get("/{session_id}/stream")
async def stream_progress(session_id: str):
    """Stream real-time progress via SSE."""
    return StreamingResponse(
        generate_sse_events(session_id),
        media_type="text/event-stream"
    )


@router.get("/{session_id}/plan")
async def get_health_plan(session_id: str):
    """Get the generated health plan."""
    # Fetch from database
    pass
```

---

## 4. Frontend Implementation

### 4.1 SSE Store (Zustand)

```typescript
// frontend/src/stores/sseStore.ts
import { create } from 'zustand';

interface SSEEvent {
  type: 'progress' | 'complete' | 'error';
  stage?: string;
  status?: string;
  data?: unknown;
  timestamp: string;
}

interface SSEStore {
  events: SSEEvent[];
  isConnected: boolean;
  isComplete: boolean;
  error: string | null;
  activeSessionId: string | null;

  connect: (sessionId: string) => void;
  disconnect: () => void;
  reset: () => void;
}

export const useSSEStore = create<SSEStore>((set, get) => ({
  events: [],
  isConnected: false,
  isComplete: false,
  error: null,
  activeSessionId: null,

  connect: (sessionId: string) => {
    const state = get();
    if (state.activeSessionId === sessionId && state.isConnected) return;

    const eventSource = new EventSource(
      `${import.meta.env.VITE_API_URL}/v1/health/${sessionId}/stream`
    );

    eventSource.onopen = () => {
      set({ isConnected: true, activeSessionId: sessionId, error: null });
    };

    eventSource.addEventListener('progress', (e) => {
      const data = JSON.parse(e.data);
      set((state) => ({
        events: [...state.events, { ...data, type: 'progress' }]
      }));
    });

    eventSource.addEventListener('complete', (e) => {
      const data = JSON.parse(e.data);
      set({
        isComplete: true,
        events: [...get().events, { ...data, type: 'complete' }]
      });
      eventSource.close();
    });

    eventSource.addEventListener('error', (e) => {
      set({ error: 'Connection error', isConnected: false });
    });

    // Store reference for cleanup
    (window as any).__healthSSE = eventSource;
  },

  disconnect: () => {
    const es = (window as any).__healthSSE;
    if (es) es.close();
    set({ isConnected: false, activeSessionId: null });
  },

  reset: () => {
    set({
      events: [],
      isConnected: false,
      isComplete: false,
      error: null,
      activeSessionId: null
    });
  }
}));
```

### 4.2 Progress Display Component

```tsx
// frontend/src/features/progress/HealthProgress.tsx
import { useSSEStore } from '@/stores/sseStore';

const STAGES = [
  { id: 'intake', label: 'Processing Your Information' },
  { id: 'triage', label: 'Assessing Your Needs' },
  { id: 'specialists', label: 'Consulting Specialists' },
  { id: 'safety_check', label: 'Safety Review' },
  { id: 'synthesis', label: 'Creating Your Plan' },
];

export function HealthProgress({ sessionId }: { sessionId: string }) {
  const { events, isComplete, error, connect } = useSSEStore();

  useEffect(() => {
    connect(sessionId);
    return () => useSSEStore.getState().disconnect();
  }, [sessionId]);

  const currentStage = events[events.length - 1]?.stage || 'intake';

  if (error) {
    return <ErrorDisplay message={error} />;
  }

  if (isComplete) {
    return <PlanReady sessionId={sessionId} />;
  }

  return (
    <div className="space-y-4">
      {STAGES.map((stage) => (
        <StageItem
          key={stage.id}
          label={stage.label}
          status={getStageStatus(stage.id, currentStage, events)}
        />
      ))}

      <ActivityFeed events={events} />
    </div>
  );
}
```

---

## 5. Key Patterns to Implement

### 5.1 Pattern Summary

| Pattern | Purpose | Implementation |
|---------|---------|----------------|
| **State Reducer** | Merge parallel agent outputs | `Annotated[list, operator.add]` |
| **Supervisor Routing** | Dynamic agent selection | `route_to_specialists() → list[Send]` |
| **Structured Output** | Reliable JSON responses | `model.with_structured_output(Schema)` |
| **SSE Streaming** | Real-time progress | FastAPI `StreamingResponse` |
| **Safety Gate** | Medical safety validation | Mandatory `safety_check` node |
| **Checkpointing** | Workflow persistence | `PostgresSaver` checkpointer |

### 5.2 Health Domain Considerations

```python
# ALWAYS include these safety measures:

# 1. Mandatory disclaimer
HEALTH_DISCLAIMER = """
IMPORTANT: This AI-generated health information is for educational purposes only.
It is not a substitute for professional medical advice, diagnosis, or treatment.
Always consult with a qualified healthcare provider before making health decisions.
If you are experiencing a medical emergency, call 911 immediately.
"""

# 2. Red flag detection
RED_FLAGS = [
    "chest pain", "difficulty breathing", "severe headache",
    "stroke symptoms", "suicidal thoughts", "severe bleeding",
    "allergic reaction", "loss of consciousness"
]

# 3. Medication interaction checking
# 4. Condition-specific contraindications
# 5. Human-in-the-loop for high-risk recommendations
```

---

## 6. Getting Started Commands

```bash
# Backend Setup
cd backend
poetry install
poetry run alembic upgrade head  # Run migrations
poetry run uvicorn app.main:app --reload --port 8500

# Frontend Setup
cd frontend
npm install
npm run dev  # Starts on port 5173

# Database (Docker)
docker compose up -d postgres

# Environment Variables (.env)
DATABASE_URL=postgresql://user:pass@localhost:5432/health_coach
OPENAI_API_KEY=sk-...
LANGCHAIN_API_KEY=lsv2_...  # Langfuse
LANGCHAIN_PROJECT=health-coach
LANGCHAIN_TRACING_V2=true
```

---

## 7. Testing Strategy

```python
# tests/test_triage.py
import pytest
from app.workflows.nodes.triage import triage_node

@pytest.mark.asyncio
async def test_triage_routes_to_specialists():
    state = {
        "health_goals": ["weight_loss"],
        "symptoms": ["fatigue", "headache"],
        "medications": ["metformin"],
    }

    result = await triage_node(state)

    assert "triage_decision" in result
    assert "symptom_checker" in result["triage_decision"]["specialists_needed"]
    assert "medication_reviewer" in result["triage_decision"]["specialists_needed"]


@pytest.mark.asyncio
async def test_emergency_escalation():
    state = {
        "symptoms": ["chest pain", "difficulty breathing"],
    }

    result = await triage_node(state)

    assert result["triage_decision"]["urgency"] == "emergency"
    assert len(result["triage_decision"]["red_flags"]) > 0
```

---

## Summary

This guide provides a complete blueprint for building a Health Coach agent system using:

1. **LangGraph** for multi-agent orchestration with parallel execution
2. **Supervisor pattern** for intelligent agent routing
3. **Safety-first design** with mandatory validation gates
4. **Real-time SSE streaming** for progress updates
5. **PostgreSQL + pgvector** for data and personalization

The architecture is modular - you can add/remove specialist agents, adjust the triage logic, and customize the plan generation without restructuring the entire system.

**Next Steps**:
1. Clone the SkillForge repo for reference implementation
2. Set up the basic project structure
3. Implement state and graph builder first
4. Add one specialist agent and test end-to-end
5. Gradually add more agents and safety checks
