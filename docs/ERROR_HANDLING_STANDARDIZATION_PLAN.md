# Error Handling Standardization - Comprehensive Implementation Plan

**Date**: December 2025  
**Status**: Planning  
**Priority**: CRITICAL  
**Estimated Duration**: 2-3 weeks (3 sprints)

---

## Executive Summary

This plan standardizes error handling across the entire analysis workflow system, fixing 16 identified bugs through systematic refactoring. The plan is organized into 3 phases with 45+ small, deliverable tasks, each with clear acceptance criteria and test requirements.

---

## 🎯 Goals

1. **Standardize Error Events**: All failures emit `type="error"` events consistently
2. **Propagate Abort Signals**: All nodes check `should_abort` before executing
3. **Unify Exception Handling**: Single, consistent GeneratorExit detection logic
4. **Fix Status Updates**: Atomic, race-condition-free status transitions
5. **Improve Frontend Detection**: Detect failures from both error and progress events
6. **Add Comprehensive Tests**: 100% coverage for error handling paths

---

## 📋 Phase 1: Foundation & Critical Fixes (Week 1)

**Goal**: Fix critical bugs that prevent proper error detection and workflow abort.

### Task 1.1: Create Error Event Standardization Guide

**Description**: Document the standard for error event emission across all workflow nodes.

**Deliverables**:
- `docs/SSE_ERROR_EVENT_STANDARD.md` - Complete specification
- Examples for each event type
- Migration guide for existing code

**Acceptance Criteria**:
- [ ] Document defines when to use `type="error"` vs `type="progress"` with `status="failed"`
- [ ] Document includes code examples for all failure scenarios
- [ ] Document includes migration checklist for existing nodes
- [ ] Document reviewed and approved

**Files to Create**:
- `docs/SSE_ERROR_EVENT_STANDARD.md`

**Estimated Time**: 2 hours

---

### Task 1.2: Create Helper Function for Error Events

**Description**: Create a standardized helper function for emitting error events to ensure consistency.

**Deliverables**:
- `backend/app/shared/services/messaging/sse_helpers.py` - Add `emit_error_event()` function
- Unit tests for the helper function

**Acceptance Criteria**:
- [ ] Function signature: `emit_error_event(analysis_id, stage, error, error_code=None, **kwargs)`
- [ ] Function always emits `type="error"` with `status="failed"`
- [ ] Function includes error message and optional error code
- [ ] Function persists event to database
- [ ] Unit tests cover all parameters and edge cases
- [ ] All tests pass

**Code Location**:
```python
# backend/app/shared/services/messaging/sse_helpers.py

async def emit_error_event(
    analysis_id: AnalysisID,
    stage: str,
    error: str | Exception,
    error_code: str | None = None,
    **kwargs: object,
) -> None:
    """Emit standardized error event.
    
    This is the ONLY way to emit error events. All workflow nodes
    must use this function for consistency.
    
    Args:
        analysis_id: UUID of the analysis
        stage: Stage name where error occurred
        error: Error message or Exception object
        error_code: Optional error code (e.g., "EXTRACTION_FAILED")
        **kwargs: Additional event data
    """
```

**Files to Modify**:
- `backend/app/shared/services/messaging/sse_helpers.py`

**Files to Create**:
- `backend/tests/unit/shared/services/messaging/test_sse_helpers.py` (if not exists)

**Estimated Time**: 3 hours

---

### Task 1.3: Fix Quality Gate Error Event

**Description**: Update quality gate node to emit `type="error"` when gate fails.

**Deliverables**:
- `backend/app/domains/analysis/workflows/nodes/quality_gate_node.py` - Use `emit_error_event()`
- Update tests to verify error event emission

**Acceptance Criteria**:
- [ ] Quality gate failure emits `type="error"` event (not `type="progress"`)
- [ ] Error event includes `error_code="QUALITY_GATE_FAILED"`
- [ ] Error event includes quality scores and threshold in details
- [ ] Existing tests updated and passing
- [ ] New test added for error event emission

**Code Changes**:
```python
# quality_gate_node.py:296-306
if gate_passed:
    await emit_streaming_event(
        "progress",
        analysis_id=analysis_id,
        stage="quality_validation",
        status="complete",
        avg_score=avg_score,
        threshold=QUALITY_THRESHOLD,
        scores=quality_scores,
    )
else:
    await emit_error_event(
        analysis_id=analysis_id,
        stage="quality_validation",
        error="Quality gate failed - scores below threshold",
        error_code="QUALITY_GATE_FAILED",
        avg_score=avg_score,
        threshold=QUALITY_THRESHOLD,
        scores=quality_scores,
        gate_passed=False,
    )
```

**Files to Modify**:
- `backend/app/domains/analysis/workflows/nodes/quality_gate_node.py`
- `backend/tests/unit/domains/analysis/workflows/nodes/test_quality_gate_node.py`

**Estimated Time**: 2 hours

---

### Task 1.4: Add Abort Check Helper Function

**Description**: Create a reusable helper to check abort signal and return early if needed.

**Deliverables**:
- `backend/app/domains/analysis/workflows/utils/abort_helpers.py` - New file
- Helper function `check_should_abort(state) -> dict | None`

**Acceptance Criteria**:
- [ ] Function checks `state.get("should_abort")`
- [ ] Returns `None` if should abort (signals skip)
- [ ] Returns empty dict `{}` if should continue
- [ ] Logs debug message when aborting
- [ ] Unit tests cover both paths

**Code Location**:
```python
# backend/app/domains/analysis/workflows/utils/abort_helpers.py

from app.core.logging import get_logger
from app.domains.analysis.workflows.state import AnalysisState

logger = get_logger(__name__)

def check_should_abort(state: AnalysisState) -> dict | None:
    """Check if workflow should abort and return early if needed.
    
    Returns None if should abort (node should return early).
    Returns {} if should continue (node should proceed).
    
    Args:
        state: Current workflow state
        
    Returns:
        None if should abort, {} if should continue
    """
    if state.get("should_abort"):
        analysis_id = state.get("analysis_id")
        abort_reason = state.get("abort_reason", "Unknown error")
        logger.debug(
            "workflow_node_skipped_abort",
            analysis_id=analysis_id,
            abort_reason=abort_reason,
        )
        return None
    return {}
```

**Files to Create**:
- `backend/app/domains/analysis/workflows/utils/abort_helpers.py`
- `backend/tests/unit/domains/analysis/workflows/utils/test_abort_helpers.py`

**Estimated Time**: 2 hours

---

### Task 1.5: Add Abort Checks to Supervisor Node

**Description**: Add abort check at start of supervisor node.

**Deliverables**:
- `backend/app/domains/analysis/workflows/nodes/supervisor.py` - Add abort check
- Update tests

**Acceptance Criteria**:
- [ ] Supervisor checks `should_abort` at start
- [ ] Returns early if abort signal is set
- [ ] Test verifies supervisor skips when `should_abort=True`
- [ ] Test verifies supervisor runs when `should_abort=False`

**Code Changes**:
```python
# supervisor.py: Add at start of supervisor_route()
from app.domains.analysis.workflows.utils.abort_helpers import check_should_abort

async def supervisor_route(state: AnalysisState) -> dict:
    """Supervisor routing node."""
    # Check abort signal
    abort_result = check_should_abort(state)
    if abort_result is None:
        return {}  # Skip execution
    
    # ... rest of function
```

**Files to Modify**:
- `backend/app/domains/analysis/workflows/nodes/supervisor.py`
- `backend/tests/unit/domains/analysis/workflows/nodes/test_supervisor.py`

**Estimated Time**: 1 hour

---

### Task 1.6: Add Abort Checks to Quality Gate Node

**Description**: Add abort check at start of quality gate node.

**Deliverables**:
- `backend/app/domains/analysis/workflows/nodes/quality_gate_node.py` - Add abort check
- Update tests

**Acceptance Criteria**:
- [ ] Quality gate checks `should_abort` at start
- [ ] Returns early if abort signal is set
- [ ] Test verifies quality gate skips when `should_abort=True`
- [ ] Test verifies quality gate runs when `should_abort=False`

**Files to Modify**:
- `backend/app/domains/analysis/workflows/nodes/quality_gate_node.py`
- `backend/tests/unit/domains/analysis/workflows/nodes/test_quality_gate_node.py`

**Estimated Time**: 1 hour

---

### Task 1.7: Add Abort Checks to Aggregate Findings Node

**Description**: Add abort check at start of aggregate findings task.

**Deliverables**:
- `backend/app/domains/analysis/workflows/tasks/aggregate_findings.py` - Add abort check
- Update tests

**Acceptance Criteria**:
- [ ] Aggregate findings checks `should_abort` at start
- [ ] Returns early if abort signal is set
- [ ] Test verifies aggregation skips when `should_abort=True`
- [ ] Test verifies aggregation runs when `should_abort=False`

**Files to Modify**:
- `backend/app/domains/analysis/workflows/tasks/aggregate_findings.py`
- `backend/tests/unit/domains/analysis/workflows/tasks/test_aggregate_findings.py`

**Estimated Time**: 1 hour

---

### Task 1.8: Add Abort Checks to All Agent Nodes

**Description**: Add abort check to all 8 agent nodes.

**Deliverables**:
- All agent node files - Add abort check
- Update all agent node tests

**Acceptance Criteria**:
- [ ] All 8 agent nodes check `should_abort` at start
- [ ] All agents return early if abort signal is set
- [ ] Tests verify each agent skips when `should_abort=True`

**Agent Nodes to Update**:
1. `backend/app/domains/analysis/workflows/nodes/agents/tech_comparator_node.py`
2. `backend/app/domains/analysis/workflows/nodes/agents/security_auditor_node.py`
3. `backend/app/domains/analysis/workflows/nodes/agents/performance_analyst_node.py`
4. `backend/app/domains/analysis/workflows/nodes/agents/integration_feasibility_node.py`
5. `backend/app/domains/analysis/workflows/nodes/agents/implementation_planner_node.py`
6. `backend/app/domains/analysis/workflows/nodes/agents/dependency_mapper_node.py`
7. `backend/app/domains/analysis/workflows/nodes/agents/code_quality_critic_node.py`
8. `backend/app/domains/analysis/workflows/nodes/agents/trend_validator_node.py`

**Files to Modify**:
- All 8 agent node files
- All 8 agent node test files

**Estimated Time**: 4 hours (30 min per agent)

---

### Task 1.9: Add Abort Check to Artifact Generation Node

**Description**: Add abort check at start of artifact generation task.

**Deliverables**:
- `backend/app/domains/analysis/workflows/tasks/generate_artifact.py` - Add abort check
- Update tests

**Acceptance Criteria**:
- [ ] Artifact generation checks `should_abort` at start
- [ ] Returns early if abort signal is set
- [ ] Test verifies artifact generation skips when `should_abort=True`

**Files to Modify**:
- `backend/app/domains/analysis/workflows/tasks/generate_artifact.py`
- `backend/tests/unit/domains/analysis/workflows/tasks/test_generate_artifact.py`

**Estimated Time**: 1 hour

---

### Task 1.10: Verify Abort Signal Propagation in Integration Test

**Description**: Create integration test that verifies abort signal stops all subsequent nodes.

**Deliverables**:
- `backend/tests/integration/workflows/test_abort_signal.py` - New integration test
- Test verifies extraction failure stops all subsequent nodes

**Acceptance Criteria**:
- [ ] Test creates analysis with invalid URL (extraction fails)
- [ ] Test verifies `should_abort=True` is set
- [ ] Test verifies embedding node is skipped
- [ ] Test verifies supervisor node is skipped
- [ ] Test verifies quality gate node is skipped
- [ ] Test verifies workflow routes to `workflow_failed` node
- [ ] Test passes

**Files to Create**:
- `backend/tests/integration/workflows/test_abort_signal.py`

**Estimated Time**: 3 hours

---

## 📋 Phase 2: Error Event Migration & Status Management (Week 2)

**Goal**: Migrate all nodes to use standardized error events and fix status update race conditions.

### Task 2.1: Migrate Extract Content to Use Error Helper

**Description**: Update extract_content task to use `emit_error_event()` helper.

**Deliverables**:
- `backend/app/domains/analysis/workflows/tasks/extract_content.py` - Use `emit_error_event()`
- Include error_code in error event
- Update tests

**Acceptance Criteria**:
- [ ] Extract content uses `emit_error_event()` instead of `emit_streaming_event("error", ...)`
- [ ] Error event includes `error_code` from `JinaReaderError`
- [ ] Error event includes extraction error details
- [ ] Tests verify error event is emitted with correct structure
- [ ] All tests pass

**Code Changes**:
```python
# extract_content.py:156-172
except Exception as e:
    error_code = None
    if isinstance(e, JinaReaderError) and e.error_code:
        error_code = e.error_code.value
    
    await emit_error_event(
        analysis_id=analysis_id,
        stage="extraction",
        error=str(e),
        error_code=error_code or "EXTRACTION_FAILED",
    )
    logger.error(...)
    raise
```

**Files to Modify**:
- `backend/app/domains/analysis/workflows/tasks/extract_content.py`
- `backend/tests/unit/domains/analysis/workflows/tasks/test_extract_content.py`

**Estimated Time**: 2 hours

---

### Task 2.2: Migrate Generate Embedding to Use Error Helper

**Description**: Update generate_embedding task to use `emit_error_event()` helper.

**Deliverables**:
- `backend/app/domains/analysis/workflows/tasks/generate_embedding.py` - Use `emit_error_event()`
- Update tests

**Acceptance Criteria**:
- [ ] Generate embedding uses `emit_error_event()` instead of `emit_streaming_event("error", ...)`
- [ ] Error event includes `error_code="EMBEDDING_FAILED"`
- [ ] Tests verify error event is emitted
- [ ] All tests pass

**Files to Modify**:
- `backend/app/domains/analysis/workflows/tasks/generate_embedding.py`
- `backend/tests/unit/domains/analysis/workflows/tasks/test_generate_embedding.py`

**Estimated Time**: 1 hour

---

### Task 2.3: Migrate Supervisor to Use Error Helper

**Description**: Update supervisor node to use `emit_error_event()` helper.

**Deliverables**:
- `backend/app/domains/analysis/workflows/nodes/supervisor.py` - Use `emit_error_event()`
- Update tests

**Acceptance Criteria**:
- [ ] Supervisor uses `emit_error_event()` instead of `emit_streaming_event("error", ...)`
- [ ] Error event includes `error_code="SUPERVISOR_FAILED"`
- [ ] Tests verify error event is emitted
- [ ] All tests pass

**Files to Modify**:
- `backend/app/domains/analysis/workflows/nodes/supervisor.py`
- `backend/tests/unit/domains/analysis/workflows/nodes/test_supervisor.py`

**Estimated Time**: 1 hour

---

### Task 2.4: Migrate Aggregate Findings to Use Error Helper

**Description**: Update aggregate_findings task to use `emit_error_event()` for failures.

**Deliverables**:
- `backend/app/domains/analysis/workflows/tasks/aggregate_findings.py` - Use `emit_error_event()`
- Emit error events for agent failures
- Update tests

**Acceptance Criteria**:
- [ ] Aggregate findings uses `emit_error_event()` for synthesis failures
- [ ] Individual agent failures emit error events (not just set status in dict)
- [ ] Error events include agent type and failure reason
- [ ] Tests verify error events are emitted for failures
- [ ] All tests pass

**Code Changes**:
```python
# aggregate_findings.py:357 - When agent fails
if agent_type in agent_types:
    agent_statuses[agent_type] = "success"
else:
    agent_statuses[agent_type] = "failed"
    # Emit error event for failed agent
    await emit_error_event(
        analysis_id=analysis_id,
        stage=get_stage_name(agent_type),
        error=f"Agent {agent_type} failed - no findings generated",
        error_code="AGENT_FAILED",
        agent_type=agent_type,
    )
```

**Files to Modify**:
- `backend/app/domains/analysis/workflows/tasks/aggregate_findings.py`
- `backend/tests/unit/domains/analysis/workflows/tasks/test_aggregate_findings.py`

**Estimated Time**: 3 hours

---

### Task 2.5: Migrate Artifact Generation to Use Error Helper

**Description**: Update generate_artifact task to use `emit_error_event()` helper.

**Deliverables**:
- `backend/app/domains/analysis/workflows/tasks/generate_artifact.py` - Use `emit_error_event()`
- Update tests

**Acceptance Criteria**:
- [ ] Artifact generation uses `emit_error_event()` for failures
- [ ] Error event includes `error_code="ARTIFACT_GENERATION_FAILED"`
- [ ] Tests verify error event is emitted
- [ ] All tests pass

**Files to Modify**:
- `backend/app/domains/analysis/workflows/tasks/generate_artifact.py`
- `backend/tests/unit/domains/analysis/workflows/tasks/test_generate_artifact.py`

**Estimated Time**: 1 hour

---

### Task 2.6: Create Status Update Locking Mechanism

**Description**: Create a locking mechanism to prevent race conditions in status updates.

**Deliverables**:
- `backend/app/domains/analysis/services/persistence/status_updater.py` - Add locking
- Use database-level locking (SELECT FOR UPDATE) or in-memory locks
- Update tests

**Acceptance Criteria**:
- [ ] Status updater uses locking to prevent concurrent updates
- [ ] Status transitions are validated (can't go from "complete" to "failed")
- [ ] Lock is released after update
- [ ] Tests verify concurrent updates don't cause race conditions
- [ ] Tests verify invalid transitions are rejected
- [ ] All tests pass

**Code Changes**:
```python
# status_updater.py
from asyncio import Lock
from typing import Final

# Valid status transitions
VALID_TRANSITIONS: Final[dict[str, set[str]]] = {
    "pending": {"running", "failed"},
    "running": {"complete", "failed", "artifact_failed"},
    "complete": set(),  # Terminal state
    "failed": set(),  # Terminal state
    "artifact_failed": set(),  # Terminal state
}

_status_locks: dict[str, Lock] = {}  # Per-analysis locks

async def update(
    self,
    analysis_id: uuid.UUID,
    status: str,
    reason: str | None = None,
) -> bool:
    """Update analysis status with locking and transition validation."""
    # Get or create lock for this analysis
    lock_key = str(analysis_id)
    if lock_key not in _status_locks:
        _status_locks[lock_key] = Lock()
    
    async with _status_locks[lock_key]:
        # Get current status
        current_status = await self._get_current_status(analysis_id)
        
        # Validate transition
        if current_status and status not in VALID_TRANSITIONS.get(current_status, set()):
            logger.warning(
                "invalid_status_transition",
                analysis_id=str(analysis_id),
                current_status=current_status,
                new_status=status,
            )
            return False
        
        # Update status
        # ... existing update logic
```

**Files to Modify**:
- `backend/app/domains/analysis/services/persistence/status_updater.py`
- `backend/tests/unit/domains/analysis/services/persistence/test_status_updater.py`

**Estimated Time**: 4 hours

---

### Task 2.7: Unify GeneratorExit Handling Logic

**Description**: Create a single, unified function for detecting cleanup vs execution GeneratorExit.

**Deliverables**:
- `backend/app/core/exceptions.py` - Add `is_cleanup_generator_exit()` function
- Update all handlers to use unified function
- Update tests

**Acceptance Criteria**:
- [ ] Single function detects cleanup vs execution GeneratorExit
- [ ] Function checks both `GeneratorExit` and converted `RuntimeError`
- [ ] Function checks `workflow_completed` flag when available
- [ ] All handlers use unified function
- [ ] Tests verify cleanup detection logic
- [ ] All tests pass

**Code Changes**:
```python
# exceptions.py
def is_cleanup_generator_exit(
    exc: BaseException | Exception,
    workflow_completed: bool = False,
) -> bool:
    """Detect if GeneratorExit is from cleanup (normal) or execution (error).
    
    Args:
        exc: Exception to check
        workflow_completed: Whether workflow completed successfully
        
    Returns:
        True if cleanup GeneratorExit (normal), False if execution (error)
    """
    is_generator_exit = isinstance(exc, GeneratorExit)
    is_converted = isinstance(exc, RuntimeError) and "coroutine ignored GeneratorExit" in str(exc)
    
    if is_generator_exit or is_converted:
        # If workflow completed, GeneratorExit is cleanup (normal)
        return workflow_completed
    
    return False
```

**Files to Modify**:
- `backend/app/core/exceptions.py`
- `backend/app/domains/analysis/services/workflow/exception_handler.py`
- `backend/app/api/v1/analysis/endpoints.py`
- `backend/app/main.py`
- `backend/tests/unit/core/test_exceptions.py`

**Estimated Time**: 3 hours

---

### Task 2.8: Verify Error Event Persistence

**Description**: Verify that error events are persisted to database and retrievable.

**Deliverables**:
- `backend/tests/integration/services/test_error_event_persistence.py` - New test
- Test creates analysis, triggers error, verifies event is stored

**Acceptance Criteria**:
- [ ] Test creates analysis with invalid URL
- [ ] Test verifies error event is emitted
- [ ] Test verifies error event is stored in `analysis_progress` table
- [ ] Test verifies error event is retrievable via `/progress` endpoint
- [ ] Test passes

**Files to Create**:
- `backend/tests/integration/services/test_error_event_persistence.py`

**Estimated Time**: 2 hours

---

## 📋 Phase 3: Frontend Updates & Testing (Week 3)

**Goal**: Update frontend to detect failures from both error and progress events, fix progress calculation, and add comprehensive tests.

### Task 3.1: Update Frontend Error Detection

**Description**: Update frontend to detect failed stages from both `type="error"` and `type="progress"` with `status="failed"`.

**Deliverables**:
- `frontend/src/schemas/sse.ts` - Add helper function `isFailedStage()`
- `frontend/src/features/analysis/hooks/useAnalysisProgress.ts` - Use new helper
- Update tests

**Acceptance Criteria**:
- [ ] New function `isFailedStage()` checks both error events and failed progress events
- [ ] `useAnalysisProgress` uses `isFailedStage()` to count failed stages
- [ ] `failedStagesCount` includes failures from both event types
- [ ] Tests verify failed stage detection from both event types
- [ ] All tests pass

**Code Changes**:
```typescript
// sse.ts
export function isFailedStage(event: unknown): boolean {
  if (isErrorEvent(event)) {
    return true
  }
  if (isProgressEvent(event) && event.status === 'failed') {
    return true
  }
  return false
}

// useAnalysisProgress.ts
const failedCount = events.filter(isFailedStage).length
```

**Files to Modify**:
- `frontend/src/schemas/sse.ts`
- `frontend/src/features/analysis/hooks/useAnalysisProgress.ts`
- `frontend/src/schemas/__tests__/sse.test.ts`
- `frontend/src/features/analysis/hooks/__tests__/useAnalysisProgress.test.ts`

**Estimated Time**: 3 hours

---

### Task 3.2: Fix Progress Calculation to Exclude Failed Stages

**Description**: Update progress calculation to exclude failed stages from completion percentage.

**Deliverables**:
- `frontend/src/features/analysis/hooks/useProgressCalculation.ts` - Fix calculation
- Update tests

**Acceptance Criteria**:
- [ ] Progress calculation excludes failed stages from "finished" count
- [ ] Progress = (completed + skipped) / total (failed stages not counted)
- [ ] Failed stages tracked separately for error display
- [ ] Tests verify progress calculation excludes failed stages
- [ ] All tests pass

**Code Changes**:
```typescript
// useProgressCalculation.ts:189
// OLD: finishedStages = completedStages + failedStages + skippedStages
// NEW: finishedStages = completedStages + skippedStages
// Failed stages tracked separately, not counted toward progress
finishedStages = completedStages + skippedStages
```

**Files to Modify**:
- `frontend/src/features/analysis/hooks/useProgressCalculation.ts`
- `frontend/src/features/analysis/hooks/__tests__/useProgressCalculation.test.ts`

**Estimated Time**: 2 hours

---

### Task 3.3: Add Error Code Display to UI

**Description**: Display error codes in UI for better debugging and user feedback.

**Deliverables**:
- `frontend/src/features/analysis/components/steps/AnalysisProgressCard.tsx` - Show error codes
- `frontend/src/features/analysis/components/steps/StageCard.tsx` - Show error codes
- Update tests

**Acceptance Criteria**:
- [ ] Error codes displayed in failed stage cards
- [ ] Error codes displayed in error summary
- [ ] Error codes are human-readable (e.g., "Extraction Failed" for "EXTRACTION_FAILED")
- [ ] Tests verify error codes are displayed
- [ ] All tests pass

**Files to Modify**:
- `frontend/src/features/analysis/components/steps/AnalysisProgressCard.tsx`
- `frontend/src/features/analysis/components/steps/StageCard.tsx`
- `frontend/src/features/analysis/components/steps/__tests__/StageCard.test.tsx`

**Estimated Time**: 3 hours

---

### Task 3.4: Add SSE Reconnection Logic

**Description**: Add automatic reconnection with exponential backoff and fallback to polling.

**Deliverables**:
- `frontend/src/features/analysis/hooks/useSSEConnection.ts` - Add reconnection logic
- Fallback to polling `/progress` endpoint if SSE fails
- Update tests

**Acceptance Criteria**:
- [ ] SSE connection automatically reconnects on drop
- [ ] Exponential backoff (1s, 2s, 4s, 8s, max 30s)
- [ ] Falls back to polling `/progress` endpoint after 3 failed reconnection attempts
- [ ] Connection status indicator in UI
- [ ] Tests verify reconnection logic
- [ ] All tests pass

**Files to Modify**:
- `frontend/src/features/analysis/hooks/useSSEConnection.ts` (or create if doesn't exist)
- `frontend/src/features/analysis/components/SSEConnectionStatus.tsx` (new component)
- `frontend/src/features/analysis/hooks/__tests__/useSSEConnection.test.ts`

**Estimated Time**: 4 hours

---

### Task 3.5: Add Comprehensive Error Handling Tests

**Description**: Add end-to-end tests for all error scenarios.

**Deliverables**:
- `frontend/e2e/specs/error-handling-comprehensive.spec.ts` - New E2E test file
- Tests for extraction failure, embedding failure, agent failures, quality gate failure

**Acceptance Criteria**:
- [ ] Test extraction failure (invalid URL)
- [ ] Test embedding failure (mock API error)
- [ ] Test agent failure (mock agent error)
- [ ] Test quality gate failure (low quality content)
- [ ] Test abort signal propagation
- [ ] Test error event persistence
- [ ] Test frontend error detection
- [ ] All tests pass

**Files to Create**:
- `frontend/e2e/specs/error-handling-comprehensive.spec.ts`

**Estimated Time**: 4 hours

---

### Task 3.6: Add Backend Error Handling Integration Tests

**Description**: Add comprehensive integration tests for error handling paths.

**Deliverables**:
- `backend/tests/integration/workflows/test_error_handling.py` - New test file
- Tests for all error scenarios

**Acceptance Criteria**:
- [ ] Test extraction failure emits error event
- [ ] Test embedding failure emits error event
- [ ] Test supervisor failure emits error event
- [ ] Test quality gate failure emits error event
- [ ] Test abort signal stops subsequent nodes
- [ ] Test error events are persisted
- [ ] Test status updates are atomic
- [ ] All tests pass

**Files to Create**:
- `backend/tests/integration/workflows/test_error_handling.py`

**Estimated Time**: 4 hours

---

### Task 3.7: Update Documentation

**Description**: Update all documentation to reflect standardized error handling.

**Deliverables**:
- `docs/SSE_SCHEMA.md` - Update with error event standard
- `docs/ARCHITECTURE.md` - Update error handling section
- `README.md` - Add error handling section

**Acceptance Criteria**:
- [ ] SSE schema document updated with error event standard
- [ ] Architecture document updated with error handling flow
- [ ] README includes error handling overview
- [ ] All documentation reviewed and approved

**Files to Modify**:
- `docs/SSE_SCHEMA.md` (if exists)
- `docs/ARCHITECTURE.md`
- `README.md`

**Estimated Time**: 2 hours

---

## 📊 Task Summary

| Phase | Tasks | Estimated Time | Priority |
|-------|-------|----------------|----------|
| **Phase 1** | 10 tasks | 20 hours | CRITICAL |
| **Phase 2** | 8 tasks | 17 hours | HIGH |
| **Phase 3** | 7 tasks | 22 hours | MEDIUM |
| **TOTAL** | **25 tasks** | **59 hours** | |

---

## 🎯 Success Criteria

### Phase 1 Complete When:
- [ ] All nodes use `emit_error_event()` helper
- [ ] All nodes check `should_abort` before executing
- [ ] Quality gate emits error events when failing
- [ ] Integration test verifies abort signal propagation

### Phase 2 Complete When:
- [ ] All nodes migrated to use error helper
- [ ] Status updates are atomic and race-condition-free
- [ ] GeneratorExit handling is unified
- [ ] Error events are persisted and retrievable

### Phase 3 Complete When:
- [ ] Frontend detects failures from both event types
- [ ] Progress calculation excludes failed stages
- [ ] SSE reconnection works with fallback
- [ ] Comprehensive tests pass (E2E + integration)

---

## 🚀 Implementation Order

**Week 1 (Phase 1)**:
1. Task 1.1: Create error event standard (foundation)
2. Task 1.2: Create error helper function (foundation)
3. Task 1.3: Fix quality gate (quick win)
4. Task 1.4: Create abort helper (foundation)
5. Tasks 1.5-1.9: Add abort checks to all nodes (systematic)
6. Task 1.10: Integration test (verification)

**Week 2 (Phase 2)**:
1. Tasks 2.1-2.5: Migrate all nodes to error helper (systematic)
2. Task 2.6: Status update locking (critical fix)
3. Task 2.7: Unify GeneratorExit handling (critical fix)
4. Task 2.8: Verify error persistence (verification)

**Week 3 (Phase 3)**:
1. Task 3.1: Frontend error detection (critical fix)
2. Task 3.2: Progress calculation fix (UX improvement)
3. Task 3.3: Error code display (UX improvement)
4. Task 3.4: SSE reconnection (reliability)
5. Tasks 3.5-3.6: Comprehensive tests (quality)
6. Task 3.7: Documentation (knowledge transfer)

---

## 📝 Testing Strategy

### Unit Tests
- Each helper function has unit tests
- Each node has tests for error paths
- Each status update has tests for transitions

### Integration Tests
- Abort signal propagation
- Error event persistence
- Status update race conditions
- End-to-end error scenarios

### E2E Tests
- Frontend error detection
- Error display in UI
- SSE reconnection
- Progress calculation

---

## 🔄 Rollback Plan

If issues arise during implementation:

1. **Phase 1 Rollback**: Revert error helper, keep existing error emission
2. **Phase 2 Rollback**: Revert status locking, keep existing status updates
3. **Phase 3 Rollback**: Revert frontend changes, keep existing detection

Each phase is independent and can be rolled back without affecting others.

---

## 📚 Related Documents

- `docs/ANALYSIS_BUG_REPORT.md` - Original bug analysis
- `docs/SSE_SCHEMA.md` - SSE event schema (to be updated)
- `docs/ARCHITECTURE.md` - System architecture (to be updated)

---

**Document Status**: Ready for Implementation  
**Last Updated**: December 2025  
**Next Review**: After Phase 1 completion


