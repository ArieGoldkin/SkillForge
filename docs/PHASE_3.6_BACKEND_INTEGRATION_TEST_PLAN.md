# Phase 3.6: Backend Error Handling Integration Tests - Comprehensive Plan

**Status**: Planning Phase  
**Based on**: E2E Test Results & Existing Test Coverage Analysis  
**Date**: December 2025

---

## 📊 Current State Analysis

### ✅ What We Already Have

```
┌─────────────────────────────────────────────────────────────────┐
│                    EXISTING TEST COVERAGE                        │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ✅ Unit Tests (Complete)                                       │
│     ├─ test_exceptions.py          → GeneratorExit detection    │
│     ├─ test_status_updater.py      → Status locking/validation  │
│     ├─ test_sse_helpers.py         → emit_error_event()         │
│     ├─ test_abort_helpers.py       → check_should_abort()       │
│     └─ test_quality_gate_node.py   → Quality gate errors        │
│                                                                  │
│  ✅ Integration Tests (Partial)                                 │
│     ├─ test_error_event_persistence.py                          │
│     │   ├─ ✅ Extraction failure → error event                  │
│     │   └─ ✅ Error event contains error_code                   │
│     │                                                           │
│     ├─ test_abort_signal.py                                     │
│     │   ├─ ✅ Abort stops subsequent nodes                      │
│     │   └─ ✅ Abort routes to workflow_failed                   │
│     │                                                           │
│     └─ test_api_contract.py                                     │
│         └─ ✅ SSE error event format validation                 │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### ❌ What's Missing (Gaps Identified)

```
┌─────────────────────────────────────────────────────────────────┐
│                      TEST COVERAGE GAPS                          │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ❌ Embedding Failure Tests                                      │
│     └─ No integration test for embedding generation failures    │
│                                                                  │
│  ❌ Supervisor Failure Tests                                    │
│     └─ No integration test for supervisor routing failures     │
│                                                                  │
│  ❌ Quality Gate Failure Tests                                   │
│     └─ No integration test for quality gate failure workflow    │
│                                                                  │
│  ❌ Agent Failure Tests                                          │
│     └─ No integration tests for individual agent failures        │
│                                                                  │
│  ❌ Aggregation Failure Tests                                    │
│     └─ No integration test for aggregation error handling       │
│                                                                  │
│  ❌ Artifact Generation Failure Tests                           │
│     └─ No integration test for artifact generation failures     │
│                                                                  │
│  ❌ Status Update Atomicity Tests                               │
│     └─ No tests for concurrent status update race conditions   │
│                                                                  │
│  ❌ SSE Event Emission Verification                             │
│     └─ Tests don't verify events are emitted to broadcaster     │
│                                                                  │
│  ❌ End-to-End Error Flow Tests                                  │
│     └─ No tests covering full error path from node → DB → SSE   │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

---

## 🎯 Phase 3.6 Requirements (From Plan)

### Acceptance Criteria Breakdown

```
┌─────────────────────────────────────────────────────────────────┐
│              PHASE 3.6 ACCEPTANCE CRITERIA                       │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  [ ] Test extraction failure emits error event                   │
│      ✅ COVERED: test_error_event_persistence.py                 │
│                                                                  │
│  [ ] Test embedding failure emits error event                    │
│      ❌ MISSING: Need new test                                   │
│                                                                  │
│  [ ] Test supervisor failure emits error event                   │
│      ❌ MISSING: Need new test                                   │
│                                                                  │
│  [ ] Test quality gate failure emits error event                 │
│      ❌ MISSING: Need new test                                   │
│                                                                  │
│  [ ] Test abort signal stops subsequent nodes                    │
│      ✅ COVERED: test_abort_signal.py                            │
│                                                                  │
│  [ ] Test error events are persisted                             │
│      ✅ COVERED: test_error_event_persistence.py                 │
│                                                                  │
│  [ ] Test status updates are atomic                              │
│      ❌ MISSING: Need new test                                   │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

---

## 🏗️ Proposed Test Architecture

### Test File Structure

```
backend/tests/integration/workflows/
└── test_error_handling.py          ← NEW FILE (Phase 3.6)
    │
    ├── Test Extraction Failures
    │   ├── ✅ test_extraction_failure_emits_error_event()
    │   └── ✅ test_extraction_failure_persists_error_event()
    │
    ├── Test Embedding Failures
    │   ├── ❌ test_embedding_failure_emits_error_event()
    │   └── ❌ test_embedding_failure_stops_workflow()
    │
    ├── Test Supervisor Failures
    │   ├── ❌ test_supervisor_failure_emits_error_event()
    │   └── ❌ test_supervisor_failure_stops_workflow()
    │
    ├── Test Quality Gate Failures
    │   ├── ❌ test_quality_gate_failure_emits_error_event()
    │   └── ❌ test_quality_gate_failure_stops_workflow()
    │
    ├── Test Agent Failures
    │   ├── ❌ test_agent_failure_emits_error_event()
    │   └── ❌ test_agent_failure_does_not_stop_workflow()
    │
    ├── Test Aggregation Failures
    │   ├── ❌ test_aggregation_failure_emits_error_event()
    │   └── ❌ test_aggregation_failure_stops_workflow()
    │
    ├── Test Artifact Generation Failures
    │   ├── ❌ test_artifact_failure_emits_error_event()
    │   └── ❌ test_artifact_failure_updates_status()
    │
    ├── Test Status Update Atomicity
    │   ├── ❌ test_concurrent_status_updates_are_serialized()
    │   └── ❌ test_invalid_status_transitions_are_rejected()
    │
    └── Test SSE Event Emission
        ├── ❌ test_error_event_emitted_to_broadcaster()
        └── ❌ test_error_event_retrievable_via_sse_stream()
```

---

## 🔄 Test Flow Architecture

### Complete Error Flow Test Pattern

```
┌─────────────────────────────────────────────────────────────────┐
│              ERROR HANDLING TEST FLOW                            │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  1. SETUP                                                       │
│     ├─ Create Analysis record in DB                             │
│     ├─ Mock service to raise specific error                     │
│     └─ Prepare test assertions                                 │
│                                                                  │
│  2. EXECUTION                                                   │
│     ├─ Run WorkflowOrchestrator.run()                          │
│     ├─ Workflow processes until error occurs                   │
│     └─ Error is caught and handled                             │
│                                                                  │
│  3. VERIFICATION (Multi-Layer)                                 │
│     │                                                           │
│     ├─ Layer 1: Database State                                 │
│     │   ├─ Analysis.status == "failed"                         │
│     │   ├─ Analysis.error_code == expected_code                │
│     │   ├─ Analysis.failed_at_stage == expected_stage           │
│     │   └─ AnalysisProgress has error event                    │
│     │                                                           │
│     ├─ Layer 2: Event Persistence                              │
│     │   ├─ Error event in analysis_progress table              │
│     │   ├─ Event has type="error"                              │
│     │   ├─ Event has status="failed"                           │
│     │   ├─ Event has stage=expected_stage                      │
│     │   ├─ Event has error message                             │
│     │   └─ Event has error_code                                │
│     │                                                           │
│     ├─ Layer 3: SSE Event Emission                             │
│     │   ├─ Event published to EventBroadcaster                 │
│     │   ├─ Event retrievable via /progress endpoint           │
│     │   └─ Event format matches SSE schema                     │
│     │                                                           │
│     └─ Layer 4: Workflow Behavior                              │
│         ├─ Subsequent nodes skipped (if abort)                 │
│         ├─ Status updates are atomic                            │
│         └─ No race conditions                                  │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

---

## 📋 Detailed Test Specifications

### Test Category 1: Embedding Failures

```python
# Test: Embedding generation failure
# Mock: OpenAI embedding API to raise exception
# Verify:
#   - Error event emitted with stage="embedding"
#   - Error event persisted to DB
#   - Analysis status = "failed"
#   - Workflow stops (abort signal)
#   - Subsequent nodes (supervisor, agents) NOT executed
```

### Test Category 2: Supervisor Failures

```python
# Test: Supervisor routing failure
# Mock: LLM call to supervisor to raise exception
# Verify:
#   - Error event emitted with stage="supervisor_routing"
#   - Error event persisted to DB
#   - Analysis status = "failed"
#   - Workflow stops
#   - Agent nodes NOT executed
```

### Test Category 3: Quality Gate Failures

```python
# Test: Quality gate failure (low quality content)
# Mock: Quality gate to return gate_passed=False
# Verify:
#   - Error event emitted with stage="quality_validation"
#   - Error event has error_code="QUALITY_GATE_FAILED"
#   - Error event persisted to DB
#   - Analysis status = "quality_gate_failed"
#   - Workflow stops
#   - Artifact generation NOT executed
```

### Test Category 4: Agent Failures

```python
# Test: Individual agent failure (e.g., tech_comparator)
# Mock: Agent LLM call to raise exception
# Verify:
#   - Error event emitted with stage="tech_comparison"
#   - Error event persisted to DB
#   - Analysis status = "failed" (or continues if partial failure allowed)
#   - Other agents may still execute (non-blocking)
#   - Aggregation handles agent failure gracefully
```

### Test Category 5: Aggregation Failures

```python
# Test: Aggregation failure
# Mock: Aggregation logic to raise exception
# Verify:
#   - Error event emitted with stage="aggregation"
#   - Error event persisted to DB
#   - Analysis status = "failed"
#   - Workflow stops
#   - Artifact generation NOT executed
```

### Test Category 6: Artifact Generation Failures

```python
# Test: Artifact generation failure
# Mock: Artifact generation to raise exception
# Verify:
#   - Error event emitted with stage="artifact_generation"
#   - Error event persisted to DB
#   - Analysis status = "artifact_failed"
#   - Analysis.artifact_id = None
#   - Workflow completes (terminal failure)
```

### Test Category 7: Status Update Atomicity

```python
# Test: Concurrent status updates
# Scenario: Multiple threads try to update status simultaneously
# Verify:
#   - Only one update succeeds (database-level locking)
#   - Status transitions are validated
#   - Invalid transitions are rejected
#   - No race conditions
#   - Final status is consistent
```

### Test Category 8: SSE Event Emission

```python
# Test: Error event emitted to SSE broadcaster
# Verify:
#   - Event published to EventBroadcaster
#   - Event retrievable via /api/v1/analyze/{id}/progress
#   - Event format matches SSE schema
#   - Event contains all required fields
#   - Event is persisted to DB
```

---

## 🔧 Implementation Strategy

### Phase 1: Core Error Event Tests (2 hours)

```
Priority: HIGH
Focus: Verify error events are emitted and persisted for all stages

Tests to Create:
├─ test_embedding_failure_emits_error_event()
├─ test_supervisor_failure_emits_error_event()
├─ test_quality_gate_failure_emits_error_event()
├─ test_agent_failure_emits_error_event()
├─ test_aggregation_failure_emits_error_event()
└─ test_artifact_failure_emits_error_event()
```

### Phase 2: Workflow Behavior Tests (1 hour)

```
Priority: HIGH
Focus: Verify abort signals and workflow stopping

Tests to Create:
├─ test_embedding_failure_stops_workflow()
├─ test_supervisor_failure_stops_workflow()
├─ test_quality_gate_failure_stops_workflow()
├─ test_aggregation_failure_stops_workflow()
└─ test_agent_failure_does_not_stop_workflow()  # Agents are non-blocking
```

### Phase 3: Status Update Tests (30 minutes)

```
Priority: MEDIUM
Focus: Verify atomic status updates and transition validation

Tests to Create:
├─ test_concurrent_status_updates_are_serialized()
└─ test_invalid_status_transitions_are_rejected()
```

### Phase 4: SSE Integration Tests (30 minutes)

```
Priority: MEDIUM
Focus: Verify SSE event emission and retrieval

Tests to Create:
├─ test_error_event_emitted_to_broadcaster()
└─ test_error_event_retrievable_via_sse_stream()
```

---

## 🧪 Test Implementation Pattern

### Standard Test Template

```python
@pytest.mark.asyncio
@pytest.mark.integration
async def test_<stage>_failure_emits_error_event(requires_database):
    """Test that <stage> failure emits error event.
    
    Flow:
    1. Create analysis record
    2. Mock <service> to raise error
    3. Run workflow orchestrator
    4. Verify error event emitted
    5. Verify error event persisted
    6. Verify analysis status updated
    """
    # 1. Setup
    analysis_id = uuid.uuid4()
    test_url = f"https://test-{analysis_id}.com"
    
    async with AsyncSessionLocal() as session:
        analysis = Analysis(
            id=analysis_id,
            url=test_url,
            content_type="article",
            status="pending",
        )
        session.add(analysis)
        await session.commit()
    
    # 2. Mock service to fail
    with patch("app.domains.analysis.workflows.tasks.<service>") as mock:
        mock.side_effect = <ExpectedException>("Error message", error_code="ERROR_CODE")
        
        # 3. Run workflow
        orchestrator = WorkflowOrchestrator()
        await orchestrator.run(analysis_id, test_url)
    
    # 4. Verify error event persisted
    event_found = await wait_for_event_persistence(analysis_id, "error", max_wait=10.0)
    assert event_found, "Error event should be persisted"
    
    # 5. Verify event structure
    async with AsyncSessionLocal() as session:
        stmt = (
            select(AnalysisProgress)
            .where(AnalysisProgress.analysis_id == analysis_id)
            .where(AnalysisProgress.progress_data["type"].astext == "error")
            .order_by(AnalysisProgress.created_at.desc())
        )
        result = await session.execute(stmt)
        error_event = result.scalar_one()
        
        assert error_event.stage == "<expected_stage>"
        assert error_event.status == "failed"
        assert error_event.progress_data.get("error_code") == "ERROR_CODE"
    
    # 6. Verify analysis status
    async with AsyncSessionLocal() as session:
        stmt = select(Analysis).where(Analysis.id == analysis_id)
        result = await session.execute(stmt)
        analysis = result.scalar_one()
        
        assert analysis.status == "failed"
        assert analysis.failed_at_stage == "<expected_stage>"
```

---

## 📊 Test Coverage Matrix

```
┌─────────────────────┬──────────┬──────────┬──────────┬──────────┐
│ Test Category       │ Unit     │ Integ    │ E2E      │ Status   │
├─────────────────────┼──────────┼──────────┼──────────┼──────────┤
│ Extraction Failure  │    ✅    │    ✅    │    ✅    │ Complete │
│ Embedding Failure   │    ✅    │    ❌    │    ❌    │ Missing  │
│ Supervisor Failure  │    ✅    │    ❌    │    ❌    │ Missing  │
│ Quality Gate Fail   │    ✅    │    ❌    │    ❌    │ Missing  │
│ Agent Failure       │    ✅    │    ❌    │    ❌    │ Missing  │
│ Aggregation Failure │    ✅    │    ❌    │    ❌    │ Missing  │
│ Artifact Failure    │    ✅    │    ❌    │    ❌    │ Missing  │
│ Abort Signal        │    ✅    │    ✅    │    ✅    │ Complete │
│ Status Atomicity    │    ✅    │    ❌    │    ❌    │ Missing  │
│ SSE Emission        │    ✅    │    ❌    │    ❌    │ Missing  │
└─────────────────────┴──────────┴──────────┴──────────┴──────────┘

Legend:
  ✅ = Covered
  ❌ = Missing
```

---

## 🎯 Key Insights from E2E Test Results

### What We Learned

1. **E2E Tests Require Full Stack**
   - Tests need backend running and processing analyses
   - Tests need real error events emitted
   - Tests validate end-to-end flow (API → DB → SSE → Frontend)

2. **Backend Integration Tests Fill the Gap**
   - Can test error handling without frontend
   - Can test database persistence directly
   - Can test SSE event emission in isolation
   - Faster execution than E2E tests

3. **Test Layers Complement Each Other**
   ```
   Unit Tests      → Test individual functions/methods
   Integration     → Test workflow + DB + SSE (Phase 3.6)
   E2E Tests       → Test full stack (API → Frontend)
   ```

---

## 🚀 Implementation Priority

### Must Have (Critical Path)

1. ✅ **Extraction failure tests** - Already covered
2. ❌ **Embedding failure tests** - High priority (early stage failure)
3. ❌ **Supervisor failure tests** - High priority (routing failure)
4. ❌ **Quality gate failure tests** - High priority (validation failure)
5. ✅ **Abort signal tests** - Already covered

### Should Have (Important)

6. ❌ **Aggregation failure tests** - Medium priority
7. ❌ **Artifact failure tests** - Medium priority
8. ❌ **Status atomicity tests** - Medium priority

### Nice to Have (Enhancement)

9. ❌ **Agent failure tests** - Lower priority (non-blocking)
10. ❌ **SSE emission verification** - Lower priority (already tested in API contract)

---

## 📝 Estimated Effort

```
┌─────────────────────────────────────────────────────────────┐
│                    EFFORT BREAKDOWN                         │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  Phase 1: Core Error Event Tests      → 2 hours            │
│  Phase 2: Workflow Behavior Tests     → 1 hour              │
│  Phase 3: Status Update Tests         → 30 minutes          │
│  Phase 4: SSE Integration Tests       → 30 minutes          │
│                                                              │
│  Total Estimated Time:                 → 4 hours            │
│                                                              │
│  Matches Plan Estimate:                → ✅ Yes             │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

---

## ✅ Next Steps

1. **Create test file**: `backend/tests/integration/workflows/test_error_handling.py`
2. **Implement Phase 1 tests** (6 tests for error event emission)
3. **Implement Phase 2 tests** (5 tests for workflow behavior)
4. **Implement Phase 3 tests** (2 tests for status atomicity)
5. **Implement Phase 4 tests** (2 tests for SSE emission)
6. **Run all tests** and verify coverage
7. **Update test documentation**

---

## 🔍 Dependencies

- ✅ Database fixtures (existing)
- ✅ WorkflowOrchestrator (existing)
- ✅ Mock patterns (existing)
- ✅ Error event persistence helpers (existing)
- ❌ SSE broadcaster test helpers (may need to create)

---

**Status**: Ready for implementation  
**Blockers**: None  
**Estimated Completion**: 4 hours
