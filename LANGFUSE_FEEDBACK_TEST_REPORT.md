# Langfuse Feedback Integration E2E Test Report

**Date:** December 19, 2025
**Test Objective:** Verify end-to-end Langfuse feedback integration from artifact page to Langfuse UI
**Status:** ⚠️ **BLOCKED - Critical Bug Found**

---

## Test Execution Summary

### Test Environment
- Frontend: http://localhost:5173 ✅ Running
- Backend API: http://localhost:8500 ✅ Running
- Langfuse UI: http://localhost:3000 ✅ Running
- Test Artifact URL: `/artifact/78151bce-52aa-4847-8ba7-db0324cdd6ff?analysisId=dff652c1-9ca3-49c2-a8be-8db528447e54`

### Test Steps Completed

#### ✅ Step 1: Navigate to Artifact Page
- **Result:** SUCCESS
- **Evidence:** Screenshots captured showing artifact page loaded
- **Observations:**
  - Markdown content rendered correctly
  - Feedback section visible with "Was this helpful?" prompt
  - Thumbs up/down buttons present and accessible

#### ✅ Step 2: Submit Thumbs-Up Feedback
- **Result:** SUCCESS (Frontend)
- **Evidence:**
  - Screenshot shows thumbs-up button in selected state (green background)
  - Button `aria-pressed="true"` attribute confirmed
  - HTTP 200 OK response from `/api/v1/annotations/feedback`
- **Observations:**
  - Frontend UI updated optimistically
  - API request completed successfully
  - No visible errors to user

#### ❌ Step 3: Verify in Langfuse Scores Page
- **Result:** FAILURE
- **Evidence:** No `user_feedback` score found in Langfuse after 20 seconds
- **Screenshots:**
  - `04-langfuse-scores-not-found.png`: Shows "Project Not Found" error
  - `07-langfuse-negative-not-found.png`: Same error for negative feedback

#### ⚠️ Step 4: Check Annotation Queue
- **Result:** NOT REACHED (test failed at Step 3)

---

## Critical Bug Discovered

### Issue: `trace_id` Not Passed to Backend

**Evidence from Backend Logs:**
```
[debug] langfuse_score_skipped_no_trace - 'No trace_id provided, skipping Langfuse submission'
```

**Root Cause Analysis:**

1. **Expected Flow (from Analysis page):**
   ```
   Analysis SSE → useAnalysisProgress extracts traceId →
   GuideButton navigation with state={{ traceId }} →
   ArtifactPage reads location.state.traceId →
   FeedbackButtons receives traceId →
   useFeedback sends to backend →
   Langfuse receives score with trace_id
   ```

2. **Actual Flow (direct URL navigation):**
   ```
   Direct URL navigation (no state) →
   ArtifactPage reads location.state.traceId → ❌ undefined →
   FeedbackButtons receives traceId=null →
   useFeedback sends trace_id=null →
   Backend skips Langfuse submission
   ```

3. **Code Evidence:**
   - `ArtifactPage.tsx:25`: `const traceId = (location.state as { traceId?: string } | undefined)?.traceId`
   - `annotation_service.py:121`: Logs show `trace_id=None` in feedback submission
   - `annotation_service.py`: Contains logic to skip Langfuse when `trace_id` is None

### Impact

- **Severity:** 🔴 **CRITICAL**
- **User Impact:** Feedback scores are **never sent to Langfuse** when users:
  - Navigate directly to artifact URL (bookmarks, shared links)
  - Refresh the artifact page
  - Access artifact from Library page
- **Only Works When:** User clicks "View Guide" from analysis progress page (preserves navigation state)

### Database Evidence

**Annotation Queue Errors:**
```sql
INSERT INTO annotation_queue (artifact_id, trace_id, reason, status, created_at, reviewed_at)
VALUES (..., None, 'negative_feedback', 'pending', datetime.datetime(..., tzinfo=timezone.utc), None)

Error: invalid input for query argument $5:
datetime.datetime(2025, 12, 19, 12, 21, ...) (can't subtract offset-naive and offset-aware datetimes)
```

**Secondary Bug Found:** Timezone-aware datetime incompatibility in annotation_queue table.

---

## Recommended Fixes

### Fix #1: Fetch `trace_id` from Analysis (RECOMMENDED)

**Implementation:**
1. Add `trace_id` field to `analyses` table (if not exists)
2. Store `trace_id` when analysis completes
3. Create GET `/api/v1/analyses/{analysis_id}` endpoint that returns `trace_id`
4. Update `ArtifactPage.tsx` to fetch `trace_id` using `analysisId` query param

**Code Changes Required:**
```typescript
// frontend/src/features/artifact/ArtifactPage.tsx
const { analysisId } = routeApi.useSearch()
const { data: analysis } = useQuery({
  queryKey: ['analysis', analysisId],
  queryFn: () => fetch(`/api/v1/analyses/${analysisId}`).then(r => r.json()),
  enabled: !!analysisId
})
const traceId = analysis?.trace_id ?? locationStateTraceId
```

**Pros:**
- Works for all navigation paths (direct URL, refresh, bookmarks)
- Single source of truth (database)
- Backward compatible with navigation state

**Cons:**
- Requires database migration
- Additional API call on artifact page load

### Fix #2: Store `trace_id` in Artifact (ALTERNATIVE)

**Implementation:**
1. Add `trace_id` column to `artifacts` table
2. Store `trace_id` when artifact is created
3. Return `trace_id` in existing GET `/api/v1/artifacts/{id}` endpoint

**Pros:**
- No additional API call (artifact already fetched)
- Simpler frontend logic

**Cons:**
- Denormalizes data (trace_id stored in multiple places)
- May not handle artifact regeneration correctly

### Fix #3: Fix Annotation Queue Datetime Bug

**File:** `backend/app/core/annotation_service.py:397`

**Change:**
```python
# Before
created_at = datetime.now(UTC)  # Timezone-aware

# After
created_at = datetime.now(UTC).replace(tzinfo=None)  # Timezone-naive to match DB column

# OR better: Update DB schema to use timezone-aware TIMESTAMP WITH TIME ZONE
```

---

## Test Artifacts

### Screenshots Captured
1. `01-artifact-initial.png` - Artifact page loaded
2. `02-before-feedback.png` - Before clicking thumbs-up
3. `03-after-feedback.png` - After feedback submission (green selected state)
4. `04-langfuse-scores-not-found.png` - Langfuse "Project Not Found" error
5. `06-comment-dialog.png` - Comment dialog for negative feedback
6. `07-langfuse-negative-not-found.png` - Negative feedback not found in Langfuse

### Log Files
- `/tmp/langfuse_test.log` - Full Playwright test output
- Backend logs: Contain `langfuse_score_skipped_no_trace` debug messages

---

## Next Steps

### Immediate Actions Required
1. ✅ **File GitHub Issue:** Track `trace_id` missing bug
2. ⚠️ **Implement Fix #1:** Add `trace_id` fetch from analysis endpoint
3. ⚠️ **Fix Datetime Bug:** Annotation queue timezone handling
4. ⚠️ **Re-run E2E Test:** Verify complete flow after fixes

### Long-term Improvements
1. **Add Integration Tests:** Test feedback submission with mocked Langfuse
2. **Add Monitoring:** Alert when feedback scores fail to submit to Langfuse
3. **Update Documentation:** Document trace_id requirement and fallback behavior

---

## Conclusion

The Langfuse feedback integration is **functionally complete** but has a critical bug that prevents scores from being submitted in most real-world scenarios. The frontend UI works correctly, the backend API accepts feedback, but the `trace_id` linkage is broken when users navigate directly to artifact URLs.

**Recommendation:** Implement Fix #1 before release to ensure feedback scores are reliably captured in Langfuse for quality improvement analysis.

---

**Test Execution Details:**
- Test Framework: Playwright v1.40+
- Test Duration: ~30 seconds per test
- Browser: Chromium (headless)
- Test File: `frontend/e2e/specs/langfuse-feedback.spec.ts`
