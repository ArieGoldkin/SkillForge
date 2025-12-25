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
  /** Hero summary card (for both in-progress and completed - Issue #533) */
  readonly heroSummaryCard: Locator;
  /** Active analysis view container (default fallback view) */
  readonly activeAnalysisView: Locator;
  /** Stage indicator test ID */
  readonly stageIndicator: Locator;
  /** Status text test ID */
  readonly statusText: Locator;
  /** View Results button in HeroSummaryCard (Issue #533) */
  readonly viewResultsButton: Locator;
  /** View Guide link/button in AnalysisCompleteCard (fallback view) */
  readonly viewGuideButton: Locator;
  /** Combined: Any button/link that leads to artifact (View Results OR View Guide) */
  readonly viewArtifactButton: Locator;
  /** Error message alert */
  readonly errorMessage: Locator;
  /** Analysis heading (Issue #533 - HeroSummaryCard h2) - covers all states */
  readonly analysisHeading: Locator;

  constructor(page: Page) {
    super(page);
    // Issue #533: HeroSummaryCard has data-testid="hero-summary-card"
    this.heroSummaryCard = page.getByTestId('hero-summary-card');
    // Active analysis view container (present in default fallback route)
    this.activeAnalysisView = page.getByTestId('active-analysis-view');
    this.stageIndicator = page.getByTestId('stage-indicator');
    this.statusText = page.getByTestId('status-text');

    // View Results button in HeroSummaryCard (Issue #533)
    this.viewResultsButton = page.getByRole('button', { name: /view.*result/i });
    // View Guide link/button in AnalysisCompleteCard (fallback completion view)
    this.viewGuideButton = page.getByRole('link', { name: /view.*guide/i });
    // Combined: Find any button/link that leads to artifact
    // This covers both CompletedAnalysisView (View Results) and AnalysisCompleteCard (View Guide)
    this.viewArtifactButton = page
      .getByRole('button', { name: /view.*result/i })
      .or(page.getByRole('link', { name: /view.*guide/i }));

    this.errorMessage = page.getByRole('alert');
    // Analysis heading - covers all states in HeroSummaryCard:
    // - "Analysis Complete" (completed successfully)
    // - "Complete with Errors" (completed with failures)
    // - "Analysis In Progress" (still running)
    // - "Analysis Completed with Errors" (legacy CompleteCardContent)
    this.analysisHeading = page.getByRole('heading', {
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
    // Issue #533: HeroSummaryCard shows analysis heading
    // Accept "Analysis Complete" or "Complete with Errors" as valid completion states
    await expect(this.analysisHeading).toBeVisible({ timeout });
  }

  /**
   * Wait for page to fully load (HeroSummaryCard or ActiveAnalysisView visible)
   */
  async waitForPageLoad(timeout = 20000) {
    // Wait for either HeroSummaryCard or ActiveAnalysisView to be visible
    const pageLoaded = this.heroSummaryCard.or(this.activeAnalysisView);
    await expect(pageLoaded).toBeVisible({ timeout });
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
