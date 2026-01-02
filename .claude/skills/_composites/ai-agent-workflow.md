---
name: ai-agent-workflow
description: Build autonomous AI agents and multi-agent systems
version: 1.0.0
type: composite
includes:
  - ai-llm/agentic-workflows
  - ai-llm/multi-agent-orchestration
  - ai-llm/multi-agent-synthesis
  - ai-llm/function-calling
trigger: "**/workflows/**/*.py"
---

# AI Agent Workflow

Complete guide for building autonomous AI agents and multi-agent systems.

## When to Use

- Creating autonomous task-completion agents
- Building multi-agent collaborative systems
- Implementing ReAct or Tree of Thoughts patterns
- Orchestrating specialized agents for complex tasks

## Architecture Overview

```
┌─────────────────────────────────────────────────────────┐
│                    SUPERVISOR                           │
│          (routes tasks, resolves conflicts)             │
└───────────────────────┬─────────────────────────────────┘
                        │
        ┌───────────────┼───────────────┐
        ▼               ▼               ▼
┌───────────────┐ ┌───────────────┐ ┌───────────────┐
│   Agent A     │ │   Agent B     │ │   Agent C     │
│  (Researcher) │ │  (Analyzer)   │ │   (Writer)    │
└───────────────┘ └───────────────┘ └───────────────┘
        │               │               │
        └───────────────┼───────────────┘
                        ▼
                  ┌───────────────┐
                  │  SYNTHESIZER  │
                  │  (combines)   │
                  └───────────────┘
```

## Included Skills

1. **agentic-workflows** - ReAct pattern, Tree of Thoughts, self-correction
2. **multi-agent-orchestration** - Supervisor pattern, dependency graphs
3. **multi-agent-synthesis** - Fan-out/fan-in, LLM-as-judge
4. **function-calling** - Tool definitions, execution loops

## Quick Start

```python
from langgraph.graph import StateGraph, END
from langchain_core.messages import HumanMessage

# Define state
class AgentState(TypedDict):
    messages: list[BaseMessage]
    next: str

# Build graph
workflow = StateGraph(AgentState)
workflow.add_node("supervisor", supervisor_node)
workflow.add_node("researcher", researcher_node)
workflow.add_node("writer", writer_node)
workflow.add_conditional_edges("supervisor", route_to_agent)
workflow.add_edge("researcher", "supervisor")
workflow.add_edge("writer", "supervisor")
workflow.set_entry_point("supervisor")

app = workflow.compile()
result = app.invoke({"messages": [HumanMessage("Research AI trends")]})
```

## See Also

- [agentic-workflows](../_atomic/ai-llm/agentic-workflows.md)
- [multi-agent-orchestration](../_atomic/ai-llm/multi-agent-orchestration.md)
- [multi-agent-synthesis](../_atomic/ai-llm/multi-agent-synthesis.md)
- [function-calling](../_atomic/ai-llm/function-calling.md)
