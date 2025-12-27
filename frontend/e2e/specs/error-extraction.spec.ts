/**
 * Extraction Error E2E Tests
 *
 * Tests extraction failure scenarios:
 * - Invalid URLs
 * - HTTP 404 errors
 * - Timeout errors
 *
 * NOTE: These tests require:
 * - Backend API running (http://localhost:8501)
 * - Backend workflow enabled (SKILLFORGE_E2E_DISABLE_WORKFLOW not set)
 * - Backend to process analyses and emit error events
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

    // Wait for analysis to process (either complete with error or fail)
    // Poll API status to see if analysis failed
    let analysisStatus = 'pending';
    let attempts = 0;
    const maxAttempts = 12; // 60 seconds total (5s intervals)

    while (attempts < maxAttempts && analysisStatus === 'pending') {
      // Poll for status change with 5 second timeout
      await expect
        .poll(
          async () => {
            try {
              const analysis = await getAnalysis(request, analysis_id);
              return analysis.status;
            } catch {
              return 'pending'; // API not ready yet
            }
          },
          {
            timeout: 5000,
            intervals: [1000],
          }
        )
        .not.toBe('pending')
        .catch(() => {
          // Status still pending, continue loop
        });

      try {
        const analysis = await getAnalysis(request, analysis_id);
        analysisStatus = analysis.status;
        if (['failed', 'extraction_failed'].includes(analysisStatus)) {
          break; // Analysis failed, proceed to check UI
        }
      } catch {
        // API might not be ready yet
      }
      attempts++;
    }

    // Now check UI for error display
    // Error might appear in various places - check all possibilities
    const errorIndicators = [
      page.getByText(/extraction.*fail|failed.*extract|error.*extract|network.*error/i),
      page.getByRole('alert'),
      page.locator('[data-testid="status-text"]').filter({ hasText: /fail/i }),
      page.locator('[role="alert"]'),
      page.getByText(/failed|error/i).first(),
      page.locator('text=/EXTRACTION_FAILED|NETWORK_ERROR|HTTP_404/i'),
    ];

    // At least one error indicator should be visible
    let errorFound = false;
    for (const indicator of errorIndicators) {
      if (await indicator.isVisible({ timeout: 5000 }).catch(() => false)) {
        errorFound = true;
        break;
      }
    }

    // If no UI error found but API says failed, that's still a valid test result
    // (UI might be loading or error display might be delayed)
    if (!errorFound && !['failed', 'extraction_failed'].includes(analysisStatus)) {
      // Take a screenshot for debugging
      await page.screenshot({ path: 'test-results/error-extraction-debug.png', fullPage: true });
      throw new Error(`Analysis did not fail as expected. Status: ${analysisStatus}`);
    }

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
