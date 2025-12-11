import type { Page } from '@playwright/test';
import {
  mockAnalysisResponse,
  mockAnalysisComplete,
  createSSEStream,
  mockArtifactWithMetadata,
  mockArtifactContent,
  mockLibraryResponse,
  mockTutorSession,
  mockChatResponse,
} from '../fixtures';

/**
 * Mock the analyze API endpoints.
 */
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
  await page.route(/\/api\/v1\/analyze\/[^/]+$/, async (route) => {
    const url = route.request().url();
    if (url.includes('/stream')) return route.continue();
    if (route.request().method() === 'GET') {
      await route.fulfill({ status: 200, json: mockAnalysisComplete });
    } else {
      await route.continue();
    }
  });
}

/**
 * Mock the SSE stream endpoint.
 */
export async function mockSSEStream(page: Page) {
  await page.route('**/api/v1/analyze/*/stream', async (route) => {
    const body = createSSEStream();

    await route.fulfill({
      status: 200,
      headers: {
        'Content-Type': 'text/event-stream',
        'Cache-Control': 'no-cache',
        Connection: 'keep-alive',
      },
      body,
    });
  });
}

/**
 * Mock SSE stream failure for error testing.
 */
export async function mockSSEStreamFailure(page: Page) {
  await page.route('**/api/v1/analyze/*/stream', async (route) => {
    await route.abort('connectionfailed');
  });
}

/**
 * Mock the artifact API endpoints.
 */
export async function mockArtifactAPI(page: Page) {
  // GET /api/v1/artifacts/:id
  await page.route(/\/api\/v1\/artifacts\/[^/]+$/, async (route) => {
    await route.fulfill({ status: 200, json: mockArtifactWithMetadata });
  });

  // GET /api/v1/artifacts/:id/download
  await page.route('**/api/v1/artifacts/*/download', async (route) => {
    await route.fulfill({
      status: 200,
      headers: {
        'Content-Type': 'text/markdown',
        'Content-Disposition': 'attachment; filename="implementation-guide.md"',
      },
      body: mockArtifactContent,
    });
  });

  // GET /api/v1/analyze/:id/artifact
  await page.route('**/api/v1/analyze/*/artifact', async (route) => {
    await route.fulfill({ status: 200, json: mockArtifactWithMetadata });
  });
}

/**
 * Mock the library API endpoints.
 */
export async function mockLibraryAPI(page: Page) {
  await page.route('**/api/v1/library*', async (route) => {
    await route.fulfill({ status: 200, json: mockLibraryResponse });
  });
}

/**
 * Mock empty library response.
 */
export async function mockEmptyLibraryAPI(page: Page) {
  await page.route('**/api/v1/library*', async (route) => {
    await route.fulfill({
      status: 200,
      json: { items: [], total: 0, limit: 15, offset: 0 },
    });
  });
}

/**
 * Mock the tutor API endpoints.
 */
export async function mockTutorAPI(page: Page) {
  // GET /api/v1/tutor/:sessionId
  await page.route(/\/api\/v1\/tutor\/[^/]+$/, async (route) => {
    if (route.request().method() === 'GET') {
      await route.fulfill({ status: 200, json: mockTutorSession });
    } else {
      await route.continue();
    }
  });

  // POST /api/v1/tutor/:sessionId/message
  await page.route('**/api/v1/tutor/*/message', async (route) => {
    if (route.request().method() === 'POST') {
      await route.fulfill({ status: 200, json: mockChatResponse });
    } else {
      await route.continue();
    }
  });

  // POST /api/v1/tutor - Create session
  await page.route(/\/api\/v1\/tutor$/, async (route) => {
    if (route.request().method() === 'POST') {
      await route.fulfill({ status: 200, json: mockTutorSession });
    } else {
      await route.continue();
    }
  });
}

/**
 * Mock API error response.
 */
export async function mockAPIError(page: Page, pattern: string | RegExp, statusCode = 500) {
  await page.route(pattern, async (route) => {
    await route.fulfill({
      status: statusCode,
      json: { error: 'Internal Server Error', message: 'Something went wrong' },
    });
  });
}

/**
 * Mock network failure.
 */
export async function mockNetworkFailure(page: Page, pattern: string | RegExp) {
  await page.route(pattern, async (route) => {
    await route.abort('failed');
  });
}

/**
 * Mock all APIs at once for convenience.
 */
export async function mockAllAPIs(page: Page) {
  await mockAnalyzeAPI(page);
  await mockSSEStream(page);
  await mockArtifactAPI(page);
  await mockLibraryAPI(page);
  await mockTutorAPI(page);
}
