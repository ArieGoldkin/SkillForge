# Issue #88: Backend Sends Agent Names Instead of Stage Names

**Status:** ✅ **COMPLETE**  
**Assignee:** Yonatan  
**Story Points:** 3 pts  
**Priority:** MEDIUM  
**Completed:** December 2024  
**GitHub Issue:** [#88](https://github.com/ArieGoldkin/SkillForge/issues/88)

---

## Issue Overview

**Title:** [🔵 Backend] Standardize SSE Events to Use Stage Names [3 pts]

**Description:**  
Backend was sending agent names (e.g., `implementation_planner`) in SSE events, but frontend expects stage names (e.g., `implementation_planning`). Frontend created a workaround, but backend should standardize to use proper stage names.

**Labels:** `🔵 backend`, `🐛 bug`, `api`, `sse`, `frontend-integration`

---

## Problem Statement

### Frontend Workaround (Nov 27, 2025)

Frontend had to create `normalizeStageNameFromBackend()` function to map agent names to stage names:
- Backend sent: `implementation_planner` (agent name)
- Frontend expected: `implementation_planning` (stage name)
- Frontend workaround: Added mapping function with 73 new unit tests

### Root Cause

- **File:** `backend/app/workflows/agents/base.py`
- **Issue:** SSE events used agent_type directly instead of stage_name
- **Problem:** Inconsistent naming between internal agent identifiers and external API contract

---

## Solution

Created centralized agent configuration registry with stage name mapping. All SSE events now use proper stage names from the registry.

### Implementation Approach

1. Created `backend/app/core/agent_config.py` with centralized `AGENT_REGISTRY`
2. Added `get_stage_name()` function to convert agent_type → stage_name
3. Updated `base.py` to use `get_stage_name()` for all SSE events
4. Ensured all agents use proper stage names in SSE events

---

## Files Modified

### Primary Changes

- **`backend/app/core/agent_config.py`** (NEW)
  - Centralized `AGENT_REGISTRY` with agent_type → stage_name mapping
  - `get_agent_config()` and `get_stage_name()` helper functions
  - Single source of truth for agent-to-stage mapping

- **`backend/app/workflows/agents/base.py`**
  - Line 27: Import `get_stage_name` from agent_config
  - Line 191: Use `get_stage_name(agent_type)` instead of agent_type
  - Line 195: SSE events now use `stage=stage_name` (proper stage name)

- **`backend/app/workflows/nodes/supervisor.py`**
  - Uses `get_stage_name("supervisor")` for SSE events

- **`backend/app/workflows/tasks/generate_embedding.py`**
  - Uses `get_stage_name("embedding")` for SSE events

---

## Acceptance Criteria

- [x] Centralized agent configuration registry created ✅
- [x] `get_stage_name()` function implemented ✅
- [x] All SSE events use stage names instead of agent names ✅
- [x] Frontend workaround can be removed (optional) ✅
- [x] All agents properly mapped to stage names ✅

---

## Technical Details

### ✅ Implementation (COMPLETE)

**File:** `backend/app/core/agent_config.py`

```python
# Centralized agent registry with stage name mapping
AGENT_REGISTRY: dict[str, AgentConfig] = {
    "tech_comparator": AgentConfig(
        agent_type="tech_comparator",
        stage_name="tech_comparison",  # ✅ Proper stage name
        display_name="Tech Comparison",
    ),
    "implementation_planner": AgentConfig(
        agent_type="implementation_planner",
        stage_name="implementation_planning",  # ✅ Proper stage name
        display_name="Implementation Planning",
    ),
    # ... all agents mapped
}

def get_stage_name(agent_type: str) -> StageName:
    """Get stage name for agent type."""
    return get_agent_config(agent_type).stage_name
```

**File:** `backend/app/workflows/agents/base.py` (lines 191-196)

```python
# Get stage name from agent config (single source of truth)
stage_name = get_stage_name(agent_type)  # ✅ Converts agent → stage
await emit_streaming_event(
    "progress",
    analysis_id=analysis_id,
    stage=stage_name,  # ✅ Sends stage name, not agent name
    status=status,
    agent_type=agent_type,  # Keep agent_type in details for debugging
    **kwargs,
)
```

**Verification:**
- ✅ Centralized registry in `agent_config.py`
- ✅ All SSE events use `get_stage_name()` to get proper stage names
- ✅ Frontend workaround no longer needed (but kept for backward compatibility)
- ✅ Consistent naming between backend and frontend

---

## Related Issues

- **Issue #40:** SSE Endpoint Implementation (original SSE implementation)
- **Issue #43:** SSE Client Hook (frontend workaround created Nov 27, 2025)
- Discovered during frontend-backend integration testing

---

## Verification

After implementation:

1. **Code Review:** Verified all SSE events use `get_stage_name()`
2. **Integration Test:** Verified stage names match frontend expectations
3. **Frontend:** Can remove workaround (optional, kept for backward compatibility)

---

## Notes

- Frontend workaround (`normalizeStageNameFromBackend()`) can be removed in future cleanup
- Agent registry is single source of truth for agent-to-stage mapping
- `agent_type` still included in SSE event details for debugging
- All stage names match SSE_SCHEMA.md specification
