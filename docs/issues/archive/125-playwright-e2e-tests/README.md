# Issue #125: E2E Tests with Playwright

**Status:** In Progress
**Assignee:** Arie (Frontend)
**Sprint:** Sprint 7 - Testing & Deployment
**Story Points:** 8 pts
**GitHub Issue:** [#125](https://github.com/ArieGoldkin/SkillForge/issues/125)
**Feature Branch:** `feature/125-playwright-e2e-tests`

---

## Issue Overview

**Title:** [Frontend] Task 7.1 - Write E2E Tests with Playwright [8 pts]

**Description:**
Comprehensive end-to-end testing with Playwright to validate all user-facing functionality across the SkillForge frontend application. This includes URL submission, analysis progress tracking, artifact viewing, tutoring sessions, and library search/filter functionality.

**Labels:** `feature`, `frontend`, `testing`, `sprint-7`

---

## Current State Analysis

### Existing Infrastructure (Unit Tests)

| Component | Status | Details |
|-----------|--------|---------|
| **Vitest** | Installed | v4.0.13, configured with jsdom |
| **@testing-library/react** | Installed | v16.3.0 |
| **@testing-library/user-event** | Installed | v14.6.1 |
| **Test Count** | 81+ tests | All passing |
| **Coverage** | V8 provider | HTML/JSON reports |

### Missing Infrastructure (E2E Tests)

| Component | Status | Action Required |
|-----------|--------|-----------------|
| **@playwright/test** | Not Installed | `npm install -D @playwright/test` |
| **playwright.config.ts** | Missing | Create configuration file |
| **e2e/ directory** | Missing | Create test structure |
| **npm scripts** | Missing | Add `test:e2e`, `test:e2e:ui` |
| **Browser binaries** | Missing | `npx playwright install` |

---

## Architecture

### Test Infrastructure Architecture

```
                    ┌─────────────────────────────────────────────────────────────┐
                    │                  E2E TEST ARCHITECTURE                       │
                    ├─────────────────────────────────────────────────────────────┤
                    │                                                             │
                    │  ┌─────────────────┐                                        │
                    │  │   Playwright    │  Test Runner                           │
                    │  │   Test Runner   │  - Chromium, Firefox, WebKit           │
                    │  └────────┬────────┘  - Parallel execution                  │
                    │           │           - Screenshot/Video capture            │
                    │           │                                                 │
                    │           ▼                                                 │
                    │  ┌─────────────────┐                                        │
                    │  │  Page Objects   │  Abstraction Layer                     │
                    │  │  - HomePage     │  - Encapsulate selectors               │
                    │  │  - AnalyzePage  │  - Reusable actions                    │
                    │  │  - ArtifactPage │  - Maintainable tests                  │
                    │  │  - TutorPage    │                                        │
                    │  │  - LibraryPage  │                                        │
                    │  └────────┬────────┘                                        │
                    │           │                                                 │
                    │           ▼                                                 │
                    │  ┌─────────────────┐                                        │
                    │  │   Test Specs    │  Test Files                            │
                    │  │  - home.spec    │  - User journey tests                  │
                    │  │  - analysis     │  - Happy path + edge cases             │
                    │  │  - artifact     │  - Responsive tests                    │
                    │  │  - tutor        │                                        │
                    │  │  - library      │                                        │
                    │  └────────┬────────┘                                        │
                    │           │                                                 │
                    │           ▼                                                 │
                    │  ┌─────────────────────────────────────────────────────┐    │
                    │  │              Frontend Application                   │    │
                    │  │  ┌─────────┐  ┌─────────┐  ┌─────────┐             │    │
                    │  │  │   /     │  │/analyze │  │/artifact│             │    │
                    │  │  │  Home   │  │   $id   │  │  $id    │             │    │
                    │  │  └────┬────┘  └────┬────┘  └────┬────┘             │    │
                    │  │       │            │            │                   │    │
                    │  │  ┌────┴────┐  ┌────┴────┐  ┌────┴────┐             │    │
                    │  │  │ /tutor  │  │/library │  │   404   │             │    │
                    │  │  │  $id    │  │         │  │         │             │    │
                    │  │  └─────────┘  └─────────┘  └─────────┘             │    │
                    │  └─────────────────────────────────────────────────────┘    │
                    │           │                                                 │
                    │           ▼                                                 │
                    │  ┌─────────────────┐                                        │
                    │  │   API Mocking   │  Route Interception                    │
                    │  │  page.route()   │  - Mock /api/v1/* endpoints            │
                    │  │                 │  - Mock SSE streams                    │
                    │  │                 │  - Fixture data                        │
                    │  └─────────────────┘                                        │
                    │                                                             │
                    └─────────────────────────────────────────────────────────────┘
```

### Route to Test Case Mapping

```
                    ┌─────────────────────────────────────────────────────────────┐
                    │                  ROUTE → TEST MAPPING                        │
                    ├─────────────────────────────────────────────────────────────┤
                    │                                                             │
                    │   ROUTE                    TEST CASES                       │
                    │   ═══════════════════════════════════════════════════════  │
                    │                                                             │
                    │   /                                                         │
                    │   └── Home.tsx                                              │
                    │       ├── Submit URL and view progress       → home.spec   │
                    │       ├── Analyze YouTube video              → home.spec   │
                    │       ├── Analyze GitHub repo                → home.spec   │
                    │       └── Error handling (invalid URL)       → error.spec  │
                    │                                                             │
                    │   /analyze/$id                                              │
                    │   └── AnalyzeResult.tsx                                     │
                    │       ├── View SSE progress updates          → analysis    │
                    │       ├── See completion state               → analysis    │
                    │       └── Navigate to artifact               → analysis    │
                    │                                                             │
                    │   /artifact/$artifactId                                     │
                    │   └── ArtifactPage.tsx                                      │
                    │       ├── Preview markdown content           → artifact    │
                    │       ├── Download artifact (.md)            → artifact    │
                    │       └── Copy code blocks                   → artifact    │
                    │                                                             │
                    │   /tutor/$sessionId                                         │
                    │   └── TutorSession.tsx                                      │
                    │       ├── Start tutoring session             → tutor.spec  │
                    │       ├── Send/receive messages              → tutor.spec  │
                    │       └── View chat history                  → tutor.spec  │
                    │                                                             │
                    │   /library                                                  │
                    │   └── Library.tsx                                           │
                    │       ├── Search library                     → library     │
                    │       ├── Filter by content type             → library     │
                    │       ├── Toggle search modes                → library     │
                    │       └── Navigate to analysis               → library     │
                    │                                                             │
                    │   /* (catch-all)                                            │
                    │   └── NotFound.tsx                                          │
                    │       └── 404 page display                   → error.spec  │
                    │                                                             │
                    └─────────────────────────────────────────────────────────────┘
```

---

## File Structure

### Proposed Directory Structure

```
frontend/
├── playwright.config.ts              # Playwright configuration
├── e2e/
│   ├── fixtures/
│   │   ├── index.ts                  # Re-export all fixtures
│   │   ├── analysis.fixture.ts       # Mock analysis API responses
│   │   ├── artifact.fixture.ts       # Mock artifact/markdown content
│   │   ├── library.fixture.ts        # Mock library search results
│   │   ├── tutor.fixture.ts          # Mock tutoring session data
│   │   └── sse.fixture.ts            # Mock SSE event sequences
│   │
│   ├── page-objects/
│   │   ├── index.ts                  # Re-export all page objects
│   │   ├── base.page.ts              # Base page class with common methods
│   │   ├── home.page.ts              # Home page (URL input, submit)
│   │   ├── analyze.page.ts           # Analysis page (progress tracker)
│   │   ├── artifact.page.ts          # Artifact page (preview, download)
│   │   ├── tutor.page.ts             # Tutor page (chat interface)
│   │   └── library.page.ts           # Library page (search, filters)
│   │
│   ├── specs/
│   │   ├── home.spec.ts              # URL submission tests (5 tests)
│   │   ├── analysis.spec.ts          # Progress tracking tests (4 tests)
│   │   ├── artifact.spec.ts          # Artifact viewing tests (4 tests)
│   │   ├── tutor.spec.ts             # Tutoring session tests (4 tests)
│   │   ├── library.spec.ts           # Search/filter tests (5 tests)
│   │   ├── responsive.spec.ts        # Mobile viewport tests (4 tests)
│   │   └── error-handling.spec.ts    # Error & edge case tests (4 tests)
│   │
│   └── utils/
│       ├── test-helpers.ts           # Common test utilities
│       ├── mock-api.ts               # API route mocking utilities
│       └── wait-helpers.ts           # Custom wait conditions
│
├── package.json                      # + E2E scripts
└── .gitignore                        # + playwright artifacts
```

---

## Implementation Plan

### Phase 1: Infrastructure Setup (2 Story Points)

**Estimated Time:** 2-3 hours

#### 1.1 Install Dependencies

```bash
cd frontend
npm install -D @playwright/test
npx playwright install chromium firefox webkit
```

#### 1.2 Create Playwright Configuration

```typescript
// playwright.config.ts
import { defineConfig, devices } from '@playwright/test';

export default defineConfig({
  testDir: './e2e/specs',
  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 2 : 0,
  workers: process.env.CI ? 1 : undefined,
  reporter: [
    ['html', { open: 'never' }],
    ['list'],
  ],
  use: {
    baseURL: 'http://localhost:5173',
    trace: 'on-first-retry',
    screenshot: 'only-on-failure',
    video: 'on-first-retry',
  },
  projects: [
    { name: 'chromium', use: { ...devices['Desktop Chrome'] } },
    { name: 'firefox', use: { ...devices['Desktop Firefox'] } },
    { name: 'webkit', use: { ...devices['Desktop Safari'] } },
    { name: 'mobile', use: { ...devices['iPhone 13'] } },
  ],
  webServer: {
    command: 'npm run dev',
    url: 'http://localhost:5173',
    reuseExistingServer: !process.env.CI,
    timeout: 120000,
  },
});
```

#### 1.3 Add NPM Scripts

```json
{
  "scripts": {
    "test:e2e": "playwright test",
    "test:e2e:ui": "playwright test --ui",
    "test:e2e:headed": "playwright test --headed",
    "test:e2e:debug": "playwright test --debug",
    "test:e2e:chromium": "playwright test --project=chromium"
  }
}
```

#### 1.4 Update .gitignore

```gitignore
# Playwright
/test-results/
/playwright-report/
/blob-report/
/playwright/.cache/
```

---

### Phase 2: Page Objects & Fixtures (1 Story Point)

**Estimated Time:** 1-2 hours

#### 2.1 Base Page Object

```typescript
// e2e/page-objects/base.page.ts
import { Page, Locator, expect } from '@playwright/test';

export abstract class BasePage {
  constructor(protected page: Page) {}

  async navigate(path: string = '/') {
    await this.page.goto(path);
  }

  async waitForPageLoad() {
    await this.page.waitForLoadState('networkidle');
  }

  protected getByTestId(testId: string): Locator {
    return this.page.getByTestId(testId);
  }

  protected getByRole(role: string, options?: { name?: string }): Locator {
    return this.page.getByRole(role as any, options);
  }
}
```

#### 2.2 Home Page Object

```typescript
// e2e/page-objects/home.page.ts
import { Page, Locator, expect } from '@playwright/test';
import { BasePage } from './base.page';

export class HomePage extends BasePage {
  // Locators
  readonly urlInput: Locator;
  readonly submitButton: Locator;
  readonly skillLevelSelector: Locator;
  readonly errorMessage: Locator;
  readonly loadingSpinner: Locator;

  constructor(page: Page) {
    super(page);
    this.urlInput = page.getByPlaceholder(/paste.*url/i);
    this.submitButton = page.getByRole('button', { name: /analyze/i });
    this.skillLevelSelector = page.getByTestId('skill-level-selector');
    this.errorMessage = page.getByRole('alert');
    this.loadingSpinner = page.getByTestId('loading-spinner');
  }

  async goto() {
    await this.navigate('/');
  }

  async submitUrl(url: string) {
    await this.urlInput.fill(url);
    await this.submitButton.click();
  }

  async selectSkillLevel(level: 'beginner' | 'intermediate' | 'advanced') {
    await this.skillLevelSelector.click();
    await this.page.getByRole('option', { name: level }).click();
  }

  async expectNavigatedToAnalysis() {
    await expect(this.page).toHaveURL(/\/analyze\/.+/);
  }

  async expectError(message?: string) {
    await expect(this.errorMessage).toBeVisible();
    if (message) {
      await expect(this.errorMessage).toContainText(message);
    }
  }
}
```

#### 2.3 Analysis Fixture

```typescript
// e2e/fixtures/analysis.fixture.ts
export const mockAnalysisResponse = {
  analysis_id: 'test-analysis-123',
  url: 'https://example.com/article',
  content_type: 'article',
  status: 'processing',
  sse_endpoint: '/api/v1/analyze/test-analysis-123/stream',
};

export const mockAnalysisComplete = {
  ...mockAnalysisResponse,
  status: 'complete',
  artifact_id: 'test-artifact-456',
};

export const mockSSEEvents = [
  { stage: 'extraction', status: 'running', progress: 10 },
  { stage: 'extraction', status: 'complete', progress: 20 },
  { stage: 'supervisor_routing', status: 'running', progress: 25 },
  { stage: 'supervisor_routing', status: 'complete', progress: 30 },
  { stage: 'tech_comparator', status: 'running', progress: 40 },
  { stage: 'tech_comparator', status: 'complete', progress: 50 },
  { stage: 'security_auditor', status: 'running', progress: 55 },
  { stage: 'security_auditor', status: 'complete', progress: 60 },
  { stage: 'aggregation', status: 'running', progress: 80 },
  { stage: 'aggregation', status: 'complete', progress: 90 },
  { stage: 'artifact_generation', status: 'running', progress: 95 },
  { stage: 'artifact_generation', status: 'complete', progress: 100 },
];
```

---

### Phase 3: Core Test Specs (4 Story Points)

**Estimated Time:** 4-6 hours

#### 3.1 Home Page Tests (home.spec.ts)

| Test Case | Description | Priority |
|-----------|-------------|----------|
| `should submit URL and navigate to analysis` | Happy path URL submission | P0 |
| `should show error for invalid URL` | Validation error display | P0 |
| `should show loading state during submission` | UX feedback | P1 |
| `should handle YouTube video URL` | Content type: video | P1 |
| `should handle GitHub repo URL` | Content type: repository | P1 |

#### 3.2 Analysis Page Tests (analysis.spec.ts)

| Test Case | Description | Priority |
|-----------|-------------|----------|
| `should display progress stages via SSE` | Real-time updates | P0 |
| `should show completion state` | Final state UI | P0 |
| `should navigate to artifact on completion` | Navigation flow | P0 |
| `should handle SSE disconnection` | Error recovery | P1 |

#### 3.3 Artifact Page Tests (artifact.spec.ts)

| Test Case | Description | Priority |
|-----------|-------------|----------|
| `should preview markdown content` | Render markdown | P0 |
| `should download artifact as .md` | File download | P0 |
| `should copy code blocks to clipboard` | Copy functionality | P1 |
| `should display artifact metadata` | Title, date, topics | P1 |

#### 3.4 Tutor Page Tests (tutor.spec.ts)

| Test Case | Description | Priority |
|-----------|-------------|----------|
| `should start tutoring session` | Session initialization | P0 |
| `should send message and receive response` | Chat interaction | P0 |
| `should display chat history` | Message persistence | P1 |
| `should show typing indicator` | UX feedback | P2 |

#### 3.5 Library Page Tests (library.spec.ts)

| Test Case | Description | Priority |
|-----------|-------------|----------|
| `should search library by query` | Search functionality | P0 |
| `should filter by content type` | Filter dropdown | P0 |
| `should toggle search modes` | Hybrid/fulltext/semantic | P1 |
| `should navigate to analysis from card` | Card click navigation | P0 |
| `should show empty state` | No results UI | P1 |

---

### Phase 4: Edge Cases & Responsive (1 Story Point)

**Estimated Time:** 1-2 hours

#### 4.1 Responsive Tests (responsive.spec.ts)

| Test Case | Viewport | Description |
|-----------|----------|-------------|
| `should display mobile navigation` | 375x667 | Hamburger menu |
| `should handle form on mobile` | 375x667 | Touch-friendly inputs |
| `should show responsive grid` | 768x1024 | Tablet layout |
| `should work on desktop` | 1280x720 | Standard desktop |

#### 4.2 Error Handling Tests (error-handling.spec.ts)

| Test Case | Description |
|-----------|-------------|
| `should display 404 for unknown routes` | NotFound page |
| `should handle API errors gracefully` | Error boundaries |
| `should recover from SSE disconnection` | Reconnection logic |
| `should show empty states` | No data scenarios |

---

## Test Case Details

### Acceptance Criteria Mapping

| # | Acceptance Criteria | Test File | Test Case |
|---|---------------------|-----------|-----------|
| 1 | Submit URL and view progress | home.spec.ts, analysis.spec.ts | `should submit URL and navigate`, `should display progress` |
| 2 | Download artifact | artifact.spec.ts | `should download artifact as .md` |
| 3 | Preview markdown | artifact.spec.ts | `should preview markdown content` |
| 4 | Start tutoring session | tutor.spec.ts | `should start tutoring session` |
| 5 | Search library | library.spec.ts | `should search library by query` |
| 6 | Filter by content type | library.spec.ts | `should filter by content type` |
| 7 | Analyze YouTube video | home.spec.ts | `should handle YouTube video URL` |
| 8 | Analyze GitHub repo | home.spec.ts | `should handle GitHub repo URL` |
| 9 | Error handling (invalid URL) | error-handling.spec.ts | `should show error for invalid URL` |
| 10 | Responsive design (mobile) | responsive.spec.ts | `should display mobile navigation` |

---

## Technical Considerations

### SSE Mocking Strategy

Server-Sent Events require special handling in Playwright:

```typescript
// e2e/utils/mock-api.ts
export async function mockSSEStream(page: Page, events: SSEEvent[]) {
  await page.route('**/api/v1/analyze/*/stream', async (route) => {
    const body = events.map(e => `data: ${JSON.stringify(e)}\n\n`).join('');

    await route.fulfill({
      status: 200,
      headers: {
        'Content-Type': 'text/event-stream',
        'Cache-Control': 'no-cache',
        'Connection': 'keep-alive',
      },
      body,
    });
  });
}
```

### API Mocking Pattern

```typescript
// e2e/utils/mock-api.ts
export async function mockAnalyzeAPI(page: Page) {
  // Mock POST /api/v1/analyze
  await page.route('**/api/v1/analyze', async (route) => {
    if (route.request().method() === 'POST') {
      await route.fulfill({
        status: 200,
        json: mockAnalysisResponse,
      });
    }
  });

  // Mock GET /api/v1/analyze/:id
  await page.route('**/api/v1/analyze/*', async (route) => {
    if (route.request().method() === 'GET') {
      await route.fulfill({
        status: 200,
        json: mockAnalysisComplete,
      });
    }
  });
}
```

### CI Configuration

```yaml
# .github/workflows/e2e.yml
name: E2E Tests
on: [push, pull_request]

jobs:
  e2e:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with:
          node-version: 20
      - name: Install dependencies
        run: cd frontend && npm ci
      - name: Install Playwright
        run: cd frontend && npx playwright install --with-deps chromium
      - name: Run E2E tests
        run: cd frontend && npm run test:e2e -- --project=chromium
      - uses: actions/upload-artifact@v4
        if: always()
        with:
          name: playwright-report
          path: frontend/playwright-report/
```

---

## Metrics & Success Criteria

### Test Coverage Goals

| Metric | Target | Status |
|--------|--------|--------|
| Test cases implemented | 30 | Pending |
| Routes covered | 6/6 | Pending |
| Acceptance criteria | 10/10 | Pending |
| Browser coverage | 3 browsers | Pending |
| Mobile viewports | 2 viewports | Pending |

### Quality Gates

- [ ] All tests pass in CI
- [ ] No flaky tests (3 consecutive green runs)
- [ ] Test execution < 5 minutes
- [ ] Screenshot artifacts on failure
- [ ] Video recordings available for debugging

---

## Running Tests

### Local Development

```bash
# Run all E2E tests
npm run test:e2e

# Run with UI mode (interactive)
npm run test:e2e:ui

# Run in headed mode (visible browser)
npm run test:e2e:headed

# Run specific test file
npm run test:e2e -- e2e/specs/home.spec.ts

# Run specific project (browser)
npm run test:e2e -- --project=chromium

# Debug mode
npm run test:e2e:debug
```

### CI/CD

```bash
# CI-optimized run (Chromium only, parallel disabled)
npm run test:e2e -- --project=chromium --workers=1
```

---

## Related Issues

- **Issue #139:** End-to-End Deployment Testing [3 pts] (Infrastructure E2E)
- **Issue #126:** Task 7.2 - Performance Optimization [5 pts]
- **Issue #127:** Task 7.3 - Deploy to Vercel [3 pts]
- **Issue #128:** Task 7.4 - UI Polish [5 pts]

---

## Dependencies

### Blocking Issues

None - All prerequisite features are implemented.

### Required by

- Issue #139: End-to-End Deployment Testing (needs E2E infrastructure)

---

## Notes

1. **Page Object Model (POM):** Using POM for maintainability - when UI changes, update page objects instead of all tests.

2. **Fixture-based Mocking:** All API responses are mocked via fixtures to ensure test isolation and speed.

3. **SSE Testing:** Server-Sent Events require special route interception with chunked response simulation.

4. **Parallel Execution:** Tests are designed to run in parallel with no shared state between test files.

5. **Mobile-First Testing:** Responsive tests use actual device viewports from Playwright's device library.

---

**Plan Created:** December 11, 2025
**Last Updated:** December 11, 2025
**Author:** Claude Code
