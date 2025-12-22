# Orchestrator Fix Architecture Plan - Deep Research & Visualization

**Date**: December 22, 2025  
**Status**: Research & Planning  
**Goal**: Fix workflow orchestrator to handle early failures gracefully

---

## 🔍 Current Architecture Analysis

### Workflow Execution Flow

```
┌─────────────────────────────────────────────────────────────────┐
│                    CURRENT WORKFLOW FLOW                        │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  1. WorkflowOrchestrator.run()                                  │
│     │                                                            │
│     ├─ Create config (thread_id, metadata)                      │
│     ├─ Execute: analysis_workflow.ainvoke(input_state, config) │
│     │   │                                                        │
│     │   ├─ extract_content_node                                 │
│     │   │   ├─ Success → Continue                               │
│     │   │   └─ Failure → should_abort=True → workflow_failed   │
│     │   │                                                       │
│     │   ├─ _generate_embedding_node                            │
│     │   │   ├─ Success → Continue                               │
│     │   │   └─ Failure → should_abort=True → workflow_failed   │
│     │   │                                                       │
│     │   ├─ supervisor_node                                      │
│     │   ├─ agent_nodes (parallel)                               │
│     │   ├─ quality_gate_node                                    │
│     │   ├─ aggregate_findings                                   │
│     │   └─ generate_artifact                                    │
│     │                                                           │
│     └─ Return result (dict with workflow_status)               │
│                                                                  │
│  2. Orchestrator Post-Processing                                │
│     │                                                            │
│     ├─ IF result is dict:                                       │
│     │   ├─ validate_workflow_result(result)                     │
│     │   │   └─ Check: raw_content, extraction_metadata,        │
│     │   │             content_embedding                         │
│     │   │                                                       │
│     │   ├─ IF missing_fields:                                  │
│     │   │   ├─ ❌ PROBLEM: Always tries to validate, even       │
│     │   │   │   when workflow_status="failed"                   │
│     │   │   ├─ Update status to "analysis_failed"              │
│     │   │   └─ Emit error event                                │
│     │   │                                                       │
│     │   ├─ IF all fields present:                               │
│     │   │   ├─ persist_workflow_data(result)                   │
│     │   │   ├─ validate_artifact_exists()                       │
│     │   │   └─ Update status to "complete"                     │
│     │   │                                                       │
│     └─ Exception handling (GeneratorExit, RuntimeError)         │
│         └─ handle_workflow_exception()                          │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### Current Problem Flow

```
┌─────────────────────────────────────────────────────────────────┐
│                    FAILURE SCENARIO FLOW                         │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  Step 1: Embedding Fails                                        │
│     │                                                            │
│     ├─ generate_embedding() raises EmbeddingError               │
│     ├─ Node emits error event (✅ CORRECT)                      │
│     ├─ Node sets should_abort=True                              │
│     ├─ Workflow routes to workflow_failed node                 │
│     └─ workflow_failed node sets:                               │
│         ├─ workflow_status="failed"                             │
│         ├─ final_error="Embedding generation failed"            │
│         └─ Returns incomplete result (no raw_content, etc.)     │
│                                                                  │
│  Step 2: Orchestrator Receives Result                           │
│     │                                                            │
│     ├─ result = {"workflow_status": "failed", ...}             │
│     ├─ Orchestrator checks: isinstance(result, dict) → TRUE     │
│     ├─ validate_workflow_result(result)                        │
│     │   └─ ❌ PROBLEM: Missing raw_content,                    │
│     │      extraction_metadata, content_embedding               │
│     │                                                           │
│     ├─ missing_fields = ["raw_content", "extraction_metadata",│
│     │                     "content_embedding"]                   │
│     ├─ ❌ PROBLEM: Tries to update status to "analysis_failed" │
│     │   But status is already "failed" (from exception_handler)│
│     │                                                           │
│     └─ ❌ ERROR: Invalid status transition:                     │
│         failed -> analysis_failed                               │
│                                                                  │
│  Step 3: Status Transition Conflict                             │
│     │                                                            │
│     ├─ StatusUpdater.update(analysis_id, "analysis_failed")     │
│     ├─ Current status: "failed"                                 │
│     ├─ Check VALID_TRANSITIONS["failed"]                        │
│     │   └─ Allowed: {"cancelled"}                               │
│     ├─ ❌ ERROR: "analysis_failed" not in allowed transitions  │
│     └─ ValueError: Invalid status transition                    │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

---

## 🎯 Root Cause Analysis

### Issue 1: Validation Logic Doesn't Check Workflow Status

**Current Code** (orchestrator.py:138-154):
```python
if isinstance(result, dict):
    missing_fields = validate_workflow_result(result)
    if missing_fields:
        # ❌ PROBLEM: Always tries to update, even if already failed
        await self.status_updater.update(
            analysis_id, AnalysisStatus.ANALYSIS_FAILED.value
        )
```

**Problem**:
- Validates result without checking `workflow_status`
- Tries to update status even when workflow already failed
- Doesn't distinguish between "incomplete success" vs "intentional failure"

**Architectural Issue**:
- Validation assumes all incomplete results are errors
- Doesn't account for workflows that fail early (expected incomplete results)

---

### Issue 2: Status Transition Rules Are Too Strict

**Current Rules** (status_updater.py:45-67):
```python
VALID_TRANSITIONS = {
    "failed": {"cancelled"},  # ❌ Too restrictive
    "extraction_failed": {"failed", "cancelled"},
    "analysis_failed": {"failed", "cancelled"},
    # ...
}
```

**Problem**:
- `failed` can only transition to `cancelled`
- But orchestrator tries `failed -> analysis_failed`
- No way to refine a generic `failed` to a specific failure type

**Architectural Issue**:
- Generic `failed` status is terminal, but we want to refine it
- Need to allow refinement transitions (generic → specific)

---

### Issue 3: Exception Handler Sets Status Before Orchestrator

**Current Flow**:
```
1. Workflow raises exception
2. handle_workflow_exception() sets status="failed"  ← FIRST
3. Orchestrator tries to set status="analysis_failed" ← SECOND (conflicts)
```

**Problem**:
- Exception handler updates status immediately
- Orchestrator tries to update again with more specific status
- Race condition / double update conflict

**Architectural Issue**:
- Two different code paths trying to set status
- No coordination between exception handler and orchestrator

---

## 🏗️ Proposed Architecture Fix

### Solution 1: Check Workflow Status Before Validation

```
┌─────────────────────────────────────────────────────────────────┐
│              PROPOSED ORCHESTRATOR FLOW                         │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  1. Execute Workflow                                            │
│     │                                                            │
│     └─ result = await analysis_workflow.ainvoke(...)           │
│                                                                  │
│  2. Check Workflow Status FIRST                                │
│     │                                                            │
│     ├─ IF result.get("workflow_status") == "failed":           │
│     │   │                                                       │
│     │   ├─ ✅ SKIP validation (expected incomplete result)       │
│     │   ├─ ✅ SKIP persistence (no data to persist)             │
│     │   ├─ ✅ Status already set by workflow_failed node        │
│     │   └─ ✅ Return early (workflow handled failure)           │
│     │                                                           │
│     ├─ IF result.get("workflow_status") == "completed":         │
│     │   │                                                       │
│     │   ├─ Validate result (expect complete data)              │
│     │   ├─ Persist data                                         │
│     │   ├─ Validate artifact                                    │
│     │   └─ Update status to "complete"                         │
│     │                                                           │
│     └─ IF result.get("workflow_status") is None/missing:        │
│         │                                                        │
│         ├─ ⚠️ Legacy workflow (old version)                     │
│         ├─ Validate result (backward compatibility)              │
│         └─ Handle as before                                     │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### Solution 2: Allow Status Refinement Transitions

```
┌─────────────────────────────────────────────────────────────────┐
│              PROPOSED STATUS TRANSITION RULES                   │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  Current (Too Restrictive):                                     │
│  ┌─────────────────────────────────────────────┐                │
│  │ "failed": {"cancelled"}                     │                │
│  └─────────────────────────────────────────────┘                │
│                                                                  │
│  Proposed (Allow Refinement):                                   │
│  ┌─────────────────────────────────────────────┐                │
│  │ "failed": {                                 │                │
│  │   "cancelled",                              │                │
│  │   "extraction_failed",    ← Allow refinement│                │
│  │   "analysis_failed",      ← Allow refinement│                │
│  │   "artifact_failed",     ← Allow refinement│                │
│  │   "quality_gate_failed"  ← Allow refinement│                │
│  │ }                                           │                │
│  └─────────────────────────────────────────────┘                │
│                                                                  │
│  Rationale:                                                     │
│  - Generic "failed" can be refined to specific failure type     │
│  - More specific status provides better user feedback           │
│  - Still prevents invalid transitions (e.g., failed → complete)  │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### Solution 3: Coordinate Exception Handler & Orchestrator

```
┌─────────────────────────────────────────────────────────────────┐
│          PROPOSED EXCEPTION HANDLING COORDINATION               │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  Option A: Exception Handler Sets Generic Status                │
│  ┌─────────────────────────────────────────────┐                │
│  │ handle_workflow_exception():                │                │
│  │   ├─ Set status="failed" (generic)          │                │
│  │   └─ Orchestrator can refine later          │                │
│  └─────────────────────────────────────────────┘                │
│                                                                  │
│  Option B: Exception Handler Doesn't Set Status                 │
│  ┌─────────────────────────────────────────────┐                │
│  │ handle_workflow_exception():                │                │
│  │   ├─ Only emit error event                  │                │
│  │   └─ Let orchestrator set status            │                │
│  └─────────────────────────────────────────────┘                │
│                                                                  │
│  Option C: Check Status Before Updating (Recommended)            │
│  ┌─────────────────────────────────────────────┐                │
│  │ StatusUpdater.update():                     │                │
│  │   ├─ IF current_status is terminal:         │                │
│  │   │   ├─ IF to_status is refinement:        │                │
│  │   │   │   └─ ✅ Allow (refinement)           │                │
│  │   │   └─ ELSE:                               │                │
│  │   │       └─ ❌ Reject (already terminal)   │                │
│  │   └─ ELSE:                                   │                │
│  │       └─ Normal transition validation        │                │
│  └─────────────────────────────────────────────┘                │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

---

## 📊 Architecture Decision Matrix

### Approach Comparison

```
┌─────────────────────────────────────────────────────────────────┐
│              SOLUTION COMPARISON MATRIX                         │
├──────────────┬──────────────┬──────────────┬────────────────────┤
│ Approach     │ Complexity   │ Risk         │ Best Practice      │
├──────────────┼──────────────┼──────────────┼────────────────────┤
│ Check        │ Low          │ Low          │ ✅ Explicit        │
│ workflow_    │              │              │    status check    │
│ status first │              │              │                    │
├──────────────┼──────────────┼──────────────┼────────────────────┤
│ Allow        │ Medium       │ Medium       │ ✅ Flexible        │
│ refinement   │              │              │    transitions     │
│ transitions  │              │              │                    │
├──────────────┼──────────────┼──────────────┼────────────────────┤
│ Skip         │ Low          │ Low          │ ✅ Performance     │
│ validation   │              │              │    optimization    │
│ for failures │              │              │                    │
└──────────────┴──────────────┴──────────────┴────────────────────┘
```

---

## 🎯 Recommended Solution Architecture

### Phase 1: Orchestrator Status-Aware Validation

```
┌─────────────────────────────────────────────────────────────────┐
│         ORCHESTRATOR STATUS-AWARE VALIDATION FLOW                │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  result = await analysis_workflow.ainvoke(...)                  │
│                                                                  │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │ IF result.get("workflow_status") == "failed":            │   │
│  │                                                          │   │
│  │   ✅ Workflow already handled failure                    │   │
│  │   ✅ Status already set by workflow_failed node         │   │
│  │   ✅ Error events already emitted                        │   │
│  │   ✅ Return early (no validation/persistence needed)     │   │
│  └──────────────────────────────────────────────────────────┘   │
│                                                                  │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │ ELIF result.get("workflow_status") == "completed":       │   │
│  │                                                          │   │
│  │   ✅ Validate result (expect complete data)              │   │
│  │   ✅ Persist data                                        │   │
│  │   ✅ Validate artifact                                   │   │
│  │   ✅ Update status to "complete"                         │   │
│  └──────────────────────────────────────────────────────────┘   │
│                                                                  │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │ ELSE (workflow_status missing/None):                    │   │
│  │                                                          │   │
│  │   ⚠️ Legacy workflow or unexpected state                │   │
│  │   ✅ Validate result (backward compatibility)            │   │
│  │   ✅ Handle as before (existing logic)                   │   │
│  └──────────────────────────────────────────────────────────┘   │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### Phase 2: Status Refinement Transitions

```
┌─────────────────────────────────────────────────────────────────┐
│              STATUS REFINEMENT TRANSITION RULES                  │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  Principle: Generic → Specific (Refinement)                     │
│                                                                  │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │ "failed" → {"extraction_failed", "analysis_failed",      │   │
│  │            "artifact_failed", "quality_gate_failed",       │   │
│  │            "cancelled"}                                   │   │
│  │                                                           │   │
│  │ Rationale:                                               │   │
│  │ - Generic "failed" can be refined to specific type       │   │
│  │ - Provides better user feedback                          │   │
│  │ - Still prevents invalid transitions                     │   │
│  └──────────────────────────────────────────────────────────┘   │
│                                                                  │
│  Principle: Specific → Generic (Not Allowed)                   │
│                                                                  │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │ "extraction_failed" → {"failed", "cancelled"}             │   │
│  │                                                           │   │
│  │ Rationale:                                               │   │
│  │ - Specific status should not become generic              │   │
│  │ - Maintains semantic meaning                            │   │
│  └──────────────────────────────────────────────────────────┘   │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### Phase 3: Exception Handler Coordination

```
┌─────────────────────────────────────────────────────────────────┐
│         EXCEPTION HANDLER & ORCHESTRATOR COORDINATION            │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  Current Problem:                                                │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │ Exception Handler: Sets status="failed"                  │   │
│  │ Orchestrator: Tries status="analysis_failed"              │   │
│  │ Result: Conflict (invalid transition)                     │   │
│  └──────────────────────────────────────────────────────────┘   │
│                                                                  │
│  Proposed Solution:                                             │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │ Exception Handler:                                        │   │
│  │   ├─ Only handles exceptions that escape workflow         │   │
│  │   ├─ Sets generic status="failed"                        │   │
│  │   └─ Emits error event                                    │   │
│  │                                                           │   │
│  │ Orchestrator:                                             │   │
│  │   ├─ Checks workflow_status first                        │   │
│  │   ├─ IF "failed": Skip validation (already handled)      │   │
│  │   ├─ IF "completed": Validate and persist                │   │
│  │   └─ Can refine generic "failed" to specific type         │   │
│  │      (if workflow_status indicates specific failure)       │   │
│  └──────────────────────────────────────────────────────────┘   │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

---

## 🏛️ Architectural Principles

### Principle 1: Status-Aware Processing

```
┌─────────────────────────────────────────────────────────────────┐
│              STATUS-AWARE PROCESSING PRINCIPLE                   │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ✅ GOOD: Check workflow_status before processing               │
│     │                                                            │
│     ├─ IF "failed": Skip validation (expected)                  │
│     ├─ IF "completed": Validate and persist                     │
│     └─ IF missing: Handle legacy/backward compatibility        │
│                                                                  │
│  ❌ BAD: Always validate regardless of status                    │
│     │                                                            │
│     ├─ Validates failed workflows (unnecessary)                │
│     ├─ Tries to update already-failed status                    │
│     └─ Causes transition conflicts                               │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### Principle 2: Refinement Over Replacement

```
┌─────────────────────────────────────────────────────────────────┐
│              REFINEMENT TRANSITION PRINCIPLE                   │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ✅ GOOD: Allow generic → specific refinement                  │
│     │                                                            │
│     ├─ "failed" → "extraction_failed" (refinement)              │
│     ├─ "failed" → "analysis_failed" (refinement)                │
│     └─ Provides better user feedback                            │
│                                                                  │
│  ❌ BAD: Block all transitions from terminal states             │
│     │                                                            │
│     ├─ "failed" → "cancelled" only                             │
│     ├─ No way to refine generic status                         │
│     └─ Loses semantic information                               │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### Principle 3: Single Source of Truth

```
┌─────────────────────────────────────────────────────────────────┐
│              SINGLE SOURCE OF TRUTH PRINCIPLE                  │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ✅ GOOD: Workflow state drives orchestrator decisions         │
│     │                                                            │
│     ├─ workflow_status in result determines flow               │
│     ├─ Orchestrator respects workflow's decision               │
│     └─ No conflicting status updates                            │
│                                                                  │
│  ❌ BAD: Multiple code paths set status independently           │
│     │                                                            │
│     ├─ Exception handler sets status                           │
│     ├─ Orchestrator tries to set different status               │
│     └─ Causes conflicts and race conditions                    │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

---

## 🔧 Implementation Plan

### Step 1: Update Orchestrator Validation Logic

**File**: `backend/app/domains/analysis/services/workflow/orchestrator.py`

**Change**:
```python
# BEFORE (lines 138-154)
if isinstance(result, dict):
    missing_fields = validate_workflow_result(result)
    if missing_fields:
        # Always tries to update, even if already failed
        await self.status_updater.update(...)

# AFTER
if isinstance(result, dict):
    workflow_status = result.get("workflow_status")
    
    # Skip validation for failed workflows (expected incomplete results)
    if workflow_status == "failed":
        logger.debug(
            "workflow_already_failed",
            analysis_id=str(analysis_id),
            final_error=result.get("final_error"),
        )
        # Status already set by workflow_failed node
        # Error events already emitted
        return
    
    # Only validate completed workflows
    if workflow_status == "completed":
        missing_fields = validate_workflow_result(result)
        if missing_fields:
            # This is unexpected - completed workflow should have all fields
            await self.status_updater.update(...)
```

### Step 2: Update Status Transition Rules

**File**: `backend/app/domains/analysis/services/persistence/status_updater.py`

**Change**:
```python
# BEFORE (line 62)
"failed": {"cancelled"},  # Too restrictive

# AFTER
"failed": {
    "cancelled",
    "extraction_failed",    # Allow refinement
    "analysis_failed",       # Allow refinement
    "artifact_failed",       # Allow refinement
    "quality_gate_failed",   # Allow refinement
},
```

### Step 3: Add Refinement Detection Logic

**File**: `backend/app/domains/analysis/services/persistence/status_updater.py`

**Add**:
```python
# Refinement transitions: generic → specific
REFINEMENT_TRANSITIONS = {
    "failed": {
        "extraction_failed",
        "analysis_failed",
        "artifact_failed",
        "quality_gate_failed",
    }
}

def _is_refinement_transition(from_status: str, to_status: str) -> bool:
    """Check if transition is a refinement (generic → specific)."""
    refinements = REFINEMENT_TRANSITIONS.get(from_status, set())
    return to_status in refinements

# In update() method:
if current_status == to_status:
    # No-op: already at target status
    return

if _is_refinement_transition(current_status, to_status):
    # Allow refinement: generic → specific
    logger.debug(
        "status_refinement_allowed",
        analysis_id=str(analysis_id),
        from_status=current_status,
        to_status=to_status,
    )
    # Continue with update
elif not _is_valid_transition(current_status, to_status):
    # Invalid transition
    raise ValueError(...)
```

---

## 📐 Architecture Validation

### Alignment with Existing Patterns

```
┌─────────────────────────────────────────────────────────────────┐
│              ARCHITECTURE ALIGNMENT CHECK                       │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ✅ Status-Aware Processing                                      │
│     ├─ Matches workflow_status pattern in state                 │
│     ├─ Respects workflow's failure handling                     │
│     └─ Consistent with abort signal pattern                     │
│                                                                  │
│  ✅ Refinement Transitions                                       │
│     ├─ Follows existing status hierarchy                        │
│     ├─ Maintains semantic meaning                               │
│     └─ Prevents invalid transitions                              │
│                                                                  │
│  ✅ Single Source of Truth                                       │
│     ├─ Workflow state drives decisions                          │
│     ├─ Orchestrator respects workflow                          │
│     └─ No conflicting updates                                    │
│                                                                  │
│  ✅ Backward Compatibility                                       │
│     ├─ Handles missing workflow_status (legacy)                │
│     ├─ Maintains existing validation for completed workflows    │
│     └─ No breaking changes                                      │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### Best Practices Compliance

```
┌─────────────────────────────────────────────────────────────────┐
│              BEST PRACTICES VALIDATION                          │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ✅ Fail-Fast Principle                                         │
│     ├─ Check workflow_status first                              │
│     ├─ Skip unnecessary processing                             │
│     └─ Early return for failed workflows                       │
│                                                                  │
│  ✅ Separation of Concerns                                      │
│     ├─ Workflow handles execution                               │
│     ├─ Orchestrator handles post-processing                    │
│     └─ Clear boundaries                                        │
│                                                                  │
│  ✅ Idempotency                                                 │
│     ├─ Status updates are idempotent                            │
│     ├─ No-op if already at target status                       │
│     └─ Safe to retry                                            │
│                                                                  │
│  ✅ Observability                                                │
│     ├─ Log status-aware decisions                               │
│     ├─ Track refinement transitions                             │
│     └─ Clear error messages                                     │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

---

## 🎨 Complete Flow Visualization

### Fixed Orchestrator Flow

```
┌─────────────────────────────────────────────────────────────────┐
│              FIXED ORCHESTRATOR EXECUTION FLOW                  │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │ 1. Execute Workflow                                      │   │
│  │    result = await analysis_workflow.ainvoke(...)        │   │
│  └──────────────────────────────────────────────────────────┘   │
│                           │                                      │
│                           ▼                                      │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │ 2. Check Workflow Status                                 │   │
│  │    workflow_status = result.get("workflow_status")       │   │
│  └──────────────────────────────────────────────────────────┘   │
│                           │                                      │
│        ┌──────────────────┼──────────────────┐                  │
│        │                  │                  │                  │
│        ▼                  ▼                  ▼                  │
│  ┌──────────┐      ┌──────────┐      ┌──────────┐              │
│  │ "failed" │      │"completed"│      │  None/   │              │
│  │          │      │          │      │ missing  │              │
│  └──────────┘      └──────────┘      └──────────┘              │
│        │                  │                  │                  │
│        │                  │                  │                  │
│        ▼                  ▼                  ▼                  │
│  ┌──────────┐      ┌──────────┐      ┌──────────┐              │
│  │ Skip     │      │ Validate │      │ Legacy   │              │
│  │ validation│      │ & persist│      │ handling │              │
│  │          │      │          │      │          │              │
│  │ ✅ Status │      │ ✅ Check │      │ ✅ Validate│             │
│  │   already │      │   fields │      │   result  │             │
│  │   set     │      │          │      │          │             │
│  │          │      │ ✅ Persist│      │ ✅ Handle │             │
│  │ ✅ Error  │      │   data   │      │   as      │             │
│  │   events  │      │          │      │   before  │             │
│  │   emitted │      │ ✅ Check │      │          │             │
│  │          │      │   artifact│      │          │             │
│  │ ✅ Return │      │          │      │          │             │
│  │   early   │      │ ✅ Update│      │          │             │
│  │          │      │   status │      │          │             │
│  └──────────┘      └──────────┘      └──────────┘              │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### Status Transition Flow

```
┌─────────────────────────────────────────────────────────────────┐
│              STATUS TRANSITION DECISION TREE                    │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  Current Status: "failed" (generic)                             │
│        │                                                        │
│        ├─ To: "extraction_failed"                              │
│        │   └─ ✅ ALLOWED (refinement)                           │
│        │                                                        │
│        ├─ To: "analysis_failed"                                │
│        │   └─ ✅ ALLOWED (refinement)                           │
│        │                                                        │
│        ├─ To: "artifact_failed"                                │
│        │   └─ ✅ ALLOWED (refinement)                           │
│        │                                                        │
│        ├─ To: "quality_gate_failed"                             │
│        │   └─ ✅ ALLOWED (refinement)                           │
│        │                                                        │
│        ├─ To: "cancelled"                                      │
│        │   └─ ✅ ALLOWED (user action)                         │
│        │                                                        │
│        └─ To: "complete"                                       │
│            └─ ❌ REJECTED (invalid)                             │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

---

## 🔍 Research Findings

### LangGraph Best Practices

1. **Workflow State as Source of Truth**
   - Workflow should set `workflow_status` in state
   - Orchestrator should respect workflow's decision
   - Don't override workflow's status determination

2. **Incomplete Results Are Expected for Failures**
   - Failed workflows don't produce complete results
   - Validation should be conditional on success
   - Don't validate what doesn't exist

3. **Status Refinement Pattern**
   - Generic status → Specific status (refinement) is common
   - Provides better observability
   - Maintains semantic hierarchy

### Our Application Patterns

1. **Abort Signal Pattern** (Issue #441)
   - `should_abort=True` signals early termination
   - `workflow_failed` node handles cleanup
   - Orchestrator should respect this pattern

2. **Status Hierarchy**
   - Generic: `failed`
   - Specific: `extraction_failed`, `analysis_failed`, etc.
   - Refinement maintains hierarchy

3. **Error Event Emission**
   - Nodes emit error events when they fail
   - `workflow_failed` node emits final error
   - Orchestrator shouldn't duplicate error events

---

## ✅ Validation Checklist

- [x] Solution respects workflow's abort signal pattern
- [x] Solution maintains backward compatibility
- [x] Solution follows existing status hierarchy
- [x] Solution doesn't duplicate error events
- [x] Solution aligns with LangGraph best practices
- [x] Solution is testable and maintainable
- [x] Solution provides better observability
- [x] Solution prevents status transition conflicts

---

## 📋 Implementation Summary

### Changes Required

1. **Orchestrator** (`orchestrator.py`)
   - Check `workflow_status` before validation
   - Skip validation for `workflow_status="failed"`
   - Only validate completed workflows

2. **Status Updater** (`status_updater.py`)
   - Add refinement transition rules
   - Allow `failed` → specific failure types
   - Add refinement detection logic

3. **Tests** (already created)
   - Tests will pass once fixes are applied
   - No test changes needed

### Risk Assessment

- **Risk Level**: Low
- **Breaking Changes**: None (backward compatible)
- **Test Impact**: Tests will pass after fixes
- **Performance Impact**: Positive (skip unnecessary validation)

---

**Status**: Ready for Implementation  
**Estimated Time**: 2-3 hours  
**Dependencies**: None (can be implemented independently)
