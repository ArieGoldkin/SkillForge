---
description: Explore codebase section or find implementations
---

Explore: $ARGUMENTS

Use the Task tool with `subagent_type="Explore"` to search the codebase:

```
Task(
  subagent_type="Explore",
  prompt="Find and explain: $ARGUMENTS",
  description="Exploring $ARGUMENTS"
)
```

Common explorations:
- "How does authentication work?"
- "Where are API endpoints defined?"
- "Find all usages of EventBroadcaster"
- "What's the workflow for content analysis?"
- "How does the frontend communicate with backend?"

Tips:
- Use Explore agent for open-ended searches
- Use Grep for specific patterns: `Grep(pattern="class.*Service")`
- Use Glob for file patterns: `Glob(pattern="**/*repository*.py")`
- Read specific files directly if you know the path

Key directories:
- `backend/app/workflows/` - LangGraph agent workflows
- `backend/app/api/` - FastAPI endpoints
- `backend/app/services/` - Business logic
- `frontend/src/features/` - React feature modules
- `frontend/src/components/` - Shared UI components
