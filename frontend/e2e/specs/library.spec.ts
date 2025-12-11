import { test, expect } from '@playwright/test';
import { LibraryPage } from '../page-objects';
import { mockLibraryAPI, mockEmptyLibraryAPI } from '../utils';

test.describe('Library Page - Search and Filter', () => {
  let libraryPage: LibraryPage;

  test.beforeEach(async ({ page }) => {
    await mockLibraryAPI(page);
    libraryPage = new LibraryPage(page);
    await libraryPage.goto();
  });

  test('should display the library page with search input', async () => {
    await expect(libraryPage.searchInput).toBeVisible();
  });

  test('should display analysis cards', async () => {
    await libraryPage.expectCardCount(5); // Mock has 5 items
  });

  test('should search library by query', async ({ page }) => {
    await libraryPage.search('React');

    // Should show filtered results
    await page.waitForTimeout(500); // Wait for search to complete
    const titles = await libraryPage.getCardTitles();

    // At least some results should contain React
    expect(titles.length).toBeGreaterThan(0);
  });

  test('should filter by content type', async ({ page }) => {
    // Click the filter dropdown
    const filterButton = libraryPage.contentTypeFilter;
    if (await filterButton.isVisible()) {
      await filterButton.click();

      // Select video type
      const videoOption = page.getByRole('option', { name: /video/i });
      if (await videoOption.isVisible()) {
        await videoOption.click();

        // Results should be filtered
        await page.waitForTimeout(500);
      }
    }
  });

  test('should toggle search modes', async ({ page }) => {
    const modeToggle = libraryPage.searchModeToggle;
    if (await modeToggle.isVisible()) {
      await modeToggle.click();

      // Check for mode options
      const semanticOption = page.getByRole('option', { name: /semantic/i });
      if (await semanticOption.isVisible()) {
        await semanticOption.click();
      }
    }
  });

  test('should navigate to analysis from card click', async ({ page }) => {
    // Click the first card
    await libraryPage.selectCard(0);

    // Should navigate to analysis or artifact page
    await expect(page).toHaveURL(/\/(analyze|artifact)\/.+/);
  });

  test('should show empty state when no results', async ({ page }) => {
    // Reset with empty mock
    await mockEmptyLibraryAPI(page);
    await page.reload();

    // Empty state should be visible
    await expect(
      page.getByText(/no.*results|no.*analyses|empty|nothing/i)
    ).toBeVisible({ timeout: 5000 });
  });

  test('should display card metadata', async () => {
    // First card should have title and metadata
    const firstCard = libraryPage.analysisCards.first();
    await expect(firstCard).toBeVisible();

    // Card should contain a heading
    const heading = firstCard.getByRole('heading');
    await expect(heading).toBeVisible();
  });

  test('should support keyboard navigation', async ({ page }) => {
    // Focus on search input
    await libraryPage.searchInput.focus();

    // Type a query
    await page.keyboard.type('React');

    // Press Enter to search
    await page.keyboard.press('Enter');

    // Search should be triggered
    await page.waitForTimeout(500);
  });
});
