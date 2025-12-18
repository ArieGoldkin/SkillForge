import type { Page, Locator } from '@playwright/test';
import { expect } from '@playwright/test';
import { BasePage } from './base.page';

/**
 * Page object for the Library page (search and filter analyses).
 * Handles search, filtering, and navigation to individual analyses.
 */
export class LibraryPage extends BasePage {
  readonly searchInput: Locator;
  readonly searchButton: Locator;
  readonly contentTypeFilter: Locator;
  readonly searchModeToggle: Locator;
  readonly analysisCards: Locator;
  readonly emptyState: Locator;
  readonly loadingState: Locator;
  readonly pagination: Locator;

  constructor(page: Page) {
    super(page);
    this.searchInput = page.getByPlaceholder(/search/i);
    this.searchButton = page.getByRole('button', { name: /search/i });
    // Fallback selectors for filter/toggle that might have different implementations
    this.contentTypeFilter = page.getByTestId('content-type-filter').or(page.getByRole('combobox', { name: /type|filter/i }));
    this.searchModeToggle = page.getByTestId('search-mode-toggle').or(page.getByRole('combobox', { name: /mode/i }));
    // Cards can be in various formats - look for article elements or card-like structures
    this.analysisCards = page.getByTestId('analysis-card').or(page.locator('article, [class*="card"]').filter({ hasText: /.+/ }));
    this.emptyState = page.getByTestId('empty-state').or(page.getByText(/no.*results|no.*found/i));
    this.loadingState = page.getByTestId('loading-state').or(page.locator('[aria-busy="true"]'));
    this.pagination = page.getByTestId('pagination').or(page.getByRole('navigation', { name: /pagination/i }));
  }

  async goto() {
    await this.navigate('/library');
  }

  /**
   * Search the library with proper API response waiting.
   * Waits for the library API response instead of using arbitrary timeouts.
   */
  async search(query: string) {
    await this.searchInput.fill(query);

    // Set up response promise BEFORE triggering the action to avoid race condition
    const responsePromise = this.page.waitForResponse(
      (response) =>
        response.url().includes('/api/v1/library') && response.status() === 200
    );

    // Trigger immediate search with Enter key (no search button exists)
    await this.searchInput.press('Enter');

    // Wait for API response to complete
    await responsePromise;

    // Wait for loading state to clear (if it exists)
    await expect(this.loadingState).not.toBeVisible({ timeout: 10000 }).catch(() => {
      // Loading state might not be implemented or might be very brief
    });
  }

  /**
   * Search without waiting for response (for testing immediate UI behavior).
   */
  async searchNoWait(query: string) {
    await this.searchInput.fill(query);
    await this.searchInput.press('Enter');
  }

  async filterByContentType(type: 'all' | 'article' | 'video' | 'repository') {
    await this.contentTypeFilter.click();
    await this.page.getByRole('option', { name: new RegExp(type, 'i') }).click();
  }

  async toggleSearchMode(mode: 'hybrid' | 'fulltext' | 'semantic') {
    await this.searchModeToggle.click();
    await this.page.getByRole('option', { name: new RegExp(mode, 'i') }).click();
  }

  async selectCard(index: number) {
    await this.analysisCards.nth(index).click();
  }

  /**
   * Wait for cards to be visible in the library grid.
   * Useful after navigation or search operations.
   */
  async waitForCards(timeout = 10000) {
    // Wait for the list container to be visible first
    await this.page.locator('[role="list"]').waitFor({ state: 'visible', timeout });

    // Then wait for at least one card (if data exists)
    // Using a shorter timeout since grid is already visible
    await this.analysisCards.first().waitFor({ state: 'visible', timeout: 5000 }).catch(() => {
      // No cards might be valid (empty state)
    });
  }

  async expectCardCount(count: number) {
    await expect(this.analysisCards).toHaveCount(count);
  }

  async expectEmptyState() {
    await expect(this.emptyState).toBeVisible();
  }

  async expectLoading() {
    await expect(this.loadingState).toBeVisible();
  }

  async expectNavigatedToAnalysis() {
    await expect(this.page).toHaveURL(/\/analyze\/.+/);
  }

  async getCardTitles(): Promise<string[]> {
    const titles: string[] = [];
    const count = await this.analysisCards.count();
    for (let i = 0; i < count; i++) {
      const title = await this.analysisCards.nth(i).getByRole('heading').textContent();
      if (title) titles.push(title);
    }
    return titles;
  }
}
