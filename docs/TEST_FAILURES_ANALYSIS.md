# Integration Test Failures - Comprehensive Analysis

**Date**: 2025-12-22  
**Total Failures**: 55 (down from 119)  
**Status**: Root cause analysis complete  
**Progress**: 64 tests fixed (54% reduction in failures)

## Executive Summary

This document provides a thorough analysis of the remaining 55 test failures, categorized by root cause with proposed fixes. All fixes follow professional standards and address root causes, not symptoms.

### Quick Statistics

| Category | Failures | Priority | Estimated Fix Time |
|----------|----------|----------|-------------------|
| Module Path Patches | 14 | High (Quick Win) | 1-2 hours |
| Mock Signatures | 3 | High (Quick Win) | 30 min |
| Database Constraints | 15+ | Medium | 2-3 hours |
| Status Transitions | 5 | Medium | 1-2 hours |
| Event Loop Closure | 12+ | High (Complex) | 3-4 hours |
| Agent Attributes | 2 | Medium | 30 min |
| HTTP Status Codes | 4 | High (Quick Win) | 30 min |
| Missing Imports | 3 | Low | 30 min |
| Background Tasks | 1 | Medium | 30 min |
| Assertion Logic | 4 | Medium | 1-2 hours |
| Embedding Errors | 1 | Medium | 30 min |
| **TOTAL** | **55+** | - | **12-18 hours** |

### Recommended Fix Order

1. **Phase 1** (Quick Wins): Categories 1, 2, 7 → 21 tests (2-3 hours)
2. **Phase 2** (Data Integrity): Categories 3, 4 → 20+ tests (3-4 hours)  
3. **Phase 3** (Async Issues): Category 5 → 12+ tests (3-4 hours)
4. **Phase 4** (Edge Cases): Categories 6, 8-11 → 11 tests (2-3 hours)

---

## Failure Categories

### Category 1: Incorrect Module Path Patches (14 failures)

**Root Cause**: Tests are patching modules that don't exist at the specified paths.

**Affected Tests**:
- `test_api_complete.py`: Multiple tests patching `app.api.v1.analyze`
- `test_api_contract.py`: Tests patching `app.api.v1.analyze`
- `test_library.py`: Tests patching `app.api.v1.library`
- `test_search_api.py`: All tests patching `app.api.v1.search`

**Actual Structure**:
```
app/api/v1/
  analysis/           # Package (not "analyze")
    __init__.py
    endpoints.py      # This is what tests call "analyze"
    library.py
    search.py
```

**Required Fixes**:
1. Replace `app.api.v1.analyze` → `app.api.v1.analysis.endpoints`
2. Replace `app.api.v1.library` → `app.api.v1.analysis.library`
3. Replace `app.api.v1.search` → `app.api.v1.analysis.search`

**Files to Update**:
- `backend/tests/integration/api/v1/test_api_complete.py` (6 locations)
- `backend/tests/integration/api/v1/test_api_contract.py` (4 locations)
- `backend/tests/integration/api/v1/test_library.py` (5 locations)
- `backend/tests/integration/api/v1/analysis/test_search_api.py` (14 locations)

**Estimated Impact**: 14 tests fixed

---

### Category 2: Workflow Orchestrator Mock Signature Mismatch (3 failures)

**Root Cause**: Mock functions don't match the actual `WorkflowOrchestrator.run()` signature.

**Actual Signature**:
```python
async def run(self, analysis_id: uuid.UUID, url: str, skill_level: str = "intermediate") -> None
```

**Test Mocks** (incorrect):
```python
async def mock_run_workflow_task(analysis_id: str, url: str) -> None:
    # Only 2 args, missing skill_level
```

**Affected Tests**:
- `test_post_analyze_sse_events`
- `test_post_analyze_concurrent_requests`
- `test_post_analyze_content_types` (possible)

**Required Fix**:
Update mock signatures to match actual:
```python
async def mock_run_workflow_task(analysis_id: str, url: str, skill_level: str = "intermediate") -> None:
    # Correct signature
```

**Files to Update**:
- `backend/tests/integration/api/v1/analysis/test_analyze_endpoint.py`

**Estimated Impact**: 3 tests fixed

---

### Category 3: Database Constraint Violations (15+ failures)

**Root Cause**: Tests create Analysis records with `status='complete'` but missing required fields for complete status.

**Constraints** (from schema):
1. `check_complete_has_content`: `status='complete'` requires `raw_content IS NOT NULL`
2. `check_complete_has_metadata`: `status='complete'` requires `extraction_metadata IS NOT NULL AND extraction_metadata != '{}'`
3. `check_complete_has_embedding`: `status='complete'` requires `content_embedding IS NOT NULL`
4. Embedding dimensions: Must be 1536 (not 768 or other values)

**Affected Tests**:
- `test_embedding_dimensions` - Creates complete without content/embedding
- `test_search_embedding_failure_fallback` - Complete without metadata
- `test_get_by_id_concurrent_reads` - Complete without content
- `test_get_by_id_corrupted_data` - Wrong embedding dimensions (768 vs 1536)
- `test_lz4_compression_migration` - Complete without metadata
- `test_semantic_search_success` - Complete without metadata
- `test_delete_analysis_removes_record` - Complete without content
- `test_delete_analysis_cascades` - Complete without content
- Multiple search/library tests

**Required Fix Pattern**:
```python
# Use fixture helper (if available) OR create properly
analysis = Analysis(
    id=analysis_uuid,
    url=unique_url,
    content_type="article",
    status="pending",  # Start with pending
    # OR if must be complete:
    status="complete",
    raw_content="Test content",  # REQUIRED for complete
    extraction_metadata={"title": "Test"},  # REQUIRED for complete
    content_embedding=[0.0] * 1536,  # REQUIRED for complete, MUST be 1536 dims
)
```

**Files to Update**:
- `backend/tests/integration/db/test_validation_constraints.py`
- `backend/tests/integration/api/v1/test_library.py` (multiple tests)
- `backend/tests/integration/db/repositories/test_analysis_repository_read_validation_integration.py`
- `backend/tests/integration/db/test_lz4_compression_migration.py`
- `backend/tests/integration/api/v1/test_library_delete.py`

**Estimated Impact**: 15+ tests fixed

---

### Category 4: Status Transition Violations (5 failures)

**Root Cause**: Tests attempt invalid status transitions that violate business rules.

**Error Pattern**:
```
Invalid status transition: analyzing -> complete
Allowed transitions: ['cancelled', 'analysis_failed', 'failed', 'quality_gate_failed', 'generating_artifact']
```

**Valid Transitions** (from code):
- `pending` → `extracting`, `cancelled`, `failed`, `analysis_failed`
- `extracting` → `analyzing`, `cancelled`, `failed`, `analysis_failed`
- `analyzing` → `generating_artifact`, `cancelled`, `analysis_failed`, `failed`, `quality_gate_failed`
- `generating_artifact` → `complete`, `cancelled`, `failed`, `quality_gate_failed`
- Cannot go directly from `analyzing` → `complete` (must go through `generating_artifact`)

**Affected Tests**:
- `test_orchestrator_status_consistency` - Tries `analyzing` → `complete`
- `test_workflow_status_updates_to_complete` - Tries `analyzing` → `complete`
- `test_workflow_status_updates_to_failed_on_generatorexit` - Tries `pending` → `analysis_failed` (invalid)
- Tests in `test_orchestrator_integration.py`

**Required Fix**:
1. Update workflow mocks to return valid intermediate states
2. For tests that need complete status, ensure workflow goes through: `analyzing` → `generating_artifact` → `complete`
3. For error cases, use valid failure transitions: `pending` → `failed` or `extracting` → `analysis_failed`

**Files to Update**:
- `backend/tests/integration/domains/analysis/services/workflow/test_orchestrator_integration.py`
- `backend/tests/integration/api/v1/analysis/test_analyze_endpoint.py`

**Estimated Impact**: 5 tests fixed

---

### Category 5: Event Loop Closure Errors (12+ failures)

**Root Cause**: Async resources (event loops, connections) not properly cleaned up, causing "Event loop is closed" errors.

**Error Pattern**:
```
RuntimeError: Event loop is closed
```

**Affected Tests**:
- `test_error_event_contains_error_code`
- `test_error_event_retrievable_via_sse_stream`
- `test_embedding_failure_emits_error_event`
- `test_supervisor_failure_emits_error_event`
- `test_aggregation_failure_emits_error_event`
- `test_quality_gate_failure_emits_error_event`
- `test_agent_failure_emits_error_event`
- `test_artifact_failure_emits_error_event`
- `test_concurrent_status_updates_are_serialized`
- `test_invalid_status_transitions_are_rejected`
- `test_embedding_failure_stops_workflow`
- `test_supervisor_failure_stops_workflow`
- `test_quality_gate_failure_stops_workflow`
- `test_aggregation_failure_stops_workflow`

**Root Cause Analysis**:
1. Tests create async resources (broadcasters, SSE streams, database connections)
2. Resources are closed/cleaned up but event loop is still active
3. Subsequent operations try to use closed event loop

**Required Fix Pattern**:
```python
@pytest.mark.asyncio
async def test_with_async_resources(db_session):
    """Test with proper async cleanup."""
    try:
        # Test code
        pass
    finally:
        # Explicit cleanup
        await cleanup_async_resources()
        # Ensure event loop is ready for next test
        await asyncio.sleep(0.01)  # Small delay for cleanup
```

**Alternative**: Use proper async fixtures that handle cleanup:
```python
@pytest.fixture
async def async_resource():
    resource = await create_resource()
    try:
        yield resource
    finally:
        await resource.close()
        await asyncio.sleep(0.01)  # Allow cleanup to complete
```

**Files to Update**:
- `backend/tests/integration/services/test_error_event_persistence.py`
- `backend/tests/integration/domains/analysis/workflows/error_handling/test_error_events.py`
- `backend/tests/integration/domains/analysis/workflows/error_handling/test_sse_emission.py`
- `backend/tests/integration/domains/analysis/workflows/error_handling/test_status_atomicity.py`
- `backend/tests/integration/domains/analysis/workflows/error_handling/test_workflow_abort.py`

**Estimated Impact**: 12+ tests fixed

---

### Category 6: Missing Agent Attributes (2 failures)

**Root Cause**: Tests try to patch `tech_comparator_agent` attribute that doesn't exist. The actual export is `run_tech_comparator` (a function).

**Error Pattern**:
```
AttributeError: <module 'app.domains.analysis.workflows.agents.tech_comparator'> does not have the attribute 'tech_comparator_agent'
```

**Actual Structure**: 
- Module exports: `run_tech_comparator()` function (line 110)
- Tests incorrectly patch: `tech_comparator_agent` (doesn't exist)

**Affected Tests**:
- `test_artifact_failure_emits_error_event`
- `test_agent_failure_does_not_stop_workflow`

**Required Fix**:
Replace all patches of `tech_comparator_agent` with `run_tech_comparator`:

```python
# OLD (incorrect):
patch("app.domains.analysis.workflows.agents.tech_comparator.tech_comparator_agent", ...)

# NEW (correct):
patch("app.domains.analysis.workflows.agents.tech_comparator.run_tech_comparator", ...)
```

**Files to Update**:
- `backend/tests/integration/domains/analysis/workflows/error_handling/test_error_events.py` (3 locations)
- `backend/tests/integration/domains/analysis/workflows/error_handling/test_workflow_abort.py` (2 locations)

**Note**: Ensure mock signatures match `run_tech_comparator()` function signature (check function parameters).

**Estimated Impact**: 2+ tests fixed (5 patch locations total)

---

### Category 7: HTTP Status Code Mismatches (4 failures)

**Root Cause**: Tests expect different status codes than API returns.

**Issues**:
1. Tests expect `201 Created` but API returns `200 OK` (duplicate URL scenarios)
2. Tests expect `400 Bad Request` but API returns `422 Unprocessable Entity` (validation errors)

**Affected Tests**:
- `test_api_accepts_non_uuid_analysis_id` - Expects 201, gets 200
- `test_content_type_values_match_schema` - Expects 201, gets 200
- `test_list_empty_results` - Expects 200, gets 422
- `test_search_empty_query_returns_400` - Expects 400, gets 422

**Required Fix**:
1. For duplicate URL → `200 OK` is correct (existing resource), update tests to expect 200
2. For validation errors → `422 Unprocessable Entity` is correct (FastAPI default), update tests to expect 422

**Files to Update**:
- `backend/tests/integration/api/v1/test_api_complete.py`
- `backend/tests/integration/api/v1/test_api_contract.py`
- `backend/tests/integration/api/v1/test_library.py`

**Estimated Impact**: 4 tests fixed

---

### Category 8: Missing Module Imports (3 failures)

**Root Cause**: Tests import modules that don't exist. These tests reference a `tools.langfuse.queries` module that doesn't exist in the codebase.

**Issues**:
1. `ModuleNotFoundError: No module named 'tools'` - Tests trying to import from `tools.langfuse.queries`
2. Tests are part of "Layer 4: LangSmith Query Filtering" but reference Langfuse (migration completed)
3. These utility functions (`list_runs_without_generator_exit`, `get_generator_exit_count`) don't exist

**Affected Tests**:
- `test_list_runs_without_generator_exit_filter` - Tries to import `tools.langfuse.queries.list_runs_without_generator_exit`
- `test_get_generator_exit_count` - Tries to import `tools.langfuse.queries.get_generator_exit_count`
- `test_robust_traceable_propagates_generator_exit` - GeneratorExit test (separate issue)

**Root Cause Analysis**:
- No `tools/` directory exists in backend codebase
- Tests were likely written for LangSmith migration but functionality was never implemented
- After Langfuse migration, these utilities may no longer be needed

**Required Fix Options**:

**Option 1: Skip/Mark as TODO** (if functionality not needed):
```python
@pytest.mark.skip(reason="Langfuse query utilities not implemented - may not be needed")
def test_list_runs_without_generator_exit_filter(self, mock_client_class):
    ...
```

**Option 2: Implement utilities** (if functionality is needed):
- Create `backend/scripts/langfuse/queries.py` or similar
- Implement `list_runs_without_generator_exit()` and `get_generator_exit_count()`
- Update imports to correct path

**Option 3: Delete tests** (if functionality is obsolete):
- Remove tests if Langfuse filtering is handled differently now

**Files to Update**:
- `backend/tests/integration/workflows/test_generator_exit_layers.py`

**Recommendation**: Option 1 (skip) for now, mark for future implementation review

**Estimated Impact**: 2-3 tests fixed/skipped

---

### Category 9: Background Tasks Attribute Error (1 failure)

**Root Cause**: Test tries to access `request.state.background_tasks` but FastAPI State object doesn't have this attribute in test context.

**Error Pattern**:
```
AttributeError: 'State' object has no attribute 'background_tasks'
```

**Affected Test**:
- `test_api_concurrent_requests`

**Root Cause**: The test may be accessing `request.app.state.background_tasks` incorrectly, or the test client doesn't properly simulate FastAPI's state.

**Required Fix**:
1. Use proper FastAPI test client that maintains app state
2. Mock background_tasks properly if needed
3. Ensure `request.app.state` is properly initialized in test

**File to Update**:
- `backend/tests/integration/api/v1/test_api_complete.py`

**Estimated Impact**: 1 test fixed

---

### Category 10: Test Assertion Logic Issues (4 failures)

**Root Cause**: Test assertions don't match actual behavior or test setup is incorrect.

**Issues**:
1. `test_hybrid_search_combines_results` - Assert `30 == 20` (test expects 20 but gets 30 results)
2. `test_dependency_mapper_gets_correct_tools` - Assert `'get_package' in ['get_repo']` (wrong tool list)
3. `test_workflow_status_updates_to_failed_on_generatorexit` - Expected RuntimeError not raised
4. `test_post_analyze_content_types` - Status code mismatch (200 vs 201)

**Required Fix**:
1. Review test expectations vs actual behavior
2. Update assertions to match correct behavior OR fix code if behavior is wrong
3. For `test_dependency_mapper_gets_correct_tools` - Check what tools are actually returned

**Files to Update**:
- `backend/tests/integration/db/repositories/test_chunk_repository.py`
- `backend/tests/integration/mcp/test_registry_integration.py`
- `backend/tests/integration/api/v1/analysis/test_analyze_endpoint.py`

**Estimated Impact**: 4 tests fixed

---

### Category 11: Embedding Error Handling (1 failure)

**Root Cause**: Test expects error to be caught/handled but it propagates.

**Affected Test**:
- `test_embedding_failure_emits_error_event` - `EmbeddingError: Embedding generation failed`

**Issue**: Test may be missing proper error handling or mocking setup.

**Required Fix**:
1. Ensure error is properly mocked/caught in test
2. Verify error event emission happens correctly

**File to Update**:
- `backend/tests/integration/domains/analysis/workflows/error_handling/test_error_events.py`

**Estimated Impact**: 1 test fixed

---

## Implementation Priority

### Phase 1: Quick Wins (High Impact, Low Risk)
1. **Category 1**: Module path fixes (14 tests) - Simple find/replace
2. **Category 2**: Mock signature fixes (3 tests) - Add missing parameter
3. **Category 7**: HTTP status code fixes (4 tests) - Update expectations

**Estimated Fixes**: 21 tests  
**Risk Level**: Low  
**Time Estimate**: 1-2 hours

### Phase 2: Data Integrity (Medium Impact, Medium Risk)
4. **Category 3**: Constraint violations (15+ tests) - Use proper fixtures/helpers
5. **Category 4**: Status transitions (5 tests) - Fix workflow mocks

**Estimated Fixes**: 20+ tests  
**Risk Level**: Medium  
**Time Estimate**: 2-3 hours

### Phase 3: Async Resource Management (High Impact, Higher Risk)
6. **Category 5**: Event loop closure (12+ tests) - Proper cleanup patterns

**Estimated Fixes**: 12+ tests  
**Risk Level**: Higher (can affect other tests)  
**Time Estimate**: 3-4 hours

### Phase 4: Edge Cases (Low Impact, Medium Risk)
7. **Category 6**: Missing agent attributes (2 tests) - Investigate module structure
8. **Category 8**: Missing imports (3 tests) - Fix import paths
9. **Category 9**: Background tasks (1 test) - Fix state access
10. **Category 10**: Assertion logic (4 tests) - Review and fix
11. **Category 11**: Embedding errors (1 test) - Error handling

**Estimated Fixes**: 11 tests  
**Risk Level**: Medium  
**Time Estimate**: 2-3 hours

---

## Total Estimated Impact

- **Phase 1**: 21 tests → **21 fixed**
- **Phase 2**: 20+ tests → **20+ fixed**
- **Phase 3**: 12+ tests → **12+ fixed**
- **Phase 4**: 11 tests → **11 fixed**

**Total**: 55+ tests fixed (some categories may overlap)

---

## Recommendations

1. **Start with Phase 1** - Quick wins to build momentum
2. **Test incrementally** - Run tests after each category fix
3. **Use fixtures** - Create reusable helpers for common test data patterns
4. **Document patterns** - Update test documentation with proper patterns
5. **Consider test refactoring** - Some tests may benefit from structural improvements

---

## Notes

- Some failures may resolve when fixing related categories (e.g., constraint violations may fix status transition issues)
- Event loop closure issues may require changes to test infrastructure/fixtures
- Module path fixes are straightforward but need careful verification
