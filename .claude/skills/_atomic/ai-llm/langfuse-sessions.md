---
name: langfuse-sessions
description: Session tracking and user analytics with Langfuse
version: 1.0.0
tags: [langfuse, sessions, users, analytics, metadata]
size: atomic
domain: ai-llm
---

# Langfuse Sessions & User Tracking

## Session Grouping

```python
from langfuse import Langfuse

langfuse = Langfuse()

# All traces with same session_id are grouped
session_id = f"analysis_{analysis_id}"

trace1 = langfuse.trace(
    name="url_fetch",
    session_id=session_id
)

trace2 = langfuse.trace(
    name="content_analysis",
    session_id=session_id
)

trace3 = langfuse.trace(
    name="quality_gate",
    session_id=session_id
)

# View in UI: All 3 traces grouped under session
```

## User & Metadata Tracking

```python
langfuse.trace(
    name="analysis",
    user_id="user_123",
    metadata={
        "content_type": "article",
        "url": "https://example.com/post",
        "analysis_id": "abc123",
        "agent_count": 8,
        "total_cost_usd": 0.15
    },
    tags=["production", "skillforge", "security"]
)
```

## With @observe Decorator

```python
from langfuse.decorators import observe, langfuse_context

@observe(name="workflow")
async def run_workflow(user_id: str, analysis_id: str):
    # Set trace-level metadata
    langfuse_context.update_current_trace(
        user_id=user_id,
        session_id=f"session_{analysis_id}",
        metadata={
            "analysis_id": analysis_id,
            "started_at": datetime.utcnow().isoformat()
        },
        tags=["production"]
    )

    # Each child span inherits session
    await process_step_1()
    await process_step_2()
```

## Analytics Queries

```sql
-- Sessions per user (last 30 days)
SELECT
    user_id,
    COUNT(DISTINCT session_id) as sessions,
    COUNT(*) as traces,
    SUM(calculated_total_cost) as total_cost
FROM traces
WHERE timestamp > NOW() - INTERVAL '30 days'
GROUP BY user_id
ORDER BY total_cost DESC;

-- Average traces per session
SELECT
    session_id,
    COUNT(*) as trace_count,
    MIN(timestamp) as started,
    MAX(timestamp) as ended
FROM traces
WHERE session_id IS NOT NULL
GROUP BY session_id
ORDER BY trace_count DESC;
```

## Filter Patterns

```python
# Filter by content type
metadata={"content_type": "tutorial"}

# Filter by environment
tags=["production"]  # or ["staging", "development"]

# Filter by feature
metadata={"feature": "semantic_search"}

# Combine with user
user_id="power_user_123"
```

## Session Timeline View

```
Session: analysis_abc123
├── 10:00:00 url_fetch (0.5s)
├── 10:00:01 content_extraction (1.2s)
├── 10:00:02 embedding_generation (0.3s)
├── 10:00:03 agent_security (5.0s, $0.02)
├── 10:00:08 agent_performance (4.5s, $0.02)
├── 10:00:13 quality_gate (0.8s)
└── 10:00:14 artifact_generation (2.0s, $0.01)

Total: 14.3s, $0.05
```

## Best Practices

- **Always set session_id** for related traces
- **Use consistent user_id** across sessions
- **Add meaningful metadata** for filtering
- **Tag environments** (production, staging, dev)
- **Track feature usage** via metadata
