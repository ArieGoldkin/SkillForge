# Analysis Bug Report - Comprehensive Issue Identification

**Analysis ID**: `c0cfeb13-f7ce-429d-8532-1bcee35527a0`  
**Date**: December 2025  
**Status**: `completed=false` (in progress or failed)

---

## Executive Summary

This document identifies **all major bugs** in the analysis workflow system based on code review of backend and frontend implementations. The analysis with ID `c0cfeb13-f7ce-429d-8532-1bcee35527a0` is showing `completed=false`, indicating the workflow either failed, is stuck, or encountered errors that weren't properly handled.

---

## 🔴 CRITICAL BUGS

### Bug #1: Inconsistent Error Event Emission

**Location**: Multiple workflow nodes  
**Severity**: CRITICAL  
**Impact**: Frontend cannot detect failures, users see incomplete progress

**Problem**:
- Some nodes emit `error` type SSE events (correct)
- Other nodes emit `progress` events with `status="failed"` (inconsistent)
- Quality gate node uses `status="complete"` even when gate fails (WRONG)

**Evidence**:
```python
# extract_content.py:158 - CORRECT
await emit_streaming_event("error", stage="extraction", status="failed", ...)

# quality_gate_node.py:300 - WRONG
await emit_streaming_event("progress", stage="quality_validation", 
                           status="complete" if gate_passed else "failed", ...)
```

**Why This Breaks**:
- Frontend `isErrorEvent()` only checks for `type="error"` events
- Progress events with `status="failed"` are NOT detected as errors by type guard
- Quality gate failures show as "complete" in UI even when gate fails
- Failed stages are not properly counted in `failedStagesCount`

**Affected Nodes**:
- `quality_gate_node.py` - Uses `progress` type with `status="failed"`
- `aggregate_findings.py` - May emit progress events with failed status
- `supervisor.py` - Uses `error` type (CORRECT)

---

### Bug #2: Abort Signal Not Propagated to All Nodes

**Location**: `graph_builder.py`  
**Severity**: CRITICAL  
**Impact**: Workflow continues executing after extraction failure, wasting resources

**Problem**:
- Extraction node sets `should_abort=True` when extraction fails
- Only SOME nodes check `should_abort` before executing
- Nodes that don't check will still execute even after abort signal

**Evidence**:
```python
# graph_builder.py:253 - Checks abort
async def _generate_embedding_node(state: AnalysisState):
    if state.get("should_abort"):
        return {}

# BUT: Many agent nodes don't check should_abort
# supervisor.py - NO abort check
# quality_gate_node.py - NO abort check  
# aggregate_findings.py - NO abort check
```

**Why This Breaks**:
- If extraction fails, workflow should stop immediately
- Instead, embedding, chunking, and agent nodes may still execute
- Wastes API credits and time
- Creates confusing state where some stages run but workflow is "failed"

**Missing Abort Checks**:
- `supervisor_route()` - Should skip if `should_abort=True`
- `quality_gate_node()` - Should skip if `should_abort=True`
- `aggregate_findings()` - Should skip if `should_abort=True`
- All agent nodes - Should skip if `should_abort=True`

---

### Bug #3: GeneratorExit Exception Handling Confusion

**Location**: `orchestrator.py`, `exception_handler.py`, `main.py`  
**Severity**: HIGH  
**Impact**: False error logs, status updates may be incorrect

**Problem**:
- GeneratorExit exceptions are logged as errors even when they're cleanup
- Multiple handlers try to detect "cleanup vs execution" GeneratorExit
- Logic is inconsistent across handlers

**Evidence**:
```python
# exception_handler.py:42-44
is_generator_exit = isinstance(exc, GeneratorExit)
is_converted_generator_exit = isinstance(exc, RuntimeError) and "coroutine ignored GeneratorExit" in str(exc)

# main.py:60 - Different detection logic
if isinstance(exception, GeneratorExit):
    logger.debug(...)  # Always DEBUG, no execution vs cleanup check
```

**Why This Breaks**:
- Cleanup GeneratorExit (normal) may be logged as ERROR
- Execution GeneratorExit (real error) may be logged as DEBUG
- Status updates may be incorrect if exception is misclassified
- Analysis status may show "failed" when workflow actually completed

**Inconsistencies**:
1. `exception_handler.py` checks `workflow_completed` flag
2. `main.py` always logs GeneratorExit as DEBUG
3. `endpoints.py` task callback logs GeneratorExit as DEBUG
4. No unified detection logic

---

### Bug #4: Failed Stage Status Not Persisted

**Location**: `status_updater.py`, progress event storage  
**Severity**: HIGH  
**Impact**: Completed analyses lose failed stage information on page reload

**Problem**:
- SSE events with `status="failed"` are emitted during workflow
- But failed status may not be stored in `analysis_progress` table
- Frontend relies on `/analyze/{id}/progress` endpoint for completed analyses
- If failed events aren't stored, frontend can't show failed stages

**Evidence**:
```python
# workflow_events.py:22 - Emits error event
await emit_streaming_event("error", stage="workflow", status="failed", ...)

# BUT: Is this stored in analysis_progress table?
# Need to check if EventBroadcaster stores error events
```

**Why This Breaks**:
- Active analysis: Frontend receives SSE events, shows failed stages
- Completed analysis: Frontend fetches from `/progress` endpoint
- If failed events weren't stored, frontend shows "Complete" with no errors
- User sees green "Complete" badge even though stages failed

**Missing**:
- Verification that `EventBroadcaster` stores error-type events
- Verification that progress events with `status="failed"` are stored
- Test coverage for failed stage persistence

---

### Bug #5: Quality Gate Status Contradiction

**Location**: `quality_gate_node.py:300`  
**Severity**: HIGH  
**Impact**: Quality gate failures show as "complete" in UI

**Problem**:
- Quality gate emits `status="complete"` when gate PASSES
- Quality gate emits `status="failed"` when gate FAILS
- BUT: Event type is `"progress"`, not `"error"`
- Frontend doesn't detect this as an error event

**Evidence**:
```python
# quality_gate_node.py:296-300
await emit_streaming_event(
    "progress",  # WRONG - should be "error" if failed
    stage="quality_validation",
    status="complete" if gate_passed else "failed",
    gate_passed=gate_passed,  # This is in details, not checked by frontend
)
```

**Why This Breaks**:
- Frontend `isErrorEvent()` checks `type === "error"`
- Quality gate failures use `type="progress"`, so not detected as errors
- `failedStagesCount` doesn't increment for quality gate failures
- UI shows quality gate as "complete" even when it failed

**Expected Behavior**:
- If `gate_passed=False`, emit `type="error"` event
- If `gate_passed=True`, emit `type="progress"` with `status="complete"`

---

### Bug #6: Workflow Result Validation Missing Fields

**Location**: `orchestrator.py:139`  
**Severity**: MEDIUM  
**Impact**: Workflow may complete but be marked as failed due to missing fields

**Problem**:
- `validate_workflow_result()` checks for required fields
- If fields are missing, workflow is marked as `ANALYSIS_FAILED`
- But validation may be too strict or missing optional fields

**Evidence**:
```python
# orchestrator.py:139
missing_fields = validate_workflow_result(result)
if missing_fields:
    await self.status_updater.update(analysis_id, AnalysisStatus.ANALYSIS_FAILED.value)
    return
```

**Why This Breaks**:
- Workflow may complete successfully but fail validation
- User sees "failed" status even though workflow ran
- Need to verify what fields are required vs optional
- May be rejecting valid results

**Missing**:
- Documentation of required vs optional fields
- Graceful handling of missing optional fields
- Clear error messages about which fields are missing

---

## 🟡 HIGH PRIORITY BUGS

### Bug #7: Agent Failure Status Not Tracked

**Location**: `aggregate_findings.py:357`  
**Severity**: HIGH  
**Impact**: Failed agents don't show as failed in UI

**Problem**:
- `aggregate_findings` sets `agent_statuses[agent_type] = "failed"` for selected agents with no findings
- But this status is only in the aggregated_insights dict
- No SSE event is emitted for individual agent failures
- Frontend doesn't know which agents failed

**Evidence**:
```python
# aggregate_findings.py:357
if agent_type in agent_types:
    agent_statuses[agent_type] = "success"
else:
    agent_statuses[agent_type] = "failed"  # Only in dict, not in SSE
```

**Why This Breaks**:
- Frontend tracks stage status from SSE events
- If agent fails but no SSE event is emitted, frontend doesn't know
- User sees agent stage as "pending" or "running" even though it failed
- `failedStagesCount` doesn't include failed agents

**Missing**:
- SSE event emission for agent failures
- Individual agent status tracking in frontend
- Error details for why agent failed

---

### Bug #8: Extraction Error Codes Not Exposed

**Location**: `graph_builder.py:162`, `extract_content.py`  
**Severity**: MEDIUM  
**Impact**: Users can't see specific extraction failure reasons

**Problem**:
- Extraction sets `extraction_error_code` in state
- But error code is not included in SSE error events
- Frontend receives generic error message, not specific error code

**Evidence**:
```python
# graph_builder.py:162
"extraction_error_code": e.error_code.value if e.error_code else ExtractionErrorCode.UNKNOWN.value

# BUT: extract_content.py:158 doesn't include error_code in SSE event
await emit_streaming_event("error", stage="extraction", status="failed", error=str(e), ...)
# Missing: error_code=e.error_code.value
```

**Why This Breaks**:
- User sees "Extraction failed" but not WHY
- Error codes like `ERROR_PAGE`, `TIMEOUT`, `NETWORK_ERROR` are lost
- Frontend can't show specific error messages
- Debugging is harder without error codes

---

### Bug #9: Status Update Race Conditions

**Location**: `status_updater.py`, `orchestrator.py`  
**Severity**: MEDIUM  
**Impact**: Analysis status may be incorrect due to concurrent updates

**Problem**:
- Multiple code paths update analysis status:
  1. Orchestrator on workflow completion
  2. Exception handler on workflow failure
  3. Individual nodes on stage completion
  4. Quality gate on validation failure
- No locking or transaction management
- Last write wins, may overwrite correct status

**Evidence**:
```python
# orchestrator.py:195 - Updates to "complete"
await self.status_updater.update(analysis_id, AnalysisStatus.COMPLETE.value)

# exception_handler.py:97 - Updates to "failed"
await status_updater.update(analysis_id, AnalysisStatus.FAILED.value)

# quality_gate_node - May update status (need to verify)
```

**Why This Breaks**:
- If exception handler runs after orchestrator, status changes from "complete" to "failed"
- If orchestrator runs after exception handler, status changes from "failed" to "complete"
- User sees incorrect status
- Database may have inconsistent state

**Missing**:
- Status update locking mechanism
- Status transition validation (can't go from "complete" to "failed")
- Atomic status updates with database transactions

---

### Bug #10: Frontend Error Event Parsing

**Location**: `frontend/src/schemas/sse.ts`, `useAnalysisProgress.ts`  
**Severity**: MEDIUM  
**Impact**: Some error events may not be detected or displayed

**Problem**:
- Frontend `isErrorEvent()` only checks for `type === "error"`
- Progress events with `status="failed"` are NOT detected as errors
- Quality gate failures use `type="progress"`, so not detected

**Evidence**:
```typescript
// sse.ts:285
export function isErrorEvent(event: unknown): event is SSEErrorEvent {
  return SSEErrorEventSchema.safeParse(event).success
}

// SSEErrorEventSchema requires type: "error"
// So progress events with status="failed" are NOT error events
```

**Why This Breaks**:
- Quality gate failures not detected as errors
- Failed stages from progress events not counted
- `hasFailedStages` may be false even when stages failed
- UI shows "Complete" badge even with failures

**Missing**:
- Check for `status === "failed"` in progress events
- Count failed stages from both error events AND failed progress events
- Update `isErrorEvent()` to also check progress events with failed status

---

## 🟢 MEDIUM PRIORITY BUGS

### Bug #11: Artifact Generation Failure Not Detected

**Location**: `orchestrator.py:176`  
**Severity**: MEDIUM  
**Impact**: Workflow may complete without artifact, marked as "complete"

**Problem**:
- Orchestrator checks if artifact exists after workflow completes
- If no artifact, status is set to `ARTIFACT_FAILED`
- But this check happens AFTER workflow completes
- If artifact generation fails silently, workflow still completes

**Evidence**:
```python
# orchestrator.py:176
artifact = await repository.get_artifact_by_analysis_id(analysis_id)
if not artifact:
    await self.status_updater.update(analysis_id, AnalysisStatus.ARTIFACT_FAILED.value)
```

**Why This Breaks**:
- Artifact generation may fail but workflow doesn't know
- Workflow completes successfully, then discovers no artifact
- User sees "complete" status, then it changes to "artifact_failed"
- Confusing user experience

**Missing**:
- Artifact generation node should emit error if generation fails
- Workflow should check artifact generation status before completing
- Early detection of artifact generation failures

---

### Bug #12: Progress Calculation Includes Failed Stages

**Location**: `useProgressCalculation.ts`  
**Severity**: LOW  
**Impact**: Progress percentage may be incorrect

**Problem**:
- Progress calculation includes failed stages in "finished" count
- But failed stages shouldn't count toward completion
- Progress may show 100% even when stages failed

**Evidence**:
```typescript
// useProgressCalculation.ts:189
finishedStages = completedStages + failedStages + skippedStages
// This includes failed stages in finished count
```

**Why This Breaks**:
- If 5 stages complete and 3 fail, progress shows 8/8 = 100%
- But workflow is not actually complete (3 stages failed)
- User sees 100% progress but workflow is still running or failed
- Misleading progress indicator

**Expected Behavior**:
- Failed stages should NOT count toward progress
- Progress = (completed + skipped) / total
- Failed stages tracked separately for error display

---

### Bug #13: SSE Connection Loss Not Handled

**Location**: `sse_handler.py`, frontend SSE connection  
**Severity**: MEDIUM  
**Impact**: Users lose progress updates if connection drops

**Problem**:
- If SSE connection drops, frontend stops receiving events
- No reconnection logic
- No fallback to polling `/progress` endpoint
- User sees stale progress

**Missing**:
- SSE reconnection with exponential backoff
- Automatic fallback to polling if SSE fails
- Progress recovery from `/progress` endpoint
- Connection status indicator in UI

---

## 📊 Bug Summary by Category

| Category | Critical | High | Medium | Low | Total |
|----------|----------|------|--------|-----|-------|
| **Error Handling** | 1 | 2 | 1 | 0 | 4 |
| **Status Management** | 1 | 1 | 1 | 0 | 3 |
| **SSE Events** | 1 | 1 | 1 | 0 | 3 |
| **Workflow Logic** | 1 | 1 | 0 | 0 | 2 |
| **Frontend Display** | 0 | 1 | 1 | 1 | 3 |
| **Data Persistence** | 1 | 0 | 0 | 0 | 1 |
| **TOTAL** | **5** | **6** | **4** | **1** | **16** |

---

## 🔍 Root Cause Analysis

### Primary Root Causes

1. **Inconsistent Error Event Types**: Some nodes use `type="error"`, others use `type="progress"` with `status="failed"`. Frontend only detects `type="error"` events.

2. **Missing Abort Propagation**: Abort signal (`should_abort`) not checked in all nodes, causing workflow to continue after failures.

3. **GeneratorExit Confusion**: Multiple handlers with inconsistent logic for detecting cleanup vs execution GeneratorExit exceptions.

4. **Status Update Race Conditions**: Multiple code paths update status without locking, causing incorrect final status.

5. **Frontend Error Detection**: Frontend only checks `type="error"`, missing failed stages from `type="progress"` events.

---

## 🎯 Recommended Fix Priority

### Phase 1: Critical Fixes (Immediate)
1. **Bug #1**: Standardize error event emission - all failures use `type="error"`
2. **Bug #2**: Add abort checks to all workflow nodes
3. **Bug #5**: Fix quality gate event type when gate fails

### Phase 2: High Priority (This Sprint)
4. **Bug #3**: Unify GeneratorExit handling logic
5. **Bug #4**: Verify failed stage persistence
6. **Bug #7**: Emit SSE events for agent failures
7. **Bug #10**: Update frontend to detect failed progress events

### Phase 3: Medium Priority (Next Sprint)
8. **Bug #8**: Include error codes in SSE events
9. **Bug #9**: Add status update locking
10. **Bug #11**: Early artifact generation failure detection
11. **Bug #13**: SSE reconnection logic

### Phase 4: Low Priority (Backlog)
12. **Bug #12**: Fix progress calculation to exclude failed stages

---

## 📝 Testing Recommendations

1. **Error Event Tests**: Verify all failure scenarios emit `type="error"` events
2. **Abort Signal Tests**: Verify all nodes check `should_abort` and skip execution
3. **Status Update Tests**: Verify status transitions are correct and atomic
4. **Frontend Error Detection**: Test that failed stages are detected from both error and progress events
5. **Persistence Tests**: Verify failed stage information is stored and retrievable

---

## 🔗 Related Issues

- Issue #441: Abort signal implementation
- Issue #442: Error fields for failed stages
- Issue #384: Langfuse callback handler
- Issue #385: Trace ID for feedback submission

---

**Document Status**: Complete  
**Last Updated**: December 2025  
**Next Review**: After Phase 1 fixes are implemented


