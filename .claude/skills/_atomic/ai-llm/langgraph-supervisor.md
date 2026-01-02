---
name: langgraph-supervisor
description: Supervisor-worker pattern for multi-agent coordination
version: 1.0.0
tags: [ai, langgraph, supervisor, multi-agent, routing, orchestration]
size: atomic
domain: ai-llm
---

# LangGraph Supervisor Pattern

## Basic Pattern

```python
from langgraph.graph import StateGraph, END

class State(TypedDict):
    input: str
    next: str  # Routing decision
    results: Annotated[list[dict], add]

def supervisor(state: State) -> State:
    """Route to next worker or end."""
    completed = set(state.get("agents_completed", []))
    available = [a for a in ALL_AGENTS if a not in completed]

    if available:
        state["next"] = available[0]  # Round-robin
    else:
        state["next"] = END
    return state

def security_worker(state: State) -> State:
    result = analyze_security(state["input"])
    return {"results": [{"worker": "security", "result": result}]}

# Build graph
workflow = StateGraph(State)
workflow.add_node("supervisor", supervisor)
workflow.add_node("security_worker", security_worker)

# Supervisor routes dynamically
workflow.add_conditional_edges(
    "supervisor",
    lambda s: s["next"],
    {"security_worker": "security_worker", END: END}
)

# Workers return to supervisor
workflow.add_edge("security_worker", "supervisor")
workflow.set_entry_point("supervisor")
```

## Routing Strategies

### Round-Robin (All Agents)
```python
def supervisor(state):
    available = [a for a in ALL_AGENTS if a not in state["agents_completed"]]
    return {"next": available[0] if available else END}
```

### Priority-Based
```python
PRIORITIES = {"security_agent": 1, "performance_agent": 2, "style_agent": 3}

def supervisor(state):
    available = [a for a in ALL_AGENTS if a not in state["agents_completed"]]
    available.sort(key=lambda a: PRIORITIES[a])
    return {"next": available[0] if available else END}
```

### Dependency-Based
```python
DEPS = {"impl_planner": ["security_agent"], "code_examples": ["impl_planner"]}

def supervisor(state):
    completed = set(state["agents_completed"])
    for agent in ALL_AGENTS:
        if agent not in completed:
            if all(dep in completed for dep in DEPS.get(agent, [])):
                return {"next": agent}
    return {"next": END}
```

## Parallel Execution with Send

```python
from langgraph.graph import Send

def supervisor(state):
    """Dispatch all agents in parallel."""
    return [
        Send(agent, state)
        for agent in ["security_agent", "performance_agent", "style_agent"]
    ]

# All agents run concurrently - 3x speedup
```

## Error Handling

```python
def supervisor(state):
    """Retry failed agents."""
    failed = set(state.get("agents_failed", []))

    for agent in failed:
        if state["retry_count"].get(agent, 0) < 2:
            return {"next": agent}

    # Continue with remaining agents
    available = [a for a in ALL_AGENTS if a not in state["agents_completed"]]
    return {"next": available[0] if available else END}
```

## Best Practices

- **Round-robin**: When all agents must run, order doesn't matter
- **Priority**: When some agents are more important
- **Dependency**: When agents need outputs from others
- **Parallel (Send)**: When agents are independent - 3x speedup
