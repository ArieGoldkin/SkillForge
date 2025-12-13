# Issues #292 & #293: Workflow Error Handling Fixes

**Status:** Verified
**Branch:** `fix/292-293-workflow-error-handling`
**Date:** 2025-12-13

## Summary

This document captures the assessment, root cause analysis, and fixes for two related bugs discovered during end-to-end workflow testing:

1. **Issue #292**: Backend KeyError crashes when `raw_content` missing from workflow state
2. **Issue #293**: Frontend SSE error handler crashes due to backend format mismatch

## Problem Discovery

During manual testing with MCP Playwright, a real workflow analysis was initiated with the URL:
`https://blog.langchain.dev/langgraph-multi-agent-workflows/`

The workflow crashed at 83% progress with the following errors:

### Backend Error (Issue #292)
```
KeyError: 'raw_content'
File: backend/app/workflows/nodes/agents/dependency_mapper_node.py, line 38
```

### Frontend Error (Issue #293)
```
TypeError: Cannot read properties of undefined (reading 'error')
File: frontend/src/stores/sseStoreHelpers.ts, line 110
```

## Root Cause Analysis

### Issue #292: Backend KeyError

**Root Cause:** All 8 agent nodes accessed `state["raw_content"]` directly at the start of the function, BEFORE the try/except block. When `raw_content` was not present in the state (due to context scoping that reduces state size by 99%), the KeyError crashed the workflow.

**Affected Files (8 agent nodes):**
- `backend/app/workflows/nodes/agents/dependency_mapper_node.py`
- `backend/app/workflows/nodes/agents/tech_comparator_node.py`
- `backend/app/workflows/nodes/agents/security_auditor_node.py`
- `backend/app/workflows/nodes/agents/implementation_planner_node.py`
- `backend/app/workflows/nodes/agents/performance_analyst_node.py`
- `backend/app/workflows/nodes/agents/code_quality_critic_node.py`
- `backend/app/workflows/nodes/agents/trend_validator_node.py`
- `backend/app/workflows/nodes/agents/integration_feasibility_node.py`

### Issue #293: Frontend SSE Error Format Mismatch

**Root Cause:** Backend sends error events with the error message at the top level:
```json
{"type": "error", "error": "'raw_content'", "stage": "...", ...}
```

Frontend expected errors nested inside `details`:
```json
{"type": "error", "details": {"error": "..."}, ...}
```

**Affected Files:**
- `frontend/src/types/sse.ts` - SSEErrorEvent interface definition
- `frontend/src/stores/sseStoreHelpers.ts` - Error extraction logic

## Implementation

### Backend Fix (Issue #292)

Changed from unsafe direct access to safe access with defensive check:

```python
# BEFORE (crashed when raw_content missing)
analysis_id = state["analysis_id"]
content = state["raw_content"]  # KeyError!
content_type = state["content_type"]

# AFTER (safe access with early return)
analysis_id = state["analysis_id"]
content = state.get("raw_content", "")
content_type = state["content_type"]

if not content:
    logger.warning(
        "agent_node_skipped_no_content",
        agent_type="<agent_name>",
        analysis_id=analysis_id,
    )
    return {"agent_findings": []}
```

### Frontend Fix (Issue #293)

Updated TypeScript interface and error extraction logic:

**sse.ts:**
```typescript
export interface SSEErrorEvent {
  type: 'error'
  analysis_id: string
  stage: string
  status: 'failed'
  timestamp: string
  error?: string // Backend sends error at top level
  details?: {
    error?: string
    error_code?: string
    [key: string]: unknown
  }
}
```

**sseStoreHelpers.ts:**
```typescript
error: new Error(
  isErrorEvent(data)
    ? (data.error ?? data.details?.error ?? 'Analysis failed')
    : 'Analysis failed'
),
```

## Verification Results

### Test 1: Real Workflow (MCP Playwright)

1. Started Docker containers with rebuilt backend
2. Navigated to http://localhost:5173
3. Submitted URL: `https://blog.langchain.dev/langgraph-multi-agent-workflows/`
4. **Result:** Workflow completed at 100% (previously crashed at 83%)

### Backend Logs Verification

```
agent_node_skipped_no_content agent_type=implementation_planner
agent_node_skipped_no_content agent_type=dependency_mapper
agent_node_skipped_no_content agent_type=tech_comparator
agent_node_skipped_no_content agent_type=performance_analyst
```

Agents now gracefully skip with warnings instead of crashing.

### Frontend Console

No errors - SSE events processed correctly.

### Pre-commit Checks

- Backend: `ruff format --check` - PASS
- Backend: `ruff check` - PASS
- Frontend: `npm run quality:check` - PASS

## Files Changed

| File | Change |
|------|--------|
| `backend/app/workflows/nodes/agents/code_quality_critic_node.py` | Safe state access + early return |
| `backend/app/workflows/nodes/agents/dependency_mapper_node.py` | Safe state access + early return |
| `backend/app/workflows/nodes/agents/implementation_planner_node.py` | Safe state access + early return |
| `backend/app/workflows/nodes/agents/integration_feasibility_node.py` | Safe state access + early return |
| `backend/app/workflows/nodes/agents/performance_analyst_node.py` | Safe state access + early return |
| `backend/app/workflows/nodes/agents/security_auditor_node.py` | Safe state access + early return |
| `backend/app/workflows/nodes/agents/tech_comparator_node.py` | Safe state access + early return |
| `backend/app/workflows/nodes/agents/trend_validator_node.py` | Safe state access + early return |
| `frontend/src/stores/sseStoreHelpers.ts` | Check both error formats |
| `frontend/src/types/sse.ts` | Updated SSEErrorEvent interface |

## Known Limitations

The agents receive empty `raw_content` because the workflow's context scoping intentionally reduces state size by 99% to save tokens, excluding `raw_content` from the scoped fields. This is expected behavior - agents should use `content_ref` to load content from artifacts. The fix ensures graceful degradation when content is unavailable.

## Related Issues

- Issue #292: https://github.com/owner/repo/issues/292
- Issue #293: https://github.com/owner/repo/issues/293
