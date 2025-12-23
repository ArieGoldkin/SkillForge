# Fix Remaining Test Failures - Implementation Plan

**Created:** 2025-12-23
**Status:** Ready for Implementation
**Related PR:** DI Refactoring (workflow singleton replacement)

---

## Executive Summary

After the dependency injection refactoring, **22 test failures remain** (updated from initial estimate of 19). These are **pre-existing issues** unrelated to the DI changes, caused by:

- Outdated test expectations
- Schema changes not reflected in test fixtures
- Incorrect mock patch paths
- Implementation behavior changes not synced with tests

```
┌──────────────────────────────────────────────────────────────┐
│                  TEST FAILURE BREAKDOWN                       │
├──────────────────────────────────────────────────────────────┤
│  Category                    │ Count │ Complexity │ Risk     │
│  ────────────────────────────┼───────┼────────────┼──────────│
│  Exception Handler           │   7   │ Medium     │ Medium   │
│  Orchestrator Status         │   3   │ Medium     │ Medium   │
│  Agent Failure Events        │   3   │ Medium     │ Medium   │
│  Validator Legacy            │   2   │ Easy       │ Low      │
│  Status Updater              │   2   │ Easy       │ Low      │
│  Config & Events             │   5   │ Varies     │ Low-High │
│  ────────────────────────────┼───────┼────────────┼──────────│
│  TOTAL                       │  22   │            │          │
└──────────────────────────────────────────────────────────────┘
```

---

## Root Cause Analysis

### Category 1: Exception Handler Tests (7 failures)

**File:** `tests/unit/domains/analysis/services/workflow/test_exception_handler.py`

**Failing Tests:**
1. `test_exception_handler_generator_exit_during_execution`
2. `test_exception_handler_converted_generator_exit_during_execution`
3. `test_exception_handler_other_runtime_error_during_execution`
4. `test_exception_handler_value_error_during_execution`
5. `test_exception_handler_key_error_during_execution`
6. `test_exception_handler_exception_during_cleanup_is_not_suppressed`
7. `test_exception_handler_partial_match_runtime_error`

**Root Cause:**
Tests expect `WorkflowEventEmitter.emit_error()` to be called for ALL exceptions. However, the implementation (`exception_handler.py:86-99`) only calls `emit_error()` when the exception is a `WorkflowStageError`. For non-WorkflowStageError exceptions, it logs a warning but does NOT emit SSE events.

**Evidence from implementation:**
```python
# exception_handler.py lines 86-99
if not isinstance(exc, WorkflowStageError):
    log.warning(
        "Exception without stage context - not emitting SSE event. "
        "Exception should be wrapped with WorkflowStageError.",
        ...
    )
    return  # No emit_error() call!
```

**Fix Strategy:** Update tests to NOT expect `emit_error()` for non-WorkflowStageError exceptions (Option A - aligns with intentional design decision).

---

### Category 2: Orchestrator Status Tests (3 failures)

**File:** `tests/unit/domains/analysis/services/workflow/test_orchestrator_status.py`

**Failing Tests:**
1. `test_orchestrator_sets_artifact_failed_when_no_artifact`
2. `test_orchestrator_sets_complete_when_artifact_exists`
3. `test_orchestrator_sets_analysis_failed_when_result_incomplete`

**Root Cause:**
Mock workflow results are missing the `workflow_status` field. The orchestrator checks for `workflow_status == "completed"` before proceeding (lines 244-262). Without this field, status is set to "failed" with message "Workflow returned invalid or missing status".

**Evidence from logs:**
```json
{"status": null, "message": "Workflow returned invalid or missing status"}
```

**Fix Strategy:** Update mock fixtures to include complete `WorkflowResult` schema:
```python
mock_result = {
    "workflow_status": "completed",
    "content_ref": {
        "uri": f"analysis://{uuid4()}/content",
        "summary": "Test summary",
        "size_bytes": 1000,
        "content_type": "text/plain",
        "available_sections": ["summary", "full"],
    },
    "raw_content": "Test content",
    "extraction_metadata": {
        "title": "Test",
        "word_count": 100,
        "char_count": 500
    },
    "content_embedding": [0.1] * 1536,
}
```

---

### Category 3: Agent Failure Event Tests (3 failures)

**File:** `tests/unit/domains/analysis/workflows/nodes/agents/test_agent_failure_events.py`

**Failing Tests:**
1. `test_dependency_mapper_handles_timeout_error_with_specific_code`
2. `test_dependency_mapper_handles_specificity_validation_error_with_specific_code`
3. `test_dependency_mapper_handles_generic_exception_with_fallback_code`

**Root Cause:**
Patch path is wrong. Tests patch:
```python
"app.domains.analysis.workflows.nodes.agents.dependency_mapper_node.emit_agent_progress"
```

But `emit_agent_progress` is NOT defined in `dependency_mapper_node.py` - it's imported from `app.domains.analysis.workflows.agents.base`. After recent refactoring, error handling moved to `handle_agent_node_error()` in base.py.

**Error message:**
```
AttributeError: <module 'dependency_mapper_node'> does not have the attribute 'emit_agent_progress'
```

**Fix Strategy:** Update patch path to:
```python
@patch("app.domains.analysis.workflows.agents.base.emit_agent_progress", new_callable=AsyncMock)
```

---

### Category 4: Validator Legacy Tests (2 failures)

**File:** `tests/unit/domains/analysis/services/workflow/test_validator_legacy.py`

**Failing Tests:**
1. `test_validator_identifies_missing_fields`
2. `test_validator_returns_empty_list_when_all_fields_present`

**Root Cause:**
`WorkflowResult` schema updated to require `content_ref` field (Issue #244 Handle Pattern), but tests still use old schema without `content_ref`.

**Evidence:**
```
Extra items in the left set: 'content_ref'
```

**Fix Strategy:** Add `content_ref` to test fixtures:
```python
result = {
    "raw_content": "content",
    "content_ref": {
        "uri": f"analysis://{uuid4()}/content",
        "summary": "Test summary",
        "size_bytes": 1000,
        "content_type": "text/plain",
        "available_sections": ["summary", "full"],
    },
    "extraction_metadata": {"title": "Test", "word_count": 100, "char_count": 500},
    "content_embedding": [0.1] * 1536,
}
```

---

### Category 5: Status Updater Tests (2 failures)

**File:** `tests/unit/domains/analysis/services/persistence/test_status_updater.py`

**Failing Tests:**
1. `test_status_updater_update_success`
2. `test_status_updater_update_database_error`

**Root Cause (test 1):** Assertion checks `status == "complete"` but test passes status "extracting".

**Root Cause (test 2):** Implementation now re-raises database errors (intentional change), but test expects errors to be swallowed.

**Fix Strategy:**
1. Fix assertion: `"complete"` → `"extracting"`
2. Wrap call in `pytest.raises(ConnectionError)`

---

### Category 6: Config & Event Tests (5 failures)

**Files:**
- `tests/unit/core/test_config.py`
- `tests/unit/domains/analysis/services/events/test_workflow_events.py`
- `tests/unit/domains/analysis/workflows/tasks/test_generate_artifact.py`

**Failing Tests:**
1. `test_settings_loads_defaults`
2. `test_event_emitter_emit_error`
3. `test_generate_artifact_empty_aggregated_insights`
4. `test_generate_artifact_missing_aggregated_insights`
5. `test_generate_artifact_database_error`

**Root Causes:**
- **test_settings_loads_defaults:** `.env.test` autouse fixture overrides ENVIRONMENT default
- **test_event_emitter_emit_error:** Missing `stage` parameter for non-WorkflowStageError
- **generate_artifact tests:** Incomplete mocking of database session factory

---

## Implementation Plan

### Phase 1: Quick Wins (1-2 hours) - LOW RISK

| # | Test | Fix | Lines Changed |
|---|------|-----|---------------|
| 1 | test_settings_loads_defaults | Add `monkeypatch.setenv("ENVIRONMENT", "development")` | ~2 |
| 2 | test_event_emitter_emit_error | Add `stage="test"` parameter | ~1 |
| 3 | test_status_updater_update_success | Change assertion `"complete"` → `"extracting"` | ~1 |
| 4 | test_status_updater_update_database_error | Wrap in `pytest.raises(ConnectionError)` | ~3 |

**Expected Result:** 4 tests fixed

---

### Phase 2: Schema Updates (2-3 hours) - MEDIUM RISK

| # | Test File | Fix | Lines Changed |
|---|-----------|-----|---------------|
| 5-6 | test_validator_legacy.py | Add `content_ref` to fixtures | ~20 |
| 7-9 | test_orchestrator_status.py | Add complete mock data | ~30 |

**Expected Result:** 5 tests fixed

---

### Phase 3: Exception Handler (3-4 hours) - MEDIUM RISK

| # | Test File | Fix | Lines Changed |
|---|-----------|-----|---------------|
| 10-16 | test_exception_handler.py | Remove `emit_error` assertions for non-WorkflowStageError | ~50 |

**Expected Result:** 7 tests fixed

---

### Phase 4: Agent Events (2-3 hours) - MEDIUM RISK

| # | Test File | Fix | Lines Changed |
|---|-----------|-----|---------------|
| 17-19 | test_agent_failure_events.py | Update patch path to base module | ~10 |

**Expected Result:** 3 tests fixed

---

### Phase 5: Generate Artifact (3-4 hours) - HIGH RISK

| # | Test File | Fix | Lines Changed |
|---|-----------|-----|---------------|
| 20-22 | test_generate_artifact.py | Add database session factory mocking | ~40 |

**Expected Result:** 3 tests fixed

---

## Critical Files Reference

```
backend/
├── tests/unit/
│   ├── domains/analysis/
│   │   ├── services/
│   │   │   ├── workflow/
│   │   │   │   ├── test_exception_handler.py      # 7 fixes
│   │   │   │   ├── test_orchestrator_status.py    # 3 fixes
│   │   │   │   └── test_validator_legacy.py       # 2 fixes
│   │   │   ├── persistence/
│   │   │   │   └── test_status_updater.py         # 2 fixes
│   │   │   └── events/
│   │   │       └── test_workflow_events.py        # 1 fix
│   │   └── workflows/
│   │       ├── nodes/agents/
│   │       │   └── test_agent_failure_events.py   # 3 fixes
│   │       └── tasks/
│   │           └── test_generate_artifact.py      # 3 fixes
│   └── core/
│       └── test_config.py                         # 1 fix
└── app/domains/analysis/
    └── schemas/
        └── workflow_result.py                     # Reference for schema
```

---

## Verification Checklist

After each phase, run:
```bash
cd backend
poetry run pytest tests/unit/ --tb=short -q 2>&1 | grep -E "(passed|failed|error)"
```

**Expected progression:**
- After Phase 1: 18 failures → 4 fixed
- After Phase 2: 13 failures → 5 fixed
- After Phase 3: 6 failures → 7 fixed
- After Phase 4: 3 failures → 3 fixed
- After Phase 5: 0 failures → 3 fixed

---

## Notes

- **Do NOT "fix" tests by making them pass incorrectly** - understand the intended behavior first
- **Exception handler behavior is intentional** - non-WorkflowStageError exceptions should NOT emit SSE events
- **Schema changes require fixture updates** - WorkflowResult now requires `content_ref` field
- **Patch paths must match import location** - patch where function is used, not where defined
