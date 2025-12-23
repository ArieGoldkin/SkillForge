import type { Page, Locator } from '@playwright/test';
import { expect } from '@playwright/test';

import { BasePage } from './base.page';

/**
 * Page object for the Artifact page (markdown preview and download).
 * Handles viewing, downloading, and copying artifact content.
 */
export class ArtifactPage extends BasePage {
  readonly markdownContent: Locator;
  readonly downloadButton: Locator;
  readonly copyButton: Locator;
  readonly title: Locator;
  readonly metadata: Locator;
  readonly codeBlocks: Locator;
  readonly startTutorButton: Locator;
  readonly feedbackSection: Locator;
  readonly thumbsUpButton: Locator;
  readonly thumbsDownButton: Locator;
  readonly commentButton: Locator;

  constructor(page: Page) {
    super(page);
    // Use data-testid for more reliable selectors
    this.markdownContent = page.getByTestId('markdown-preview');
    this.downloadButton = page.getByTestId('download-button');
    this.copyButton = page.getByTestId('copy-button');
    // Use header-specific h1 to avoid matching markdown content headings
    this.title = page.locator('header h1');
    this.metadata = page.locator('[data-testid="artifact-metadata"], .artifact-metadata, [class*="metadata"]');
    this.codeBlocks = page.getByTestId('code-block');
    this.startTutorButton = page.getByRole('button', { name: /start.*tutor|ask.*question/i });
    // Feedback buttons
    this.feedbackSection = page.locator('text="Was this helpful?"').locator('..');
    this.thumbsUpButton = page.getByRole('button', { name: /this was helpful|thumbs up/i });
    this.thumbsDownButton = page.getByRole('button', { name: /this was not helpful|thumbs down/i });
    this.commentButton = page.getByRole('button', { name: /add comment/i });
  }

  async goto(artifactId: string, analysisId?: string | null) {
    const url = analysisId
      ? `/artifact/${artifactId}?analysisId=${analysisId}`
      : `/artifact/${artifactId}`;
    await this.navigate(url);
  }

  async expectMarkdownVisible() {
    await expect(this.markdownContent).toBeVisible();
  }

  async expectTitle(title: string | RegExp) {
    await expect(this.title).toContainText(title);
  }

  async downloadArtifact() {
    const downloadPromise = this.page.waitForEvent('download');
    await this.downloadButton.click();
    return downloadPromise;
  }

  async copyCodeBlock(index = 0) {
    // Get the code block container (which includes the copy button)
    const codeBlockContainer = this.page.getByTestId('code-block-container').nth(index);
    // Find the copy button within the container
    const copyButton = codeBlockContainer.getByTestId('copy-button');
    await copyButton.click();
  }

  async expectCodeBlocksCount(count: number) {
    await expect(this.codeBlocks).toHaveCount(count);
  }

  async navigateToTutor() {
    await this.startTutorButton.click();
    await expect(this.page).toHaveURL(/\/tutor\/.+/);
  }

  async submitThumbsUp() {
    await this.thumbsUpButton.click();
    await expect(this.thumbsUpButton).toHaveAttribute('aria-pressed', 'true');
  }

  async submitThumbsDown(comment?: string) {
    await this.thumbsDownButton.click();

    if (comment) {
      // Wait for comment dialog
      const commentDialog = this.page.locator('[role="dialog"]');
      await expect(commentDialog).toBeVisible({ timeout: 5000 });

      // Fill comment
      const commentInput = this.page.getByPlaceholder(/what could we improve/i).or(this.page.locator('textarea')).first();
      await commentInput.fill(comment);

      // Submit
      const submitButton = this.page.getByRole('button', { name: /submit|send/i });
      await submitButton.click();

      // Wait for dialog to close
      await expect(commentDialog).not.toBeVisible({ timeout: 5000 });
    }

    await expect(this.thumbsDownButton).toHaveAttribute('aria-pressed', 'true');
  }
}
