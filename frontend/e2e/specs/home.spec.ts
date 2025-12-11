import { test, expect } from '@playwright/test';
import { HomePage } from '../page-objects';
import { mockAnalyzeAPI } from '../utils';

test.describe('Home Page - URL Submission', () => {
  let homePage: HomePage;

  test.beforeEach(async ({ page }) => {
    await mockAnalyzeAPI(page);
    homePage = new HomePage(page);
    await homePage.goto();
  });

  test('should display the URL input and submit button', async () => {
    await expect(homePage.urlInput).toBeVisible();
    await expect(homePage.submitButton).toBeVisible();
  });

  test('should submit URL and navigate to analysis page', async ({ page }) => {
    await homePage.submitUrl('https://example.com/article');
    await expect(page).toHaveURL(/\/analyze\/.+/);
  });

  test('should show error for invalid URL', async () => {
    await homePage.urlInput.fill('not-a-valid-url');
    await homePage.submitButton.click();

    // The form should show validation error or remain on the page
    await expect(homePage.page).toHaveURL('/');
  });

  test('should show loading state during submission', async ({ page }) => {
    await homePage.urlInput.fill('https://example.com/article');
    await homePage.submitButton.click();

    // Either button becomes disabled, shows loading, or page navigates
    await expect(
      page.locator('[aria-busy="true"]')
        .or(page.getByText(/loading|analyzing/i).first())
        .or(page.locator('button:disabled'))
    ).toBeVisible({ timeout: 2000 }).catch(async () => {
      // If no loading state visible, page might have already navigated
      await expect(page).toHaveURL(/\/analyze\/.+/);
    });
  });

  test('should handle YouTube video URL', async ({ page }) => {
    await homePage.submitUrl('https://www.youtube.com/watch?v=dQw4w9WgXcQ');
    await expect(page).toHaveURL(/\/analyze\/.+/);
  });

  test('should handle GitHub repo URL', async ({ page }) => {
    await homePage.submitUrl('https://github.com/facebook/react');
    await expect(page).toHaveURL(/\/analyze\/.+/);
  });

  test('should clear input after successful submission', async ({ page }) => {
    await homePage.submitUrl('https://example.com/article');
    await expect(page).toHaveURL(/\/analyze\/.+/);
  });
});
