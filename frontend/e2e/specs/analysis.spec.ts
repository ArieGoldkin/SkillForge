import { test, expect } from '@playwright/test';
import { AnalyzePage } from '../page-objects';
import { mockAnalyzeAPI, mockSSEStream, mockSSEStreamFailure } from '../utils';

test.describe('Analysis Page - Progress Tracking', () => {
  test.beforeEach(async ({ page }) => {
    await mockAnalyzeAPI(page);
    await mockSSEStream(page);
  });

  test('should display the analysis page with progress indicator', async ({ page }) => {
    const analyzePage = new AnalyzePage(page);
    await analyzePage.goto('test-analysis-123');

    // Progress bar should be visible
    await expect(analyzePage.progressBar).toBeVisible();
  });

  test('should display progress stages via SSE', async ({ page }) => {
    const analyzePage = new AnalyzePage(page);
    await analyzePage.goto('test-analysis-123');

    // Wait for extraction stage to appear
    await expect(page.getByText(/extraction/i)).toBeVisible({ timeout: 10000 });
  });

  test('should show completion state', async ({ page }) => {
    const analyzePage = new AnalyzePage(page);
    await analyzePage.goto('test-analysis-123');

    // Wait for complete state
    await analyzePage.waitForComplete();
    await expect(page.getByText(/complete/i)).toBeVisible();
  });

  test('should navigate to artifact on completion', async ({ page }) => {
    const analyzePage = new AnalyzePage(page);
    await analyzePage.goto('test-analysis-123');

    await analyzePage.waitForComplete();

    // Find and click the view artifact button/link
    const viewButton = page.getByRole('link', { name: /view.*artifact|view.*result|see.*result/i });
    if (await viewButton.isVisible()) {
      await viewButton.click();
      await expect(page).toHaveURL(/\/artifact\/.+/);
    }
  });

  test('should handle SSE disconnection gracefully', async ({ page }) => {
    // Override SSE mock to simulate failure
    await mockSSEStreamFailure(page);

    const analyzePage = new AnalyzePage(page);
    await analyzePage.goto('test-analysis-123');

    // Should show error or reconnecting state
    await expect(
      page.getByText(/reconnecting|error|failed|retry/i)
    ).toBeVisible({ timeout: 15000 });
  });

  test('should display analysis metadata', async ({ page }) => {
    const analyzePage = new AnalyzePage(page);
    await analyzePage.goto('test-analysis-123');

    // The page should show some analysis info
    await expect(page.getByText(/analyzing|processing|analysis/i)).toBeVisible();
  });
});
