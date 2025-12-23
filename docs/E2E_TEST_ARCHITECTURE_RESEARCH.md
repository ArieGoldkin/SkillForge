# E2E Test Architecture Research & Planning

**Date:** 2025-12-22  
**Purpose:** Comprehensive analysis of E2E test architecture before implementing fixes  
**Status:** 🔬 Research Phase - No Code Changes

---

## 📊 Current Test Execution Flow

### CI Workflow Execution Order

```
GitHub Actions: e2e-lightweight job
│
├─ 1. Build Docker Stack
│   ├─ postgres (pgvector)
│   ├─ backend-migrate (alembic upgrade head)
│   ├─ backend (SKILLFORGE_E2E_DISABLE_WORKFLOW=true)
│   ├─ backend-seed (runs seed_e2e_fixture.py)
│   └─ frontend-e2e (Vite dev server on port 5174)
│
├─ 2. Wait for Services
│   ├─ Backend health check (http://localhost:8500/api/v1/health)
│   └─ Frontend health check (http://localhost:5174)
│
└─ 3. Run Playwright Tests
    └─ npx playwright test --project=chromium
        └─ Executes ALL tests in frontend/e2e/specs/
            └─ Tests decide to skip based on:
                - process.env.CI
                - process.env.E2E_LLM_DISABLED
                - Data availability (getLibrary, getCompletedAnalysis)
```

### Environment Variables in CI

| Variable | Value | Purpose |
|---------|-------|---------|
| `CI` | `"true"` | Signals CI environment |
| `PLAYWRIGHT_BASE_URL` | `http://localhost:5174` | Frontend URL |
| `API_BASE_URL` | `http://localhost:8500` | Backend URL |
| `E2E_LLM_DISABLED` | `"true"` | Signals lightweight mode |
| `SKILLFORGE_E2E_DISABLE_WORKFLOW` | `"true"` | Disables workflow execution |

---

## 📁 Test File Analysis

### Test Files and Their Skip Patterns

| File | Total Tests | Skip in CI | Data-Dependent | Status |
|------|-------------|------------|----------------|--------|
| `sse-progress.spec.ts` | 1 | ❌ **0** | ✅ Yes | 🔴 **FAILING** |
| `library.spec.ts` | 9 | ⚠️ 4 (conditional) | ✅ Yes | ✅ Passing |
| `artifact.spec.ts` | 7 | ⚠️ 2 (conditional) | ✅ Yes | ✅ Passing |
| `analysis.spec.ts` | 7 | ✅ 5 | ✅ Yes | ✅ Passing |
| `home.spec.ts` | 8 | ✅ 7 | ✅ Yes | ✅ Passing |
| `error-handling.spec.ts` | 10 | ✅ 1 | ❌ No | ✅ Passing |
| `full-workflow-13-stages.spec.ts` | 3 | ✅ 3 | ✅ Yes | ✅ Passing |
| `tutor.spec.ts` | 1 | ⚠️ 1 (conditional) | ✅ Yes | ✅ Passing |
| `langfuse-feedback.spec.ts` | 1 | ⚠️ 1 (conditional) | ✅ Yes | ✅ Passing |
| `responsive.spec.ts` | 1 | ⚠️ 1 (conditional) | ❌ No | ✅ Passing |

### Skip Pattern Analysis

**Pattern 1: Always Skip in CI (Workflow Tests)**
```typescript
test.skip(!!process.env.CI, 'Requires backend LLM processing');
```
- Used by: `full-workflow-13-stages.spec.ts`, most `analysis.spec.ts`, most `home.spec.ts`
- Purpose: Tests that require real workflow execution

**Pattern 2: Conditional Skip (Data-Dependent)**
```typescript
const library = await getLibrary(request);
if (library.total === 0) {
  test.skip('No seed data available');
}
```
- Used by: `library.spec.ts`, `artifact.spec.ts`, `tutor.spec.ts`
- Purpose: Skip if seed data not available

**Pattern 3: Conditional Skip (Feature-Dependent)**
```typescript
const isLangfuseConfigured = !!process.env.LANGFUSE_PUBLIC_KEY;
test.skip(!isLangfuseConfigured, 'Langfuse not configured');
```
- Used by: `langfuse-feedback.spec.ts`
- Purpose: Skip if feature not available

**Pattern 4: No Skip (Always Run)**
```typescript
// No skip condition - test always runs
test('should show progress updates', async ({ page }) => {
  // ...
});
```
- Used by: `sse-progress.spec.ts` ❌, `error-handling.spec.ts` ✅
- Purpose: Tests that should work in all environments

---

## 🔍 Seed Data Flow Analysis

### Seed Script Execution

**File:** `backend/scripts/seed_e2e_fixture.py`

**Execution Order:**
1. Runs after `backend` service is healthy
2. Checks if completed analyses exist
3. If none exist, creates:
   - 1 `Analysis` record (status='completed')
   - 1 `Artifact` record (linked to analysis)

**Timing:**
```
backend-migrate (alembic upgrade head)
    ↓
backend (starts, becomes healthy)
    ↓
backend-seed (runs seed script)
    ↓
frontend-e2e (starts)
    ↓
Playwright tests (run)
```

**Potential Race Conditions:**
- Seed script may not complete before tests start
- Tests may query API before seed data is visible
- Database transaction isolation may hide seed data temporarily

### Seed Data Availability

**What Gets Created:**
```python
analysis = {
  id: uuid4(),
  url: "https://example.com/e2e-seed",
  content_type: "article",
  title: "E2E Seed Analysis",
  status: "completed"
}

artifact = {
  id: uuid4(),
  analysis_id: analysis.id,
  markdown_content: "# E2E Seed Artifact\n...",
  version: 1
}
```

**API Endpoints That Use Seed Data:**
- `GET /api/v1/library` - Should return 1 item
- `GET /api/v1/analyze/{id}` - Should return completed analysis
- `GET /api/v1/artifacts/{id}` - Should return artifact
- `GET /api/v1/analyze/{id}/stream` - Should return final SSE state

---

## 🐛 Problem Analysis: `sse-progress.spec.ts`

### Current Test Code

```typescript
test('should show progress updates in analysis view', async ({ page }) => {
  // ❌ No skip condition
  // ❌ No data availability check
  // ❌ No assertions (only console.logs)
  // ❌ Doesn't handle empty state
  
  await page.goto('/library');
  const analysisCards = page.locator('[class*="card"]');
  const count = await analysisCards.count();
  
  if (count > 0) {
    // Only runs if cards exist
    await analysisCards.first().click();
    // ... more code with no assertions
  }
  
  // Test passes even if nothing happens!
});
```

### Why It Fails

**Hypothesis 1: No Cards Found**
- Seed data may not be visible in UI
- Library page may not have loaded data yet
- CSS selector `[class*="card"]` may not match actual card elements
- Test doesn't wait for cards to load

**Hypothesis 2: Navigation Fails**
- Clicking card may not navigate
- Analysis page may not load
- URL may not change as expected

**Hypothesis 3: Progress Bar Not Found**
- Completed analysis may not show progress bar
- Selector may be incorrect
- Element may not be visible

**Hypothesis 4: Test Timeout**
- No explicit timeouts
- May wait indefinitely for elements
- Playwright default timeout may be exceeded

### What the Test Should Validate

**Original Intent (Inferred):**
- Library page displays analysis cards
- Clicking a card navigates to analysis page
- Analysis page shows progress/status
- SSE events are received (for in-progress analyses)

**Current Reality:**
- Test doesn't validate anything (no assertions)
- Test may pass even if nothing works
- Test may fail for unclear reasons

---

## 🎯 Fix Options Analysis

### Option 1: Add Skip Condition (Quick Fix)

**Implementation:**
```typescript
test('should show progress updates in analysis view', async ({ page }) => {
  test.skip(!!process.env.CI, 'Requires backend workflow execution');
  // ... rest of test
});
```

**Pros:**
- ✅ Quick fix (1 line)
- ✅ Follows existing pattern
- ✅ Prevents CI failure immediately

**Cons:**
- ❌ Test never runs in CI
- ❌ Doesn't validate lightweight mode behavior
- ❌ Doesn't address root cause (test design)

**Use Case:** Emergency fix to unblock PR

---

### Option 2: Make Test Work in Lightweight Mode

**Implementation:**
```typescript
test('should show progress updates in analysis view', async ({ page, request }) => {
  // Check for seed data
  const library = await getLibrary(request);
  if (library.total === 0) {
    test.skip('No seed data available');
    return;
  }
  
  // Use page objects
  const libraryPage = new LibraryPage(page);
  await libraryPage.goto();
  await libraryPage.waitForCards();
  
  // Assert cards exist
  const cardCount = await libraryPage.analysisCards.count();
  expect(cardCount).toBeGreaterThan(0);
  
  // Navigate to analysis
  await libraryPage.selectCard(0);
  await expect(page).toHaveURL(/\/analyze\/.+/);
  
  // Assert analysis page loads
  const analyzePage = new AnalyzePage(page);
  await expect(analyzePage.progressBar).toBeVisible();
});
```

**Pros:**
- ✅ Test runs in CI
- ✅ Validates lightweight mode behavior
- ✅ Uses proper page objects
- ✅ Has real assertions

**Cons:**
- ⚠️ More complex (requires refactoring)
- ⚠️ May need to adjust expectations for completed analyses

**Use Case:** Proper fix that maintains test coverage

---

### Option 3: Split into Two Tests (Best Architecture)

**Lightweight Test:**
```typescript
test('should display library with seed data (lightweight)', async ({ page, request }) => {
  // This runs in CI lightweight mode
  const library = await getLibrary(request);
  
  const libraryPage = new LibraryPage(page);
  await libraryPage.goto();
  await libraryPage.waitForCards();
  
  if (library.total > 0) {
    await expect(libraryPage.analysisCards.first()).toBeVisible();
    
    // Navigate to completed analysis
    await libraryPage.selectCard(0);
    await expect(page).toHaveURL(/\/analyze\/.+/);
    
    // Completed analysis should show completion state
    const analyzePage = new AnalyzePage(page);
    await analyzePage.waitForComplete();
  } else {
    await expect(libraryPage.emptyState).toBeVisible();
  }
});
```

**Full Workflow Test:**
```typescript
test('should show real-time SSE progress updates', async ({ page }) => {
  test.skip(!!process.env.CI, 'Requires backend LLM processing');
  
  // Create new analysis and watch SSE stream
  const homePage = new HomePage(page);
  await homePage.goto();
  await homePage.submitUrl('https://example.com/article');
  
  // Wait for navigation
  await page.waitForURL(/\/analyze\/.+/);
  
  // Monitor SSE events
  const analyzePage = new AnalyzePage(page);
  await expect(analyzePage.progressBar).toBeVisible();
  
  // Wait for progress updates
  await analyzePage.waitForProgress(50); // At least 50% progress
});
```

**Pros:**
- ✅ Clear separation of concerns
- ✅ Both tests serve different purposes
- ✅ Lightweight test validates CI behavior
- ✅ Full workflow test validates real-time behavior

**Cons:**
- ⚠️ More work (2 tests instead of 1)
- ⚠️ Need to maintain both tests

**Use Case:** Long-term architecture improvement

---

## 🏗️ Recommended Architecture

### Test Classification System

**Category 1: Lightweight UI Tests** (Always Run in CI)
- Purpose: Validate UI rendering, navigation, basic functionality
- Requirements: No workflow execution, no LLM calls
- Examples: Error handling, responsive design, basic navigation

**Category 2: Data-Dependent Tests** (Run if Data Available)
- Purpose: Validate features that require seed data
- Requirements: Check data availability, skip gracefully if none
- Examples: Library display, artifact preview, completed analysis view

**Category 3: Workflow Tests** (Skip in CI)
- Purpose: Validate full workflow execution
- Requirements: Real LLM calls, workflow execution
- Examples: Full analysis workflow, real-time SSE streaming

**Category 4: Feature-Dependent Tests** (Skip if Feature Unavailable)
- Purpose: Validate optional features
- Requirements: Check feature availability
- Examples: Langfuse feedback, advanced search modes

### Test Helper Functions

**Proposed: `frontend/e2e/utils/test-helpers.ts`**

```typescript
/**
 * Skip test if no seed data is available
 */
export function skipIfNoData(condition: boolean, message: string = 'No seed data available') {
  if (!condition) {
    test.skip(message);
  }
}

/**
 * Skip test in lightweight CI mode
 */
export function skipInLightweightMode(reason: string = 'Requires backend workflow execution') {
  test.skip(!!process.env.CI && process.env.E2E_LLM_DISABLED === 'true', reason);
}

/**
 * Skip test in CI (always)
 */
export function skipInCI(reason: string = 'Requires backend LLM processing') {
  test.skip(!!process.env.CI, reason);
}

/**
 * Assert seed data exists before running test
 */
export async function requireSeedData(request: APIRequestContext) {
  const library = await getLibrary(request);
  if (library.total === 0) {
    throw new Error('Seed data required but not available');
  }
  return library;
}
```

### Test Structure Pattern

**Recommended Pattern:**
```typescript
test.describe('Feature Name', () => {
  test.beforeAll(async ({ request }) => {
    await waitForBackend(request);
  });

  test.beforeEach(async ({ page, request }) => {
    // Check data availability if needed
    const library = await getLibrary(request);
    skipIfNoData(library.total > 0);
    
    // Setup page objects
    const featurePage = new FeaturePage(page);
    await featurePage.goto();
  });

  test('should work in lightweight mode', async ({ page }) => {
    // Test that works with seed data
    // No skip condition - runs in CI
  });

  test('should work with real-time updates', async ({ page }) => {
    skipInCI('Requires backend LLM processing');
    // Test that requires workflow execution
  });
});
```

---

## 📋 Implementation Plan

### Phase 1: Immediate Fix (Unblock PR)

**Goal:** Fix failing test to unblock PR #457

**Actions:**
1. Add skip condition to `sse-progress.spec.ts`
2. Verify CI job passes
3. Document why test is skipped

**Time:** 5 minutes  
**Risk:** Low (test won't run, but won't fail)

---

### Phase 2: Proper Fix (Maintain Coverage)

**Goal:** Make test work in lightweight mode with proper assertions

**Actions:**
1. Refactor `sse-progress.spec.ts` to use page objects
2. Add data availability check
3. Add proper assertions
4. Handle empty state gracefully
5. Test locally in lightweight mode
6. Verify CI job passes

**Time:** 30-60 minutes  
**Risk:** Medium (may need to adjust expectations)

---

### Phase 3: Architecture Improvement (Long-term)

**Goal:** Establish clear test classification and patterns

**Actions:**
1. Create test helper functions
2. Document test classification system
3. Refactor existing tests to use helpers
4. Add test examples for each category
5. Update CI workflow documentation

**Time:** 2-4 hours  
**Risk:** Low (improves maintainability)

---

## 🎯 Decision Matrix

| Option | Time | Risk | Coverage | Maintainability | Recommendation |
|--------|------|------|----------|-----------------|----------------|
| **Option 1: Skip** | 5 min | Low | ❌ None | ✅ Simple | 🔴 Emergency only |
| **Option 2: Refactor** | 30-60 min | Medium | ✅ Maintained | ✅ Good | 🟡 **Recommended** |
| **Option 3: Split** | 2-4 hours | Low | ✅ Improved | ✅✅ Excellent | 🟢 Long-term |

---

## 📝 Questions to Resolve

1. **What is the actual failure?**
   - Need to see CI logs to understand exact error
   - Is it timeout? Element not found? Assertion failure?

2. **Is seed data reliably available?**
   - Check if seed script always completes before tests
   - Verify seed data is visible via API before tests run

3. **What should the test validate?**
   - For completed analyses: Should it show completion state?
   - For in-progress: Should it show progress bar?
   - For empty state: Should it handle gracefully?

4. **Should we maintain test coverage?**
   - If we skip, we lose coverage of library → analysis navigation
   - If we refactor, we maintain coverage with proper assertions

---

## 🔍 Next Steps

1. **Review CI logs** to understand exact failure
2. **Test locally** in lightweight mode to reproduce
3. **Decide on fix approach** based on time constraints
4. **Implement fix** following chosen approach
5. **Verify** fix works in CI
6. **Document** decision and patterns for future tests

---

**Status:** ✅ Research Complete - Ready for Implementation Decision

