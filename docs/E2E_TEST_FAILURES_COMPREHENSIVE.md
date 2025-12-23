# E2E Test Failures - Comprehensive Analysis

**Date**: December 22, 2025  
**Test Run**: Full suite (71 tests)  
**Result**: **28 FAILED | 29 PASSED | 12 SKIPPED | 2 DID NOT RUN**

## Executive Summary

The test environment is **partially functional** but has **critical issues** preventing many tests from passing. The main problems are:

1. **Navigation failures** - Tests can't navigate to analysis pages after URL submission
2. **Request context disposal** - Playwright request contexts timing out
3. **Missing UI elements** - Tests can't find expected DOM elements
4. **Backend health check timeouts** - Some tests fail before they even start
5. **Library page structure** - Tests expect `[role="list"]` but structure may differ

## Detailed Failure Analysis

### Category 1: Navigation Timeouts (15 failures)

**Problem**: Tests submit URLs but never navigate to `/analyze/{id}` pages.

**Affected Tests**:
- `home.spec.ts`: 5 tests failing on `page.waitForURL(/\/analyze\/.+/, { timeout: 10000 })`
- `full-workflow-13-stages.spec.ts`: 3 tests failing on navigation
- All tests that create new analyses

**Root Cause Analysis**:
```typescript
// frontend/src/features/home/Home.tsx:36
navigate({ to: '/analyze/$id', params: { id: response.analysis_id } })
```

The navigation code looks correct. Possible issues:
1. **API call failing silently** - The `analyzeAPI.createAnalysis()` might be throwing errors
2. **Navigation not completing** - TanStack Router navigation might be async and not awaited
3. **Frontend errors** - JavaScript errors preventing navigation
4. **CORS/Network issues** - API calls might be blocked

**Evidence**:
- Backend logs show analyses ARE being created successfully
- API endpoint `/api/v1/analyze` returns `analysis_id` correctly
- Tests timeout after 10 seconds waiting for navigation

**Impact**: **CRITICAL** - Core user flow broken

---

### Category 2: Request Context Disposal (7 failures)

**Problem**: Playwright `APIRequestContext` is disposed before requests complete.

**Affected Tests**:
- All `analysis.spec.ts` tests (7 failures)
- Tests using `getCompletedAnalysis()` helper

**Error Pattern**:
```
Error: apiRequestContext.get: Request context disposed.
Call log:
  - → GET http://localhost:8501/api/v1/library?limit=20&status=complete
```

**Root Cause**:
The `beforeAll` hook calls `waitForBackend(request)` which might be timing out (30s), causing the request context to be disposed. Then subsequent tests try to use the disposed context.

**Code Location**:
```typescript
// frontend/e2e/specs/analysis.spec.ts:12
test.beforeAll(async ({ request }) => {
  await waitForBackend(request);  // This might timeout
});
```

**Impact**: **HIGH** - All analysis page tests fail

---

### Category 3: Missing UI Elements (3 failures)

**Problem**: Tests can't find expected DOM elements.

**Affected Tests**:
- `artifact.spec.ts`: 
  - `should preview markdown content` - Can't find `getByTestId('markdown-preview')`
  - `should display code blocks from markdown` - Same issue
  - `should have download button visible` - Can't find `getByTestId('download-button')`

**Root Cause**:
1. **Test IDs missing** - Frontend components might not have these test IDs
2. **Component not rendering** - Artifact page might not be loading content
3. **Timing issues** - Elements might load after test timeout

**Impact**: **MEDIUM** - Artifact page functionality untested

---

### Category 4: Error Handling Issues (2 failures)

**Problem**: Error handling tests don't detect errors properly.

**Affected Tests**:
- `error-handling.spec.ts:13` - `should handle API errors gracefully on invalid URL submission`
  - Expected error to be displayed OR navigation to occur
  - Neither happened
- `error-handling.spec.ts:46` - `should handle malformed URL submission`
  - Expected alert or error text, but none found

**Root Cause**:
1. **No client-side validation** - Form might submit invalid URLs to backend
2. **Error UI not implemented** - Errors might not be displayed to user
3. **Error handling logic missing** - Backend errors might not be caught/displayed

**Impact**: **MEDIUM** - Poor user experience on errors

---

### Category 5: Library Page Structure (4 failures)

**Problem**: Tests can't find `[role="list"]` element.

**Affected Tests**:
- `library.spec.ts:26` - `should display analysis cards when data exists`
- `library.spec.ts:47` - `should search library by query`
- `library.spec.ts:152` - `should show empty state or no results for non-existent search`
- `sse-progress.spec.ts:22` - `should display library and navigate to analysis page`

**Error Pattern**:
```
TimeoutError: locator.waitFor: Timeout 10000ms exceeded.
Call log:
  - waiting for locator('[role="list"]') to be visible
```

**Root Cause**:
The library page uses `SkillGridView` which has `role="list"` on line 130, but:
1. **Component might not be rendering** - Library page might not load
2. **Different structure** - Actual DOM might use different role/selector
3. **Loading state** - Component might be in loading state indefinitely

**Impact**: **HIGH** - Library functionality untested

---

### Category 6: Backend Health Check Timeouts (4 failures)

**Problem**: `beforeAll` hooks timing out on `waitForBackend()`.

**Affected Tests**:
- `home.spec.ts:89` - GitHub repo URL test
- `home.spec.ts:122` - Backend API test
- `home.spec.ts:167` - Preserve URL test
- `library.spec.ts:106` - Toggle search modes test

**Error Pattern**:
```
"beforeAll" hook timeout of 30000ms exceeded.
  at test.beforeAll(async ({ request }) => {
    await waitForBackend(request);
```

**Root Cause**:
The backend health check (`/api/v1/health`) might be:
1. **Slow to respond** - Taking >30 seconds
2. **Failing** - Returning non-200 status
3. **Network issues** - Request not reaching backend

**Impact**: **HIGH** - Tests can't even start

---

## Backend Issues Found

### 1. MCP Client Configuration Error

**Error**:
```
TypeError: MultiServerMCPClient.__init__() got an unexpected keyword argument 'use_tool_name_prefix'. 
Did you mean 'tool_name_prefix'?
```

**Location**: `backend/app/shared/services/mcp/client.py`

**Impact**: MCP tools not loading, but workflow still runs (graceful degradation)

**Fix Required**: Change `use_tool_name_prefix` to `tool_name_prefix`

---

### 2. Langfuse Prompt Fetch 401 Error

**Error**:
```
Error while fetching prompt 'analysis-agent-trend-validator-label:production': 
status_code: 401, body: {'message': "Invalid credentials. Confirm that you've configured the correct host.", 'error': 'UnauthorizedError'}
```

**Location**: Langfuse prompt fetching

**Impact**: Some prompts might not load, but fallback prompts are used

**Fix Required**: Verify Langfuse credentials in `backend/.env.test`

---

## Test Infrastructure Issues

### 1. Test Timeouts Too Short

Many tests use 10-second timeouts for operations that can take longer:
- Navigation: 10s (might need 15-20s)
- API calls: 30s (might need 60s for full workflow)
- UI element waits: 5-10s (might need 15s)

### 2. Parallel Test Execution

Tests run with 8 workers in parallel, which might cause:
- Resource contention
- Database connection limits
- Race conditions

### 3. Request Context Lifecycle

`beforeAll` hooks create request contexts that might be disposed before tests complete.

---

## What's Working ✅

1. **Basic UI Tests** (29 passed):
   - Home page form display
   - URL input validation (some)
   - Responsive design tests (all 7 passed)
   - Error handling (some scenarios)
   - Artifact download (1 test passed)
   - Library page display (1 test passed)

2. **Backend API**:
   - Health endpoint working
   - Analysis creation working
   - Library endpoint working (returns 5 items)

3. **Test Infrastructure**:
   - Playwright setup correct
   - Test runner script working
   - Environment variables loading correctly

---

## Recommendations

### Immediate Fixes (Critical)

1. **Fix Navigation Issues**
   - Add error logging to `Home.tsx` handleSubmit
   - Verify API response structure matches expected format
   - Add navigation completion wait
   - Check for JavaScript errors in browser console

2. **Fix Request Context Disposal**
   - Increase `waitForBackend` timeout to 60s
   - Use `test.beforeEach` instead of `test.beforeAll` for request context
   - Or create new request context per test

3. **Fix Library Page Tests**
   - Verify actual DOM structure of library page
   - Update selectors to match actual implementation
   - Add loading state handling

### Short-term Fixes (High Priority)

4. **Add Missing Test IDs**
   - Add `data-testid="markdown-preview"` to artifact markdown container
   - Add `data-testid="download-button"` to download button
   - Verify all test IDs exist in components

5. **Improve Error Handling**
   - Add client-side URL validation
   - Display error messages to users
   - Add error UI components

6. **Fix Backend Issues**
   - Fix MCP client parameter name
   - Verify Langfuse credentials

### Long-term Improvements

7. **Increase Test Timeouts**
   - Navigation: 20s
   - Full workflow: 180s (3 minutes)
   - API calls: 60s

8. **Reduce Parallel Workers**
   - Use 4 workers instead of 8
   - Or run critical tests sequentially

9. **Add Test Retries**
   - Retry flaky tests 2-3 times
   - Mark truly flaky tests with `@flaky` tag

---

## Test Results Breakdown

### By Test File

| File | Passed | Failed | Skipped | Total |
|------|--------|--------|---------|-------|
| `home.spec.ts` | 2 | 5 | 1 | 8 |
| `analysis.spec.ts` | 0 | 7 | 1 | 8 |
| `artifact.spec.ts` | 4 | 3 | 0 | 7 |
| `error-handling.spec.ts` | 9 | 2 | 0 | 11 |
| `full-workflow-13-stages.spec.ts` | 0 | 3 | 0 | 3 |
| `library.spec.ts` | 2 | 4 | 2 | 8 |
| `responsive.spec.ts` | 7 | 0 | 0 | 7 |
| `sse-progress.spec.ts` | 2 | 1 | 0 | 3 |
| `langfuse-feedback.spec.ts` | 0 | 0 | 2 | 2 |
| `tutor.spec.ts` | 0 | 0 | 6 | 6 |
| Other | 3 | 0 | 0 | 3 |
| **TOTAL** | **29** | **28** | **12** | **71** |

### By Category

| Category | Passed | Failed | Success Rate |
|----------|--------|--------|--------------|
| UI/Display | 15 | 3 | 83% |
| Form Submission | 2 | 5 | 29% |
| Navigation | 0 | 15 | 0% |
| API Integration | 4 | 7 | 36% |
| Error Handling | 9 | 2 | 82% |
| Responsive Design | 7 | 0 | 100% |

---

## Investigation Steps

### Step 1: Manual Navigation Test

**Test the actual user flow manually:**

1. Open browser: http://localhost:5174
2. Open DevTools Console (F12)
3. Submit a URL: `https://example.com/test`
4. Watch for:
   - Network requests to `/api/v1/analyze`
   - Console errors
   - Navigation behavior
   - URL changes

**Expected**: Should navigate to `/analyze/{id}`  
**Actual**: Need to verify

### Step 2: Check API Response Format

**Verify backend response matches frontend expectations:**

```bash
curl -X POST http://localhost:8501/api/v1/analyze \
  -H "Content-Type: application/json" \
  -d '{"url":"https://example.com/test"}' | jq
```

**Expected Response**:
```json
{
  "analysis_id": "uuid-here",
  "sse_endpoint": "/api/v1/analyze/{id}/stream",
  "url": "https://example.com/test",
  "content_type": "article",
  "status": "pending"
}
```

**Check**: Does frontend `analyzeAPI.createAnalysis()` expect this exact format?

### Step 3: Check Frontend Error Handling

**Verify errors are being caught and logged:**

```typescript
// frontend/src/features/home/Home.tsx:27
const handleSubmit = async (e: React.FormEvent) => {
  // ... existing code ...
  try {
    const response = await analyzeAPI.createAnalysis({ url, skill_level: skillLevel })
    // Add logging here:
    console.log('Analysis created:', response)
    console.log('Navigating to:', `/analyze/${response.analysis_id}`)
    navigate({ to: '/analyze/$id', params: { id: response.analysis_id } })
  } catch (err) {
    // Is this being triggered?
    console.error('Navigation failed:', err)
    // ... existing error handling ...
  }
}
```

### Step 4: Check TanStack Router Configuration

**Verify route is properly configured:**

- Check `frontend/src/routes/` for `/analyze/$id` route
- Verify route is not lazy-loaded incorrectly
- Check for route guards that might block navigation

---

## Immediate Action Items

### Priority 1: Navigation Failures (15 tests)

**Action 1.1**: Add comprehensive logging to `Home.tsx`
```typescript
// Add before navigate call:
logger.info('Navigating to analysis', { 
  analysisId: response.analysis_id,
  url: response.url 
})
```

**Action 1.2**: Verify API response structure
- Check if `response.analysis_id` exists
- Check if response matches `AnalyzeResponse` type

**Action 1.3**: Test navigation manually
- Open http://localhost:5174
- Submit URL
- Check browser console for errors
- Check Network tab for API calls

**Action 1.4**: Increase navigation timeout in tests
```typescript
// Change from 10s to 20s
await page.waitForURL(/\/analyze\/.+/, { timeout: 20000 });
```

### Priority 2: Request Context Disposal (7 tests)

**Action 2.1**: Refactor `beforeAll` to `beforeEach`
```typescript
// Instead of:
test.beforeAll(async ({ request }) => {
  await waitForBackend(request);
});

// Use:
test.beforeEach(async ({ request }) => {
  await waitForBackend(request);
});
```

**Action 2.2**: Increase `waitForBackend` timeout
```typescript
// frontend/e2e/utils/api-helpers.ts:149
export async function waitForBackend(
  request: APIRequestContext, 
  timeout = 60000  // Change from 30000 to 60000
): Promise<void>
```

**Action 2.3**: Add retry logic
```typescript
// Retry health check 3 times with exponential backoff
```

### Priority 3: Library Page Structure (4 tests)

**Action 3.1**: Inspect actual DOM
- Open http://localhost:5174/library
- Inspect element where cards should be
- Verify actual `role` attribute

**Action 3.2**: Update selector
```typescript
// If structure is different, update:
// frontend/e2e/page-objects/library.page.ts:85
// Change from '[role="list"]' to actual selector
```

### Priority 4: Missing Test IDs (3 tests)

**Action 4.1**: Add test IDs to components
- `ArtifactPage`: Add `data-testid="markdown-preview"`
- `ArtifactPage`: Add `data-testid="download-button"`
- Verify all test IDs exist

**Action 4.2**: Update page objects
- Verify selectors match actual implementation

### Priority 5: Backend Issues

**Action 5.1**: Fix MCP client parameter
```python
# backend/app/shared/services/mcp/client.py
# Change: use_tool_name_prefix → tool_name_prefix
```

**Action 5.2**: Verify Langfuse credentials
- Check `backend/.env.test` has correct `LANGFUSE_PUBLIC_KEY` and `LANGFUSE_SECRET_KEY`
- Test Langfuse connection manually

---

## Test Environment Configuration Issues

### Issue: Duplicate package.json Key

**Fixed**: Changed `test:integration` to `test:integration:unit` to avoid conflict with E2E test script.

### Issue: Environment Variable Loading

**Status**: Working correctly - `.env.test` is loaded by test runner script.

### Issue: CORS Configuration

**Status**: Configured correctly - `CORS_ORIGINS: ["http://localhost:5174","http://localhost:5175"]`

---

## Root Cause Hypothesis

### Navigation Failures

**Most Likely Cause**: API call is failing silently or navigation is not being triggered.

**Evidence**:
1. Backend creates analyses successfully (logs confirm)
2. Tests timeout waiting for navigation
3. No JavaScript errors visible in test output

**Possible Scenarios**:
1. **API call throws error** - Caught by try/catch but error not displayed
2. **Response format mismatch** - `response.analysis_id` might be undefined
3. **Navigation blocked** - Route guard or condition preventing navigation
4. **Async timing** - Navigation happens but test checks too early

**Investigation Needed**:
- Add console.log to `Home.tsx` handleSubmit
- Check browser DevTools during manual test
- Verify API response in Network tab

---

## Conclusion

The test environment is **functional but has critical issues**. The main blocker is **navigation failures** preventing 15+ tests from passing. Once navigation is fixed, we should see significant improvement in pass rate.

**Current State**: 41% pass rate (29/71)  
**Target State**: 80%+ pass rate  
**Estimated Fix Time**: 4-6 hours for critical issues

**Critical Path**:
1. Fix navigation (15 tests) → +21% pass rate
2. Fix request context (7 tests) → +10% pass rate
3. Fix library page (4 tests) → +6% pass rate
4. Fix missing test IDs (3 tests) → +4% pass rate

**Total Potential**: 41% → 82% pass rate after fixes

