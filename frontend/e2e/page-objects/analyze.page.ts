import type { Page, Locator } from '@playwright/test';
import { expect } from '@playwright/test';
import { BasePage } from './base.page';

/**
 * Page object for the Analysis page (progress tracking via SSE).
 * Monitors real-time progress updates and completion state.
 */
export class AnalyzePage extends BasePage {
  readonly progressBar: Locator;
  readonly stageIndicator: Locator;
  readonly statusText: Locator;
  readonly viewArtifactButton: Locator;
  readonly errorMessage: Locator;

  constructor(page: Page) {
    super(page);
    this.progressBar = page.getByRole('progressbar');
    this.stageIndicator = page.getByTestId('stage-indicator');
    this.statusText = page.getByTestId('status-text');
    this.viewArtifactButton = page.getByRole('link', { name: /view.*guide|view.*artifact|view.*result/i });
    this.errorMessage = page.getByRole('alert');
  }

  async goto(analysisId: string) {
    await this.navigate(`/analyze/${analysisId}`);
  }

  async waitForStage(stageName: string, timeout = 30000) {
    await expect(this.page.getByText(new RegExp(stageName, 'i'))).toBeVisible({ timeout });
  }

  async waitForComplete(timeout = 60000) {
    // Use a specific heading that indicates completion rather than broad pattern
    await expect(
      this.page.getByRole('heading', { name: /analysis complete/i })
    ).toBeVisible({ timeout });
  }

  async getProgress(): Promise<number> {
    const progressValue = await this.progressBar.getAttribute('aria-valuenow');
    return progressValue ? parseInt(progressValue, 10) : 0;
  }

  async expectComplete() {
    await expect(this.viewArtifactButton).toBeVisible();
  }

  async navigateToArtifact() {
    await this.viewArtifactButton.click();
    await expect(this.page).toHaveURL(/\/artifact\/.+/);
  }

  async expectError() {
    await expect(this.errorMessage).toBeVisible();
  }

  async expectReconnecting() {
    await expect(this.page.getByText(/reconnecting|retrying/i)).toBeVisible();
  }
}
