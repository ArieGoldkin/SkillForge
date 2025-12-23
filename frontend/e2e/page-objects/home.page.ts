import type { Page, Locator } from '@playwright/test';
import { expect } from '@playwright/test';

import { BasePage } from './base.page';

/**
 * Page object for the Home page (URL submission).
 * Handles URL input, skill level selection, and form submission.
 */
export class HomePage extends BasePage {
  readonly urlInput: Locator;
  readonly submitButton: Locator;
  readonly skillLevelSelector: Locator;
  readonly errorMessage: Locator;
  readonly loadingSpinner: Locator;

  constructor(page: Page) {
    super(page);
    this.urlInput = page.getByPlaceholder(/paste.*url|enter.*url|url/i);
    this.submitButton = page.getByRole('button', { name: /analyze|submit|start/i });
    this.skillLevelSelector = page.getByTestId('skill-level-selector');
    this.errorMessage = page.getByRole('alert');
    this.loadingSpinner = page.getByTestId('loading-spinner');
  }

  async goto() {
    await this.navigate('/');
  }

  async submitUrl(url: string) {
    await this.urlInput.fill(url);
    await this.submitButton.click();
  }

  async selectSkillLevel(level: 'beginner' | 'intermediate' | 'advanced') {
    await this.skillLevelSelector.click();
    await this.page.getByRole('option', { name: new RegExp(level, 'i') }).click();
  }

  async expectNavigatedToAnalysis() {
    await expect(this.page).toHaveURL(/\/analyze\/.+/);
  }

  async expectError(message?: string) {
    await expect(this.errorMessage).toBeVisible();
    if (message) {
      await expect(this.errorMessage).toContainText(message);
    }
  }

  async expectLoading() {
    await expect(this.submitButton).toBeDisabled();
  }
}
