# Domains - Domain-Driven Design

Organized by business domains following DDD principles.

## Architecture

```
domains/
├── analysis/          # Content analysis domain
│   ├── schemas/       # Pydantic schemas (API + state)
│   │   ├── api/       # API request/response models
│   │   └── state/     # Workflow state models
│   └── workflows/     # LangGraph workflows
│       ├── agents/    # Specialized analysis agents
│       ├── nodes/     # Workflow nodes
│       ├── tasks/     # Reusable tasks
│       ├── analysis.py       # Main workflow
│       ├── graph_builder.py  # LangGraph construction
│       └── state.py          # AnalysisState TypedDict
│
└── tutor/             # Socratic tutoring domain
    ├── schemas/       # Tutor-specific schemas
    └── workflows/     # Tutoring workflow
```

## Domain: Analysis

Research-to-implementation content analysis pipeline.

### Purpose

Transform URLs (articles, videos, repos) into actionable implementation guides through:
1. Content extraction
2. Multi-agent analysis (8 specialized agents)
3. Quality-gated synthesis
4. Artifact generation

### Workflow

Entry point: `app.domains.analysis.workflows.analysis_workflow()`

**Stages:**
1. **Extraction** - Fetch and parse content
2. **Embedding** - Generate vector embeddings
3. **Agent Execution** - Run 8 specialized agents in parallel:
   - Tech Comparator
   - Security Auditor
   - Implementation Planner
   - Performance Analyst
   - Code Quality Critic
   - Trend Validator
   - Dependency Mapper
   - Integration Feasibility
4. **Quality Gate** - Validate agent output quality (80%+ threshold)
5. **Synthesis** - Aggregate findings with multi-tier fallback
6. **Artifact Generation** - Generate markdown guide

### Agents

See `workflows/agents/` for detailed agent implementations.

Each agent:
- Uses structured output (Pydantic schemas)
- Includes grounding data (URLs, code snippets)
- Reports confidence scores
- Emits SSE progress events

### State Management

```python
from app.domains.analysis.workflows.state import AnalysisState

# Workflow state is a TypedDict
state: AnalysisState = {
    "analysis_id": "uuid",
    "url": "https://example.com",
    "content_type": "article",
    "raw_content": "...",
    "agent_findings": [...],
    "synthesis_output": {...},
}
```

### Quality Gates

Multi-dimensional quality assessment:

- **Completeness**: All critical aspects covered
- **Actionability**: Specific, implementable guidance
- **Relevance**: Content-aligned recommendations
- **Evidence**: Source citations and code examples

Threshold: 80%+ pass rate across aspects.

## Domain: Tutor

Socratic method tutoring for technical content.

### Purpose

Interactive learning experience that:
1. Generates personalized syllabus
2. Delivers lessons via Socratic questioning
3. Assesses readiness for next topic
4. Conducts reviews and challenges

### Workflow

Entry point: `app.workflows.tutor.graph_builder.build_tutor_graph()`

**Phases:**
1. **Syllabus Generation** - Create learning roadmap
2. **Lesson Delivery** - Socratic question/answer
3. **Readiness Assessment** - Validate understanding
4. **Review** - Reinforce key concepts
5. **Final Challenge** - Capstone exercise

### State Management

```python
from app.workflows.tutor.state import TutorState

state: TutorState = {
    "session_id": "uuid",
    "analysis_id": "uuid",  # Optional
    "syllabus": {...},
    "current_section": 0,
    "current_lesson": 0,
    "messages": [...],
}
```

## Domain Isolation

Domains are isolated with clear boundaries:

- **No cross-domain imports** between analysis ↔ tutor
- **Shared utilities** via `app.shared.services/`
- **Database models** in `app.db.models/`
- **API schemas** in domain-specific `schemas/api/`

## Schemas

### API Schemas

Request/response models for API endpoints.

```python
from app.domains.analysis.schemas.api import (
    AnalyzeRequest,
    AnalyzeCreateResponse,
    AnalyzeStatusResponse,
)
```

### State Schemas

Workflow state TypedDicts.

```python
from app.domains.analysis.workflows.state import AnalysisState
from app.workflows.tutor.state import TutorState
```

## Workflows

LangGraph-based workflows for complex orchestration.

### Graph Construction

```python
from langgraph.graph import StateGraph

graph = StateGraph(AnalysisState)
graph.add_node("extract_content", extract_content_node)
graph.add_edge(START, "extract_content")
# ...
app = graph.compile()
```

### Execution

```python
result = await app.ainvoke(initial_state)
```

### Streaming

```python
async for event in app.astream_events(initial_state):
    if event["event"] == "on_chat_model_stream":
        yield event["data"]["chunk"]
```

## Testing

Domain-specific tests in `tests/unit/workflows/`:

```bash
# Test analysis domain
pytest tests/unit/workflows/agents/
pytest tests/unit/workflows/nodes/
pytest tests/unit/workflows/tasks/

# Test tutor domain
pytest tests/unit/workflows/tutor/
```

## Related Documentation

- [Analysis Workflow](./analysis/workflows/README.md)
- [Agent Documentation](./analysis/workflows/agents/README.md)
- [LangGraph Docs](https://langchain-ai.github.io/langgraph/)
