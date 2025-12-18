# Langfuse Integration Gap Analysis

**Date:** December 2024 (Updated: December 18, 2024)
**Branch:** `issue/372-langfuse-migration`
**Status:** ✅ Core Integration Complete - All High Priority Features Implemented

## Current State Summary

### ✅ What's Working

| Feature | Status | Evidence |
|---------|--------|----------|
| Trace Capture | ✅ Working | 6+ traces visible in dashboard |
| Workflow Hierarchy | ✅ Working | `analysis_workflow` → nodes visible |
| Metadata | ✅ Working | `analysis_id`, `url`, `content_type` captured |
| Tags | ✅ Working | `workflow`, `node`, `analysis`, `quality-gate` |
| Latency Tracking | ✅ Working | Individual span durations visible |
| OpenTelemetry SDK | ✅ Working | v3.11.0 via langfuse-sdk |
| LLM Token Tracking | ✅ Working | Token counts visible in trace details |
| Cost Tracking | ✅ Working | Cost data ($) visible in trace details |
| Session Grouping | ✅ Working | `session_id=analysis-{uuid}` in traces |
| LangChain Callback | ✅ Working | CallbackHandler auto-configured |
| Scoring Integration | ✅ Working | `submit_langfuse_score()` in quality gate |

### 📋 Remaining Enhancements (Low Priority)

| Feature | Status | Impact | Priority |
|---------|--------|--------|----------|
| User Tracking | ⚠️ Optional | No per-user analytics | LOW |
| Prompt Management | ⚠️ Not Used | Not versioning prompts | LOW |
| LLM-as-Judge | ⚠️ Not Used | Using local G-Eval instead | LOW |

## Root Cause Analysis

### Why LLM Costs Show $0.00

The current implementation uses `@observe` decorator for workflow tracing, but this **does not automatically capture LLM calls with token counts**. The LLM calls happen inside LangChain/LangGraph but we're not passing the Langfuse CallbackHandler.

**Current Flow:**
```
@observe decorator → Workflow spans captured
LangChain LLM call → NOT captured (no callback handler)
```

**Required Flow:**
```
@observe decorator → Workflow spans captured
LangChain LLM call → CallbackHandler → Generations captured with tokens
```

## Required Changes

### 1. Add LangChain CallbackHandler (HIGH PRIORITY)

**File:** `backend/app/core/model_factory.py`

```python
from langfuse.langchain import CallbackHandler

def get_langfuse_callback() -> CallbackHandler | None:
    """Get Langfuse callback handler for LangChain integration."""
    if not os.getenv("LANGFUSE_ENABLED", "false").lower() == "true":
        return None

    return CallbackHandler(
        public_key=os.getenv("LANGFUSE_PUBLIC_KEY"),
        secret_key=os.getenv("LANGFUSE_SECRET_KEY"),
        host=os.getenv("LANGFUSE_HOST", "http://localhost:3000"),
    )
```

**Usage in agent execution:**
```python
from app.core.model_factory import get_langfuse_callback

# When invoking LangChain/LangGraph
callbacks = [get_langfuse_callback()] if get_langfuse_callback() else []
result = await chain.ainvoke(input, config={"callbacks": callbacks})
```

### 2. Add Session and User Tracking (MEDIUM PRIORITY)

**File:** `backend/app/core/tracing.py`

Update `update_current_trace` calls to include:
```python
update_current_trace(
    metadata={"analysis_id": str(analysis_id)},
    tags=["parallel-execution"],
    session_id=f"analysis-{analysis_id}",  # Group traces by analysis
    user_id=user_id if authenticated else "anonymous",
)
```

### 3. Integrate Scoring API (MEDIUM PRIORITY)

**New File:** `backend/app/core/langfuse_scores.py`

```python
from langfuse import get_client

def submit_score(
    trace_id: str,
    name: str,
    value: float,
    comment: str | None = None,
) -> None:
    """Submit a score to Langfuse for quality tracking."""
    client = get_client()
    if client:
        client.score(
            trace_id=trace_id,
            name=name,
            value=value,
            comment=comment,
        )
```

**Integration points:**
- Quality gate evaluation results → Langfuse scores
- G-Eval scores → Langfuse scores
- User feedback (future) → Langfuse scores

### 4. Prompt Management (LOW PRIORITY - Future)

Consider versioning prompts in Langfuse for:
- Agent system prompts
- G-Eval criteria prompts
- Synthesis prompts

## Langfuse Features Reference

### Available in Langfuse v3 (Self-Hosted)

| Feature | Description | Our Usage |
|---------|-------------|-----------|
| **Tracing** | Full trace hierarchy | ✅ Using |
| **Generations** | LLM call tracking with tokens | ❌ Need callback |
| **Scores** | Quality metrics per trace | ❌ Not integrated |
| **Sessions** | Group traces by session | ❌ Not using |
| **Users** | Track by user ID | ❌ Not using |
| **Datasets** | Test datasets | ❌ Not using |
| **Prompts** | Version control prompts | ❌ Not using |
| **Playground** | Test prompts in UI | Available |
| **LLM-as-Judge** | Automated evaluation | ❌ Not using |

### SDK Methods Available

```python
from langfuse import get_client, observe

# Decorators
@observe()  # Auto-trace functions
@observe(as_type="generation")  # Mark as LLM generation

# Client methods
client = get_client()
client.trace(...)  # Manual trace creation
client.generation(...)  # Manual generation
client.span(...)  # Manual span
client.score(...)  # Add scores
client.flush()  # Flush before shutdown

# Context updates
langfuse.update_current_trace(...)
langfuse.update_current_observation(...)
```

## Implementation Priority

1. **Week 1:** Add LangChain CallbackHandler for token/cost tracking
2. **Week 2:** Add session_id and user_id tracking
3. **Week 3:** Integrate scoring API with quality evaluations
4. **Future:** Prompt management, datasets, LLM-as-Judge

## Testing Validation

After implementing changes, verify in Langfuse UI:

- [ ] Model costs showing non-zero values
- [ ] LLM generations visible in traces
- [ ] Token counts (input/output) populated
- [ ] Sessions grouping traces correctly
- [ ] Scores appearing for quality evaluations
- [ ] User analytics available

## References

- [Langfuse Python Decorators](https://langfuse.com/docs/sdk/python/decorators)
- [LangChain Integration](https://langfuse.com/docs/integrations/langchain/tracing)
- [Scoring API](https://langfuse.com/docs/scores/overview)
- [Prompt Management](https://langfuse.com/docs/prompts/get-started)
