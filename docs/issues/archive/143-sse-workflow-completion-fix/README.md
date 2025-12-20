# Issue #143: Fix Agent Type Mismatch and SSE Workflow Completion Event

**Status:** ✅ **COMPLETE**  
**Assignee:** Yonatan  
**Story Points:** 3 pts  
**Priority:** HIGH  
**Completed:** January 2025  
**GitHub Issue:** [#143](https://github.com/ArieGoldkin/SkillForge/issues/143)

---

## Issue Overview

**Title:** Bug: Agent type mismatch and SSE stage handling issues

**Description:**  
Integration testing revealed several issues preventing the analysis workflow from completing properly in the UI:
1. Backend bug: Agent type mismatch causing KeyError during aggregation
2. Frontend warning: Unknown "workflow" stage name from backend
3. UI progress stuck at 55% even though backend completed successfully
4. UX issue: Skipped agents show "pending" instead of "skipped"

**Labels:** `🐛 bug`, `📡 sse`, `🔵 backend`, `🤖 langgraph`

---

## Problem Statement

### Issue 1: Agent Type Mismatch (Critical)

**Location:** `backend/app/workflows/tasks/aggregation/synthesis.py:108`

**Problem:**
- Code uses `agent_type="aggregator"` but the agent registry expects `"aggregation"`
- Causes `KeyError: "Unknown agent_type: aggregator"` during aggregation phase
- Workflow continues but logs error

**Error Message:**
```
KeyError: "Unknown agent_type: aggregator. Available: ['tech_comparator', 'security_auditor', 
'implementation_planner', 'performance_analyst', 'code_quality_critic', 'trend_validator', 
'dependency_mapper', 'integration_feasibility', 'supervisor', 'extraction', 'embedding', 
'aggregation', 'artifact_generation']"
```

**Impact:** Error logged during aggregation, though workflow continues.

### Issue 2: Workflow Completion Event Mismatch (Critical)

**Location:** `backend/app/api/v1/workflow_runner.py:88-94`

**Problem:**
- Backend emits `type="progress"` with `stage="workflow"` when workflow completes
- Frontend doesn't recognize "workflow" as a valid stage name
- Frontend expects `type="complete"` with `stage="artifact_generation"` and `artifact_id` per SSE_SCHEMA.md

**Current Implementation (WRONG):**
```python
await emit_streaming_event(
    "progress",  # ❌ Should be "complete"
    analysis_id=str(analysis_id),
    stage="workflow",  # ❌ Should be "artifact_generation"
    status="complete",
    # ❌ Missing artifact_id
)
```

**Expected Format (per SSE_SCHEMA.md):**
```python
await emit_streaming_event(
    "complete",  # ✅ Correct event type
    analysis_id=str(analysis_id),
    stage="artifact_generation",  # ✅ Valid stage name
    status="complete",
    artifact_id=str(artifact.id),  # ✅ Required for frontend
)
```

**Impact:**
- Frontend logs: `[SSE] Unknown stage name from backend: workflow`
- Progress stuck at 55% because completion event is ignored
- `onComplete` callback never fires (needs `type="complete"` with `artifact_id`)
- UI shows "Generating Report" as incomplete even though backend finished

**Root Cause:**
Implementation deviated from `docs/issues/040-sse-endpoint/SSE_SCHEMA.md` specification. The schema clearly defines:
- Complete events must have `type: "complete"`
- Stage must be `"artifact_generation"` (not `"workflow"`)
- `details.artifact_id` is required

---

## Solution

### Fix 1: Agent Type Mismatch

**File:** `backend/app/workflows/tasks/aggregation/synthesis.py`

- Line 108: Change `agent_type="aggregator"` → `agent_type="aggregation"`
- Line 113: Change `"aggregator"` → `"aggregation"` in `extract_structured_response()`

### Fix 2: Workflow Completion Event

**File:** `backend/app/db/repositories/artifact_repository.py`

- Add method `get_artifact_by_analysis_id(analysis_id: uuid.UUID) -> Artifact | None`
- Query artifact using `select(Artifact).where(Artifact.analysis_id == analysis_id)`
- Add to `IArtifactRepository` Protocol interface

**File:** `backend/app/api/v1/workflow_runner.py`

- Remove initial `stage="workflow"` event (line 37-42) - not needed per schema
- After workflow completes successfully:
  - Query artifact by analysis_id using repository
  - Emit proper `type="complete"` event with `stage="artifact_generation"` and `artifact_id`
  - Remove the incorrect `type="progress"` with `stage="workflow"` emission
- Handle edge case: If artifact not found, still emit complete event (log warning)

---

## Files Modified

### Backend Code

1. **`backend/app/workflows/tasks/aggregation/synthesis.py`**
   - Fixed agent type from "aggregator" to "aggregation" (2 changes)

2. **`backend/app/db/repositories/artifact_repository.py`**
   - Added `get_artifact_by_analysis_id()` method to repository and protocol interface

3. **`backend/app/api/v1/workflow_runner.py`**
   - Removed initial "workflow" stage event
   - Added artifact query and proper complete event emission
   - Added error handling for artifact query failures

### Tests

4. **`backend/tests/unit/api/v1/test_workflow_runner.py`**
   - Added `test_run_workflow_task_emits_complete_event_with_artifact_id()`
   - Verifies complete event format matches SSE_SCHEMA.md specification

---

## Acceptance Criteria

- [x] Fix agent type mismatch: Change "aggregator" to "aggregation" ✅
- [x] Add `get_artifact_by_analysis_id()` method to ArtifactRepository ✅
- [x] Update workflow_runner to emit `type="complete"` event ✅
- [x] Complete event includes `stage="artifact_generation"` ✅
- [x] Complete event includes `artifact_id` in details ✅
- [x] Remove incorrect "workflow" stage events ✅
- [x] Add tests to verify complete event format ✅
- [x] Handle edge case: artifact not found gracefully ✅

---

## Technical Details

### ✅ Implementation (COMPLETE)

**Fix 1: Agent Type Mismatch**

**File:** `backend/app/workflows/tasks/aggregation/synthesis.py` (lines 108, 113)

```python
# Before
agent_type="aggregator"
extract_structured_response(final_result, "aggregator")

# After
agent_type="aggregation"
extract_structured_response(final_result, "aggregation")
```

**Fix 2: Repository Method**

**File:** `backend/app/db/repositories/artifact_repository.py`

```python
async def get_artifact_by_analysis_id(self, analysis_id: uuid.UUID) -> Artifact | None:
    """Get artifact by analysis ID."""
    result = await self.session.execute(
        select(Artifact).where(Artifact.analysis_id == analysis_id)
    )
    return result.scalar_one_or_none()
```

**Fix 3: Workflow Completion Event**

**File:** `backend/app/api/v1/workflow_runner.py` (lines 80-123)

```python
# Emit completion event with artifact_id per SSE_SCHEMA.md
# Query artifact by analysis_id to get artifact_id for complete event
try:
    from app.core.agent_config import get_stage_name
    from app.db.repositories.artifact_repository import ArtifactRepository
    from app.db.session import AsyncSessionLocal

    async with AsyncSessionLocal() as db_session:
        repository = ArtifactRepository(session=db_session)
        artifact = await repository.get_artifact_by_analysis_id(analysis_id)
        if artifact:
            await emit_streaming_event(
                "complete",
                analysis_id=str(analysis_id),
                stage=get_stage_name("artifact_generation"),
                status="complete",
                artifact_id=str(artifact.id),
            )
            logger.info(
                "workflow_complete_event_emitted",
                analysis_id=str(analysis_id),
                artifact_id=str(artifact.id),
            )
        else:
            # Artifact not found - log warning but still emit complete event
            logger.warning(
                "workflow_complete_event_no_artifact",
                analysis_id=str(analysis_id),
                message="Artifact not found, emitting complete event without artifact_id",
            )
            await emit_streaming_event(
                "complete",
                analysis_id=str(analysis_id),
                stage=get_stage_name("artifact_generation"),
                status="complete",
            )
except Exception as event_error:
    logger.error(
        "workflow_complete_event_failed",
        analysis_id=str(analysis_id),
        error=str(event_error),
        exc_info=True,
    )
    # Don't raise - workflow completed successfully, event emission is secondary
```

**Verification:**
- ✅ Agent type fixed - no more KeyError during aggregation
- ✅ Complete event format matches SSE_SCHEMA.md specification
- ✅ Artifact ID included in complete event
- ✅ No "workflow" stage events emitted
- ✅ Tests verify event format correctness
- ✅ Edge cases handled gracefully (artifact not found, query failures)

---

## Related Issues

- **Issue #72:** Artifact Generation (provides artifact_id for complete event)
- **Issue #40:** SSE Endpoint (defines SSE_SCHEMA.md specification)
- **Issue #91:** Workflow Status Fix (similar pattern for workflow completion handling)

---

## Verification

After implementation:

1. **Unit Tests:** Run `test_run_workflow_task_emits_complete_event_with_artifact_id()` to verify event format
2. **Integration Tests:** Run full workflow and verify complete event is received
3. **Backend Logs:** Verify no KeyError for "aggregator" agent type
4. **Frontend Console:** Verify no "Unknown stage name: workflow" warnings
5. **UI Progress:** Verify progress reaches 100% when workflow completes
6. **Frontend Callback:** Verify `onComplete` callback fires with artifact_id

---

## Notes

- This fix aligns backend implementation with SSE_SCHEMA.md specification
- The "workflow" stage was never part of the schema - it was an implementation mistake
- Frontend already handles `type="complete"` events correctly (no frontend changes needed)
- Artifact query is done after workflow completion to ensure artifact exists
- Error handling ensures workflow completion is not blocked by event emission failures

---

**Last Updated:** January 2025  
**Completed:** January 2025
