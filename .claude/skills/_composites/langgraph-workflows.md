---
name: langgraph-workflows
description: Complete LangGraph multi-agent workflow implementation
version: 1.0.0
type: composite
includes:
  - ai-llm/langgraph-state
  - ai-llm/langgraph-routing
  - ai-llm/langgraph-supervisor
  - ai-llm/langgraph-checkpointing
  - ai-llm/langgraph-langfuse
trigger: "**/workflows/**/*.py"
---

# LangGraph Workflows

Complete guide for building production LangGraph multi-agent workflows.

## When to Use

- Building multi-agent supervisor-worker systems
- Creating fault-tolerant workflows with checkpointing
- Implementing complex routing and branching logic
- Adding observability to LangGraph applications

## Architecture Overview

```
┌──────────────────────────────────────────────────────────────┐
│                     LANGGRAPH WORKFLOW                        │
├──────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌─────────────┐     ┌─────────────┐     ┌─────────────┐    │
│  │   STATE     │────▶│  SUPERVISOR │────▶│   ROUTING   │    │
│  │ (TypedDict) │     │   (hub)     │     │ (branching) │    │
│  └─────────────┘     └─────────────┘     └─────────────┘    │
│                             │                    │           │
│                             ▼                    ▼           │
│                      ┌─────────────┐     ┌─────────────┐    │
│                      │   AGENTS    │     │ CHECKPOINT  │    │
│                      │  (workers)  │     │  (persist)  │    │
│                      └─────────────┘     └─────────────┘    │
│                             │                    │           │
│                             └──────────┬─────────┘           │
│                                        ▼                     │
│                                 ┌─────────────┐              │
│                                 │  LANGFUSE   │              │
│                                 │ (observ.)   │              │
│                                 └─────────────┘              │
└──────────────────────────────────────────────────────────────┘
```

## Included Skills

1. **langgraph-state** - TypedDict state, accumulators, immutable patterns
2. **langgraph-routing** - Conditional edges, loop control, quality gates
3. **langgraph-supervisor** - Worker orchestration, parallel Send()
4. **langgraph-checkpointing** - Persistence, resume, human-in-the-loop
5. **langgraph-langfuse** - Tracing, cost tracking, dashboard views

## Quick Start

```python
from typing import TypedDict, Annotated
from operator import add
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.postgres import PostgresSaver
from langfuse.decorators import observe

# 1. Define state with accumulator
class AnalysisState(TypedDict):
    content: str
    next: str
    agents_completed: list[str]
    findings: Annotated[list[dict], add]  # Accumulates

# 2. Create supervisor with routing
def supervisor(state: AnalysisState) -> AnalysisState:
    completed = set(state.get("agents_completed", []))
    available = [a for a in AGENTS if a not in completed]
    return {"next": available[0] if available else "quality_gate"}

# 3. Build graph
workflow = StateGraph(AnalysisState)
workflow.add_node("supervisor", supervisor)
workflow.add_node("agent_1", agent_1_node)
workflow.add_node("quality_gate", quality_gate_node)

workflow.add_conditional_edges("supervisor", lambda s: s["next"], {
    "agent_1": "agent_1",
    "quality_gate": "quality_gate",
})
workflow.add_edge("agent_1", "supervisor")
workflow.set_entry_point("supervisor")

# 4. Compile with checkpointing
checkpointer = PostgresSaver.from_conn_string(DATABASE_URL)
app = workflow.compile(checkpointer=checkpointer)

# 5. Run with tracing
@observe(name="analysis_workflow")
async def analyze(url: str) -> dict:
    config = {"configurable": {"thread_id": f"analysis-{uuid4()}"}}
    return await app.ainvoke({"content": url}, config=config)
```

## SkillForge Integration

This pattern powers SkillForge's 8-agent content analysis:

```
backend/app/workflows/
├── analysis_workflow.py     # Main supervisor graph
├── agents/                   # Worker agents
│   ├── security_agent.py
│   ├── performance_agent.py
│   └── ...
└── quality_gate.py          # Validation gate
```

## See Also

- [langgraph-state](../_atomic/ai-llm/langgraph-state.md)
- [langgraph-routing](../_atomic/ai-llm/langgraph-routing.md)
- [langgraph-supervisor](../_atomic/ai-llm/langgraph-supervisor.md)
- [langgraph-checkpointing](../_atomic/ai-llm/langgraph-checkpointing.md)
- [langgraph-langfuse](../_atomic/ai-llm/langgraph-langfuse.md)
