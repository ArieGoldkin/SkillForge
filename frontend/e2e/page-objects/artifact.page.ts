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
}
