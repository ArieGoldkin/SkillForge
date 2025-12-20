# Issue #383: Implement Token/Cost Tracking with CallbackHandler

**Status:** 📋 Planned
**Branch:** `issue/378-385-langfuse-phase2`
**Milestone:** Langfuse Migration Phase 2
**Priority:** ⚡ HIGH
**Estimated Effort:** 2-3 hours
**Dependencies:** Issue #372 (Langfuse Migration) ✅ Complete

---

## Summary

Ensure all LLM calls consistently use Langfuse `CallbackHandler` for accurate token/cost tracking. Currently Langfuse dashboard shows **$0.00 costs** because the callback handler exists but is not passed to all LLM invocations.

## Problem Statement

**Current Issue**: `get_langfuse_callback_handler()` exists but is NOT consistently passed to all LLM invocations. Many direct `model.ainvoke()` calls bypass the callback handler.

**Impact**:
- Langfuse dashboard shows $0.00 costs (useless)
- No token count visibility per LLM call
- Cannot track cost per workflow
- No baseline for cost optimization

## Key Features

- Consistent CallbackHandler integration across all LLM calls
- Token counts visible in Langfuse UI (input/output/total)
- Cost tracking per trace and per model
- Workflow-level cost aggregation
- SSE events with cost metrics

## Current State

### ✅ What's Working
- `get_langfuse_callback_handler()` implemented
- `create_runnable_config()` includes callback
- Agent invocation paths (`invoke_agent`, `stream_agent_response`) use callbacks
- Supervisor node uses callbacks

### ❌ What's NOT Working

**12 direct `model.ainvoke()` calls WITHOUT config parameter:**

#### G-Eval Service (2 calls)
1. `backend/app/shared/services/g_eval/scorer.py:266`
2. `backend/app/shared/services/g_eval/self_consistency.py:131`

#### Tutor Workflow (7 calls)
3. `backend/app/domains/tutor/workflows/nodes/ask_socratic.py:122`
4. `backend/app/domains/tutor/workflows/nodes/final_challenge.py:128`
5. `backend/app/domains/tutor/workflows/nodes/generate_syllabus.py:109`
6. `backend/app/domains/tutor/workflows/nodes/guide_reflection.py:127`
7. `backend/app/domains/tutor/workflows/nodes/conduct_review.py:149`
8. `backend/app/domains/tutor/workflows/nodes/assess_readiness.py:136`
9. `backend/app/domains/tutor/workflows/nodes/deliver_lesson.py:147`
10. `backend/app/domains/tutor/workflows/nodes/rephrase_explain.py:147`

#### Search Reranker (1 call)
11. `backend/app/shared/services/search/reranker.py:291`

#### Context Compaction (1 call)
12. `backend/app/domains/analysis/services/context/compaction.py:220`

## Architecture Overview

```
┌───────────────────────────────────────────────────────────────────┐
│               TOKEN/COST TRACKING ARCHITECTURE                    │
├───────────────────────────────────────────────────────────────────┤
│                                                                   │
│  CURRENT (Broken):                                                │
│  ══════════════════                                               │
│  model.ainvoke(messages)  ──────┐                                │
│                                  │                                │
│                                  ↓                                │
│                            [No Callback]                          │
│                                  ↓                                │
│                        Langfuse: $0.00 cost                       │
│                                                                   │
│                                                                   │
│  FIXED (Issue #383):                                              │
│  ═══════════════════                                              │
│  from app.core.timeout_config import create_runnable_config       │
│                                                                   │
│  config = create_runnable_config()                                │
│       ↓                                                            │
│  config["callbacks"] = [langfuse_callback_handler]                │
│       ↓                                                            │
│  model.ainvoke(messages, config=config)                           │
│       ↓                                                            │
│  Langfuse CallbackHandler                                         │
│       ├─ Captures token counts (input/output)                     │
│       ├─ Calculates cost ($)                                      │
│       └─ Stores in Langfuse DB                                    │
│       ↓                                                            │
│  Langfuse UI:                                                     │
│       ├─ Trace shows $0.42 total cost                             │
│       ├─ Model breakdown: Claude $0.38, Gemini $0.04              │
│       └─ Token counts: 125,000 total (100k in, 25k out)           │
│                                                                   │
└───────────────────────────────────────────────────────────────────┘
```

## Implementation Strategy

### Phase 1: Add Config to Direct LLM Calls (2 hours)

**Pattern for all 12 files:**

```python
# BEFORE:
response = await model.ainvoke(messages)

# AFTER:
from app.core.timeout_config import create_runnable_config

config = create_runnable_config()
response = await model.ainvoke(messages, config=config)
```

**For class-based services (Reranker):**

```python
# In rerank() method:
from app.core.timeout_config import create_runnable_config

config = create_runnable_config()
response = await self.model.ainvoke(messages, config=config)
```

### Phase 2: Cost Aggregation (1 hour)

**New Service**: `backend/app/domains/analysis/services/cost_tracking.py`

```python
async def get_workflow_cost_metrics(trace_id: str) -> CostMetrics | None:
    """Fetch cost metrics for a workflow from Langfuse.

    Returns:
        CostMetrics with aggregated token counts and costs
    """
    client = get_langfuse_client()
    if not client:
        return None

    # Fetch trace with observations (LLM generations)
    trace = client.fetch_trace(trace_id)

    # Aggregate token usage across all generations
    total_cost = sum(obs.calculated_cost_usd for obs in trace.observations)

    return {
        "total_tokens": sum(obs.usage.total for obs in trace.observations),
        "prompt_tokens": sum(obs.usage.input for obs in trace.observations),
        "completion_tokens": sum(obs.usage.output for obs in trace.observations),
        "total_cost_usd": total_cost,
        "model_costs": {...},  # Per-model breakdown
    }
```

### Phase 3: SSE Cost Reporting (30 min)

**Update workflow_runner.py:**

```python
from app.domains.analysis.services.cost_tracking import get_workflow_cost_metrics
from app.core.tracing import get_current_trace_id

# After workflow completes
trace_id = get_current_trace_id()
cost_metrics = await get_workflow_cost_metrics(trace_id)

# Emit completion event with cost metrics
await emit_streaming_event(
    "analysis_complete",
    analysis_id=str(analysis_id),
    status="success",
    cost_metrics=cost_metrics,  # NEW
)
```

## Implementation Checklist

### Phase 1: Fix 12 LLM Call Sites (2 hours)

#### G-Eval Services
- [ ] **scorer.py:266** - `_score_criterion_once()`
  - Add `config = create_runnable_config()`
  - Update `model.ainvoke(messages)` → `model.ainvoke(messages, config=config)`

- [ ] **self_consistency.py:131** - `_vote_once()`
  - Same pattern as scorer.py

#### Tutor Nodes (7 files)
- [ ] **ask_socratic.py:122**
- [ ] **final_challenge.py:128**
- [ ] **generate_syllabus.py:109**
- [ ] **guide_reflection.py:127**
- [ ] **conduct_review.py:149**
- [ ] **assess_readiness.py:136**
- [ ] **deliver_lesson.py:147**
- [ ] **rephrase_explain.py:147**

Pattern for all:
```python
# Add import at top
from app.core.timeout_config import create_runnable_config

# Before model.ainvoke()
config = create_runnable_config()
response = await model.ainvoke(messages, config=config)
```

#### Search & Context Services
- [ ] **reranker.py:291** - `SemanticReranker.rerank()`
- [ ] **compaction.py:220** - `compact_context()`

### Phase 2: Cost Aggregation (1 hour)

- [ ] **Create cost_tracking.py** (new file)
  - Implement `get_workflow_cost_metrics()`
  - Implement `CostMetrics` TypedDict
  - Add error handling for Langfuse API failures

- [ ] **Update workflow_runner.py**
  - Import `get_workflow_cost_metrics`
  - Call after workflow completion
  - Include in final SSE event

### Phase 3: Testing (1 hour)

- [ ] **Unit tests** - `test_cost_tracking.py`
  - Test Langfuse client unavailable → returns None
  - Test token count aggregation
  - Test cost calculation
  - Test per-model breakdown

- [ ] **Integration tests** - `test_langfuse_integration.py`
  - Test callback records token usage
  - Test cost appears in Langfuse UI
  - Test SSE event includes cost_metrics

- [ ] **Manual verification**
  - Enable Langfuse in `.env`
  - Run analysis workflow
  - Check Langfuse UI for non-zero costs
  - Verify SSE event contains cost_metrics

## Acceptance Criteria

### Functional Requirements
- [ ] All 12 direct `model.ainvoke()` calls include `config` parameter
- [ ] Config includes Langfuse callback when enabled
- [ ] Token counts visible in Langfuse for all LLM calls
- [ ] Costs show non-zero values in Langfuse dashboard
- [ ] Cost metrics included in `analysis_complete` SSE event

### Cost Visibility
- [ ] G-Eval scorer calls show token usage
- [ ] Tutor workflow nodes show token usage
- [ ] Search reranker shows token usage
- [ ] Context compaction shows token usage
- [ ] Model name and token breakdown visible

### Code Quality
- [ ] All modified files pass linting
- [ ] Test coverage ≥80% maintained
- [ ] Unit tests pass
- [ ] Integration tests pass

### Performance
- [ ] No measurable latency increase (<5%)
- [ ] Callback overhead negligible
- [ ] Async event publishing non-blocking

## Cost Comparison

### Before (Current)
```
Langfuse Dashboard: $0.00
Token Counts: Not visible
Per-Model Costs: Not available
```

### After (Issue #383)
```
Langfuse Dashboard: $0.42 per analysis
Token Counts:
  - Total: 125,000
  - Input: 100,000
  - Output: 25,000
Per-Model Costs:
  - claude-3-5-sonnet-20241022: $0.38
  - gemini-flash-1.5: $0.04
```

## Files to Modify

### G-Eval Service (2 files)
1. `backend/app/shared/services/g_eval/scorer.py`
2. `backend/app/shared/services/g_eval/self_consistency.py`

### Tutor Workflow Nodes (8 files)
3-10. `backend/app/domains/tutor/workflows/nodes/*.py` (8 files)

### Search & Context (2 files)
11. `backend/app/shared/services/search/reranker.py`
12. `backend/app/domains/analysis/services/context/compaction.py`

### Cost Aggregation (2 new files)
13. `backend/app/domains/analysis/services/cost_tracking.py` (NEW)
14. `backend/tests/unit/services/test_cost_tracking.py` (NEW)

### Workflow Runner (1 file)
15. `backend/app/api/v1/analysis/workflow_runner.py`

## Testing Strategy

### Unit Tests
```python
# test_cost_tracking.py
async def test_returns_none_when_langfuse_disabled():
    """When Langfuse disabled, should return None."""

async def test_aggregates_token_counts():
    """Should aggregate token counts across all generations."""

async def test_calculates_total_cost():
    """Should sum costs from all LLM calls."""
```

### Integration Tests
```python
# test_langfuse_integration.py
async def test_callback_records_token_usage():
    """Verify CallbackHandler captures token usage."""

async def test_cost_appears_in_ui():
    """Manual check: Cost > $0.00 in Langfuse UI."""
```

### Manual Validation

1. **Enable Langfuse**:
```bash
# .env
LANGFUSE_ENABLED=true
LANGFUSE_PUBLIC_KEY=pk-lf-xxx
LANGFUSE_SECRET_KEY=sk-lf-xxx
LANGFUSE_HOST=http://localhost:3000
```

2. **Run analysis**:
```bash
curl -X POST http://localhost:8500/api/v1/analysis/analyze \
  -H "Content-Type: application/json" \
  -d '{"url": "https://example.com/article"}'
```

3. **Verify in Langfuse UI** (`http://localhost:3000`):
- Navigate to Traces
- Find trace for analysis
- Verify each LLM generation shows:
  - Input tokens
  - Output tokens
  - Total tokens
  - Model name
  - Calculated cost

4. **Verify SSE event**:
- Check `analysis_complete` event
- Confirm `cost_metrics` field present
- Verify values match Langfuse UI

## Related Issues

- **#372**: Langfuse Migration (dependency, complete)
- **#378**: Session & User Tracking (complementary)
- **#379**: Prompt Management (uses costs for A/B testing)

## Resources

- [Langfuse LangChain Integration](https://langfuse.com/docs/integrations/langchain/tracing)
- [LangChain CallbackHandler](https://python.langchain.com/docs/modules/callbacks/)
- [Langfuse Token Tracking](https://langfuse.com/docs/model-usage-and-cost)
