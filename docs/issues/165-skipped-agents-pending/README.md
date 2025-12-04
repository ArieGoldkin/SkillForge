# Issue #165: Skipped Agents Show 'pending' Instead of 'skipped'

**Status:** ✅ **COMPLETE**
**Assignee:** Arie
**Story Points:** 2 pts
**Priority:** MEDIUM
**Completed:** December 4, 2025
**GitHub Issue:** [#165](https://github.com/ArieGoldkin/SkillForge/issues/165)
**PR:** [#171](https://github.com/ArieGoldkin/SkillForge/pull/171)

---

## Issue Overview

**Title:** Bug: [Frontend] Skipped agents show 'pending' instead of 'skipped'

**Description:**
When the supervisor doesn't select certain agents, they remain showing as "pending" in the UI instead of being marked as "skipped". This confuses users who may think the analysis is incomplete or stuck.

**Labels:** `bug`, `frontend`, `sse`

---

## Problem Statement

### Current Behavior (Before Fix)

Agents not selected by supervisor (e.g., Tech Comparison, Performance Audit) showed:
- Status: `pending`
- Visual: Gray/waiting state (circle icon)

### Expected Behavior

Unselected agents should show:
- Status: `skipped`
- Visual: Distinct skipped state (dimmed circle, secondary badge)

### UX Impact

Users thought the analysis was incomplete or stuck when they saw pending agents that would never run.

---

## Solution

### 1. Add 'skipped' Status Type

**File:** `frontend/src/types/sse.ts`

```typescript
export type StageStatus = 'pending' | 'running' | 'complete' | 'failed' | 'skipped'
```

### 2. Mark Optional Stages in Config

**File:** `frontend/src/features/analysis/hooks/stageConfig.ts`

Added `optional` flag to stages that can be skipped by supervisor:

```typescript
export const STAGE_CONFIG: Record<AgentStageName, StageConfig> = {
  extraction: { title: 'Content Extraction', order: 1, uiStage: 'extracting' },
  supervisor_routing: { title: 'Routing to Agents', order: 2, uiStage: 'processing' },
  tech_comparison: { title: 'Tech Comparison', order: 3, uiStage: 'analyzing', optional: true },
  security_audit: { title: 'Security Audit', order: 4, uiStage: 'analyzing', optional: true },
  // ... other optional agents
  aggregation: { title: 'Aggregating Results', order: 10, uiStage: 'generating' },
  artifact_generation: { title: 'Generating Report', order: 11, uiStage: 'generating' },
}
```

### 3. Add markSkippedAgents() Function

**File:** `frontend/src/features/analysis/hooks/stageConfig.ts`

```typescript
export function markSkippedAgents(stageStatuses: Map<AgentStageName, StageStatusEntry>): void {
  const supervisorStatus = stageStatuses.get('supervisor_routing')
  if (supervisorStatus?.status !== 'complete') return

  for (const agentStage of getOptionalStages()) {
    if (!stageStatuses.has(agentStage)) {
      stageStatuses.set(agentStage, {
        status: 'skipped',
        timestamp: supervisorStatus.timestamp,
        details: { skipped_by: 'supervisor_routing' },
      })
    }
  }
}
```

### 4. Add Visual Distinction for Skipped Status

**File:** `frontend/src/features/analysis/components/steps/AnalysisStepList.tsx`

Added skipped status handling:

```typescript
// Status type
export type AnalysisStepStatus = 'pending' | 'in-progress' | 'completed' | 'failed' | 'skipped'

// Icon for skipped status
case 'skipped':
  return <Circle className={cn(iconClasses, 'text-muted-foreground opacity-50')} />

// Badge variant for skipped status
case 'skipped':
  return 'secondary'
```

### 5. Add Description for Skipped Status

**File:** `frontend/src/features/analysis/hooks/stageHelpers.ts`

```typescript
export function getStageDescription(
  stage: AgentStageName,
  status: StageStatus,
  details?: Record<string, unknown>
): string {
  // ...
  if (status === 'skipped') {
    return 'Skipped by supervisor'
  }
  return 'Waiting...'
}
```

---

## Files Modified

1. **`frontend/src/types/sse.ts`**
   - Added `'skipped'` to `StageStatus` type

2. **`frontend/src/features/analysis/hooks/stageConfig.ts`**
   - Added `optional` flag to `StageConfig` interface
   - Marked agent stages as optional in `STAGE_CONFIG`
   - Added `getOptionalStages()` helper function
   - Added `markSkippedAgents()` function
   - Added `StageStatusEntry` interface

3. **`frontend/src/features/analysis/components/steps/AnalysisStepList.tsx`**
   - Added `'skipped'` to `AnalysisStepStatus` type
   - Added skipped icon (dimmed circle)
   - Added skipped badge variant ('secondary')

4. **`frontend/src/features/analysis/hooks/stageHelpers.ts`**
   - Added skipped status mapping in `mapStageStatus()`
   - Added "Skipped by supervisor" description

5. **`frontend/src/features/analysis/hooks/useAnalysisProgress.ts`**
   - Calls `markSkippedAgents()` after supervisor completes

---

## Acceptance Criteria

- [x] Agents not selected by supervisor show 'skipped' status
- [x] Visual distinction for skipped vs pending (dimmed, secondary badge)
- [x] Description shows "Skipped by supervisor"
- [x] Skipped agents don't affect progress calculation
- [x] Works correctly with partial agent selection

---

## Verification

**Tested Scenarios:**

1. **Full agent selection** - All agents run, none skipped
2. **Partial selection** - Supervisor selects 3/7 agents, others show skipped
3. **Visual clarity** - Skipped agents clearly distinguishable from pending
4. **Progress accurate** - Progress reaches 100% with skipped agents

---

## Related Issues

- **Issue #143:** Backend SSE completion fix
- **Issue #164:** UI progress stuck at 55% (fixed in same PR)
- **Issue #150:** Dynamic Agent Workflow Visualization

---

**Last Updated:** December 4, 2025
**Completed:** December 4, 2025
