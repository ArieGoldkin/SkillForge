---
name: langgraph-state
description: State management patterns for LangGraph workflows
version: 1.0.0
tags: [ai, langgraph, state, typed-dict, pydantic, accumulator]
size: atomic
domain: ai-llm
---

# LangGraph State Management

## State Schema with TypedDict

```python
from typing import TypedDict, Annotated
from operator import add

class WorkflowState(TypedDict):
    # Simple fields - last write wins
    input: str
    output: str
    current_step: str

    # Accumulating fields - append instead of replace
    results: Annotated[list[dict], add]
    errors: Annotated[list[str], add]
```

## Accumulator Pattern

**Problem:** Multiple agents produce results. How to combine them?

```python
# WRONG - Last write wins (overwrites)
class State(TypedDict):
    results: list[dict]

# CORRECT - Accumulates
class State(TypedDict):
    results: Annotated[list[dict], add]

def agent1(state):
    return {"results": [{"agent": "1", "data": "..."}]}

def agent2(state):
    return {"results": [{"agent": "2", "data": "..."}]}  # APPENDS, not overwrites
```

## Pydantic State (with Validation)

```python
from pydantic import BaseModel, Field, validator

class WorkflowState(BaseModel):
    input: str = Field(min_length=1)
    results: list[dict] = Field(default_factory=list)

    @validator("input")
    def validate_input(cls, v):
        if "forbidden" in v.lower():
            raise ValueError("Invalid input")
        return v
```

## State Access Patterns

```python
# Read-only access
def node(state: WorkflowState) -> WorkflowState:
    input_text = state["input"]  # Read
    return {"results": [{"analysis": analyze(input_text)}]}

# Accumulation
def agent_node(state: WorkflowState) -> WorkflowState:
    return {
        "findings": [new_finding],  # Appends due to Annotated[list, add]
        "agents_completed": state["agents_completed"] + ["agent_name"]
    }
```

## Common Pitfalls

```python
# WRONG - Mutates state in-place (breaks checkpointing)
def node(state):
    state["results"].append({"new": "data"})
    return state

# CORRECT - Return new data
def node(state):
    return {"results": [{"new": "data"}]}
```

## Best Practices

- **Flat state**: Avoid deeply nested dicts
- **Immutable inputs**: Don't modify `input`, `raw_content`, etc.
- **Accumulating outputs**: Use `Annotated[list, add]` for multi-agent results
- **Control flow state**: `next_node`, `agents_completed` for routing
