---
name: langgraph-checkpointing
description: Fault tolerance with checkpoints, resume, and human-in-the-loop
version: 1.0.0
tags: [ai, langgraph, checkpointing, persistence, resume, human-in-loop]
size: atomic
domain: ai-llm
---

# LangGraph Checkpointing

## Setup Options

### In-Memory (Development)
```python
from langgraph.checkpoint import MemorySaver

memory = MemorySaver()
app = workflow.compile(checkpointer=memory)
```

### SQLite (Single Server)
```python
from langgraph.checkpoint.sqlite import SqliteSaver

checkpointer = SqliteSaver.from_conn_string("checkpoints.db")
app = workflow.compile(checkpointer=checkpointer)
```

### PostgreSQL (Production)
```python
from langgraph.checkpoint.postgres import PostgresSaver

checkpointer = PostgresSaver.from_conn_string(
    "postgresql://user:pass@localhost:5432/db"
)
app = workflow.compile(checkpointer=checkpointer)
```

## Resuming After Crash

```python
# Start workflow
config = {"configurable": {"thread_id": "analysis-123"}}
try:
    result = app.invoke({"url": "https://..."}, config=config)
except Exception as e:
    logger.error(f"Workflow crashed: {e}")

# Resume from checkpoint (same thread_id)
config = {"configurable": {"thread_id": "analysis-123"}}
result = app.invoke(None, config=config)  # None = resume
```

## Human-in-the-Loop

```python
app = workflow.compile(
    checkpointer=checkpointer,
    interrupt_before=["publish"]  # Pause before publish
)

# Run until interrupt
config = {"configurable": {"thread_id": "doc-1"}}
state = app.invoke({"content": "..."}, config=config)

# Human reviews
print(f"Draft: {state['draft']}")
approve = input("Approve? (y/n): ")

if approve == "y":
    app.update_state(config, {"approved": True})
    final_state = app.invoke(None, config=config)  # Resume
```

## Inspecting Checkpoints

```python
# Get latest state
config = {"configurable": {"thread_id": "analysis-123"}}
state = app.get_state(config)
print(f"Next step: {state.next}")
print(f"Values: {state.values}")

# Get history
for checkpoint in app.get_state_history(config):
    print(f"Node: {checkpoint.metadata['source']}")
    print(f"State: {checkpoint.values}")
```

## Common Pitfalls

```python
# WRONG - No thread_id
result = app.invoke(state)  # Can't resume!

# CORRECT - Always use thread_id
config = {"configurable": {"thread_id": "unique-id"}}
result = app.invoke(state, config=config)

# WRONG - datetime not serializable
class State(TypedDict):
    timestamp: datetime  # ERROR

# CORRECT - Use ISO string
class State(TypedDict):
    timestamp: str  # "2025-12-19T10:30:00Z"
```

## Performance Tips

- **State size**: Keep < 1MB (store IDs, not full data)
- **Checkpoint frequency**: Use `checkpoint_after=["expensive_node"]`
- **Pruning**: Delete old checkpoints after N days

## Best Practices

- **Always use thread_id**: Required for resume
- **JSON-serializable state**: Use strings for dates, IDs for large objects
- **Checkpoint expensive nodes**: LLM calls, embedding generation
- **Human-in-the-loop**: Use `interrupt_before` for approval workflows
