# Issue #384: Enable Agent Graph Visualization in Langfuse

**Status:** Ready for Implementation

**Complexity:** LOW (1-2 files, <10 lines of code)

**Impact:** HIGH (Better debugging, visual workflow insights)

**Story Points:** 2 pts

**GitHub Issue:** [#384](https://github.com/ArieGoldkin/SkillForge/issues/384)

---

## Issue Overview

**Title:** Enable Agent Graph Visualization in Langfuse

**Description:**

Langfuse released native graph visualization on February 14, 2025 (currently in beta). This feature automatically infers graph structures from observation timings, showing LangGraph workflow execution as a visual DAG in the Langfuse UI.

This is a SIMPLE, HIGH-IMPACT fix requiring minimal code changes - we just need to pass the Langfuse `CallbackHandler` to LangGraph's `graph.ainvoke()` method. No schema changes, no new dependencies, no complex refactoring.

**Labels:** `backend`, `enhancement`, `quick-win`, `observability`, `python`

---

## Why This Is a Quick Win

This issue is intentionally scoped as a **simple implementation** with **high visibility**:

1. **Minimal Code Changes:** Only 1-2 files need modification (<10 lines of code)
2. **Existing Integration:** We already have Langfuse configured and working
3. **No New Dependencies:** Langfuse SDK already includes `CallbackHandler`
4. **Automatic Graph Inference:** Langfuse automatically builds the graph from observation timings
5. **Zero Configuration:** Native Langfuse feature that "just works" once callbacks are passed
6. **High Debugging Value:** Visual workflow inspection dramatically improves debugging

---

## Current State

### What's Working

- Langfuse observability configured (`backend/app/core/langfuse_config.py`)
- `@robust_traceable` decorator traces individual nodes
- LLM calls, agent executions, and workflow steps all traced
- Trace data visible in Langfuse UI (text-based trace tree)

### What's Missing

The Langfuse `CallbackHandler` is not passed to LangGraph's `graph.ainvoke()` call, so:

- No graph visualization in Langfuse UI (only text-based trace tree)
- No visual representation of workflow DAG structure
- No visual node execution timing/flow
- Missing opportunity for visual debugging and workflow optimization

### The Gap

```python
# Current (in workflow_runner.py):
result = await analysis_workflow.ainvoke(input_state, config=config)
# ❌ No callbacks - no graph visualization

# Needed:
callbacks = [get_langfuse_callback_handler()] if get_langfuse_callback_handler() else []
config_with_callbacks = {**config, "callbacks": callbacks}
result = await analysis_workflow.ainvoke(input_state, config=config_with_callbacks)
# ✅ With callbacks - automatic graph visualization
```

---

## Architecture

### Callback Flow Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                    FastAPI Endpoint                          │
│                 POST /api/v1/analysis                        │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│              workflow_runner.py                              │
│   run_workflow_task()  (@robust_traceable wrapper)          │
│                                                              │
│   1. Get Langfuse CallbackHandler                           │
│      callbacks = [get_langfuse_callback_handler()]          │
│                                                              │
│   2. Merge callbacks into config                            │
│      config_with_callbacks = {**config, "callbacks": []}    │
│                                                              │
│   3. Pass to graph.ainvoke()                                │
│      result = await analysis_workflow.ainvoke(              │
│          input_state,                                        │
│          config=config_with_callbacks  # ← KEY CHANGE       │
│      )                                                       │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│              LangGraph StateGraph                            │
│         (analysis_workflow compiled graph)                   │
│                                                              │
│   Langfuse CallbackHandler intercepts:                      │
│   - Node start/end events                                   │
│   - LLM call events (input/output/tokens/cost)              │
│   - Agent execution events                                  │
│   - Edge transitions between nodes                          │
│                                                              │
│   Graph structure inferred from timing:                     │
│   - Node A starts/ends                                      │
│   - Node B starts/ends (child of A)                         │
│   - Node C starts/ends (sibling of B)                       │
│   - Parallel fan-out/fan-in detected automatically          │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│                    Langfuse Backend                          │
│                                                              │
│   Receives observations via CallbackHandler:                │
│   - Trace ID: analysis-{analysis_id}                        │
│   - Observations: [node_1, llm_1, agent_1, ...]            │
│   - Timings: start_time, end_time per observation           │
│                                                              │
│   Automatically builds graph:                               │
│   - Nodes = observations (spans, generations)               │
│   - Edges = parent-child relationships                      │
│   - Layout = inferred from timing and nesting               │
│                                                              │
│   UI displays:                                              │
│   - Visual DAG with nodes and edges                         │
│   - Node colors (success=green, error=red)                  │
│   - Execution timing per node                               │
│   - Interactive drill-down into node details                │
└─────────────────────────────────────────────────────────────┘
```

### Key Insight: Automatic Graph Inference

Langfuse's graph visualization works by **inferring the graph structure from observation timings**:

1. Each LangGraph node execution creates an observation (span or generation)
2. Observations have parent-child relationships based on nesting
3. Langfuse analyzes observation start/end times to detect:
   - Sequential execution (node A → node B)
   - Parallel execution (node B || node C after node A)
   - Fan-out/fan-in patterns (supervisor → agents → aggregator)
4. Graph is rendered in UI with visual DAG layout

No explicit graph schema needed - it "just works" from timing data.

---

## Implementation Checklist

This implementation is broken into 3 phases for safe, incremental rollout:

### Phase 1: Core Callback Integration (Required)

- [ ] **Modify `workflow_runner.py`**
  - [ ] Import `get_langfuse_callback_handler` from `app.core.langfuse_config`
  - [ ] Create callback handler in `run_workflow_task()` before `ainvoke()`
  - [ ] Merge callbacks into `config` dict (preserve existing timeout config)
  - [ ] Pass updated config to `analysis_workflow.ainvoke()`
  - [ ] Add debug logging for callback creation

- [ ] **Test Locally**
  - [ ] Run workflow with `LANGFUSE_ENABLED=true`
  - [ ] Verify no errors in backend logs
  - [ ] Check Langfuse UI for graph view tab
  - [ ] Verify graph shows all workflow nodes
  - [ ] Confirm node timings are accurate

- [ ] **Verify Backward Compatibility**
  - [ ] Test with `LANGFUSE_ENABLED=false` (should work without callbacks)
  - [ ] Test with missing Langfuse credentials (should gracefully skip)
  - [ ] Verify existing tests still pass

### Phase 2: Verification & Documentation (Required)

- [ ] **Update Tests**
  - [ ] Add unit test for callback handler creation
  - [ ] Add integration test verifying callbacks passed to graph
  - [ ] Mock Langfuse to avoid external dependencies in tests

- [ ] **Documentation**
  - [ ] Update `docs/ARCHITECTURE.md` with graph visualization section
  - [ ] Add screenshot of Langfuse graph view to this README
  - [ ] Document how to enable/disable graph visualization
  - [ ] Add troubleshooting guide for common issues

### Phase 3: Monitoring & Optimization (Optional)

- [ ] **Performance Monitoring**
  - [ ] Measure callback overhead (should be negligible)
  - [ ] Monitor Langfuse API latency
  - [ ] Track trace data volume growth

- [ ] **Enhancements** (Future work, not required for this issue)
  - [ ] Add custom node metadata to enhance graph view
  - [ ] Color-code nodes by stage type (extraction, agent, synthesis)
  - [ ] Add performance annotations (slow nodes highlighted)

---

## Code Examples

### 1. Modify `workflow_runner.py`

**File:** `backend/app/api/v1/analysis/workflow_runner.py`

**Current Code (lines 330-347):**

```python
# Create config with thread_id for checkpointing
# Note: Workflow-level timeout is handled by step_timeout on graph
config = create_runnable_config(thread_id=str(analysis_id))

input_state: dict[str, str] = {
    "url": url,
    "analysis_id": str(analysis_id),
    "skill_level": skill_level,
}

# Execute workflow
logger.debug(
    "workflow_execution_starting",
    analysis_id=str(analysis_id),
    url=url,
    thread_id=str(analysis_id),
)
result = await analysis_workflow.ainvoke(input_state, config=config)
```

**New Code (with callbacks):**

```python
# Create config with thread_id for checkpointing
# Note: Workflow-level timeout is handled by step_timeout on graph
config = create_runnable_config(thread_id=str(analysis_id))

# Add Langfuse callback handler for graph visualization (Issue #384)
# Langfuse automatically infers graph structure from observation timings
from app.core.langfuse_config import get_langfuse_callback_handler

callback_handler = get_langfuse_callback_handler()
if callback_handler:
    callbacks = [callback_handler]
    config = {**config, "callbacks": callbacks}
    logger.debug(
        "langfuse_callback_added",
        analysis_id=str(analysis_id),
        message="Langfuse CallbackHandler added for graph visualization",
    )
else:
    logger.debug(
        "langfuse_callback_skipped",
        analysis_id=str(analysis_id),
        message="Langfuse disabled or not configured, skipping callback",
    )

input_state: dict[str, str] = {
    "url": url,
    "analysis_id": str(analysis_id),
    "skill_level": skill_level,
}

# Execute workflow with callbacks (enables graph visualization in Langfuse)
logger.debug(
    "workflow_execution_starting",
    analysis_id=str(analysis_id),
    url=url,
    thread_id=str(analysis_id),
    callbacks_enabled=callback_handler is not None,
)
result = await analysis_workflow.ainvoke(input_state, config=config)
```

**Changes Summary:**
- **Lines added:** 8 lines (import + callback creation + config merge + logging)
- **Lines modified:** 2 lines (config dict update, debug logging)
- **Total diff:** ~10 lines

### 2. No Changes to `langfuse_config.py`

The `get_langfuse_callback_handler()` function **already exists** and is ready to use:

```python
def get_langfuse_callback_handler() -> Any:
    """Get Langfuse CallbackHandler for LangChain integration.

    Returns:
        CallbackHandler instance, or None if Langfuse is disabled
    """
    # Check if Langfuse is enabled
    langfuse_enabled = os.getenv("LANGFUSE_ENABLED", "false").lower() == "true"
    if not langfuse_enabled:
        return None

    # ... credential checks ...

    from langfuse.langchain import CallbackHandler
    handler = CallbackHandler()  # Auto-configures from env vars
    return handler
```

**No modifications needed - just import and use!**

---

## Verification Checklist

After implementing the changes, verify graph visualization works:

### 1. Enable Langfuse

**Environment Variables:**

```bash
# Required
LANGFUSE_ENABLED=true
LANGFUSE_PUBLIC_KEY=pk-...
LANGFUSE_SECRET_KEY=sk-...
LANGFUSE_HOST=http://localhost:3000

# Optional (for debugging)
LANGFUSE_DEBUG=false
LANGFUSE_RELEASE=1.0.0
```

### 2. Run Workflow

```bash
# Start backend
cd backend
poetry run uvicorn app.main:app --reload

# Trigger analysis (via frontend or curl)
curl -X POST http://localhost:8500/api/v1/analysis \
  -H "Content-Type: application/json" \
  -d '{"url": "https://example.com/article"}'
```

### 3. Check Langfuse UI

Open Langfuse UI: `http://localhost:3000`

**Expected Results:**

1. **Traces Tab:**
   - New trace with name `analysis_workflow`
   - Session ID: `analysis-{uuid}`
   - Multiple observations (spans, generations)

2. **Graph View Tab (NEW):**
   - Visual DAG showing workflow structure
   - Nodes for each stage:
     - `extract_content`
     - `generate_embedding` (parallel)
     - `supervisor_route` (parallel)
     - `execute_agents` (fan-out)
     - `aggregate_findings` (fan-in)
   - Edges showing execution flow
   - Node colors: green (success), red (error), yellow (running)
   - Node timings displayed on hover

3. **Node Details:**
   - Click any node to see detailed span info
   - Input/output data
   - Token counts (for LLM nodes)
   - Cost tracking (for LLM nodes)
   - Execution duration

### 4. Verify No Errors

**Backend Logs:**

```
[INFO] langfuse_callback_added: analysis_id={uuid}, message="Langfuse CallbackHandler added for graph visualization"
[DEBUG] workflow_execution_starting: analysis_id={uuid}, callbacks_enabled=true
[DEBUG] workflow_execution_completed: analysis_id={uuid}
```

**No Errors:**
- No `langfuse_callback_failed` warnings
- No `CallbackHandler` exceptions
- No serialization errors

### 5. Test Backward Compatibility

**With Langfuse Disabled:**

```bash
LANGFUSE_ENABLED=false poetry run uvicorn app.main:app --reload
```

**Expected:**
- Workflow runs normally without callbacks
- Log: `langfuse_callback_skipped: analysis_id={uuid}, message="Langfuse disabled..."`
- No errors or warnings

**With Missing Credentials:**

```bash
LANGFUSE_ENABLED=true
# LANGFUSE_PUBLIC_KEY not set
```

**Expected:**
- Workflow runs normally without callbacks
- Log: `langfuse_credentials_missing: public_key_set=false`
- No errors or crashes

---

## Performance Considerations

### Callback Overhead

**Expected Impact:** NEGLIGIBLE (<5ms per workflow)

The Langfuse `CallbackHandler` is designed for production use with minimal overhead:

1. **Async Processing:** Callbacks use background threads for API calls
2. **Batching:** Multiple observations batched into single HTTP request
3. **No Blocking:** Main workflow execution never waits for Langfuse API
4. **Graceful Degradation:** Callback failures don't crash the workflow

### Benchmark Data (from Langfuse docs)

| Metric | Value |
|--------|-------|
| Callback overhead per span | ~0.5ms |
| Spans per workflow | ~20-50 |
| Total callback overhead | ~10-25ms |
| Workflow duration (typical) | 15-45 seconds |
| **Overhead percentage** | **<0.1%** |

### Monitoring

Add these metrics to track callback performance:

```python
# In workflow_runner.py (optional enhancement)
import time

callback_start = time.time()
callback_handler = get_langfuse_callback_handler()
callback_time_ms = (time.time() - callback_start) * 1000

logger.debug(
    "langfuse_callback_created",
    callback_time_ms=callback_time_ms,
    analysis_id=str(analysis_id),
)
```

**Expected:** `callback_time_ms < 5ms`

---

## Files to Modify

This issue requires changes to **1 file only**:

| File | Changes | Lines Modified |
|------|---------|----------------|
| `backend/app/api/v1/analysis/workflow_runner.py` | Add callback handler to config | ~10 lines |

**No other files need modification:**
- `langfuse_config.py` - Already has `get_langfuse_callback_handler()`
- `analysis.py` - No changes (graph structure unchanged)
- `tracing.py` - No changes (decorator already works)
- Database schema - No changes needed
- Frontend - No changes needed

---

## Acceptance Criteria

### Must Have (Required for completion)

1. **Functional Requirements:**
   - [ ] Langfuse `CallbackHandler` passed to `graph.ainvoke()` in `workflow_runner.py`
   - [ ] Graph visualization appears in Langfuse UI for all workflows
   - [ ] All workflow nodes visible in graph (extraction, agents, synthesis)
   - [ ] Node execution timings accurate (±5% tolerance)
   - [ ] Parallel execution patterns visible (fan-out/fan-in)

2. **Non-Functional Requirements:**
   - [ ] Callback overhead <10ms per workflow (negligible impact)
   - [ ] Graceful degradation when Langfuse disabled/unavailable
   - [ ] No errors in backend logs related to callbacks
   - [ ] Existing tests pass (no regression)

3. **Documentation:**
   - [ ] Code comments explain callback integration (Issue #384 reference)
   - [ ] Debug logging added for callback creation
   - [ ] This README updated with verification results

### Should Have (Nice-to-have enhancements)

- [ ] Unit test for callback handler creation logic
- [ ] Integration test verifying callbacks passed to graph
- [ ] Screenshot of Langfuse graph view added to this README
- [ ] Performance metrics logged for callback overhead

### Won't Have (Explicitly out of scope)

- ❌ Custom graph layout/styling (use Langfuse defaults)
- ❌ Node metadata enhancements (future work)
- ❌ Multi-workflow comparison views (future work)
- ❌ Graph export/download functionality (use Langfuse UI)

---

## Related Documentation

- **Langfuse Graph View:** [Langfuse Docs - Graph Visualization](https://langfuse.com/docs/tracing/graph-view) (beta feature released Feb 14, 2025)
- **LangGraph Callbacks:** [LangGraph Docs - Callbacks](https://langchain-ai.github.io/langgraph/how-tos/callbacks/)
- **SkillForge Architecture:** [docs/ARCHITECTURE.md](../../ARCHITECTURE.md)
- **Observability Setup:** [backend/app/core/langfuse_config.py](../../../backend/app/core/langfuse_config.py)
- **Issue #42:** [First 3 Agents Implementation](../042-first-3-agents/README.md) (similar decorator-based tracing)

---

## Next Steps

1. **Implement Phase 1** (Core callback integration)
   - Modify `workflow_runner.py` with callback handler
   - Test locally with Langfuse UI
   - Verify graph visualization works

2. **Implement Phase 2** (Verification & docs)
   - Add unit/integration tests
   - Update architecture docs
   - Add screenshot to this README

3. **Deploy to Staging**
   - Run end-to-end workflow test
   - Verify graph view in staging Langfuse instance
   - Monitor for errors/performance issues

4. **Production Rollout**
   - Deploy to production
   - Monitor callback overhead metrics
   - Share graph view with team for debugging

---

## FAQ

### Q: Why is this a "quick win"?

**A:** Because we already have all the infrastructure:
- Langfuse is installed and configured
- `CallbackHandler` function already exists
- LangGraph workflow already traced with `@robust_traceable`
- Only need to pass callbacks to `graph.ainvoke()` (~10 lines of code)

### Q: Will this slow down workflows?

**A:** No. Callback overhead is <10ms per workflow (typically 0.1% of total execution time). Langfuse uses async processing and batching to minimize impact.

### Q: What if Langfuse is down or unavailable?

**A:** The callback handler gracefully degrades:
- `get_langfuse_callback_handler()` returns `None` if Langfuse disabled/unavailable
- Workflow runs normally without callbacks
- No errors or crashes

### Q: Do I need to modify the graph structure?

**A:** No! The graph structure is **automatically inferred** from observation timings. No schema changes or explicit graph definitions needed.

### Q: Can I customize the graph visualization?

**A:** Not in this issue. Langfuse automatically generates the graph layout. Custom styling/metadata can be added in future enhancements, but the default visualization is sufficient for debugging.

### Q: How does Langfuse detect parallel execution?

**A:** Langfuse analyzes observation start/end times:
- If two observations have overlapping time ranges → parallel execution
- If one starts after another ends → sequential execution
- Fan-out/fan-in detected from parent-child relationships + timing

### Q: Will this work with the tutor workflow too?

**A:** Yes! Once callbacks are added to `workflow_runner.py`, all LangGraph workflows automatically get graph visualization. The tutor workflow will need similar changes to its runner function.

---

**Status:** ✅ **READY FOR IMPLEMENTATION**

**Complexity:** LOW (1-2 files, <10 lines of code)

**Impact:** HIGH (Visual debugging, workflow optimization)

**Priority:** MEDIUM (Nice-to-have enhancement, not blocking)
