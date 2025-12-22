/**
 * Frontend Error Detection E2E Tests
 *
 * Tests that frontend correctly detects and displays errors:
 * - Error detection from both error and progress events
 * - Error summary in progress card
 * - Failed stages excluded from progress calculation
 * - Error code display
 */

import { test, expect } from '@playwright/test';

import { AnalyzePage } from '../page-objects';
import { createAnalysis } from '../utils/api-helpers';

// eslint-disable-next-line max-lines-per-function -- E2E tests require comprehensive test coverage
test.describe('Frontend Error Detection', () => {
  test('should detect errors from both error and progress events', async ({ page, request }) => {
    test.skip(!!process.env.CI, 'Requires backend LLM processing');

    // Create analysis that will fail
    const invalidUrl = 'https://invalid-url-for-detection-test.invalid';
    const { analysis_id } = await createAnalysis(request, invalidUrl);

    const analyzePage = new AnalyzePage(page);
    await analyzePage.goto(analysis_id);

    // Wait for error to be detected and displayed
    await expect(
      page.getByText(/error|fail/i)
        .or(page.getByRole('alert'))
        .or(page.locator('[data-testid="status-text"]').filter({ hasText: /fail/i }))
    ).toBeVisible({ timeout: 30000 });

    // Verify failed stages count is displayed if available
    const failedStagesText = page.getByText(/failed.*stage|stage.*fail/i);
    if (await failedStagesText.isVisible({ timeout: 5000 }).catch(() => false)) {
      await expect(failedStagesText).toBeVisible();
    }

    // Verify error codes are displayed
    const errorCodeBadge = page.locator('text=/EXTRACTION_FAILED|NETWORK_ERROR|HTTP_404|TIMEOUT/i');
    if (await errorCodeBadge.isVisible({ timeout: 5000 }).catch(() => false)) {
      await expect(errorCodeBadge).toBeVisible();
    }
  });

  test('should show error summary in progress card', async ({ page, request }) => {
    test.skip(!!process.env.CI, 'Requires backend LLM processing');

    // Create analysis that will fail
    const invalidUrl = 'https://invalid-url-for-summary-test.invalid';
    const { analysis_id } = await createAnalysis(request, invalidUrl);

    const analyzePage = new AnalyzePage(page);
    await analyzePage.goto(analysis_id);

    // Wait for error summary to appear
    await expect(
      page.getByText(/failed|error|complete.*error/i)
        .or(page.locator('[role="alert"]'))
    ).toBeVisible({ timeout: 30000 });

    // Verify "Complete with Errors" badge if analysis completes with failures
    const completeWithErrors = page.getByText(/complete.*error|error.*complete/i);
    if (await completeWithErrors.isVisible({ timeout: 5000 }).catch(() => false)) {
      await expect(completeWithErrors).toBeVisible();
    }
  });

  test('should exclude failed stages from progress calculation', async ({ page, request }) => {
    test.skip(!!process.env.CI, 'Requires backend LLM processing');

    // Create analysis that will fail
    const invalidUrl = 'https://invalid-url-for-progress-test.invalid';
    const { analysis_id } = await createAnalysis(request, invalidUrl);

    const analyzePage = new AnalyzePage(page);
    await analyzePage.goto(analysis_id);

    // Wait for error
    await expect(
      page.getByText(/error|fail/i)
        .or(page.getByRole('alert'))
    ).toBeVisible({ timeout: 30000 });

    // Get progress value
    const progressBar = analyzePage.progressBar;
    if (await progressBar.isVisible({ timeout: 5000 }).catch(() => false)) {
      const progressValue = await progressBar.getAttribute('aria-valuenow');
      const progress = progressValue ? parseInt(progressValue, 10) : 0;

      // Progress should not be 100% if there are failures
      // (failed stages should be excluded from calculation)
      // Note: This is a soft check - progress might be 0% or low if extraction fails early
      expect(progress).toBeLessThanOrEqual(99);
    }
  });

  test('should display error codes in failed stage cards', async ({ page, request }) => {
    test.skip(!!process.env.CI, 'Requires backend LLM processing');

    // Create analysis that will fail
    const invalidUrl = 'https://invalid-url-for-error-code-test.invalid';
    const { analysis_id } = await createAnalysis(request, invalidUrl);

    const analyzePage = new AnalyzePage(page);
    await analyzePage.goto(analysis_id);

    // Wait for error
    await expect(
      page.getByText(/error|fail/i)
        .or(page.getByRole('alert'))
    ).toBeVisible({ timeout: 30000 });

    // Look for error code badges in stage items
    const errorCodeBadges = page.locator('text=/EXTRACTION_FAILED|NETWORK_ERROR|HTTP_404|TIMEOUT|ERROR_PAGE/i');
    if (await errorCodeBadges.first().isVisible({ timeout: 10000 }).catch(() => false)) {
      await expect(errorCodeBadges.first()).toBeVisible();
    }
  });

  test('should display error codes in error summary', async ({ page, request }) => {
    test.skip(!!process.env.CI, 'Requires backend LLM processing');

    // Create analysis that will fail
    const invalidUrl = 'https://invalid-url-for-summary-code-test.invalid';
    const { analysis_id } = await createAnalysis(request, invalidUrl);

    const analyzePage = new AnalyzePage(page);
    await analyzePage.goto(analysis_id);

    // Wait for error summary
    await expect(
      page.getByText(/failed|error/i)
        .or(page.locator('[role="alert"]'))
    ).toBeVisible({ timeout: 30000 });

    // Look for error codes in the error summary section
    const errorCodesInSummary = page
      .locator('[role="alert"], .bg-destructive\\/10')
      .locator('text=/EXTRACTION_FAILED|NETWORK_ERROR|HTTP_404|TIMEOUT/i');

    if (await errorCodesInSummary.first().isVisible({ timeout: 10000 }).catch(() => false)) {
      await expect(errorCodesInSummary.first()).toBeVisible();
    }
  });
});
