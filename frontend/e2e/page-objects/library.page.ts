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
    this.contentTypeFilter = page.getByTestId('content-type-filter');
    this.searchModeToggle = page.getByTestId('search-mode-toggle');
    this.analysisCards = page.getByTestId('analysis-card');
    this.emptyState = page.getByTestId('empty-state');
    this.loadingState = page.getByTestId('loading-state');
    this.pagination = page.getByTestId('pagination');
  }

  async goto() {
    await this.navigate('/library');
  }

  async search(query: string) {
    await this.searchInput.fill(query);
    await this.searchButton.click();
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
