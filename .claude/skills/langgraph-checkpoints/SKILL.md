---
name: langgraph-checkpoints
description: LangGraph checkpointing and persistence. Use when implementing fault-tolerant workflows, resuming interrupted executions, debugging with state history, or avoiding re-running expensive operations.
---

# LangGraph Checkpointing

Persist workflow state for recovery and debugging.

## When to Use

- Fault-tolerant workflows
- Resume after crashes
- Debug state at each step
- Avoid re-running expensive LLM calls

## Checkpointer Options

```python
from langgraph.checkpoint import MemorySaver
from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.checkpoint.postgres import PostgresSaver

# Development: In-memory
memory = MemorySaver()
app = workflow.compile(checkpointer=memory)

# Production: SQLite
checkpointer = SqliteSaver.from_conn_string("checkpoints.db")
app = workflow.compile(checkpointer=checkpointer)

# Production: PostgreSQL
checkpointer = PostgresSaver.from_conn_string("postgresql://...")
app = workflow.compile(checkpointer=checkpointer)
```

## Using Thread IDs

```python
# Start new workflow
config = {"configurable": {"thread_id": "analysis-123"}}
result = app.invoke(initial_state, config=config)

# Resume interrupted workflow
config = {"configurable": {"thread_id": "analysis-123"}}
result = app.invoke(None, config=config)  # Resumes from checkpoint
```

## PostgreSQL Setup

```python
def create_checkpointer():
    """Create PostgreSQL checkpointer for production."""
    return PostgresSaver.from_conn_string(
        settings.DATABASE_URL,
        save_every=1  # Save after each node
    )

# Compile with checkpointing
app = workflow.compile(
    checkpointer=create_checkpointer(),
    interrupt_before=["quality_gate"]  # Manual review point
)
```

## Inspecting Checkpoints

```python
# Get all checkpoints for a workflow
checkpoints = app.get_state_history(config)

for checkpoint in checkpoints:
    print(f"Step: {checkpoint.metadata['step']}")
    print(f"Node: {checkpoint.metadata['source']}")
    print(f"State: {checkpoint.values}")

# Get current state
current = app.get_state(config)
print(current.values)
```

## Resuming After Crash

```python
import logging

async def run_with_recovery(workflow_id: str, initial_state: dict):
    """Run workflow with automatic recovery."""
    config = {"configurable": {"thread_id": workflow_id}}

    try:
        # Try to resume existing workflow
        state = app.get_state(config)
        if state.values:
            logging.info(f"Resuming workflow {workflow_id}")
            return app.invoke(None, config=config)
    except Exception:
        pass  # No existing checkpoint

    # Start fresh
    logging.info(f"Starting new workflow {workflow_id}")
    return app.invoke(initial_state, config=config)
```

## Step-by-Step Debugging

```python
# Execute one node at a time
for step in app.stream(initial_state, config):
    print(f"After {step['node']}: {step['state']}")
    input("Press Enter to continue...")

# Rollback to previous checkpoint
history = list(app.get_state_history(config))
previous_state = history[1]  # One step back
app.update_state(config, previous_state.values)
```

## Key Decisions

| Decision | Recommendation |
|----------|----------------|
| Development | MemorySaver (fast, no setup) |
| Production | PostgresSaver (shared, durable) |
| save_every | 1 for expensive nodes, 5 for cheap |
| Thread ID | Use deterministic ID (workflow_id) |

## Common Mistakes

- No checkpointer in production (lose progress)
- Random thread IDs (can't resume)
- Not handling missing checkpoints
- Saving too frequently (overhead)

## Related Skills

- `langgraph-state` - State design for checkpointing
- `langgraph-human-in-loop` - Interrupt patterns
- `database-schema-designer` - PostgreSQL setup
