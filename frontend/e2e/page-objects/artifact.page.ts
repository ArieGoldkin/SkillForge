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
    this.markdownContent = page.getByTestId('markdown-content');
    this.downloadButton = page.getByRole('button', { name: /download/i });
    this.copyButton = page.getByRole('button', { name: /copy/i });
    this.title = page.getByRole('heading', { level: 1 });
    this.metadata = page.getByTestId('artifact-metadata');
    this.codeBlocks = page.locator('pre code');
    this.startTutorButton = page.getByRole('button', { name: /start.*tutor|ask.*question/i });
  }

  async goto(artifactId: string) {
    await this.navigate(`/artifact/${artifactId}`);
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
    const codeBlock = this.codeBlocks.nth(index);
    await codeBlock.hover();
    await this.page.getByRole('button', { name: /copy/i }).first().click();
  }

  async expectCodeBlocksCount(count: number) {
    await expect(this.codeBlocks).toHaveCount(count);
  }

  async navigateToTutor() {
    await this.startTutorButton.click();
    await expect(this.page).toHaveURL(/\/tutor\/.+/);
  }
}
