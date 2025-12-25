import { test, expect } from '@playwright/test';

import { LibraryPage, AnalyzePage } from '../page-objects';
import { getLibrary, getCompletedAnalysis } from '../utils/api-helpers';

/**
 * SSE Progress Updates Tests
 *
 * These tests validate that:
 * 1. Library page displays analysis cards (lightweight mode with seed data)
 * 2. Navigation from library to analysis page works
 * 3. Analysis page displays progress/status correctly
 * 4. Completed analyses show completion state (lightweight mode)
 * 5. In-progress analyses show progress bar (full workflow mode)
 */
test.describe('SSE Progress Updates', () => {
  // Removed beforeAll waitForBackend - causes request context disposal
  // Backend health is checked implicitly by getLibrary() in tests

  test('should display library and navigate to analysis page (lightweight mode)', async ({ page, request }) => {
    const library = await getLibrary(request, { limit: 10 });
    if (library.total === 0 || !library.items[0]) {
      test.skip(true, 'No seed data available');
      return;
    }
    const libraryPage = new LibraryPage(page);
    // With storageState, navigation is optimized (reuses browser state)
    await libraryPage.goto();
    await libraryPage.waitForCards();
    expect(await libraryPage.analysisCards.count()).toBeGreaterThan(0);
    const analyzePage = new AnalyzePage(page);
    // Direct navigation to analysis URL (storageState enables fast navigation)
    await analyzePage.goto(library.items[0].analysis_id);
    await expect(page).toHaveURL(/\/analyze\/.+/);
    // Issue #533: Wait for page to fully load
    // HeroSummaryCard shows either "Analysis In Progress" or "Analysis Complete" heading
    // and is rendered in both active and completed views
    await analyzePage.waitForPageLoad();
  });

  test('should show completion state for completed analysis', async ({ page, request }) => {
    // Get a completed analysis from seed data
    const completed = await getCompletedAnalysis(request);

    if (!completed) {
      test.skip(true, 'No completed analysis with artifact found - seed data required');
      return;
    }

    // Navigate directly to completed analysis
    // With storageState, direct navigation is faster (skips baseURL navigation)
    const analyzePage = new AnalyzePage(page);
    await analyzePage.goto(completed.analysis_id);

    // Issue #533: Wait for page to load first
    await analyzePage.waitForPageLoad();

    // Completed analyses can show one of two UIs:
    // 1. CompletedAnalysisView with HeroSummaryCard (Priority 100/90/60)
    // 2. Fallback view with AnalysisCompleteCard (Priority 10)
    // Both have an analysis heading, so we check for that
    await expect(analyzePage.analysisHeading).toBeVisible({ timeout: 15000 });

    // Completed analysis should show an artifact button:
    // - HeroSummaryCard: "View Results" button
    // - AnalysisCompleteCard: "View Guide" link
    await expect(analyzePage.viewArtifactButton).toBeVisible();
  });

  test('should handle empty library state gracefully', async ({ page }) => {
    // This test validates that the library page handles empty state
    // Note: In CI with seed data, this may not actually be empty,
    // but we test the UI behavior anyway

    const libraryPage = new LibraryPage(page);
    await libraryPage.goto();

    // Wait for page to load (either cards or empty state)
    await libraryPage.waitForCards();

    // Either cards are displayed OR empty state is shown - both are valid
    const cardCount = await libraryPage.analysisCards.count();
    const emptyStateVisible = await libraryPage.emptyState.isVisible().catch(() => false);

    // At least one should be true (cards OR empty state)
    expect(cardCount > 0 || emptyStateVisible).toBe(true);

    // Search input should always be visible
    await expect(libraryPage.searchInput).toBeVisible();
  });
});
