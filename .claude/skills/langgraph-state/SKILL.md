---
name: langgraph-state
description: LangGraph state management patterns. Use when designing workflow state schemas, using TypedDict vs Pydantic, implementing accumulating state with Annotated operators, or managing shared state across nodes.
---

# LangGraph State Management

Design and manage state schemas for LangGraph workflows.

## When to Use

- Designing workflow state schemas
- Choosing TypedDict vs Pydantic
- Multi-agent state accumulation
- State validation and typing

## TypedDict Approach (Simple)

```python
from typing import TypedDict, Annotated
from operator import add

class WorkflowState(TypedDict):
    input: str
    output: str
    agent_responses: Annotated[list[dict], add]  # Accumulates
    metadata: dict
```

## Pydantic Approach (Validation)

```python
from pydantic import BaseModel, Field

class WorkflowState(BaseModel):
    input: str = Field(description="User input")
    output: str = ""
    agent_responses: list[dict] = Field(default_factory=list)

    def add_response(self, agent: str, result: str):
        self.agent_responses.append({"agent": agent, "result": result})
```

## Accumulating State Pattern

```python
from typing import Annotated
from operator import add

class AnalysisState(TypedDict):
    url: str
    raw_content: str

    # Accumulate agent outputs
    findings: Annotated[list[Finding], add]
    embeddings: Annotated[list[Embedding], add]

    # Control flow
    current_agent: str
    agents_completed: list[str]
    quality_passed: bool
```

**Key Pattern: `Annotated[list[T], add]`**
- Without `add`: Each node replaces the list
- With `add`: Each node appends to the list
- Critical for multi-agent workflows

## Custom Reducers

```python
from typing import Annotated

def merge_dicts(a: dict, b: dict) -> dict:
    """Custom reducer that merges dictionaries."""
    return {**a, **b}

class State(TypedDict):
    config: Annotated[dict, merge_dicts]  # Merges updates

def last_value(a, b):
    """Keep only the latest value."""
    return b

class State(TypedDict):
    status: Annotated[str, last_value]  # Overwrites
```

## State Immutability

```python
def node(state: WorkflowState) -> WorkflowState:
    """Return new state, don't mutate in place."""
    # Wrong: state["output"] = "result"
    # Right:
    return {
        **state,
        "output": "result"
    }
```

## Key Decisions

| Decision | Recommendation |
|----------|----------------|
| TypedDict vs Pydantic | TypedDict for simple, Pydantic for validation |
| Accumulators | Always use `Annotated[list, add]` for multi-agent |
| Nesting | Keep state flat (easier debugging) |
| Immutability | Return new state, don't mutate |

## Common Mistakes

- Forgetting `add` reducer (overwrites instead of accumulates)
- Mutating state in place (breaks checkpointing)
- Deeply nested state (hard to debug)
- No type hints (lose IDE support)

## Related Skills

- `langgraph-routing` - Using state for routing decisions
- `langgraph-checkpoints` - State persistence
- `type-safety-validation` - Pydantic patterns
