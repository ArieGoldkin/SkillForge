import type { Page, Locator } from '@playwright/test';
import { expect } from '@playwright/test';

import { BasePage } from './base.page';

/**
 * Page object for the Analysis page (progress tracking via SSE).
 * Monitors real-time progress updates and completion state.
 *
 * Issue #533: Updated for Hierarchical Accordion Progress Tracker
 * - HeroSummaryCard: Shows completion status with "View Results" button
 * - CompactGroupCard: Shows stage groups in responsive grid
 * - No more traditional progressbar - uses stage completion stats instead
 */
export class AnalyzePage extends BasePage {
  /** Progress bar (for in-progress analyses with traditional progress view) */
  readonly progressBar: Locator;
  /** Hero summary card (for completed analyses - Issue #533) */
  readonly heroSummaryCard: Locator;
  /** Stage indicator test ID */
  readonly stageIndicator: Locator;
  /** Status text test ID */
  readonly statusText: Locator;
  /** View Results button - Issue #533 changed from link to button */
  readonly viewArtifactButton: Locator;
  /** Legacy link selector for backward compatibility */
  readonly viewArtifactLink: Locator;
  /** Error message alert */
  readonly errorMessage: Locator;
  /** Analysis complete heading (Issue #533 - HeroSummaryCard h2) */
  readonly completionHeading: Locator;

  constructor(page: Page) {
    super(page);
    // Traditional progress bar (in-progress view)
    this.progressBar = page.getByRole('progressbar');
    // Issue #533: HeroSummaryCard is an article with aria-label
    this.heroSummaryCard = page.getByRole('article').filter({
      has: page.locator('h2'),
    });
    this.stageIndicator = page.getByTestId('stage-indicator');
    this.statusText = page.getByTestId('status-text');
    // Issue #533: View Results is now a BUTTON, not a link
    this.viewArtifactButton = page.getByRole('button', { name: /view.*result/i });
    // Legacy: Keep link selector for backward compatibility
    this.viewArtifactLink = page.getByRole('link', { name: /view.*guide|view.*artifact|view.*result/i });
    this.errorMessage = page.getByRole('alert');
    // Issue #533: Completion heading in HeroSummaryCard
    this.completionHeading = page.getByRole('heading', {
      name: /analysis complete|complete with errors|analysis in progress/i,
    });
  }

  async goto(analysisId: string) {
    await this.navigate(`/analyze/${analysisId}`);
  }

  async waitForStage(stageName: string, timeout = 30000) {
    await expect(this.page.getByText(new RegExp(stageName, 'i'))).toBeVisible({ timeout });
  }

  async waitForComplete(timeout = 60000) {
    // Issue #533: HeroSummaryCard shows completion heading
    // Accept "Analysis Complete" or "Complete with Errors" as valid completion states
    await expect(this.completionHeading).toBeVisible({ timeout });
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
