/**
 * SSE Reconnection and Polling E2E Tests
 *
 * Tests SSE connection handling:
 * - Connection status indicator
 * - Reconnection on disconnection
 * - Polling fallback
 */

import { test, expect } from '@playwright/test';

import { AnalyzePage } from '../page-objects';
import { createAnalysis } from '../utils/api-helpers';

test.describe('SSE Reconnection and Polling', () => {
  test('should show connection status indicator', async ({ page, request }) => {
    test.skip(!!process.env.CI, 'Requires backend LLM processing');

    // Create a valid analysis
    const { analysis_id } = await createAnalysis(request, 'https://example.com');

    const analyzePage = new AnalyzePage(page);
    await analyzePage.goto(analysis_id);

    // Connection status should be visible
    await expect(
      page.getByText(/connected|reconnecting|polling|disconnected/i)
        .or(page.locator('[data-testid="sse-connection-status"]'))
    ).toBeVisible({ timeout: 10000 });
  });

  test('should handle SSE disconnection and show reconnecting state', async ({ page, request }) => {
    test.skip(!!process.env.CI, 'Requires backend LLM processing');

    // Create a valid analysis
    const { analysis_id } = await createAnalysis(request, 'https://example.com');

    const analyzePage = new AnalyzePage(page);
    await analyzePage.goto(analysis_id);

    // Simulate SSE disconnection by blocking SSE endpoint
    await page.route('**/api/v1/analyze/*/stream', async (route) => {
      await route.abort('failed');
    });

    // Wait for reconnecting or polling state
    await expect(
      page.getByText(/reconnecting|polling|connection.*fail/i)
    ).toBeVisible({ timeout: 15000 });
  });
});
