# Test Failure Analysis - Error Handling Integration Tests

**Date**: December 22, 2025  
**Status**: Root Causes Identified

---

## 🔍 Root Cause Analysis

### Primary Issue: Missing AsyncMock for `close()` Method

**Error**: `TypeError: object MagicMock can't be used in 'await' expression`

**Location**: `backend/app/domains/analysis/workflows/tasks/generate_embedding.py:98`
```python
await embedding_service.close()
```

**Problem**: 
- The `EmbeddingService.close()` method is async and must be awaited
- Tests mock `EmbeddingService` but don't set `close()` as `AsyncMock`
- When workflow tries to `await embedding_service.close()`, it fails

**Fix Applied**: ✅
- Added `mock_embedding_service.close = AsyncMock()` to all embedding service mocks
- Applied to both `test_error_events.py` and `test_workflow_abort.py`

---

### Secondary Issue: Workflow Result Validation

**Error**: `workflow_result_incomplete` - Missing required fields: `['raw_content', 'extraction_metadata', 'content_embedding']`

**Location**: `backend/app/domains/analysis/services/workflow/orchestrator.py:139-154`

**Problem**:
- When workflow fails early (e.g., embedding failure), it doesn't produce a complete result
- Orchestrator validates result and expects `raw_content`, `extraction_metadata`, `content_embedding`
- Failed workflows don't have these fields, causing validation error
- This triggers status update to `analysis_failed`, which may conflict with existing `failed` status

**Impact**:
- Status transition errors: `Invalid status transition: failed -> analysis_failed`
- Workflow completes but with validation errors

**Solution Needed**:
- Orchestrator should handle incomplete results gracefully when workflow fails
- Validation should be skipped or adjusted for error scenarios
- Status transitions need to account for already-failed states

---

### Tertiary Issue: Async Context Cancellation

**Error**: `asyncio.exceptions.CancelledError` during database commit

**Location**: Database transaction commits in test teardown

**Problem**:
- Tests may be timing out or being cancelled by pytest
- Database connections are being closed while transactions are in progress
- This is likely a side effect of the workflow errors above

**Impact**:
- Tests fail with `CancelledError` instead of showing the real assertion failures
- Makes debugging harder

---

## 📊 Test Status Summary

### ✅ Passing Tests (2/15)
- `test_concurrent_status_updates_are_serialized` ✅
- `test_invalid_status_transitions_are_rejected` ✅

### ❌ Failing Tests (13/15)

**Category 1: Embedding Service Mock Issues** (Fixed)
- All tests that mock `EmbeddingService` - **FIXED** with `AsyncMock` for `close()`

**Category 2: Workflow Result Validation** (Needs Fix)
- Tests fail because orchestrator expects complete results even when workflow fails early
- Need to adjust orchestrator validation logic for error scenarios

**Category 3: Status Transition Conflicts** (Needs Fix)
- Tests fail because status is already `failed` but orchestrator tries to set `analysis_failed`
- Need to handle status transitions more gracefully

---

## 🔧 Required Fixes

### Fix 1: Embedding Service Mock ✅ DONE
```python
mock_embedding_service.close = AsyncMock()  # Added to all mocks
```

### Fix 2: Orchestrator Validation (TODO)
**File**: `backend/app/domains/analysis/services/workflow/orchestrator.py`

**Current Code** (lines 138-154):
```python
if isinstance(result, dict):
    missing_fields = validate_workflow_result(result)
    if missing_fields:
        # Always tries to update status, even if already failed
        await self.status_updater.update(
            analysis_id, AnalysisStatus.ANALYSIS_FAILED.value
        )
```

**Needed Change**:
- Check if workflow already failed before validating result
- Skip validation if `workflow_status == "failed"` in result
- Don't try to update status if analysis is already in a terminal state

### Fix 3: Status Transition Handling (TODO)
**File**: `backend/app/domains/analysis/services/persistence/status_updater.py`

**Needed Change**:
- Allow `failed -> analysis_failed` transition (or make them equivalent)
- Handle cases where status is already terminal
- Don't raise errors for redundant status updates

---

## 🎯 Next Steps

1. ✅ **DONE**: Fix embedding service mocks (add `AsyncMock` for `close()`)
2. **TODO**: Adjust orchestrator to skip validation for failed workflows
3. **TODO**: Fix status transition logic to handle already-failed states
4. **TODO**: Re-run all tests to verify fixes

---

## 📝 Notes

- The error events **ARE being emitted correctly** (visible in logs)
- The issue is with workflow cleanup and status management, not error emission
- Tests are correctly structured - the failures are due to workflow orchestration logic, not test design
