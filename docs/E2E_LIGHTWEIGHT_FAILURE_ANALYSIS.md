# E2E Lightweight Test Failure - Root Cause Analysis

**Date:** 2025-12-22  
**PR:** #457 - "Refactor: Remove backwards compatibility and reorganize workflow tests"  
**Failing Job:** `e2e-lightweight`  
**GitHub Actions Run:** https://github.com/ArieGoldkin/SkillForge/actions/runs/20426353382/job/58687359643?pr=457

---

## 🔍 Executive Summary

The `e2e-lightweight` CI job is failing because **`sse-progress.spec.ts`** runs in CI without proper skip conditions or assertions. The test expects library data and SSE progress updates, but in lightweight mode (workflow disabled), the test environment may not have the expected data or behavior.

**Root Cause:** Test architecture mismatch - test runs in CI but doesn't account for lightweight mode constraints.

---

## 📊 Failure Analysis

### Test That's Failing

**File:** `frontend/e2e/specs/sse-progress.spec.ts`  
**Test:** `should show progress updates in analysis view`

### Why It's Failing

1. **No Skip Condition**: Unlike other tests that require LLM processing, this test has NO `test.skip(!!process.env.CI, ...)` condition
2. **Expects Data**: Test navigates to `/library` and expects to find analysis cards
3. **No Assertions**: Test only logs information - no actual assertions to validate behavior
4. **Workflow Disabled**: In lightweight mode, `SKILLFORGE_E2E_DISABLE_WORKFLOW=true`, so:
   - New analyses won't complete (workflow never runs)
   - Only seeded data exists (from `seed_e2e_fixture.py`)
   - SSE streams may not behave as expected

### Test Code Issues

```typescript
test('should show progress updates in analysis view', async ({ page }) => {
  // ❌ No skip condition for CI
  // ❌ No assertions - only console.logs
  // ❌ Doesn't handle empty state
  // ❌ Doesn't verify seed data exists
  
  await page.goto('/library');
  const analysisCards = page.locator('[class*="card"]');
  const count = await analysisCards.count();
  
  if (count > 0) {
    // Only runs if cards exist - but what if they don't?
    await analysisCards.first().click();
    // ... more code with no assertions
  }
  
  // Test passes even if nothing happens!
});
```

---

## 🏗️ Architecture Issues

### 1. **Inconsistent Test Skip Patterns**

**Current State:**
- ✅ `full-workflow-13-stages.spec.ts` - Skips in CI (requires LLM)
- ✅ `analysis.spec.ts` - Most tests skip in CI
- ✅ `home.spec.ts` - Most tests skip in CI
- ❌ `sse-progress.spec.ts` - **NO skip condition**
- ❌ `library.spec.ts` - Some tests skip conditionally (data-dependent)

**Problem:** No clear pattern for which tests should run in lightweight mode.

### 2. **Lightweight Mode Behavior**

**Environment Variables:**
- `E2E_LLM_DISABLED: "true"` (set in workflow)
- `SKILLFORGE_E2E_DISABLE_WORKFLOW: "true"` (set in docker-compose)

**Impact:**
- Workflow orchestrator is disabled (line 249 in `endpoints.py`)
- No real LLM calls
- No workflow execution
- Only seeded data available

**Expected Behavior:**
- Tests should validate UI rendering, navigation, API connectivity
- Tests should NOT require workflow execution
- Tests should handle empty/minimal data gracefully

### 3. **Seed Data Reliability**

**Seed Script:** `backend/scripts/seed_e2e_fixture.py`
- Creates 1 completed analysis + artifact
- Only runs if no completed analyses exist
- May not be visible in UI if:
  - Seed runs after test starts
  - UI hasn't loaded data yet
  - Database query fails

**Problem:** Test assumes seed data is always available and visible.

---

## 🔧 Root Cause Summary

### Primary Issue
**Test runs in CI but doesn't account for lightweight mode constraints.**

1. **Missing Skip Condition**: Test should either skip in CI or be designed for lightweight mode
2. **No Assertions**: Test logs but doesn't validate anything
3. **Data Assumptions**: Test assumes library has cards without checking seed data availability
4. **No Error Handling**: Test doesn't handle empty state or missing data gracefully

### Secondary Issues
1. **Inconsistent Test Patterns**: Some tests skip in CI, others don't - no clear strategy
2. **Seed Data Timing**: Seed script may run after test starts, causing race conditions
3. **Test Design**: Test is more of a "smoke test" than a proper E2E test

---

## ✅ Recommended Fixes

### Fix 1: Add Proper Skip Condition (Quick Fix)

```typescript
test('should show progress updates in analysis view', async ({ page }) => {
  // Skip in CI lightweight mode - this test requires workflow execution
  test.skip(!!process.env.CI, 'Requires backend workflow execution');
  
  // ... rest of test
});
```

**Pros:** Quick fix, follows existing pattern  
**Cons:** Test won't run in CI at all

### Fix 2: Make Test Work in Lightweight Mode (Better Fix)

```typescript
test('should show progress updates in analysis view', async ({ page, request }) => {
  // Check if we have seed data
  const library = await getLibrary(request);
  
  if (library.total === 0) {
    test.skip('No seed data available');
    return;
  }
  
  await page.goto('/library');
  await libraryPage.waitForCards();
  
  // Assert cards are visible
  const cardCount = await libraryPage.analysisCards.count();
  expect(cardCount).toBeGreaterThan(0);
  
  // Click first card
  await libraryPage.selectCard(0);
  
  // Wait for navigation
  await expect(page).toHaveURL(/\/analyze\/.+/);
  
  // Assert progress bar is visible (for completed analysis)
  await expect(analyzePage.progressBar).toBeVisible();
});
```

**Pros:** Test runs in CI, validates lightweight mode behavior  
**Cons:** Requires refactoring test

### Fix 3: Split Test into Two (Best Fix)

**Lightweight Test:** Validates UI rendering with seed data
```typescript
test('should display library page with seed data', async ({ page, request }) => {
  // This runs in CI lightweight mode
  const library = await getLibrary(request);
  
  await page.goto('/library');
  await libraryPage.waitForCards();
  
  if (library.total > 0) {
    await expect(libraryPage.analysisCards.first()).toBeVisible();
  } else {
    await expect(libraryPage.emptyState).toBeVisible();
  }
});
```

**Full Workflow Test:** Validates SSE progress with real workflow
```typescript
test('should show real-time SSE progress updates', async ({ page }) => {
  test.skip(!!process.env.CI, 'Requires backend LLM processing');
  
  // Create new analysis and watch SSE stream
  // ... full workflow test
});
```

**Pros:** Clear separation, both tests serve different purposes  
**Cons:** More work, but better architecture

---

## 🎯 Architecture Recommendations

### 1. **Test Classification System**

Create clear categories:

| Category | CI Behavior | Example |
|----------|-------------|---------|
| **Lightweight UI Tests** | ✅ Always run | Library page renders, navigation works |
| **Data-Dependent Tests** | ⚠️ Skip if no data | Library shows cards, search works |
| **Workflow Tests** | ❌ Skip in CI | Full analysis workflow, SSE streaming |
| **LLM Integration Tests** | ❌ Skip in CI | Real LLM calls, artifact generation |

### 2. **Test Helper Functions**

```typescript
// frontend/e2e/utils/test-helpers.ts
export function skipIfNoData(condition: boolean, message: string) {
  if (!condition) {
    test.skip(message);
  }
}

export function skipInLightweightMode(reason: string) {
  test.skip(!!process.env.CI && process.env.E2E_LLM_DISABLED === 'true', reason);
}
```

### 3. **Seed Data Verification**

```typescript
test.beforeAll(async ({ request }) => {
  // Verify seed data exists before running tests
  const library = await getLibrary(request);
  if (library.total === 0) {
    console.warn('⚠️  No seed data available - some tests will be skipped');
  }
});
```

---

## 📝 Immediate Action Items

1. **Fix `sse-progress.spec.ts`** - Add skip condition or refactor for lightweight mode
2. **Review all E2E tests** - Ensure consistent skip patterns
3. **Add test assertions** - Replace console.logs with actual assertions
4. **Document test categories** - Create clear guidelines for which tests run when
5. **Improve seed data reliability** - Ensure seed runs before tests start

---

## 🔍 Verification Steps

After fixes:

1. **Run locally in lightweight mode:**
   ```bash
   E2E_LLM_DISABLED=true npm run test:e2e:chromium
   ```

2. **Verify CI job passes:**
   - Check GitHub Actions run
   - Verify test output shows proper skips
   - Confirm no false positives

3. **Test in full mode:**
   ```bash
   E2E_LLM_ENABLED=true npm run test:e2e:chromium
   ```

---

## 📚 Related Files

- `.github/workflows/e2e-tests.yml` - CI workflow configuration
- `docker-compose.e2e.yml` - E2E environment setup
- `backend/scripts/seed_e2e_fixture.py` - Seed data script
- `frontend/e2e/specs/sse-progress.spec.ts` - Failing test
- `backend/app/api/v1/analysis/endpoints.py` - Workflow disable logic

---

**Status:** 🔴 **CRITICAL** - Blocking PR merge  
**Priority:** **HIGH** - Fix before merging PR #457  
**Estimated Fix Time:** 30 minutes (quick fix) to 2 hours (proper refactor)

