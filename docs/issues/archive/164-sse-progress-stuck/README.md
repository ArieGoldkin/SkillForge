# Issue #164: UI Progress Stuck at 55% - Handle 'workflow' Stage Completion

**Status:** ✅ **COMPLETE**
**Assignee:** Arie
**Story Points:** 3 pts
**Priority:** HIGH
**Completed:** December 4, 2025
**GitHub Issue:** [#164](https://github.com/ArieGoldkin/SkillForge/issues/164)
**PR:** [#171](https://github.com/ArieGoldkin/SkillForge/pull/171)

---

## Issue Overview

**Title:** Bug: [Frontend] UI Progress stuck at 55% - handle 'workflow' stage completion

**Description:**
The UI progress bar gets stuck at 55% even though the backend completes successfully. The frontend SSE handler doesn't recognize the `workflow` stage when backend sends completion events.

**Labels:** `bug`, `frontend`, `sse`, `in-progress`

---

## Problem Statement

### Root Cause

The backend emits workflow-level events with stages that the frontend didn't recognize:

```json
{"stage": "workflow", "status": "complete"}
```

The frontend `StageName` type only included agent-specific stages, not workflow-level stages like `workflow`, `pattern_comparison`, or `metrics`.

### Impact

- Frontend logs: `[SSE] Unknown stage name from backend: workflow`
- Progress stuck at 55% because completion event was ignored
- `onComplete` callback didn't fire properly
- UI showed "Generating Report" as incomplete even though backend finished

---

## Solution

### 1. Add Workflow Stage Types

**File:** `frontend/src/types/sse.ts`

Added separate type definitions for agent stages vs workflow stages:

```typescript
// Agent stages displayed in UI
export type AgentStageName =
  | 'extraction'
  | 'supervisor_routing'
  | 'tech_comparison'
  | 'security_audit'
  | 'implementation_planning'
  | 'performance_audit'
  | 'code_quality_audit'
  | 'trends_analysis'
  | 'dependencies_analysis'
  | 'aggregation'
  | 'artifact_generation'

// Workflow-level stages (not displayed in UI)
export type WorkflowStageName = 'workflow' | 'pattern_comparison' | 'metrics'

// Combined type for SSE handling
export type StageName = AgentStageName | WorkflowStageName
```

### 2. Handle Workflow Stage in Normalizer

**File:** `frontend/src/features/analysis/hooks/stageConfig.ts`

Updated `normalizeStageNameFromBackend()` to recognize workflow stages:

```typescript
const WORKFLOW_STAGES: WorkflowStageName[] = ['workflow', 'pattern_comparison', 'metrics']

export function normalizeStageNameFromBackend(
  backendName: string
): AgentStageName | WorkflowStageName | null {
  // Check if it's a workflow-level stage (not displayed in UI)
  if (WORKFLOW_STAGES.includes(backendName as WorkflowStageName)) {
    return backendName as WorkflowStageName
  }
  // ... rest of logic
}
```

### 3. Capture artifact_id from Both Events

**File:** `frontend/src/features/analysis/hooks/useAnalysisProgress.ts`

Updated event handling to capture `artifact_id` from both `workflow` and `artifact_generation` complete events:

```typescript
// Capture artifact_id from workflow complete or artifact_generation complete
if (data.details?.artifact_id) {
  setArtifactId(data.details.artifact_id as string)
}

// Handle workflow complete event
if (normalizedStage === 'workflow' && data.status === 'complete') {
  // Workflow is complete - mark all remaining stages as complete
  // This triggers 100% progress
}
```

---

## Files Modified

1. **`frontend/src/types/sse.ts`**
   - Added `AgentStageName` type for UI-displayed stages
   - Added `WorkflowStageName` type for workflow-level stages
   - Updated `StageName` to be union of both
   - Added `'skipped'` to `StageStatus` type

2. **`frontend/src/features/analysis/hooks/stageConfig.ts`**
   - Updated to use `AgentStageName` for `STAGE_CONFIG`
   - Added `WORKFLOW_STAGES` array
   - Updated `normalizeStageNameFromBackend()` to handle workflow stages
   - Added `isAgentStage()` type guard

3. **`frontend/src/features/analysis/hooks/useAnalysisProgress.ts`**
   - Handle `workflow` stage complete event
   - Capture `artifact_id` from workflow events
   - Refactored to reduce complexity and meet linting rules

4. **`frontend/src/features/analysis/hooks/stageHelpers.ts`**
   - Updated to use `AgentStageName` type
   - Added `'skipped'` status handling

5. **`frontend/src/stores/sseStoreHelpers.ts`**
   - Fixed null safety issue: `data.details?.error`

---

## Acceptance Criteria

- [x] Frontend recognizes `workflow` stage from backend
- [x] Progress reaches 100% when workflow completes
- [x] `artifact_id` captured from workflow complete event
- [x] No "Unknown stage name" warnings in console
- [x] `onComplete` callback fires with artifact_id
- [x] Code passes linting rules (reduced complexity)

---

## Verification

**Tested Scenarios:**

1. **Full workflow completion** - Progress reaches 100%
2. **Artifact navigation** - After complete, can navigate to artifact
3. **No console warnings** - No "Unknown stage name" warnings
4. **Partial agent selection** - Supervisor selects subset of agents, progress still completes

---

## Related Issues

- **Issue #143:** Backend portion of SSE completion fix
- **Issue #165:** Skipped agents showing 'pending' (fixed in same PR)
- **Issue #40:** SSE Endpoint (defines SSE schema)

---

**Last Updated:** December 4, 2025
**Completed:** December 4, 2025
