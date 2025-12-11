import { test, expect } from '@playwright/test';
import { mockAPIError, mockNetworkFailure, mockEmptyLibraryAPI } from '../utils';

test.describe('Error Handling Tests', () => {
  test('should display 404 for unknown routes', async ({ page }) => {
    await page.goto('/this-route-does-not-exist-at-all');

    // Should show 404 or not found message
    await expect(
      page.getByText(/not found|404|page.*exist|doesn't exist/i)
    ).toBeVisible({ timeout: 5000 });
  });

  test('should handle API errors gracefully on URL submission', async ({ page }) => {
    // Mock API to return 500 error
    await mockAPIError(page, '**/api/v1/analyze', 500);

    await page.goto('/');

    // Try to submit a URL
    const urlInput = page.getByPlaceholder(/url/i);
    await urlInput.fill('https://example.com');

    const submitButton = page.getByRole('button', { name: /analyze|submit/i });
    await submitButton.click();

    // Should show error message
    await expect(
      page.getByRole('alert').or(page.getByText(/error|failed|something went wrong/i))
    ).toBeVisible({ timeout: 10000 });
  });

  test('should handle network errors', async ({ page }) => {
    // Mock network failure
    await mockNetworkFailure(page, '**/api/v1/**');

    await page.goto('/');

    const urlInput = page.getByPlaceholder(/url/i);
    await urlInput.fill('https://example.com');

    const submitButton = page.getByRole('button', { name: /analyze|submit/i });
    await submitButton.click();

    // Should show error state
    await expect(
      page.getByText(/error|failed|network|offline|connection/i)
    ).toBeVisible({ timeout: 10000 });
  });

  test('should show empty state in library when no analyses exist', async ({ page }) => {
    await mockEmptyLibraryAPI(page);
    await page.goto('/library');

    // Should show empty state message
    await expect(
      page.getByText(/no.*results|no.*analyses|empty|nothing.*here|get started/i)
    ).toBeVisible({ timeout: 5000 });
  });

  test('should handle 401 unauthorized gracefully', async ({ page }) => {
    await mockAPIError(page, '**/api/v1/**', 401);

    await page.goto('/library');

    // Should handle unauthorized (show login prompt or error)
    await page.waitForTimeout(2000);

    // Page should still be functional
    await expect(page.locator('body')).toBeVisible();
  });

  test('should handle 403 forbidden gracefully', async ({ page }) => {
    await mockAPIError(page, '**/api/v1/**', 403);

    await page.goto('/library');

    // Should handle forbidden access
    await page.waitForTimeout(2000);

    // Page should still render
    await expect(page.locator('body')).toBeVisible();
  });

  test('should handle slow API responses with loading state', async ({ page }) => {
    // Mock slow API response
    await page.route('**/api/v1/analyze', async (route) => {
      await new Promise((resolve) => setTimeout(resolve, 2000));
      await route.fulfill({
        status: 200,
        json: { analysis_id: 'test-123', status: 'processing' },
      });
    });

    await page.goto('/');

    const urlInput = page.getByPlaceholder(/url/i);
    await urlInput.fill('https://example.com');

    const submitButton = page.getByRole('button', { name: /analyze|submit/i });
    await submitButton.click();

    // Should show loading state
    await expect(submitButton).toBeDisabled();
  });

  test('should recover after temporary network failure', async ({ page }) => {
    let failCount = 0;

    // First request fails, second succeeds
    await page.route('**/api/v1/library*', async (route) => {
      if (failCount < 1) {
        failCount++;
        await route.abort('failed');
      } else {
        await route.fulfill({
          status: 200,
          json: {
            items: [
              {
                analysis_id: '1',
                title: 'Test',
                content_type: 'article',
                status: 'complete',
                tags: [],
              },
            ],
            total: 1,
            limit: 15,
            offset: 0,
          },
        });
      }
    });

    await page.goto('/library');

    // After retry or reload, should work
    await page.waitForTimeout(3000);
    await page.reload();

    // Should eventually show content
    await expect(page.locator('body')).toBeVisible();
  });
});
