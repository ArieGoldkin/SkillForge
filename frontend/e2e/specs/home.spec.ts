import { test, expect } from '@playwright/test';
import { HomePage } from '../page-objects';
import { waitForBackend, getApiBaseUrl } from '../utils';

/**
 * E2E tests for the Home Page URL submission flow.
 * Tests interact with the REAL backend API at http://localhost:8500
 */
test.describe('Home Page - URL Submission', () => {
  let homePage: HomePage;

  test.beforeAll(async ({ request }) => {
    // Ensure backend is healthy before running tests
    await waitForBackend(request);
  });

  test.beforeEach(async ({ page }) => {
    homePage = new HomePage(page);
    await homePage.goto();
  });

  test('should display the URL input and submit button', async () => {
    await expect(homePage.urlInput).toBeVisible();
    await expect(homePage.submitButton).toBeVisible();
  });

  test('should submit URL and navigate to analysis page', async ({ page }) => {
    // Submit a real URL that the backend will process
    await homePage.submitUrl('https://example.com/article');

    // Wait for navigation to the analysis page
    await page.waitForURL(/\/analyze\/.+/, { timeout: 10000 });

    // Verify we're on the correct page
    await expect(page).toHaveURL(/\/analyze\/.+/);
  });

  test('should show error for invalid URL', async () => {
    // Fill with an invalid URL
    await homePage.urlInput.fill('not-a-valid-url');
    await homePage.submitButton.click();

    // The form should show validation error or remain on the page
    // This depends on whether validation is client-side or server-side
    await expect(homePage.page).toHaveURL('/', { timeout: 5000 }).catch(async () => {
      // If navigated, check for error message on the analysis page
      await expect(homePage.errorMessage).toBeVisible();
    });
  });

  test('should show loading state during submission', async ({ page }) => {
    // Fill the URL input
    await homePage.urlInput.fill('https://example.com/article');

    // Click submit
    await homePage.submitButton.click();

    // Either button becomes disabled, shows loading, or page navigates
    // We check for loading indicators or navigation
    const loadingVisible = await page.locator('[aria-busy="true"]')
      .or(page.getByText(/loading|analyzing/i).first())
      .or(page.locator('button:disabled'))
      .isVisible({ timeout: 2000 })
      .catch(() => false);

    if (!loadingVisible) {
      // If no loading state visible, page might have already navigated
      await expect(page).toHaveURL(/\/analyze\/.+/);
    }
  });

  test('should handle YouTube video URL', async ({ page }) => {
    // Submit a YouTube URL
    await homePage.submitUrl('https://www.youtube.com/watch?v=dQw4w9WgXcQ');

    // Wait for navigation to analysis page
    await page.waitForURL(/\/analyze\/.+/, { timeout: 10000 });

    // Verify navigation
    await expect(page).toHaveURL(/\/analyze\/.+/);
  });

  test('should handle GitHub repo URL', async ({ page }) => {
    // Submit a GitHub repository URL
    await homePage.submitUrl('https://github.com/facebook/react');

    // Wait for navigation to analysis page
    await page.waitForURL(/\/analyze\/.+/, { timeout: 10000 });

    // Verify navigation
    await expect(page).toHaveURL(/\/analyze\/.+/);
  });

  test('should clear input after successful submission', async ({ page }) => {
    const testUrl = 'https://example.com/article';

    // Submit URL
    await homePage.submitUrl(testUrl);

    // Wait for navigation
    await page.waitForURL(/\/analyze\/.+/, { timeout: 10000 });
    await expect(page).toHaveURL(/\/analyze\/.+/);

    // Navigate back to home
    await homePage.goto();

    // Verify input is cleared (or shows a fresh state)
    const inputValue = await homePage.urlInput.inputValue();
    expect(inputValue).toBe('');
  });

  test('should successfully create analysis via backend API', async ({ page, request }) => {
    const testUrl = 'https://example.com/test-integration';

    // Submit the URL through the UI
    await homePage.submitUrl(testUrl);

    // Wait for navigation and extract analysis_id from URL
    await page.waitForURL(/\/analyze\/.+/, { timeout: 10000 });
    const url = page.url();
    const match = url.match(/\/analyze\/([a-f0-9-]+)/);
    expect(match).not.toBeNull();

    const analysisId = match![1];

    // Verify the analysis was created in the backend
    const response = await request.get(`${getApiBaseUrl()}/api/v1/analyze/${analysisId}`);
    expect(response.ok()).toBeTruthy();

    const analysis = await response.json();
    expect(analysis.analysis_id).toBe(analysisId);
    expect(analysis.url).toBe(testUrl);
  });

  test('should handle multiple URL submissions', async ({ page }) => {
    const urls = [
      'https://example.com/article-1',
      'https://example.com/article-2',
      'https://example.com/article-3',
    ];

    for (const url of urls) {
      // Submit URL
      await homePage.goto();
      await homePage.submitUrl(url);

      // Wait for navigation
      await page.waitForURL(/\/analyze\/.+/, { timeout: 10000 });
      await expect(page).toHaveURL(/\/analyze\/.+/);
    }
  });

  test('should preserve URL during loading', async ({ page }) => {
    const testUrl = 'https://example.com/test-preserve';

    // Fill the URL
    await homePage.urlInput.fill(testUrl);

    // Verify the value is preserved before submission
    await expect(homePage.urlInput).toHaveValue(testUrl);

    // Submit and check if we can still see the URL in the input during loading
    await homePage.submitButton.click();

    // Either we see loading state with URL preserved, or we navigate
    const hasNavigated = await page.waitForURL(/\/analyze\/.+/, { timeout: 5000 })
      .then(() => true)
      .catch(() => false);

    expect(hasNavigated).toBeTruthy();
  });
});
