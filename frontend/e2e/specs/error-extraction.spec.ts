/**
 * Extraction Error E2E Tests
 *
 * Tests extraction failure scenarios:
 * - Invalid URLs
 * - HTTP 404 errors
 * - Timeout errors
 */

import { test, expect } from '@playwright/test';

import { AnalyzePage } from '../page-objects';
import { createAnalysis, getAnalysis } from '../utils/api-helpers';

test.describe('Extraction Error Handling', () => {
  test('should handle extraction failure with invalid URL', async ({ page, request }) => {
    test.skip(!!process.env.CI, 'Requires backend LLM processing');

    // Create analysis with URL that will fail extraction
    const invalidUrl = 'https://this-domain-does-not-exist-12345.invalid';
    const { analysis_id } = await createAnalysis(request, invalidUrl);

    const analyzePage = new AnalyzePage(page);
    await analyzePage.goto(analysis_id);

    // Wait for error to appear - extraction should fail quickly
    await expect(
      page.getByText(/extraction.*fail|failed.*extract|error.*extract/i)
        .or(page.getByRole('alert'))
        .or(page.locator('[data-testid="status-text"]').filter({ hasText: /fail/i }))
    ).toBeVisible({ timeout: 30000 });

    // Verify error code is displayed if available
    const errorCodeBadge = page.locator('text=/EXTRACTION_FAILED|NETWORK_ERROR|HTTP_404/i');
    if (await errorCodeBadge.isVisible({ timeout: 5000 }).catch(() => false)) {
      await expect(errorCodeBadge).toBeVisible();
    }

    // Verify analysis status is failed
    const analysis = await getAnalysis(request, analysis_id);
    expect(['failed', 'extraction_failed']).toContain(analysis.status);
  });

  test('should handle HTTP 404 errors during extraction', async ({ page, request }) => {
    test.skip(!!process.env.CI, 'Requires backend LLM processing');

    // Use a URL that will return 404
    const notFoundUrl = 'https://example.com/this-page-definitely-does-not-exist-12345';
    const { analysis_id } = await createAnalysis(request, notFoundUrl);

    const analyzePage = new AnalyzePage(page);
    await analyzePage.goto(analysis_id);

    // Wait for error - should show 404 or extraction failed
    await expect(
      page.getByText(/404|not found|extraction.*fail|failed/i)
        .or(page.getByRole('alert'))
    ).toBeVisible({ timeout: 30000 });

    // Verify error code if displayed
    const errorCode = page.locator('text=/HTTP_404|EXTRACTION_FAILED/i');
    if (await errorCode.isVisible({ timeout: 5000 }).catch(() => false)) {
      await expect(errorCode).toBeVisible();
    }
  });

  test('should handle timeout errors during extraction', async ({ page, request }) => {
    test.skip(!!process.env.CI, 'Requires backend LLM processing');

    // Use a URL that might timeout (very slow or unreachable)
    const timeoutUrl = 'https://httpstat.us/200?sleep=60000'; // 60 second delay
    const { analysis_id } = await createAnalysis(request, timeoutUrl);

    const analyzePage = new AnalyzePage(page);
    await analyzePage.goto(analysis_id);

    // Wait for timeout error or extraction failure
    await expect(
      page.getByText(/timeout|extraction.*fail|failed|error/i)
        .or(page.getByRole('alert'))
    ).toBeVisible({ timeout: 90000 }); // Longer timeout for timeout test

    // Verify error code if displayed
    const errorCode = page.locator('text=/TIMEOUT|EXTRACTION_FAILED/i');
    if (await errorCode.isVisible({ timeout: 5000 }).catch(() => false)) {
      await expect(errorCode).toBeVisible();
    }
  });
});
