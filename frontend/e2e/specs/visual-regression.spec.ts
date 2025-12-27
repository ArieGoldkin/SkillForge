import { test, expect } from '@playwright/test';

import { HomePage, AnalyzePage, ArtifactPage } from '../page-objects';
import { getCompletedAnalysis, createAnalysis } from '../utils/api-helpers';

/**
 * E2E Visual Regression Tests using Playwright's native toHaveScreenshot().
 *
 * These tests capture visual snapshots for visual regression testing.
 * Playwright will compare snapshots across runs to detect unintended UI changes.
 *
 * Run with: npm run e2e:vrt
 */
test.describe('Visual Regression Tests', () => {
  test.describe('Homepage', () => {
    test('should match homepage snapshot (light mode)', async ({ page }) => {
      const homePage = new HomePage(page);
      await homePage.goto();
      await homePage.urlInput.waitFor({ state: 'visible', timeout: 10000 });

      await expect(page).toHaveScreenshot('homepage-light.png');
    });

    test('should match homepage snapshot (dark mode)', async ({ page }) => {
      const homePage = new HomePage(page);
      await homePage.goto();
      await homePage.urlInput.waitFor({ state: 'visible', timeout: 10000 });

      // Toggle dark mode via localStorage
      await page.evaluate(() => {
        localStorage.setItem('theme', 'dark');
        document.documentElement.classList.add('dark');
      });

      // Wait for theme to apply
      await page.waitForTimeout(500);

      await expect(page).toHaveScreenshot('homepage-dark.png');
    });

    test('should match homepage with URL input filled', async ({ page }) => {
      const homePage = new HomePage(page);
      await homePage.goto();
      await homePage.urlInput.waitFor({ state: 'visible', timeout: 10000 });

      await homePage.urlInput.fill('https://example.com/article');

      await expect(page).toHaveScreenshot('homepage-url-filled.png');
    });
  });

  test.describe('Library Page', () => {
    test('should match library page with analysis cards', async ({ page, request }) => {
      // Get a completed analysis to ensure we have library content
      const completed = await getCompletedAnalysis(request);

      if (!completed) {
        test.skip(!completed, 'No completed analysis available - create one first');
      }

      await page.goto('/library');

      // Wait for library content to load
      await page.waitForSelector('[data-testid="analysis-card"], [role="article"]', { timeout: 10000 });

      // Mask timestamps and dynamic content
      await expect(page).toHaveScreenshot('library-with-cards.png', {
        mask: [
          page.locator('time'),
          page.locator('[data-testid="timestamp"]'),
        ],
      });
    });

    test('should match library page (empty state)', async ({ page }) => {
      // This test assumes a fresh state with no analyses
      // You may need to skip this in environments with existing data
      await page.goto('/library');

      // Wait for page to fully load
      await page.waitForLoadState('networkidle');

      await expect(page).toHaveScreenshot('library-empty-state.png');
    });
  });

  test.describe('Analysis Progress States', () => {
    test('should match analysis progress - loading state', async ({ page, request }) => {
      test.skip(!!process.env.CI, 'Requires backend LLM processing');

      // Create a new analysis to capture loading state
      const { analysis_id } = await createAnalysis(request);

      const analyzePage = new AnalyzePage(page);
      await analyzePage.goto(analysis_id);

      // Wait for page to load
      await analyzePage.waitForPageLoad();

      // Mask dynamic content like timestamps and progress percentages
      await expect(page).toHaveScreenshot('analysis-loading.png', {
        mask: [
          page.locator('time'),
          page.locator('[data-testid="timestamp"]'),
          page.locator('[data-testid="progress-percentage"]'),
        ],
      });
    });

    test('should match analysis progress - complete state', async ({ page, request }) => {
      const completed = await getCompletedAnalysis(request);

      if (!completed) {
        test.skip(!completed, 'No completed analysis available - create one first');
      }

      const analyzePage = new AnalyzePage(page);
      await analyzePage.goto(completed!.analysis_id);

      await analyzePage.waitForComplete();

      // Mask timestamps but keep status badges visible
      await expect(page).toHaveScreenshot('analysis-complete.png', {
        mask: [
          page.locator('time'),
          page.locator('[data-testid="timestamp"]'),
        ],
      });
    });

    test('should match analysis progress - error state', async ({ page }) => {
      test.skip(true, 'Error state snapshot - requires manual setup or mock');

      // This test would require backend to return an error state
      // or mock the SSE stream to simulate error condition
      const analyzePage = new AnalyzePage(page);
      await analyzePage.goto('mock-error-id');

      // Wait for error message
      await page.waitForSelector('[role="alert"], [data-testid="error-message"]', { timeout: 10000 });

      await expect(page).toHaveScreenshot('analysis-error.png');
    });
  });

  test.describe('Artifact View', () => {
    test('should match artifact page with markdown rendering', async ({ page, request }) => {
      const completed = await getCompletedAnalysis(request);

      if (!completed || !completed.artifact_id) {
        test.skip(!completed?.artifact_id, 'No completed analysis with artifact available');
      }

      const artifactPage = new ArtifactPage(page);
      await artifactPage.goto(completed!.artifact_id);

      // Wait for markdown content to render
      await page.waitForSelector('article, [data-testid="markdown-content"]', { timeout: 10000 });

      // Mask timestamps
      await expect(page).toHaveScreenshot('artifact-markdown.png', {
        mask: [
          page.locator('time'),
          page.locator('[data-testid="timestamp"]'),
        ],
      });
    });

    test('should match artifact page - dark mode', async ({ page, request }) => {
      const completed = await getCompletedAnalysis(request);

      if (!completed || !completed.artifact_id) {
        test.skip(!completed?.artifact_id, 'No completed analysis with artifact available');
      }

      const artifactPage = new ArtifactPage(page);
      await artifactPage.goto(completed!.artifact_id);

      // Toggle dark mode
      await page.evaluate(() => {
        localStorage.setItem('theme', 'dark');
        document.documentElement.classList.add('dark');
      });

      await page.waitForTimeout(500);

      // Mask timestamps
      await expect(page).toHaveScreenshot('artifact-dark.png', {
        mask: [
          page.locator('time'),
          page.locator('[data-testid="timestamp"]'),
        ],
      });
    });
  });

  test.describe('Component Showcase', () => {
    test('should match component showcase page', async ({ page }) => {
      // Navigate to component showcase (if it exists)
      // This assumes you have a /showcase or /components route
      // Adjust the route based on your actual implementation
      test.skip(true, 'Component showcase page not implemented - skip for now');

      await page.goto('/showcase');
      await page.waitForLoadState('networkidle');

      await expect(page).toHaveScreenshot('component-showcase.png');
    });
  });

  test.describe('Responsive Viewports', () => {
    test('should match homepage on mobile viewport', async ({ page }) => {
      // Set mobile viewport
      await page.setViewportSize({ width: 375, height: 667 });

      const homePage = new HomePage(page);
      await homePage.goto();
      await homePage.urlInput.waitFor({ state: 'visible', timeout: 10000 });

      await expect(page).toHaveScreenshot('homepage-mobile-375px.png');
    });

    test('should match library page on tablet viewport', async ({ page, request }) => {
      const completed = await getCompletedAnalysis(request);

      if (!completed) {
        test.skip(!completed, 'No completed analysis available');
      }

      // Set tablet viewport
      await page.setViewportSize({ width: 768, height: 1024 });

      await page.goto('/library');
      await page.waitForSelector('[data-testid="analysis-card"], [role="article"]', { timeout: 10000 });

      // Mask timestamps
      await expect(page).toHaveScreenshot('library-tablet-768px.png', {
        mask: [
          page.locator('time'),
          page.locator('[data-testid="timestamp"]'),
        ],
      });
    });

    test('should match analysis page on desktop viewport', async ({ page, request }) => {
      const completed = await getCompletedAnalysis(request);

      if (!completed) {
        test.skip(!completed, 'No completed analysis available');
      }

      // Set desktop viewport
      await page.setViewportSize({ width: 1280, height: 800 });

      const analyzePage = new AnalyzePage(page);
      await analyzePage.goto(completed!.analysis_id);
      await analyzePage.waitForComplete();

      // Mask timestamps
      await expect(page).toHaveScreenshot('analysis-desktop-1280px.png', {
        mask: [
          page.locator('time'),
          page.locator('[data-testid="timestamp"]'),
        ],
      });
    });
  });
});
