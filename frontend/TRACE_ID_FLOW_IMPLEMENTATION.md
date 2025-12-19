# Trace ID Flow Implementation

## Overview
Fixed the frontend trace_id flow so that feedback submissions include the trace_id for Langfuse tracking. The trace_id is now extracted from SSE complete events and passed through the component tree to the FeedbackButtons component.

## Problem
Backend logs showed `trace_id=None` when feedback was submitted. The SSE events contained `trace_id` in complete events, but it was never extracted or passed to the feedback API.

## Root Cause
1. `useAnalysisProgress.ts` extracted `artifact_id` from SSE complete events but IGNORED `trace_id`
2. `AnalysisProgressData` interface had no `traceId` field
3. Component chain did not pass `traceId` through props
4. `ArtifactPage.tsx` hardcoded `traceId={null}` for FeedbackButtons

## Solution
Implemented complete trace_id plumbing from SSE events to FeedbackButtons component.

## Files Modified

### 1. `frontend/src/features/analysis/hooks/useAnalysisProgress.ts`
**Changes:**
- Added `traceId?: string` to `AnalysisProgressData` interface (line 51)
- Added `traceId?: string` to `ProcessedEvents` interface (line 76)
- Updated `processEvent()` function signature to include `traceId` in state parameter (line 101)
- Added trace_id extraction logic in `processEvent()` when handling complete events (lines 161-165):
  ```typescript
  // Capture trace_id from complete event for Langfuse feedback tracking
  const traceId = isCompleteEvent(event) ? event.trace_id : undefined
  if (traceId) {
    state.traceId = traceId
  }
  ```
- Updated `processEvents()` state initialization to include `traceId` (line 196)
- Updated `useAnalysisProgress()` return value to include `traceId` (line 649)

### 2. `frontend/src/features/analysis/components/states/CompletedAnalysisView.tsx`
**Changes:**
- Added `traceId?: string` to `CompletedAnalysisViewProps` interface (line 10)
- Added `traceId` parameter to function (line 26)
- Passed `traceId` to `AnalysisCompleteCard` component (line 53)

### 3. `frontend/src/features/analysis/AnalyzeResult.tsx`
**Changes:**
- Extracted `traceId` from `useAnalysisProgress()` hook (line 141)
- Passed `traceId` to both `CompletedAnalysisView` instances (lines 180, 195)
- Passed `traceId` to `AnalysisCompleteCard` in progress view (line 242)

### 4. `frontend/src/features/analysis/components/states/AnalysisCompleteCard.tsx`
**Changes:**
- Added `traceId?: string` to `AnalysisCompleteCardProps` interface (line 10)
- Added `traceId` parameter to function (line 21)
- Passed `traceId` to `CompleteCardContent` component (line 38)

### 5. `frontend/src/features/analysis/components/states/internal/CompleteCardContent.tsx`
**Changes:**
- Added `traceId?: string` to `CompleteCardContentProps` interface (line 10)
- Added `traceId` parameter to function (line 21)
- Passed `traceId` to `ActionButtons` component (line 54)

### 6. `frontend/src/features/analysis/components/states/internal/ActionButtons.tsx`
**Changes:**
- Added `traceId?: string` to `ActionButtonsProps` interface (line 17)
- Added `traceId` parameter to function (line 26)
- Passed `traceId` to `GuideButton` component (line 49)

### 7. `frontend/src/features/analysis/components/states/internal/GuideButton.tsx`
**Changes:**
- Added `traceId?: string` to `GuideButtonProps` interface (line 11)
- Added `traceId` parameter to function (line 15)
- Added `state={{ traceId }}` to `Link` component to pass traceId through React Router state (line 21)

### 8. `frontend/src/features/artifact/ArtifactPage.tsx`
**Changes:**
- Imported `useLocation` from `@tanstack/react-router` (line 7)
- Added location state extraction using `useLocation()` hook (lines 24-25):
  ```typescript
  const location = useLocation()
  const traceId = (location.state as { traceId?: string } | undefined)?.traceId
  ```
- Changed `traceId={null}` to `traceId={traceId ?? null}` in FeedbackButtons (line 54)

## Data Flow

```
SSE Complete Event (trace_id)
    ↓
useAnalysisProgress.ts (extract from event.trace_id)
    ↓
AnalysisProgressData.traceId
    ↓
AnalyzeResult.tsx (from hook)
    ↓
CompletedAnalysisView.tsx (prop)
    ↓
AnalysisCompleteCard.tsx (prop)
    ↓
CompleteCardContent.tsx (prop)
    ↓
ActionButtons.tsx (prop)
    ↓
GuideButton.tsx (prop)
    ↓
Link component (state={{ traceId }})
    ↓
ArtifactPage.tsx (useLocation().state.traceId)
    ↓
FeedbackButtons component (traceId prop)
    ↓
Backend API (POST /api/v1/feedback with trace_id)
```

## SSE Event Type Reference
The `trace_id` field already existed in the SSE event types:

```typescript
export interface SSECompleteEvent {
  type: 'complete'
  analysis_id: string
  stage: 'artifact_generation' | 'workflow'
  status: 'complete'
  timestamp: string
  trace_id?: string  // Langfuse trace ID for feedback submission
  artifact_id?: string
  details?: Record<string, unknown>
}
```

## Testing Verification
After these changes, when a user:
1. Completes an analysis (receives SSE complete event with trace_id)
2. Navigates to the artifact page (via "View Guide" button)
3. Clicks the feedback button (thumbs up/down)

The API call should include the `trace_id` from the original SSE event, allowing Langfuse to properly track the feedback submission.

## Code Quality
- ✅ TypeScript type checking: PASS (`npm run typecheck`)
- ✅ ESLint linting: PASS (`npm run lint`)
- ✅ No runtime errors expected
- ✅ Backward compatible (traceId is optional everywhere)

## Implementation Date
December 19, 2025
