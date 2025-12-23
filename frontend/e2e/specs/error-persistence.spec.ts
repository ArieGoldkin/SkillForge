/**
 * Error Event Persistence E2E Tests
 *
 * Tests that error events are properly persisted and retrievable:
 * - Error events saved to database
 * - Error events retrieved on page reload
 */

import { test, expect } from '@playwright/test';

import { AnalyzePage } from '../page-objects';
import { createAnalysis } from '../utils/api-helpers';

test.describe('Error Event Persistence', () => {
  test('should persist error events to database', async ({ page, request }) => {
    test.skip(!!process.env.CI, 'Requires backend LLM processing');

    // Create analysis that will fail
    const invalidUrl = 'https://invalid-url-for-error-persistence-test.invalid';
    const { analysis_id } = await createAnalysis(request, invalidUrl);

    const analyzePage = new AnalyzePage(page);
    await analyzePage.goto(analysis_id);

    // Wait for error to appear
    await expect(
      page.getByText(/error|fail/i)
        .or(page.getByRole('alert'))
    ).toBeVisible({ timeout: 30000 });

    // Fetch progress events from API to verify persistence
    const progressResponse = await request.get(
      `${process.env.API_BASE_URL || 'http://localhost:8501'}/api/v1/analyze/${analysis_id}/progress`
    );

    if (progressResponse.ok()) {
      const progressData = await progressResponse.json();
      const errorEvents = progressData.events.filter(
        (event: { type?: string; status?: string }) =>
          event.type === 'error' || event.status === 'failed'
      );

      // Should have at least one error event
      expect(errorEvents.length).toBeGreaterThan(0);

      // Verify error event structure
      const errorEvent = errorEvents[0];
      expect(errorEvent).toHaveProperty('stage');
      expect(errorEvent).toHaveProperty('status', 'failed');
      if (errorEvent.details) {
        expect(errorEvent.details).toHaveProperty('error');
      }
    }
  });

  test('should retrieve error events on page reload', async ({ page, request }) => {
    test.skip(!!process.env.CI, 'Requires backend LLM processing');

    // Create analysis that will fail
    const invalidUrl = 'https://invalid-url-for-reload-test.invalid';
    const { analysis_id } = await createAnalysis(request, invalidUrl);

    const analyzePage = new AnalyzePage(page);
    await analyzePage.goto(analysis_id);

    // Wait for error to appear
    await expect(
      page.getByText(/error|fail/i)
        .or(page.getByRole('alert'))
    ).toBeVisible({ timeout: 30000 });

    // Reload page
    await page.reload();
    await page.waitForLoadState('domcontentloaded');

    // Error should still be visible after reload (from persisted events)
    await expect(
      page.getByText(/error|fail/i)
        .or(page.getByRole('alert'))
    ).toBeVisible({ timeout: 10000 });
  });
});
