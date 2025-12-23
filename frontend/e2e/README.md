# E2E Testing with Playwright

This directory contains End-to-End (E2E) tests for SkillForge using Playwright.

## Overview

Our E2E test suite uses Playwright's `storageState` feature to optimize test execution time by 50-70%. This approach, inspired by [CyberArk's optimization](https://medium.com/cyberark-engineering/how-this-feature-reduced-our-e2e-tests-from-15-minutes-to-3-cd847ecbbc0f), eliminates repeated navigation and authentication steps.

## Key Features

- **storageState Optimization**: Browser state (cookies, localStorage, sessionStorage) is saved once and reused across all tests
- **Parallel Execution**: 4 workers run tests simultaneously in CI (4× speedup)
- **Direct URL Navigation**: Tests can start from any URL without navigating from baseURL
- **Reduced Flakiness**: No repeated login/navigation steps that can fail

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│              Global Setup (Once)                        │
│  ┌──────────┐                                           │
│  │ Browser  │ → Navigate to baseURL → Save state       │
│  └────┬─────┘                                           │
│       │                                                 │
│       ▼                                                 │
│  ┌──────────────────────┐                              │
│  │ storageState.json    │                              │
│  │ (cookies, storage)   │                              │
│  └──────────────────────┘                              │
└─────────────────────────────────────────────────────────┘
                    │
                    │ Reused by all tests
                    ▼
┌─────────────────────────────────────────────────────────┐
│         Test Execution (Parallel)                       │
│                                                          │
│  Test 1          Test 2          Test 3                │
│  ┌─────┐        ┌─────┐        ┌─────┐                │
│  │Load │        │Load │        │Load │                │
│  │State│        │State│        │State│                │
│  └──┬──┘        └──┬──┘        └──┬──┘                │
│     │              │              │                    │
│     ▼              ▼              ▼                    │
│  Start from authenticated state (no navigation!)      │
└─────────────────────────────────────────────────────────┘
```

## File Structure

```
frontend/e2e/
├── global-setup.ts          # Creates storageState.json once
├── specs/                    # Test files (*.spec.ts)
├── page-objects/            # Page Object Model classes
├── utils/                    # Test utilities
│   ├── state-helpers.ts     # StorageState management utilities
│   └── ...
└── .auth/                    # Generated directory (gitignored)
    └── storageState.json    # Browser state (auto-generated)
```

## Running Tests

### Local Development

```bash
cd frontend

# Run all tests
npm run test:e2e

# Run specific test file
npx playwright test specs/analysis.spec.ts

# Run with UI (headed mode)
npx playwright test --headed

# Run in debug mode
npx playwright test --debug
```

### CI Environment

Tests run automatically in GitHub Actions on:
- Push to `main` or `dev` branches
- Pull requests
- Manual workflow dispatch

The CI workflow:
1. Creates `.auth/` directory
2. Runs global setup (creates `storageState.json`)
3. Executes tests with 4 parallel workers
4. Reports performance metrics

## Configuration

### Playwright Config

See `playwright.config.ts` for full configuration. Key settings:

- **globalSetup**: `./e2e/global-setup.ts` - Creates storageState
- **workers**: `4` in CI, `undefined` locally (auto-detects CPU cores)
- **storageState**: `.auth/storageState.json` - Used by all projects

### Environment Variables

- `PLAYWRIGHT_BASE_URL`: Test environment URL (default: `http://localhost:5174`)
- `API_BASE_URL`: Backend API URL (default: `http://localhost:8501`)
- `CI`: Set to `"true"` in CI environments
- `E2E_LLM_DISABLED`: Set to `"true"` for lightweight tests (no LLM calls)

## Writing Tests

### Best Practices

1. **Start from specific URLs**: With storageState, you can navigate directly to any URL:
   ```typescript
   // ✅ Good: Direct navigation
   await page.goto('/analyze/analysis-id');
   
   // ❌ Avoid: Unnecessary navigation from baseURL
   await page.goto('/');
   await page.goto('/analyze/analysis-id');
   ```

2. **Use Page Objects**: All navigation should go through page objects:
   ```typescript
   const analyzePage = new AnalyzePage(page);
   await analyzePage.goto(analysisId); // Uses storageState
   ```

3. **Leverage storageState**: Tests automatically benefit from saved state - no special code needed.

### Example Test

```typescript
import { test, expect } from '@playwright/test';
import { AnalyzePage } from '../page-objects';

test.describe('Analysis Page', () => {
  test('should display analysis', async ({ page, request }) => {
    // Get analysis ID from API
    const analysis = await getAnalysis(request);
    
    // Navigate directly to analysis URL
    // storageState makes this fast (no baseURL navigation)
    const analyzePage = new AnalyzePage(page);
    await analyzePage.goto(analysis.analysis_id);
    
    // Test assertions
    await expect(analyzePage.progressBar).toBeVisible();
  });
});
```

## Performance Metrics

### Expected Improvements

With storageState optimization:
- **50-70% reduction** in test execution time
- **4× speedup** from parallel execution (4 workers)
- **Reduced flakiness** from eliminated navigation steps

### CI Metrics

Performance metrics are automatically tracked in GitHub Actions:
- Test execution time
- Number of parallel workers
- storageState file size
- Optimization status

View metrics in the workflow summary after each test run.

## Troubleshooting

### storageState Not Created

**Symptom**: Tests run but no performance improvement

**Solution**:
1. Check `.auth/` directory exists: `ls -la frontend/.auth/`
2. Verify global setup runs: Check test output for "Global setup completed"
3. Check file permissions: Ensure write access to `.auth/` directory

### Tests Fail with storageState

**Symptom**: Tests fail when storageState is used

**Solution**:
1. Delete corrupted state: `rm frontend/.auth/storageState.json`
2. Re-run tests (global setup will recreate state)
3. Check baseURL matches test environment

### Parallel Execution Conflicts

**Symptom**: Tests interfere with each other

**Solution**:
1. Ensure tests are isolated (no shared state)
2. Use unique test data per test
3. Check for race conditions in test code

## State Management Utilities

The `state-helpers.ts` utility provides functions for managing storageState:

```typescript
import { 
  readStorageState, 
  validateStorageState,
  shouldRefreshStorageState,
  getStorageStateStats 
} from '../utils/state-helpers';

// Check if state needs refresh
if (shouldRefreshStorageState()) {
  // State is older than 1 hour, should refresh
}

// Get state statistics
const stats = getStorageStateStats();
console.log(`State size: ${stats?.size} bytes`);
console.log(`State age: ${stats?.ageMs}ms`);
```

## References

- [Playwright storageState Documentation](https://playwright.dev/docs/auth#reuse-authentication-state)
- [CyberArk E2E Optimization Article](https://medium.com/cyberark-engineering/how-this-feature-reduced-our-e2e-tests-from-15-minutes-to-3-cd847ecbbc0f)
- [Playwright Best Practices](https://playwright.dev/docs/best-practices)
