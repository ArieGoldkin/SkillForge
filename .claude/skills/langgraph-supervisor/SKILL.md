---
name: langgraph-supervisor
description: LangGraph supervisor-worker pattern. Use when building central coordinator agents that route to specialized workers, implementing round-robin or priority-based agent dispatch.
---

# LangGraph Supervisor Pattern

Coordinate multiple specialized agents with a central supervisor.

## When to Use

- Multiple specialist agents
- Central coordination needed
- Dynamic agent routing
- Progress tracking across agents

## Basic Supervisor

```python
from langgraph.graph import StateGraph, END

def supervisor(state: WorkflowState) -> WorkflowState:
    """Route to next worker based on state."""
    if state["needs_analysis"]:
        state["next"] = "analyzer"
    elif state["needs_validation"]:
        state["next"] = "validator"
    else:
        state["next"] = END
    return state

def analyzer(state: WorkflowState) -> WorkflowState:
    """Specialized analysis worker."""
    result = analyze(state["input"])
    state["results"].append(result)
    return state

# Build graph
workflow = StateGraph(WorkflowState)
workflow.add_node("supervisor", supervisor)
workflow.add_node("analyzer", analyzer)
workflow.add_node("validator", validator)

# Supervisor routes dynamically
workflow.add_conditional_edges(
    "supervisor",
    lambda s: s["next"],
    {
        "analyzer": "analyzer",
        "validator": "validator",
        END: END
    }
)

# Workers return to supervisor
workflow.add_edge("analyzer", "supervisor")
workflow.add_edge("validator", "supervisor")

workflow.set_entry_point("supervisor")
app = workflow.compile()
```

## Round-Robin Supervisor

```python
ALL_AGENTS = ["security", "tech", "implementation", "tutorial"]

def supervisor_node(state: AnalysisState) -> AnalysisState:
    """Route to next available agent."""
    completed = set(state["agents_completed"])
    available = [a for a in ALL_AGENTS if a not in completed]

    if not available:
        state["next"] = "quality_gate"
    else:
        state["next"] = available[0]

    return state

# Register all agent nodes
for agent_name in ALL_AGENTS:
    workflow.add_node(agent_name, create_agent_node(agent_name))
    workflow.add_edge(agent_name, "supervisor")
```

## Priority-Based Routing

```python
AGENT_PRIORITIES = {
    "security": 1,    # Run first
    "tech": 2,
    "implementation": 3,
    "tutorial": 4     # Run last
}

def priority_supervisor(state: WorkflowState) -> WorkflowState:
    """Route by priority, not round-robin."""
    completed = set(state["agents_completed"])
    available = [a for a in AGENT_PRIORITIES if a not in completed]

    if not available:
        state["next"] = "finalize"
    else:
        # Sort by priority
        next_agent = min(available, key=lambda a: AGENT_PRIORITIES[a])
        state["next"] = next_agent

    return state
```

## LLM-Based Supervisor

```python
async def llm_supervisor(state: WorkflowState) -> WorkflowState:
    """Use LLM to decide next agent."""
    response = await llm.chat([{
        "role": "user",
        "content": f"""Task: {state['input']}

Completed agents: {state['agents_completed']}
Available agents: {list(AGENTS.keys())}

Which agent should handle this next?
Respond with just the agent name or 'DONE'."""
    }])

    next_agent = response.content.strip()
    state["next"] = next_agent if next_agent != "DONE" else END
    return state
```

## Tracking Progress

```python
def agent_node_factory(agent_name: str):
    """Create agent node that tracks completion."""
    async def node(state: WorkflowState) -> WorkflowState:
        result = await agents[agent_name].run(state["input"])

        return {
            **state,
            "results": state["results"] + [result],
            "agents_completed": state["agents_completed"] + [agent_name],
            "current_agent": None
        }
    return node
```

## Key Decisions

| Decision | Recommendation |
|----------|----------------|
| Routing strategy | Round-robin for uniform, priority for critical-first |
| Max agents | 3-8 specialists (avoid overhead) |
| Failure handling | Skip failed agent, continue with others |
| Coordination | Centralized supervisor (simpler debugging) |

## Common Mistakes

- No completion tracking (runs agents forever)
- Forgetting worker → supervisor edge
- Missing END condition
- Heavy supervisor logic (should be lightweight)

## Related Skills

- `langgraph-routing` - Conditional edges
- `multi-agent-orchestration` - Fan-out patterns
- `langgraph-state` - State for agent tracking
