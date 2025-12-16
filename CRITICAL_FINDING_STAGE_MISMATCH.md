# 🚨 CRITICAL: Frontend/Backend Stage Name Mismatch

**Date:** 2025-12-16
**Severity:** HIGH - Blocking E2E validation
**Status:** ❌ **BLOCKING ALL FRONTEND PROGRESS TRACKING**

---

## Executive Summary

The frontend and backend use **completely different stage naming conventions** for workflow progress tracking. This causes:
- ❌ Frontend shows 0% progress while backend runs successfully
- ❌ SSE events sent but not recognized by frontend
- ❌ Impossible to validate if `integration_feasibility` stage exists
- ❌ E2E tests fail despite workflow completing successfully

---

## The Mismatch

### Backend Sends (5 Workflow Stages)
```
extraction → embedding → supervisor_routing → aggregation → quality_validation
```

**Evidence:** Backend logs from analysis `ffc9913b-8c75-411b-9381-0f43c7305338`
```
✅ extraction (complete)
✅ embedding (complete)
✅ supervisor_routing (complete) → Selected 3 agents: implementation_planner, performance_analyst, security_auditor
✅ aggregation (complete) → Synthesis phases 1-3
❌ quality_validation (failed) → Scores too low
```

### Frontend Expects (13 Agent Names)
```typescript
// frontend/src/types/sse.ts
export type AgentStageName =
  | 'extraction'
  | 'embedding'
  | 'supervisor_routing'
  | 'tech_comparison'          // ❌ NEVER SENT BY BACKEND
  | 'security_audit'           // ❌ NEVER SENT BY BACKEND
  | 'implementation_planning'  // ❌ NEVER SENT BY BACKEND
  | 'performance_audit'        // ❌ NEVER SENT BY BACKEND
  | 'code_quality_audit'       // ❌ NEVER SENT BY BACKEND
  | 'trends_analysis'          // ❌ NEVER SENT BY BACKEND
  | 'dependencies_analysis'    // ❌ NEVER SENT BY BACKEND
  | 'integration_feasibility'  // ❌ NEVER SENT BY BACKEND (NEW!)
  | 'aggregation'
  | 'artifact_generation'
```

---

## Root Cause

The frontend was designed assuming the backend would send **individual agent names** as stages (e.g., `tech_comparison`, `security_audit`).

The backend actually sends **workflow orchestration stages** (e.g., `supervisor_routing` → runs multiple agents internally).

**When supervisor_routing runs:**
- Backend: Runs 3 agents in parallel (implementation_planner, performance_analyst, security_auditor)
- Frontend expects: 3 separate SSE events (`implementation_planning`, `performance_audit`, `security_audit`)
- Frontend receives: 1 SSE event (`supervisor_routing`)
- **Result:** Frontend doesn't recognize the event, progress stuck at 0%

---

## Evidence

### Successful Backend Workflow (OpenAI gpt-4o-mini)
```
2025-12-16 17:48:44 [info] workflow_extraction_started
2025-12-16 17:48:48 [info] workflow_extraction_complete (word_count=1582)
2025-12-16 17:48:54 [info] workflow_embedding_complete
2025-12-16 17:49:09 [info] compress_all_findings_complete (agent_count=3)
2025-12-16 17:51:08 [info] workflow_aggregation_complete (findings_count=3)
2025-12-16 17:51:44 [info] quality_gate_evaluated (gate_passed=False)
```

### SSE Events Sent (Buffer Size Proof)
```
2025-12-16 17:51:08 [debug] publish_success (buffer_size=31, subscribers=1)
```

**31 SSE events were sent**, but frontend recognized **0 stages** because stage names didn't match!

### Playwright Test Results
```
❌ Test Failed: 0/13 stages detected
   - Progress: 0%
   - Stages encountered: [] (empty set)
   - Expected: ['supervisor_routing', 'content_extraction', ..., 'integration_feasibility']
   - Actual backend stages: ['extraction', 'embedding', 'supervisor_routing', 'aggregation', 'quality_validation']
```

---

## Impact Assessment

### Immediate Impact
1. ❌ **Progress bar always shows 0%** - Users think workflow is broken
2. ❌ **E2E tests fail** - Cannot validate 13-stage workflow
3. ❌ **Cannot verify `integration_feasibility` exists** - The new stage may not exist in backend at all
4. ❌ **Workflow appears stuck** - Frontend shows "Waiting for agent activity..." while backend completes successfully

### Long-term Impact
1. **Impossible to add new agents** - Frontend types are hardcoded with wrong stage names
2. **No visibility into agent execution** - Users don't know which agents are running
3. **Poor UX** - Users abandon analyses thinking they're stuck
4. **False positives in monitoring** - Alerts fire for "stuck" workflows that are actually running

---

## Questions to Resolve

1. **Does `integration_feasibility` agent exist in backend?**
   - We added it to frontend types
   - Backend logs show only 3 agents: `implementation_planner`, `performance_analyst`, `security_auditor`
   - No mention of `integration_feasibility` anywhere in backend logs

2. **What are the ACTUAL workflow stages in backend?**
   - Need to check backend source code for definitive list
   - Current evidence: `extraction`, `embedding`, `supervisor_routing`, `aggregation`, `quality_validation`

3. **Should frontend show agent names or workflow stages?**
   - **Option A:** Backend sends agent-level events (requires backend change)
   - **Option B:** Frontend shows workflow stages (requires frontend change)
   - **Option C:** Hybrid approach (show workflow stages, expand to agents)

---

## Recommended Fix

### Short-term (Unblock E2E Testing)
1. Update `frontend/src/types/sse.ts` to use ACTUAL backend stage names:
   ```typescript
   export type WorkflowStage =
     | 'extraction'
     | 'embedding'
     | 'supervisor_routing'
     | 'aggregation'
     | 'quality_validation'
     | 'artifact_generation'  // If it exists
   ```

2. Update all `AgentStageName` references to `WorkflowStage`

3. Remove agent-specific types (`tech_comparison`, `security_audit`, etc.)

### Long-term (Proper Solution)
1. **Backend:** Add agent-level SSE events during `supervisor_routing`
   - When `implementation_planner` runs → emit `{ stage: 'implementation_planning', status: 'running' }`
   - When `security_auditor` completes → emit `{ stage: 'security_audit', status: 'complete' }`

2. **Frontend:** Support both workflow stages AND agent stages
   - Show high-level progress bar for workflow stages (5 stages)
   - Show detailed progress for agent execution (8+ agents)
   - Expandable UI: Click "supervisor_routing" to see individual agents

3. **Investigate `integration_feasibility`:**
   - Search backend codebase for this agent
   - If missing: Create issue to add it
   - If exists: Find out why it's not being invoked

---

## Files to Investigate Next

### Backend
```
backend/app/workflows/nodes/supervisor_node.py       # Agent selection logic
backend/app/workflows/nodes/extraction_node.py        # Extraction stage
backend/app/workflows/nodes/aggregation_node.py       # Aggregation stage
backend/app/workflows/graph.py                        # Workflow definition
backend/app/services/event_broadcaster.py             # SSE event emission
```

### Frontend
```
frontend/src/types/sse.ts                             # Type definitions (WRONG!)
frontend/src/features/analysis/hooks/stageConfig.ts  # Stage configuration
frontend/src/features/analysis/hooks/stageHelpers.ts # Stage name mappings
frontend/src/features/analysis/components/progress/  # Progress UI
```

---

## Test Results

### Test 1: Anthropic Claude (Baseline)
- **Status:** ❌ Blocked at `supervisor_routing`
- **Cause:** API credits depleted
- **Stages reached:** 3 (extraction, embedding, supervisor_routing started)
- **Frontend recognized:** 0 stages (stage name mismatch)

### Test 2: OpenAI gpt-4o-mini (After Switch)
- **Status:** ✅ Workflow completed
- **Result:** Quality gate failed (expected for low-quality test content)
- **Stages completed:** 5 (extraction, embedding, supervisor_routing, aggregation, quality_validation)
- **Frontend recognized:** 0 stages (stage name mismatch)
- **Proof:** 31 SSE events in buffer, 1 subscriber connected

---

## Conclusion

The frontend is **functionally blind** to backend progress. Despite:
- ✅ Backend workflows completing successfully
- ✅ SSE events being sent (31 events, 1 subscriber)
- ✅ All integrations working (OpenAI, Jina, PostgreSQL)

The frontend shows:
- ❌ 0% progress
- ❌ "Waiting for agent activity..."
- ❌ No stages detected

**This is a critical architectural mismatch that blocks all frontend progress tracking.**

---

## Next Actions

1. ✅ **Document this finding** (this file)
2. 🔄 **Search backend codebase** for actual stage definitions
3. 🔄 **Check if `integration_feasibility` agent exists** in backend
4. ⏳ **Create RFC** for stage naming convention alignment
5. ⏳ **Fix frontend types** to match backend reality
6. ⏳ **Re-run E2E test** after types fixed
7. ⏳ **Add backend agent-level events** (long-term enhancement)

---

**Primary Blockers:**
1. Cannot validate 13-stage workflow (stage mismatch)
2. Cannot verify `integration_feasibility` exists (never appears in logs)
3. Cannot test frontend UI (progress always 0%)

**Status:** Requires backend codebase investigation before frontend fixes can proceed.
