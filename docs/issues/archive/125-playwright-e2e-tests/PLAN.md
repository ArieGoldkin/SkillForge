# Implementation Plan: Issue #125 - Playwright E2E Tests

**Issue:** [#125](https://github.com/ArieGoldkin/SkillForge/issues/125)
**Branch:** `feature/125-playwright-e2e-tests`
**Estimated Effort:** 8 Story Points (~8-13 hours)

---

## Executive Summary

This plan outlines the implementation of comprehensive E2E testing using Playwright for the SkillForge frontend application. The implementation is divided into 4 phases with clear deliverables and success criteria.

---

## Phase Overview

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                         IMPLEMENTATION PHASES                                    │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                 │
│   PHASE 1                PHASE 2                PHASE 3                PHASE 4  │
│   Infrastructure         Page Objects           Core Tests             Edge     │
│   (2 pts)                (1 pt)                 (4 pts)                Cases    │
│                                                                        (1 pt)   │
│   ┌──────────┐          ┌──────────┐          ┌──────────┐          ┌────────┐ │
│   │ Playwright│          │ 5 Page   │          │ 5 Spec   │          │ 2 Spec │ │
│   │ Install  │    →     │ Objects  │    →     │ Files    │    →     │ Files  │ │
│   │ Config   │          │ Fixtures │          │ ~25 tests│          │~5 tests│ │
│   └──────────┘          └──────────┘          └──────────┘          └────────┘ │
│                                                                                 │
│   ~2-3 hours             ~1-2 hours            ~4-6 hours            ~1-2 hrs  │
│                                                                                 │
└─────────────────────────────────────────────────────────────────────────────────┘
```

---

## Phase 1: Infrastructure Setup (2 Story Points)

### Duration: 2-3 hours

### Tasks

#### 1.1 Install Playwright

```bash
cd frontend
npm install -D @playwright/test
npx playwright install chromium firefox webkit
```

**Verification:**
```bash
npx playwright --version
# Expected: Version 1.40.0 or higher
```

#### 1.2 Create playwright.config.ts

**File:** `frontend/playwright.config.ts`

```typescript
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
    ['json', { outputFile: 'test-results/results.json' }],
  ],

  use: {
    baseURL: 'http://localhost:5173',
    trace: 'on-first-retry',
    screenshot: 'only-on-failure',
    video: 'on-first-retry',
  },

  projects: [
    {
      name: 'chromium',
      use: { ...devices['Desktop Chrome'] },
    },
    {
      name: 'firefox',
      use: { ...devices['Desktop Firefox'] },
    },
    {
      name: 'webkit',
      use: { ...devices['Desktop Safari'] },
    },
    {
      name: 'mobile-chrome',
      use: { ...devices['Pixel 5'] },
    },
    {
      name: 'mobile-safari',
      use: { ...devices['iPhone 13'] },
    },
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

**Update:** `frontend/package.json`

```json
{
  "scripts": {
    "test:e2e": "playwright test",
    "test:e2e:ui": "playwright test --ui",
    "test:e2e:headed": "playwright test --headed",
    "test:e2e:debug": "playwright test --debug",
    "test:e2e:chromium": "playwright test --project=chromium",
    "test:e2e:report": "playwright show-report"
  }
}
```

#### 1.4 Create Directory Structure

```bash
mkdir -p frontend/e2e/{fixtures,page-objects,specs,utils}
touch frontend/e2e/fixtures/index.ts
touch frontend/e2e/page-objects/index.ts
touch frontend/e2e/utils/index.ts
```

#### 1.5 Update .gitignore

**Append to:** `frontend/.gitignore`

```gitignore
# Playwright
/test-results/
/playwright-report/
/blob-report/
/playwright/.cache/
```

### Deliverables

- [ ] `@playwright/test` installed
- [ ] Browsers installed (chromium, firefox, webkit)
- [ ] `playwright.config.ts` created
- [ ] NPM scripts added
- [ ] Directory structure created
- [ ] `.gitignore` updated

### Verification

```bash
# Run empty test suite (should pass with no tests)
npm run test:e2e
```

---

## Phase 2: Page Objects & Fixtures (1 Story Point)

### Duration: 1-2 hours

### Tasks

#### 2.1 Base Page Object

**File:** `frontend/e2e/page-objects/base.page.ts`

```typescript
import { Page, Locator, expect } from '@playwright/test';

export abstract class BasePage {
  constructor(protected page: Page) {}

  async navigate(path: string = '/') {
    await this.page.goto(path);
    await this.waitForPageLoad();
  }

  async waitForPageLoad() {
    await this.page.waitForLoadState('networkidle');
  }

  async waitForElement(locator: Locator, timeout = 10000) {
    await locator.waitFor({ state: 'visible', timeout });
  }

  protected getByTestId(testId: string): Locator {
    return this.page.getByTestId(testId);
  }

  protected getByRole(role: Parameters<Page['getByRole']>[0], options?: Parameters<Page['getByRole']>[1]): Locator {
    return this.page.getByRole(role, options);
  }

  async takeScreenshot(name: string) {
    await this.page.screenshot({ path: `test-results/screenshots/${name}.png` });
  }
}
```

#### 2.2 Page Objects

| File | Class | Key Methods |
|------|-------|-------------|
| `home.page.ts` | `HomePage` | `goto()`, `submitUrl()`, `selectSkillLevel()`, `expectError()` |
| `analyze.page.ts` | `AnalyzePage` | `goto(id)`, `waitForStage()`, `getProgress()`, `expectComplete()` |
| `artifact.page.ts` | `ArtifactPage` | `goto(id)`, `downloadArtifact()`, `copyCodeBlock()`, `expectMarkdown()` |
| `tutor.page.ts` | `TutorPage` | `goto(sessionId)`, `sendMessage()`, `waitForResponse()`, `getMessages()` |
| `library.page.ts` | `LibraryPage` | `goto()`, `search()`, `filterByType()`, `toggleSearchMode()`, `selectCard()` |

#### 2.3 Fixtures

**File:** `frontend/e2e/fixtures/analysis.fixture.ts`

```typescript
export const mockAnalysisResponse = {
  analysis_id: 'test-analysis-123',
  url: 'https://example.com/article',
  content_type: 'article',
  status: 'processing',
  sse_endpoint: '/api/v1/analyze/test-analysis-123/stream',
};

export const mockSSEEvents = [
  { event: 'progress', data: { stage: 'extraction', status: 'running', progress: 10 } },
  { event: 'progress', data: { stage: 'extraction', status: 'complete', progress: 20 } },
  { event: 'progress', data: { stage: 'supervisor_routing', status: 'complete', progress: 30 } },
  { event: 'progress', data: { stage: 'tech_comparator', status: 'complete', progress: 50 } },
  { event: 'progress', data: { stage: 'aggregation', status: 'complete', progress: 80 } },
  { event: 'progress', data: { stage: 'artifact_generation', status: 'complete', progress: 100 } },
  { event: 'complete', data: { artifact_id: 'test-artifact-456' } },
];
```

**File:** `frontend/e2e/fixtures/artifact.fixture.ts`

```typescript
export const mockArtifactContent = `# Implementation Guide

## Executive Summary
This guide covers React hooks best practices.

## Key Findings
- Use \`useState\` for local state
- Use \`useEffect\` for side effects
- Use custom hooks for reusable logic

## Code Example
\`\`\`typescript
const useCounter = () => {
  const [count, setCount] = useState(0);
  return { count, increment: () => setCount(c => c + 1) };
};
\`\`\`
`;

export const mockArtifactMetadata = {
  artifact_id: 'test-artifact-456',
  analysis_id: 'test-analysis-123',
  title: 'React Hooks Best Practices',
  topics: ['React', 'Hooks', 'TypeScript'],
  complexity: 'intermediate',
  created_at: '2025-12-11T10:00:00Z',
};
```

#### 2.4 API Mocking Utilities

**File:** `frontend/e2e/utils/mock-api.ts`

```typescript
import { Page, Route } from '@playwright/test';
import { mockAnalysisResponse, mockSSEEvents } from '../fixtures/analysis.fixture';
import { mockArtifactContent, mockArtifactMetadata } from '../fixtures/artifact.fixture';

export async function mockAnalyzeAPI(page: Page) {
  // POST /api/v1/analyze - Create analysis
  await page.route('**/api/v1/analyze', async (route) => {
    if (route.request().method() === 'POST') {
      await route.fulfill({ status: 200, json: mockAnalysisResponse });
    } else {
      await route.continue();
    }
  });

  // GET /api/v1/analyze/:id - Get analysis status
  await page.route('**/api/v1/analyze/*', async (route) => {
    const url = route.request().url();
    if (url.includes('/stream')) return route.continue();
    if (route.request().method() === 'GET') {
      await route.fulfill({
        status: 200,
        json: { ...mockAnalysisResponse, status: 'complete', artifact_id: 'test-artifact-456' },
      });
    }
  });
}

export async function mockSSEStream(page: Page) {
  await page.route('**/api/v1/analyze/*/stream', async (route) => {
    const events = mockSSEEvents.map(e =>
      `event: ${e.event}\ndata: ${JSON.stringify(e.data)}\n\n`
    ).join('');

    await route.fulfill({
      status: 200,
      headers: {
        'Content-Type': 'text/event-stream',
        'Cache-Control': 'no-cache',
        'Connection': 'keep-alive',
      },
      body: events,
    });
  });
}

export async function mockArtifactAPI(page: Page) {
  // GET /api/v1/artifacts/:id
  await page.route('**/api/v1/artifacts/*', async (route) => {
    if (route.request().url().includes('/download')) {
      await route.fulfill({
        status: 200,
        headers: {
          'Content-Type': 'text/markdown',
          'Content-Disposition': 'attachment; filename="implementation-guide.md"',
        },
        body: mockArtifactContent,
      });
    } else {
      await route.fulfill({ status: 200, json: mockArtifactMetadata });
    }
  });

  // GET /api/v1/analyze/:id/artifact
  await page.route('**/api/v1/analyze/*/artifact', async (route) => {
    await route.fulfill({
      status: 200,
      json: { ...mockArtifactMetadata, markdown_content: mockArtifactContent },
    });
  });
}

export async function mockLibraryAPI(page: Page) {
  await page.route('**/api/v1/library*', async (route) => {
    await route.fulfill({
      status: 200,
      json: {
        items: [
          { analysis_id: '1', title: 'React Hooks Guide', content_type: 'article', status: 'complete', tags: ['React'] },
          { analysis_id: '2', title: 'TypeScript Tips', content_type: 'article', status: 'complete', tags: ['TypeScript'] },
          { analysis_id: '3', title: 'Node.js Video', content_type: 'video', status: 'complete', tags: ['Node.js'] },
        ],
        total: 3,
        limit: 15,
        offset: 0,
      },
    });
  });
}

export async function mockAllAPIs(page: Page) {
  await mockAnalyzeAPI(page);
  await mockSSEStream(page);
  await mockArtifactAPI(page);
  await mockLibraryAPI(page);
}
```

### Deliverables

- [ ] `base.page.ts` created
- [ ] 5 page objects created (home, analyze, artifact, tutor, library)
- [ ] 4 fixture files created (analysis, artifact, library, sse)
- [ ] `mock-api.ts` utilities created
- [ ] All exports in index files

### Verification

```bash
# TypeScript compilation check
npx tsc --noEmit -p e2e/tsconfig.json
```

---

## Phase 3: Core Test Specs (4 Story Points)

### Duration: 4-6 hours

### Tasks

#### 3.1 Home Page Tests

**File:** `frontend/e2e/specs/home.spec.ts`

```typescript
import { test, expect } from '@playwright/test';
import { HomePage } from '../page-objects/home.page';
import { mockAnalyzeAPI } from '../utils/mock-api';

test.describe('Home Page - URL Submission', () => {
  let homePage: HomePage;

  test.beforeEach(async ({ page }) => {
    await mockAnalyzeAPI(page);
    homePage = new HomePage(page);
    await homePage.goto();
  });

  test('should submit URL and navigate to analysis page', async ({ page }) => {
    await homePage.submitUrl('https://example.com/article');
    await expect(page).toHaveURL(/\/analyze\/.+/);
  });

  test('should show error for invalid URL', async () => {
    await homePage.submitUrl('not-a-valid-url');
    await homePage.expectError();
  });

  test('should show loading state during submission', async ({ page }) => {
    await homePage.urlInput.fill('https://example.com/article');
    await homePage.submitButton.click();
    // Check loading state appears
    await expect(homePage.submitButton).toBeDisabled();
  });

  test('should handle YouTube video URL', async ({ page }) => {
    await homePage.submitUrl('https://www.youtube.com/watch?v=dQw4w9WgXcQ');
    await expect(page).toHaveURL(/\/analyze\/.+/);
  });

  test('should handle GitHub repo URL', async ({ page }) => {
    await homePage.submitUrl('https://github.com/facebook/react');
    await expect(page).toHaveURL(/\/analyze\/.+/);
  });
});
```

#### 3.2 Analysis Page Tests

**File:** `frontend/e2e/specs/analysis.spec.ts`

```typescript
import { test, expect } from '@playwright/test';
import { AnalyzePage } from '../page-objects/analyze.page';
import { mockAnalyzeAPI, mockSSEStream } from '../utils/mock-api';

test.describe('Analysis Page - Progress Tracking', () => {
  test.beforeEach(async ({ page }) => {
    await mockAnalyzeAPI(page);
    await mockSSEStream(page);
  });

  test('should display progress stages via SSE', async ({ page }) => {
    const analyzePage = new AnalyzePage(page);
    await analyzePage.goto('test-analysis-123');

    // Wait for progress to appear
    await expect(page.getByText(/extraction/i)).toBeVisible();
  });

  test('should show completion state', async ({ page }) => {
    const analyzePage = new AnalyzePage(page);
    await analyzePage.goto('test-analysis-123');

    await analyzePage.waitForComplete();
    await expect(page.getByText(/complete/i)).toBeVisible();
  });

  test('should navigate to artifact on completion', async ({ page }) => {
    const analyzePage = new AnalyzePage(page);
    await analyzePage.goto('test-analysis-123');

    await analyzePage.waitForComplete();
    await page.getByRole('link', { name: /view.*artifact/i }).click();

    await expect(page).toHaveURL(/\/artifact\/.+/);
  });

  test('should handle SSE disconnection gracefully', async ({ page }) => {
    // Mock failed SSE connection
    await page.route('**/api/v1/analyze/*/stream', (route) => route.abort('connectionfailed'));

    const analyzePage = new AnalyzePage(page);
    await analyzePage.goto('test-analysis-123');

    // Should show reconnecting or error state
    await expect(page.getByText(/reconnecting|error/i)).toBeVisible({ timeout: 10000 });
  });
});
```

#### 3.3 Additional Test Files

| File | Tests | Coverage |
|------|-------|----------|
| `artifact.spec.ts` | 4 tests | Markdown preview, download, copy, metadata |
| `tutor.spec.ts` | 4 tests | Start session, send message, history, typing |
| `library.spec.ts` | 5 tests | Search, filter, modes, navigation, empty |

### Deliverables

- [ ] `home.spec.ts` (5 tests)
- [ ] `analysis.spec.ts` (4 tests)
- [ ] `artifact.spec.ts` (4 tests)
- [ ] `tutor.spec.ts` (4 tests)
- [ ] `library.spec.ts` (5 tests)
- [ ] Total: ~22 core tests

### Verification

```bash
# Run all core tests
npm run test:e2e -- --project=chromium

# Expected: 22 tests passing
```

---

## Phase 4: Edge Cases & Responsive (1 Story Point)

### Duration: 1-2 hours

### Tasks

#### 4.1 Responsive Tests

**File:** `frontend/e2e/specs/responsive.spec.ts`

```typescript
import { test, expect, devices } from '@playwright/test';
import { mockAllAPIs } from '../utils/mock-api';

test.describe('Responsive Design', () => {
  test.beforeEach(async ({ page }) => {
    await mockAllAPIs(page);
  });

  test('should display mobile navigation on small screens', async ({ page }) => {
    await page.setViewportSize({ width: 375, height: 667 });
    await page.goto('/');

    // Mobile menu button should be visible
    await expect(page.getByRole('button', { name: /menu/i })).toBeVisible();
  });

  test('should handle form inputs on mobile', async ({ page }) => {
    await page.setViewportSize({ width: 375, height: 667 });
    await page.goto('/');

    const urlInput = page.getByPlaceholder(/url/i);
    await urlInput.fill('https://example.com');

    // Input should be usable
    await expect(urlInput).toHaveValue('https://example.com');
  });

  test('should show responsive grid on tablet', async ({ page }) => {
    await page.setViewportSize({ width: 768, height: 1024 });
    await page.goto('/library');

    // Grid should be visible
    await expect(page.locator('[class*="grid"]')).toBeVisible();
  });

  test('should work correctly on desktop', async ({ page }) => {
    await page.setViewportSize({ width: 1280, height: 720 });
    await page.goto('/');

    // Desktop navigation should be visible
    await expect(page.getByRole('navigation')).toBeVisible();
  });
});
```

#### 4.2 Error Handling Tests

**File:** `frontend/e2e/specs/error-handling.spec.ts`

```typescript
import { test, expect } from '@playwright/test';

test.describe('Error Handling', () => {
  test('should display 404 for unknown routes', async ({ page }) => {
    await page.goto('/this-route-does-not-exist');
    await expect(page.getByText(/not found|404/i)).toBeVisible();
  });

  test('should handle API errors gracefully', async ({ page }) => {
    await page.route('**/api/v1/analyze', (route) =>
      route.fulfill({ status: 500, json: { error: 'Internal Server Error' } })
    );

    await page.goto('/');
    await page.getByPlaceholder(/url/i).fill('https://example.com');
    await page.getByRole('button', { name: /analyze/i }).click();

    await expect(page.getByRole('alert')).toBeVisible();
  });

  test('should show empty state in library', async ({ page }) => {
    await page.route('**/api/v1/library*', (route) =>
      route.fulfill({ status: 200, json: { items: [], total: 0 } })
    );

    await page.goto('/library');
    await expect(page.getByText(/no.*results|empty/i)).toBeVisible();
  });

  test('should handle network errors', async ({ page }) => {
    await page.route('**/api/v1/**', (route) => route.abort('failed'));

    await page.goto('/');
    await page.getByPlaceholder(/url/i).fill('https://example.com');
    await page.getByRole('button', { name: /analyze/i }).click();

    await expect(page.getByText(/error|failed/i)).toBeVisible();
  });
});
```

### Deliverables

- [ ] `responsive.spec.ts` (4 tests)
- [ ] `error-handling.spec.ts` (4 tests)
- [ ] Total: ~8 additional tests

### Verification

```bash
# Run all tests including mobile projects
npm run test:e2e

# Expected: ~30 tests passing across all browsers
```

---

## Summary

### Test Count by File

| Spec File | Tests | Priority |
|-----------|-------|----------|
| `home.spec.ts` | 5 | P0 |
| `analysis.spec.ts` | 4 | P0 |
| `artifact.spec.ts` | 4 | P0 |
| `tutor.spec.ts` | 4 | P1 |
| `library.spec.ts` | 5 | P0 |
| `responsive.spec.ts` | 4 | P1 |
| `error-handling.spec.ts` | 4 | P1 |
| **Total** | **30** | |

### Acceptance Criteria Coverage

| Criteria | Spec File | Status |
|----------|-----------|--------|
| Submit URL and view progress | home.spec, analysis.spec | Planned |
| Download artifact | artifact.spec | Planned |
| Preview markdown | artifact.spec | Planned |
| Start tutoring session | tutor.spec | Planned |
| Search library | library.spec | Planned |
| Filter by content type | library.spec | Planned |
| Analyze YouTube video | home.spec | Planned |
| Analyze GitHub repo | home.spec | Planned |
| Error handling (invalid URL) | error-handling.spec | Planned |
| Responsive design (mobile) | responsive.spec | Planned |

### Timeline

| Phase | Duration | Story Points |
|-------|----------|--------------|
| Phase 1: Infrastructure | 2-3 hours | 2 |
| Phase 2: Page Objects | 1-2 hours | 1 |
| Phase 3: Core Tests | 4-6 hours | 4 |
| Phase 4: Edge Cases | 1-2 hours | 1 |
| **Total** | **8-13 hours** | **8** |

---

**Plan Created:** December 11, 2025
**Author:** Claude Code
