---
name: langgraph-routing
description: Conditional routing and branching patterns
version: 1.0.0
tags: [ai, langgraph, routing, conditional, branching, loops]
size: atomic
domain: ai-llm
---

# LangGraph Conditional Routing

## Basic Conditional Edge

```python
from langgraph.graph import StateGraph, END

def route_function(state: WorkflowState) -> str:
    """Decide next node based on state."""
    if state["score"] >= 0.8:
        return "success_path"
    else:
        return "retry_path"

workflow = StateGraph(WorkflowState)
workflow.add_conditional_edges(
    "check",  # Source node
    route_function,  # Routing function
    {
        "success_path": "success_path",
        "retry_path": "retry_path"
    }
)
```

## Common Routing Patterns

### Binary Decision (Pass/Fail)
```python
def route_validation(state):
    return "pass" if state["valid"] else "fail"
```

### Multi-Way Branching
```python
def route_by_content_type(state):
    content_type = detect_type(state["content"])
    return {
        "code": "code_analyzer",
        "tutorial": "tutorial_analyzer",
        "research": "research_analyzer"
    }.get(content_type, "general_analyzer")
```

### Loop Control
```python
def route_iteration(state):
    if state["iterations"] >= 5 or state["converged"]:
        return "exit"
    return "continue"

workflow.add_conditional_edges("check_convergence", route_iteration, {
    "continue": "process",  # Loop back
    "exit": "finalize"
})
workflow.add_edge("process", "check_convergence")  # Create loop
```

### Quality Gate with Retry
```python
def route_after_quality_gate(state) -> str:
    if state["quality_passed"]:
        return "compress_findings"
    elif state["retry_count"] < 2:
        return "supervisor"  # Retry
    else:
        return END  # Give up

workflow.add_conditional_edges("quality_gate", route_after_quality_gate, {
    "compress_findings": "compress_findings",
    "supervisor": "supervisor",
    END: END
})
```

## Dynamic END Routing

```python
from langgraph.graph import END

def route_to_end(state):
    return END if state["done"] else "continue"

workflow.add_conditional_edges("check", route_to_end, {
    "continue": "next_step",
    END: END
})
```

## Common Pitfalls

```python
# WRONG - Missing case returns None → ERROR
def bad_router(state):
    if state["score"] > 0.8: return "high"
    elif state["score"] > 0.5: return "medium"
    # What if score ≤ 0.5?

# CORRECT - Handle all cases
def good_router(state):
    if state["score"] > 0.8: return "high"
    elif state["score"] > 0.5: return "medium"
    else: return "low"  # Default case

# WRONG - Infinite loop
def bad_loop(state):
    return "retry" if state["score"] < 0.8 else "done"

# CORRECT - Loop limit
def safe_loop(state):
    if state["score"] < 0.8 and state["retries"] < 3:
        return "retry"
    return "done"
```

## Best Practices

- **Pure functions**: Routing functions should only READ state, not modify
- **Handle all cases**: Always have a default return value
- **Loop limits**: Prevent infinite loops with retry counters
- **Pre-compute in nodes**: Do expensive work in nodes, not routing functions
