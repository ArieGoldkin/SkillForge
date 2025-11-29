# 🏗️ SkillForge - Architecture & Workflow Diagrams

**Version:** 1.3  
**Last Updated:** December 20, 2025  
**Project:** SkillForge - Research-to-Implementation Pipeline

---

## 📖 Viewing Mermaid Diagrams

This document contains Mermaid diagrams that require a compatible viewer to render properly.

### ✅ Recommended Viewers

1. **VS Code**: Install the "Markdown Preview Mermaid Support" extension
   - Extension ID: `bierner.markdown-mermaid`
   - Press `Cmd+Shift+V` (Mac) or `Ctrl+Shift+V` (Windows/Linux) to preview

2. **GitHub**: Diagrams render automatically when viewing on GitHub.com

3. **Online Viewer**: Copy diagram code to [Mermaid Live Editor](https://mermaid.live/)

4. **Cursor/VS Code**: Use the built-in markdown preview (may require extension)

### 🔧 Quick Fix

If diagrams don't render:
- Open the file in VS Code with the Mermaid extension installed
- Or view on GitHub.com
- Or copy the ```mermaid code blocks to [mermaid.live](https://mermaid.live/)

---

## 📋 Table of Contents

1. [Project Structure](#project-structure)
2. [System Architecture](#system-architecture)
3. [Backend Workflow (LangGraph v1.0)](#backend-workflow-langgraph-v10)
4. [Integration Flow](#integration-flow)
5. [Sprint 1 Workflow](#sprint-1-workflow)
6. [Sprint 2 Workflow](#sprint-2-workflow)
7. [Component Relationships](#component-relationships)
8. [Data Flow](#data-flow)
9. [Deployment Architecture](#deployment-architecture)
10. [Prompt Templating](#prompt-templating)

---

## Project Structure

```mermaid
graph TB
    subgraph "SkillForge Project"
        Root[SkillForge Root]
        
        subgraph "Backend [Yonatan]"
            Backend[backend/]
            BackendApp[app/]
            BackendAPI[api/v1/]
            BackendCore[core/]
            BackendDB[db/]
            BackendModels[models/]
            BackendSchemas[schemas/]
            BackendServices[services/]
            BackendWorkflows[workflows/]
            BackendAlembic[alembic/]
            BackendTests[tests/]
            BackendPyProject[pyproject.toml]
            
            Backend --> BackendApp
            BackendApp --> BackendAPI
            BackendApp --> BackendCore
            BackendApp --> BackendDB
            BackendApp --> BackendModels
            BackendApp --> BackendSchemas
            BackendApp --> BackendServices
            BackendApp --> BackendWorkflows
            Backend --> BackendAlembic
            Backend --> BackendTests
            Backend --> BackendPyProject
        end
        
        subgraph "Frontend [Arie]"
            Frontend[frontend/]
            FrontendSrc[src/]
            FrontendComponents[components/]
            FrontendHooks[hooks/]
            FrontendPages[pages/]
            FrontendTypes[types/]
            FrontendPackage[package.json]
            
            Frontend --> FrontendSrc
            FrontendSrc --> FrontendComponents
            FrontendSrc --> FrontendHooks
            FrontendSrc --> FrontendPages
            FrontendSrc --> FrontendTypes
            Frontend --> FrontendPackage
        end
        
        subgraph "Documentation"
            Docs[docs/]
            DocsRoadmap[ROADMAP.md]
            DocsParallel[ROADMAP_PARALLEL.md]
            DocsBackend[YONATAN_BACKEND_TASKS.md]
            DocsFrontend[ARIE_FRONTEND_TASKS.md]
            DocsIntegration[INTEGRATION_POINTS.md]
            DocsStories[USER_STORIES.md]
            
            Docs --> DocsRoadmap
            Docs --> DocsParallel
            Docs --> DocsBackend
            Docs --> DocsFrontend
            Docs --> DocsIntegration
            Docs --> DocsStories
        end
        
        Root --> Backend
        Root --> Frontend
        Root --> Docs
    end
    
    style Backend fill:#e1f5ff,stroke:#0077cc
    style Frontend fill:#ffe1f5,stroke:#cc0077
    style Docs fill:#f0f0f0,stroke:#666
```

---

## System Architecture

```mermaid
graph TB
    subgraph "Client Layer"
        User[👤 User]
        Browser[🌐 Browser]
        User --> Browser
    end
    
    subgraph "Frontend [Arie]"
        React[React 19 App]
        Router[React Router]
        Query[TanStack Query]
        SSE[useSSE Hook]
        Components[UI Components]
        
        Browser --> React
        React --> Router
        React --> Query
        React --> SSE
        React --> Components
    end
    
    subgraph "Backend API [Yonatan]"
        FastAPI[FastAPI Server]
        Endpoints[API Endpoints]
        SSEEndpoint[SSE Endpoint]
        Repos[Repository Layer]
        
        React -->|HTTP/REST| FastAPI
        React -->|SSE Stream| SSEEndpoint
        FastAPI --> Endpoints
        Endpoints --> Repos
        SSEEndpoint --> Repos
    end
    
    subgraph "Business Logic [Yonatan]"
        Services[Services]
        Workflows[LangGraph Workflows]
        Agents[LangChain Agents<br/>Async with Timeouts]
        
        Repos --> Services
        Services --> Workflows
        Workflows --> Agents
    end
    
    subgraph "Data Layer [Yonatan]"
        PostgreSQL[(PostgreSQL)]
        PGVector[(PGVector)]
        Alembic[Alembic Migrations]
        
        Repos --> PostgreSQL
        Services --> PGVector
        Alembic --> PostgreSQL
    end
    
    subgraph "External Services"
        JinaAI[Jina AI Reader]
        OpenAI[OpenAI API]
        
        Services --> JinaAI
        Agents --> OpenAI
    end
    
    style React fill:#ffe1f5,stroke:#cc0077
    style FastAPI fill:#e1f5ff,stroke:#0077cc
    style PostgreSQL fill:#336791,stroke:#fff,color:#fff
    style Workflows fill:#e1f5ff,stroke:#0077cc
```

---

## Backend Workflow (LangGraph v1.0 StateGraph)

```mermaid
graph TB
    Start([User Submits URL])
    
    subgraph "FastAPI Endpoint"
        Validate[Validate URL]
        CreateRecord[Create Analysis Record]
        ReturnID[Return analysis_id]
    end
    
    subgraph "LangGraph v1.0 StateGraph"
        EntryPoint[StateGraph Entry: extract]
        
        subgraph "Workflow Nodes"
            Extract[extract node]
            
            subgraph "Parallel Execution (Fan-Out)"
                Embed[embedding node]
                Supervisor[supervisor node]
            end
            
            Router[route_to_agents<br/>Send API]
            
            subgraph "Agent Nodes (Native LangGraph Parallel via Send API)"
                TechComp[tech_comparator node]
                Security[security_auditor node]
                ImplPlan[implementation_planner node]
                Perf[performance_analyst node]
                CodeQual[code_quality_critic node]
                Trends[trend_validator node]
                Deps[dependency_mapper node]
                IntFeas[integration_feasibility node]
            end
            
            Aggregate[aggregate node]
        end
    end
    
    subgraph "SSE Events"
        SSEProgress[progress events]
        SSEComplete[complete event]
        SSEError[error events]
    end
    
    subgraph "Database"
        SaveProgress[Save Progress]
        SaveFindings[Save Agent Findings]
        SaveArtifact[Save Artifact]
    end
    
    Start --> Validate
    Validate --> CreateRecord
    CreateRecord --> ReturnID
    ReturnID --> EntryPoint
    
    EntryPoint --> Extract
    Extract -->|"SSE: extraction running"| SSEProgress
    Extract --> Embed
    Extract --> Supervisor
    
    Embed -->|"SSE: embedding complete"| SSEProgress
    Supervisor -->|"SSE: supervisor_routing"| SSEProgress
    Embed --> Router
    Supervisor --> Router
    
    Router -->|"Send API<br/>Dynamic Routing"| TechComp
    Router -->|"Send API"| Security
    Router -->|"Send API"| ImplPlan
    Router -->|"Send API"| Perf
    Router -->|"Send API"| CodeQual
    Router -->|"Send API"| Trends
    Router -->|"Send API"| Deps
    Router -->|"Send API"| IntFeas
    
    TechComp -->|"SSE: tech_comparison"| SSEProgress
    Security -->|"SSE: security_audit"| SSEProgress
    ImplPlan -->|"SSE: implementation_planning"| SSEProgress
    Perf -->|"SSE: performance_audit"| SSEProgress
    CodeQual -->|"SSE: code_quality"| SSEProgress
    Trends -->|"SSE: trends_analysis"| SSEProgress
    Deps -->|"SSE: dependencies"| SSEProgress
    IntFeas -->|"SSE: integration_feasibility"| SSEProgress
    
    TechComp -->|"Fan-In<br/>State Reducer"| Aggregate
    Security --> Aggregate
    ImplPlan --> Aggregate
    Perf --> Aggregate
    CodeQual --> Aggregate
    Trends --> Aggregate
    Deps --> Aggregate
    IntFeas --> Aggregate
    
    Aggregate -->|"SSE: aggregation complete"| SSEComplete
    
    Extract --> SaveProgress
    TechComp --> SaveFindings
    Security --> SaveFindings
    ImplPlan --> SaveFindings
    Perf --> SaveFindings
    CodeQual --> SaveFindings
    Trends --> SaveFindings
    Deps --> SaveFindings
    IntFeas --> SaveFindings
    Aggregate --> SaveArtifact
    
    End([Analysis Complete])
    SSEComplete --> End
    
    style EntryPoint fill:#e1f5ff,stroke:#0077cc
    style Extract fill:#e1f5ff,stroke:#0077cc
    style Supervisor fill:#ffd700,stroke:#ff8c00
    style Router fill:#ffd700,stroke:#ff8c00
    style TechComp fill:#90ee90,stroke:#228b22
    style Security fill:#90ee90,stroke:#228b22
    style ImplPlan fill:#90ee90,stroke:#228b22
    style Perf fill:#90ee90,stroke:#228b22
    style CodeQual fill:#90ee90,stroke:#228b22
    style Trends fill:#90ee90,stroke:#228b22
    style Deps fill:#90ee90,stroke:#228b22
    style IntFeas fill:#90ee90,stroke:#228b22
    style Aggregate fill:#e1f5ff,stroke:#0077cc
    style SSEProgress fill:#ffe1f5,stroke:#cc0077
    style SSEComplete fill:#90ee90,stroke:#228b22
```

---

## Integration Flow

```mermaid
sequenceDiagram
    participant U as User
    participant F as Frontend (Arie)
    participant B as Backend API (Yonatan)
    participant W as LangGraph Workflow
    participant DB as PostgreSQL
    participant SSE as SSE Stream
    
    U->>F: Submit URL
    F->>B: POST /api/v1/analyze
    B->>DB: Create Analysis Record
    DB-->>B: analysis_id
    B-->>F: {analysis_id, status: "pending"}
    
    F->>SSE: GET /api/v1/analyze/{id}/stream
    SSE-->>F: SSE Connection Established
    
    B->>W: Start Workflow (analysis_id)
    
    W->>W: task extract_content
    W->>SSE: Emit progress extraction running
    SSE-->>F: Event: extraction running
    W->>DB: Save Progress
    W->>W: Content extracted
    
    W->>W: task generate_embedding
    W->>DB: Save Embedding
    
    W->>W: task supervisor_route
    W->>SSE: Emit progress supervisor_routing
    SSE-->>F: Event: supervisor_routing
    
    W->>W: route_to_agents (Send API)
    W->>W: Parallel agent nodes (tech_comparator, security_auditor, ...)
    W->>SSE: Emit progress tech_comparison running
    SSE-->>F: Event: tech_comparison running
    W->>DB: Save Findings
    W->>SSE: Emit progress tech_comparison complete
    SSE-->>F: Event: tech_comparison complete
    
    Note over W: ... 5 more sub-agents
    
    W->>W: task aggregate_findings
    W->>W: task generate_artifact
    W->>DB: Save Artifact
    W->>SSE: Emit "complete" (artifact_generation)
    SSE-->>F: Event: complete
    F->>U: Show "Download" button
    
    U->>F: Click Download
    F->>B: GET /api/v1/artifacts/{id}/download
    B->>DB: Fetch Artifact
    DB-->>B: Markdown Content
    B-->>F: File Download
    F->>U: Download Complete
```

---

## Sprint 1 Workflow

```mermaid
gantt
    title Sprint 1: Foundation (Week 1-2)
    dateFormat YYYY-MM-DD
    section Yonatan (Backend)
    Setup Poetry + FastAPI        :2025-11-25, 2d
    Database Schema + Migrations  :2025-11-27, 2d
    Content Extraction (Jina)    :2025-11-29, 2d
    Embedding Service             :2025-12-01, 2d
    Basic LangGraph Workflow      :2025-12-03, 2d
    section Arie (Frontend)
    Setup React 19 + Vite        :2025-11-25, 2d
    Mock API Layer               :2025-11-27, 2d
    URL Input Form               :2025-11-29, 2d
    Component Library            :2025-12-01, 2d
    Routing                      :2025-12-03, 2d
    section Integration
    API Contract Meeting         :milestone, 2025-11-27, 0d
    First E2E Test               :milestone, 2025-12-05, 0d
```

```mermaid
graph LR
    subgraph "Day 1-2: Independent"
        Y1[Yonatan: Setup]
        A1[Arie: Setup]
    end
    
    subgraph "Day 3: Integration #1"
        Meeting[API Contract Meeting]
        Contract[Lock Contract]
    end
    
    subgraph "Day 4-10: Parallel"
        Y2[Yonatan: Implement]
        A2[Arie: Build UI]
    end
    
    subgraph "Day 10: Integration #2"
        Test[E2E Test]
    end
    
    Y1 --> Meeting
    A1 --> Meeting
    Meeting --> Contract
    Contract --> Y2
    Contract --> A2
    Y2 --> Test
    A2 --> Test
    
    style Meeting fill:#ffd700,stroke:#ff8c00
    style Test fill:#90ee90,stroke:#228b22
```

---

## Sprint 2 Workflow

```mermaid
graph TB
    subgraph "Day 1: BLOCKER"
        SSE[SSE Schema Handoff]
        YonatanSSE[Yonatan provides schema]
        ArieSSE[Arie receives schema]
        YonatanSSE --> SSE
        SSE --> ArieSSE
    end
    
    subgraph "Day 2-7: Parallel"
        YonatanWork[Yonatan:<br/>- LangGraph v1.0<br/>- Supervisor<br/>- SSE Events<br/>- 3 Sub-agents]
        ArieWork[Arie:<br/>- useSSE Hook<br/>- Progress UI<br/>- Analysis Page<br/>- Loading States]
    end
    
    subgraph "Day 8: Integration #3"
        SSETest[Live SSE Testing]
        HappyPath[Happy Path Test]
        ErrorTest[Error Handling Test]
        ConnectionTest[Connection Loss Test]
        
        SSETest --> HappyPath
        SSETest --> ErrorTest
        SSETest --> ConnectionTest
    end
    
    subgraph "Day 9-10: Refinement"
        YonatanRefine[Yonatan: Fix Issues]
        ArieRefine[Arie: Polish UI]
    end
    
    SSE --> YonatanWork
    SSE --> ArieWork
    YonatanWork --> SSETest
    ArieWork --> SSETest
    SSETest --> YonatanRefine
    SSETest --> ArieRefine
    
    style SSE fill:#ff6b6b,stroke:#c92a2a
    style SSETest fill:#90ee90,stroke:#228b22
```

---

## Component Relationships

```mermaid
classDiagram
    class FastAPIEndpoint {
        +POST /api/v1/analyze
        +GET /api/v1/analyze/{id}/stream
        +GET /api/v1/artifacts/{id}/download
    }
    
    class IAnalysisRepository {
        <<interface>>
        +create(url: str) Analysis
        +get_by_id(id: UUID) Analysis
        +list_active() List[Analysis]
    }
    
    class AnalysisRepository {
        -db: AsyncSession
        +create(url: str) Analysis
        +get_by_id(id: UUID) Analysis
        +list_active() List[Analysis]
    }
    
    class AnalysisModel {
        +id: UUID
        +url: str
        +status: str
        +created_at: datetime
    }
    
    class LangGraphWorkflow {
        +entrypoint checkpointer
        +task extract_content
        +task supervisor_route
        +task run_agents
        +task generate_artifact
    }
    
    class SupervisorAgent {
        +create_agent()
        +route(content: str) List[str]
    }
    
    class SubAgent {
        +create_agent()
        +analyze(content: str) dict
    }
    
    class EventBroadcaster {
        +publish(channel: str, event: dict)
        +subscribe(channel: str) AsyncIterator
    }
    
    class SSEEndpoint {
        +stream_analysis_progress(id: UUID)
        +event_generator() AsyncIterator
    }
    
    FastAPIEndpoint --> IAnalysisRepository : depends on
    IAnalysisRepository <|.. AnalysisRepository : implements
    AnalysisRepository --> AnalysisModel : uses
    FastAPIEndpoint --> LangGraphWorkflow : invokes
    LangGraphWorkflow --> SupervisorAgent : uses
    SupervisorAgent --> SubAgent : routes to
    LangGraphWorkflow --> EventBroadcaster : emits events
    EventBroadcaster --> SSEEndpoint : streams to
    SSEEndpoint --> FastAPIEndpoint : returns
    
    style IAnalysisRepository fill:#e1f5ff,stroke:#0077cc
    style LangGraphWorkflow fill:#ffd700,stroke:#ff8c00
    style EventBroadcaster fill:#ffe1f5,stroke:#cc0077
```

---

## Data Flow

```mermaid
flowchart TD
    Start([User Input: URL])
    
    subgraph "Request Flow"
        Validate[Validate URL Format]
        DetectType[Detect Content Type]
        CreateAnalysis[Create Analysis Record]
    end
    
    subgraph "Content Extraction"
        JinaExtract[Jina AI Extract]
        YouTubeExtract[YouTube Transcript]
        GitHubExtract[GitHub Repo]
    end
    
    subgraph "Processing"
        GenerateEmbed[Generate Embedding]
        StoreEmbed[Store in PGVector]
        SupervisorDecide[Supervisor Routes]
    end
    
    subgraph "Agent Analysis"
        TechComp[Tech Comparator]
        Security[Security Auditor]
        ImplPlan[Implementation Planner]
        Perf[Performance Auditor]
        CodeQual[Code Quality]
        Trends[Trends Analyzer]
        Deps[Dependencies]
    end
    
    subgraph "Aggregation"
        Aggregate[Aggregate Findings]
        GenerateMarkdown[Generate Markdown]
        SaveArtifact[Save Artifact]
    end
    
    subgraph "Response"
        SSEStream[SSE Stream Events]
        Download[Download Endpoint]
    end
    
    Start --> Validate
    Validate --> DetectType
    DetectType --> CreateAnalysis
    
    CreateAnalysis --> JinaExtract
    CreateAnalysis --> YouTubeExtract
    CreateAnalysis --> GitHubExtract
    
    JinaExtract --> GenerateEmbed
    YouTubeExtract --> GenerateEmbed
    GitHubExtract --> GenerateEmbed
    
    GenerateEmbed --> StoreEmbed
    StoreEmbed --> SupervisorDecide
    
    SupervisorDecide --> TechComp
    SupervisorDecide --> Security
    SupervisorDecide --> ImplPlan
    SupervisorDecide --> Perf
    SupervisorDecide --> CodeQual
    SupervisorDecide --> Trends
    SupervisorDecide --> Deps
    
    TechComp --> Aggregate
    Security --> Aggregate
    ImplPlan --> Aggregate
    Perf --> Aggregate
    CodeQual --> Aggregate
    Trends --> Aggregate
    Deps --> Aggregate
    
    Aggregate --> GenerateMarkdown
    GenerateMarkdown --> SaveArtifact
    
    CreateAnalysis --> SSEStream
    JinaExtract --> SSEStream
    SupervisorDecide --> SSEStream
    TechComp --> SSEStream
    Security --> SSEStream
    SaveArtifact --> SSEStream
    
    SaveArtifact --> Download
    
    End([User Downloads Artifact])
    Download --> End
    
    style SupervisorDecide fill:#ffd700,stroke:#ff8c00
    style SSEStream fill:#ffe1f5,stroke:#cc0077
    style Download fill:#90ee90,stroke:#228b22
```

---

## Deployment Architecture

```mermaid
graph TB
    subgraph "Development"
        DevUser[Developer]
        DevFrontend[Frontend Dev Server<br/>localhost:5173]
        DevBackend[Backend Dev Server<br/>localhost:8000]
        DevDB[(PostgreSQL Dev<br/>localhost:5432)]
        DevOpenAI[OpenAI API<br/>GPT-5 Mini]
        
        DevUser --> DevFrontend
        DevFrontend --> DevBackend
        DevBackend --> DevDB
        DevBackend --> DevOpenAI
    end
    
    subgraph "Production"
        ProdUser[End Users]
        ProdCDN[Vercel<br/>Frontend (React 19)]
        ProdAPI[Railway<br/>Backend API (FastAPI)]
        ProdDB[(Supabase<br/>PostgreSQL + PGVector)]
        ProdOpenAI[OpenAI API<br/>GPT-5 Mini]
        
        ProdUser --> ProdCDN
        ProdCDN -->|SSE + REST| ProdAPI
        ProdAPI --> ProdDB
        ProdAPI --> ProdOpenAI
    end
    
    subgraph "CI/CD"
        GitHub[GitHub Repository]
        GitHubActions[GitHub Actions]
        Tests[Test Suite]
        Lint[Linting & Type Check]
        Build[Build & Deploy]
        
        GitHub --> GitHubActions
        GitHubActions --> Tests
        GitHubActions --> Lint
        Tests --> Build
        Lint --> Build
        Build --> ProdAPI
        Build --> ProdCDN
    end
    
    style DevFrontend fill:#ffe1f5,stroke:#cc0077
    style DevBackend fill:#e1f5ff,stroke:#0077cc
    style ProdCDN fill:#ffe1f5,stroke:#cc0077
    style ProdAPI fill:#e1f5ff,stroke:#0077cc
    style GitHubActions fill:#90ee90,stroke:#228b22
```

---

## Backend Pattern Architecture

```mermaid
graph TB
    subgraph "API Layer"
        Router[FastAPI Router]
        Endpoint[API Endpoint]
        Schema[Pydantic Schema]
    end
    
    subgraph "Repository Pattern"
        Interface[IRepository Interface]
        Impl[Repository Implementation]
        Model[SQLAlchemy Model]
    end
    
    subgraph "Service Layer"
        Service[Business Logic Service]
        Extraction[Content Extraction]
        Embedding[Embedding Service]
    end
    
    subgraph "Workflow Layer"
        LangGraph[LangGraph v1.0]
        EntryPoint["@entrypoint"]
        Tasks["@task functions"]
        Checkpointer[PostgreSQL Checkpointer]
    end
    
    subgraph "Agent Layer"
        Supervisor[Supervisor Agent<br/>create_agent]
        SubAgents[Sub-Agents<br/>create_agent]
        Tools[Agent Tools]
    end
    
    subgraph "Event Layer"
        Broadcaster[Event Broadcaster]
        SSE[SSE Endpoint]
        Events[Progress Events]
    end
    
    Router --> Endpoint
    Endpoint --> Schema
    Endpoint --> Interface
    Interface --> Impl
    Impl --> Model
    
    Endpoint --> Service
    Service --> Extraction
    Service --> Embedding
    
    Service --> LangGraph
    LangGraph --> EntryPoint
    EntryPoint --> Tasks
    EntryPoint --> Checkpointer
    
    Tasks --> Supervisor
    Supervisor --> SubAgents
    SubAgents --> Tools
    
    Tasks --> Broadcaster
    Broadcaster --> SSE
    Broadcaster --> Events
    
    style Interface fill:#e1f5ff,stroke:#0077cc
    style LangGraph fill:#ffd700,stroke:#ff8c00
    style Supervisor fill:#ffd700,stroke:#ff8c00
    style SSE fill:#ffe1f5,stroke:#cc0077
```

---

## Backend Architecture Patterns

This section documents the key architectural patterns and best practices used in the SkillForge backend.

### Repository Pattern

**Purpose:** Abstract database access and provide a clean interface for data operations.

**Implementation:**
- Repository interfaces define contracts for data operations
- Implementations use SQLAlchemy AsyncSession for database access
- Dependency injection via FastAPI Depends for testability

**Example:**
```python
from app.db.repositories.analysis import IAnalysisRepository, get_analysis_repository

@router.post("/analyze")
async def create_analysis(
    request: AnalyzeRequest,
    repo: IAnalysisRepository = Depends(get_analysis_repository)
) -> AnalyzeResponse:
    analysis = await repo.create(url=request.url)
    return AnalyzeResponse.from_orm(analysis)
```

**Benefits:**
- Testability: Easy to mock repositories in tests
- Maintainability: Database logic isolated from business logic
- Flexibility: Can swap implementations without changing business logic

**Status:** Pattern defined, implementation pending (Issue #41)

### Service Layer

**Purpose:** Encapsulate business logic and coordinate between repositories and external services.

**Responsibilities:**
- Business logic implementation
- External API integration (Jina Reader, OpenAI)
- Data transformation and validation
- Error handling and retry logic

**Current Services:**
- `EmbeddingService`: Generates semantic embeddings using OpenAI (text-embedding-3-small, 1536 dimensions)
- `JinaReader`: Extracts content from URLs
- `EventBroadcaster`: Pub/sub messaging for SSE events

**Pattern:**
```python
class EmbeddingService:
    """Service for generating semantic embeddings."""
    
    async def generate_embedding(self, text: str) -> EmbeddingVector:
        # Business logic here
        # Retry logic, error handling, normalization
        pass
```

### Workflow Orchestration (LangGraph v1.0)

**Purpose:** Orchestrate multi-step analysis workflows with state management and checkpointing.

**Implementation:**
- Uses LangGraph v1.0 Functional API (`@entrypoint`, `@task`)
- PostgreSQL checkpointer for persistent state (production)
- MemorySaver fallback for development
- Thread-based isolation per analysis

**Pattern:**
```python
@task
async def extract_content(url: str, analysis_id: AnalysisID) -> dict:
    """Extract content task."""
    # Task implementation
    pass

@entrypoint(checkpointer=checkpointer)
async def analysis_workflow(input_data: dict) -> dict:
    """Main workflow orchestration."""
    result = await extract_content(input_data["url"], input_data["analysis_id"])
    return result
```

**Benefits:**
- Automatic state persistence
- Workflow resumption after failures
- Clear task boundaries
- Easy to add new tasks

### SSE Event Broadcasting

**Purpose:** Provide real-time progress updates to clients during long-running workflows.

**Architecture:**
- `EventBroadcaster`: In-memory pub/sub using asyncio.Queue
- Channel-based messaging: `workflow:{analysis_id}`
- Automatic cleanup on client disconnect
- Thread-safe with asyncio.Lock

**Flow:**
1. Workflow emits events via `emit_streaming_event()`
2. Events published to broadcaster channel
3. SSE endpoint subscribes to channel
4. Events streamed to connected clients

**Pattern:**
```python
# In workflow
from app.services.sse_helpers import emit_streaming_event

await emit_streaming_event(
    "progress",
    analysis_id=analysis_id,
    stage="extraction",
    status="running",
)

# In SSE endpoint
from app.services.event_broadcaster import broadcaster

async for event in broadcaster.subscribe(f"workflow:{analysis_id}"):
    yield {"event": event["type"], "data": json.dumps(event)}
```

**Event Schema:** See [`docs/issues/040-sse-endpoint/SSE_SCHEMA.md`](../docs/issues/040-sse-endpoint/SSE_SCHEMA.md) for complete event type definitions and TypeScript types.

**Benefits:**
- Real-time user feedback
- No polling required
- Automatic connection management
- Scalable (in-memory, can be extended to Redis)

### Error Handling Strategy

**Purpose:** Provide consistent error handling across the application.

**Exception Hierarchy:**
```
SkillForgeException (base)
├── ServiceException
│   ├── EmbeddingError
│   └── JinaReaderError
├── WorkflowError
└── DatabaseError
```

**Pattern:**
- Custom exceptions inherit from `SkillForgeException`
- Service layer raises specific exceptions
- Global exception handler in FastAPI middleware
- Structured error responses with request IDs

**Implementation:**
```python
# Service raises specific exception
raise EmbeddingError("Embedding generation failed")

# Global handler catches and formats
@app.exception_handler(SkillForgeException)
async def skillforge_exception_handler(request: Request, exc: SkillForgeException):
    return JSONResponse(
        status_code=500,
        content={"error": {"code": type(exc).__name__, "message": str(exc)}}
    )
```

**Benefits:**
- Consistent error responses
- Easy error categorization
- Better debugging with exception types
- Client-friendly error messages

### Database Connection Pooling

**Purpose:** Efficiently manage database connections and prevent connection exhaustion.

**Configuration:**
- `pool_size`: 5 connections maintained
- `max_overflow`: 10 additional connections
- `pool_recycle`: 3600 seconds (1 hour)
- `pool_pre_ping`: Verify connections before use

**Pattern:**
```python
engine = create_async_engine(
    database_url,
    pool_size=DB_POOL_SIZE,
    max_overflow=DB_MAX_OVERFLOW,
    pool_recycle=DB_POOL_RECYCLE,
    pool_pre_ping=True,
)
```

**Benefits:**
- Connection reuse (performance)
- Automatic connection health checks
- Prevents connection leaks
- Handles connection failures gracefully

### Constants Management

**Purpose:** Centralize magic numbers and configuration values.

**Location:** `app/core/constants.py`

**Categories:**
- HTTP status codes
- Timeout values
- Text and message limits
- Retry configuration
- Database pool settings
- Content type constants

**Benefits:**
- Single source of truth
- Easy to update values
- Better code readability
- Type safety

### Type Aliases

**Purpose:** Improve code readability and maintainability with semantic type names.

**Location:** `app/core/types.py`

**Aliases:**
- `EmbeddingVector`: `list[float]`
- `AnalysisID`: `str`
- `ChannelName`: `str`
- `EventData`: `dict[str, object]`
- `ExtractionResult`: `dict[str, str | int | dict[str, str]]`

**Benefits:**
- Self-documenting code
- Easier refactoring
- Better IDE support
- Type safety

---

**Document Maintained By:** Yonatan & Arie  
**Last Updated:** November 28, 2025  

### Viewing Instructions

**To view Mermaid diagrams:**
- **VS Code/Cursor**: Install "Markdown Preview Mermaid Support" extension, then press `Cmd+Shift+V` (Mac) or `Ctrl+Shift+V` (Windows/Linux)
- **GitHub**: View on GitHub.com - diagrams render automatically
- **Online**: Copy any ```mermaid code block to [Mermaid Live Editor](https://mermaid.live/)

**Note**: Plain text editors and some markdown viewers do not support Mermaid rendering. Use one of the recommended viewers above.

