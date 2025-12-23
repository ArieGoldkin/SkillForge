# Issue #489: SSE Frontend Shows "Analysis Failed" When Backend Succeeds

## Summary

The frontend displays "Received invalid progress event from server" and "Analysis failed" even when the backend completes the analysis successfully. This is a critical UX failure that misleads users into thinking their analysis crashed.

## Evidence

```
Tab URL: http://localhost:5173/analyze/b68afefd-4591-4da0-b4b3-6376d59f7c8a?completed=false

Page shows:
- status "Received invalid progress event from server"
- status "Analysis failed. Received invalid progress event from server"

Database shows:
SELECT status FROM analyses WHERE id = 'b68afefd-4591-4da0-b4b3-6376d59f7c8a';
-- Result: 'complete'
```

## Root Cause Analysis

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                        ISSUE #489 - EVENT FLOW DIAGRAM                       │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│   BACKEND (Working ✓)                    FRONTEND (Failing ✗)               │
│   ══════════════════                     ═══════════════════                │
│                                                                              │
│   ┌─────────────────┐                    ┌─────────────────┐                │
│   │  Workflow Node  │ ─────emit────────▶ │  EventSource    │                │
│   │   (LangGraph)   │    progress        │   (Browser)     │                │
│   └────────┬────────┘                    └────────┬────────┘                │
│            │                                      │                          │
│            ▼                                      ▼                          │
│   ┌─────────────────┐                    ┌─────────────────┐                │
│   │ EventBroadcaster│                    │  sseStore.ts    │                │
│   │ (Buffer: 100)   │ ═══════SSE═══════▶ │  handleProgress │                │
│   └────────┬────────┘                    └────────┬────────┘                │
│            │                                      │                          │
│            ▼                                      ▼                          │
│   ┌─────────────────┐                    ┌─────────────────┐                │
│   │  sse_handler.py │                    │  parseSSEEvent  │                │
│   │  (FastAPI SSE)  │                    │  (Zod Schema)   │                │
│   └────────┬────────┘                    └────────┬────────┘                │
│            │                                      │                          │
│            ▼                                      ▼                          │
│   ┌─────────────────┐                    ┌─────────────────┐                │
│   │   DB: complete  │                    │  ❌ VALIDATION  │ ◀── PROBLEM!  │
│   │   ✓ SUCCESS     │                    │     FAILED!     │                │
│   └─────────────────┘                    └─────────────────┘                │
│                                                   │                          │
│                                                   ▼                          │
│                                          ┌─────────────────┐                │
│                                          │ "Analysis Failed│                │
│                                          │  Invalid event" │                │
│                                          └─────────────────┘                │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

**Root Cause Discovery**: The frontend's Zod schema validation **rejects valid events** and sets an error state that blocks recovery:
1. **Schema strictness** - Some backend events have fields the schema doesn't expect
2. **Error cascade** - One invalid event sets `error` state, hiding subsequent valid completion
3. **No recovery** - Once error state is set, UI doesn't check REST API for actual status

---

## Solution: Approach 4 - Comprehensive (Defense in Depth)

### Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                    APPROACH 4: LAYERED DEFENSE ARCHITECTURE                      │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                  │
│   ┌─────────────────────────────────────────────────────────────────────────┐   │
│   │ LAYER 1: SSE STREAM (Primary - Real-time)                              │   │
│   │ ────────────────────────────────────────────                           │   │
│   │  • Parse events with Zod validation                                    │   │
│   │  • On validation fail: LOG ONLY, don't crash                           │   │
│   │  • Continue processing other events                                    │   │
│   └─────────────────────────────────────────────────────────────────────────┘   │
│                                          │                                       │
│                                          │ Error/Timeout/Complete                │
│                                          ▼                                       │
│   ┌─────────────────────────────────────────────────────────────────────────┐   │
│   │ LAYER 2: REST API VERIFICATION (Fallback - Authoritative)              │   │
│   │ ─────────────────────────────────────────────────────────              │   │
│   │  • On SSE error → wait 2s → check REST API                             │   │
│   │  • If REST shows complete → clear error, show success                  │   │
│   │  • If REST shows failed → keep error (it's real)                       │   │
│   └─────────────────────────────────────────────────────────────────────────┘   │
│                                          │                                       │
│                                          ▼                                       │
│   ┌─────────────────────────────────────────────────────────────────────────┐   │
│   │ LAYER 3: SMART COMPLETION HANDLING                                      │   │
│   │ ─────────────────────────────────────                                   │   │
│   │  • Verify artifact exists before showing success                        │   │
│   │  • Navigate to artifact on confirmed completion                         │   │
│   └─────────────────────────────────────────────────────────────────────────┘   │
│                                                                                  │
└─────────────────────────────────────────────────────────────────────────────────┘
```

### Solution Scoring

| Criteria | Approach 1 (Defensive) | Approach 2 (REST) | Approach 3 (Schema) | Approach 4 (Combined) |
|----------|------------------------|-------------------|---------------------|----------------------|
| Reliability | 6/10 | 9/10 | 7/10 | **10/10** |
| Implementation Speed | 9/10 | 6/10 | 5/10 | 4/10 |
| Maintainability | 7/10 | 8/10 | 8/10 | 8/10 |
| User Experience | 5/10 | 9/10 | 6/10 | **10/10** |
| Future-Proofing | 5/10 | 8/10 | 9/10 | **10/10** |
| **WEIGHTED SCORE** | 6.4 | 8.1 | 6.9 | **8.6** |
| **FINAL SCORE** | 7/10 | 9/10 | 8/10 | **10/10** |

---

## Implementation Phases

### Phase 1: Defensive Parsing (~2 hours)

**Goal**: Stop crashing on invalid events - log and continue instead.

**Files to modify**:
- `frontend/src/stores/sseStoreHelpers.ts`
- `frontend/src/stores/sseStore.ts`

**Key Change** (sseStoreHelpers.ts:229-258):

```typescript
// BEFORE: Crashes on invalid event
if (!validatedData) {
  logger.error('Progress event validation failed', { rawData })
  store.setState({
    error: new Error('Received invalid progress event from server'), // ❌ PROBLEM
  })
  return
}

// AFTER: Logs and continues
if (!validatedData) {
  logger.warn('Progress event validation failed - skipping event', {
    rawData,
    hint: 'Backend may have added new fields - schema update may be needed',
  })
  store.setState((state) => ({
    _validationFailures: state._validationFailures + 1,
  }))
  // DON'T set error state - let other events continue
  return
}
```

### Phase 2: REST API Fallback (~3 hours)

**Goal**: When SSE shows error, verify with REST API and override if needed.

**New file**: `frontend/src/features/analysis/hooks/useStatusReconciliation.ts`

```typescript
export function useStatusReconciliation({
  analysisId,
  enabled = true,
}: UseStatusReconciliationParams): ReconciliationResult {
  // When SSE error is set, wait 2 seconds then verify with REST
  useEffect(() => {
    if (!enabled || !analysisId || !error || isComplete) return

    const timeout = setTimeout(async () => {
      const status = await analyzeAPI.getAnalysisStatus(analysisId)

      if (status.status === 'complete') {
        // REST says complete - override SSE error!
        clearError()
        setComplete(true)
      }
    }, 2000)

    return () => clearTimeout(timeout)
  }, [error, analysisId])
}
```

### Phase 3: Completion Handling (~2 hours)

**Goal**: Integrate reconciliation into the progress hook.

**File to modify**: `frontend/src/features/analysis/hooks/useAnalysisProgress.ts`

```typescript
// Add reconciliation
const { reconciledStatus, reconciledArtifactId } = useStatusReconciliation({
  analysisId,
  enabled: errorInfo.hasError || isComplete,
})

// Use reconciled values
const finalIsComplete = reconciledStatus === 'complete' || isComplete
const finalHasError = reconciledStatus === 'failed' ||
                      (errorInfo.hasError && reconciledStatus !== 'complete')
```

### Phase 4: Testing & Telemetry (~2 hours)

**Goal**: Prove it works with comprehensive tests.

**Test files**:
- `frontend/src/stores/__tests__/sseStoreHelpers.test.ts` (+4 tests)
- `frontend/src/features/analysis/hooks/__tests__/useStatusReconciliation.test.ts` (+8 tests)
- `frontend/src/features/analysis/hooks/__tests__/useAnalysisProgress.integration.test.ts` (+5 tests)

---

## File-by-File Implementation Checklist

| Phase | File | Change Type | Description |
|-------|------|-------------|-------------|
| 1 | `sseStoreHelpers.ts` | Modify | Don't crash on invalid events |
| 1 | `sseStore.ts` | Modify | Add `_validationFailures`, `clearError`, `setComplete` |
| 2 | `useStatusReconciliation.ts` | **New** | REST API verification hook |
| 3 | `useAnalysisProgress.ts` | Modify | Integrate reconciliation |
| 4 | `sseStoreHelpers.test.ts` | Modify | +4 defensive parsing tests |
| 4 | `useStatusReconciliation.test.ts` | **New** | +8 reconciliation tests |
| 4 | `useAnalysisProgress.integration.test.ts` | **New** | +5 integration tests |

---

## Acceptance Criteria

- [ ] Frontend shows correct status when backend completes
- [ ] Parse errors logged but don't show as "Analysis failed"
- [ ] Fallback to REST API check if SSE is unreliable
- [ ] Add E2E test for SSE → completion flow
- [ ] All existing SSE tests pass
- [ ] TypeScript types updated
- [ ] Lint + format checks pass

---

## Implementation Dependencies

```
STEP 1                    STEP 2                    STEP 3
────────                  ────────                  ────────

┌──────────────┐         ┌──────────────┐         ┌──────────────┐
│ sseStore.ts  │────────▶│useStatusRec- │────────▶│useAnalysis-  │
│              │         │onciliation.ts│         │Progress.ts   │
│ Add actions: │         │              │         │              │
│ • clearError │         │ NEW HOOK     │         │ INTEGRATE    │
│ • setComplete│         │ (uses store) │         │ (uses hook)  │
└──────────────┘         └──────────────┘         └──────────────┘
      │
      │
      ▼
┌──────────────┐
│sseStoreHelp- │
│ers.ts        │
│              │
│ MODIFY:      │
│ Defensive    │
│ parsing      │
└──────────────┘
```

**Parallelization**: Step 1 (sseStore.ts + sseStoreHelpers.ts) can be done in parallel with test writing.

---

## References

- [MDN: Using Server-Sent Events](https://developer.mozilla.org/en-US/docs/Web/API/Server-sent_events/Using_server-sent_events)
- [SSE Protocol Best Practices](https://mcp-cloud.ai/docs/sse-protocol/best-practices)
- [AWS: Timeouts, Retries and Backoff with Jitter](https://aws.amazon.com/builders-library/timeouts-retries-and-backoff-with-jitter/)

---

## Related Files

- `frontend/src/stores/sseStore.ts` - SSE connection state management
- `frontend/src/stores/sseStoreHelpers.ts` - Event handlers (main fix location)
- `frontend/src/schemas/sse.ts` - Zod validation schemas
- `frontend/src/features/analysis/hooks/useAnalysisProgress.ts` - Progress transformation
- `frontend/src/features/analysis/hooks/useAnalysisStatus.ts` - Existing REST verification
- `frontend/src/services/api.service.ts` - REST API client
- `backend/app/api/v1/analysis/sse_handler.py` - Backend SSE endpoint
- `backend/app/shared/services/messaging/broadcaster.py` - Event buffering
