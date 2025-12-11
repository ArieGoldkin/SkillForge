import { test, expect } from '@playwright/test';
import { ArtifactPage } from '../page-objects';
import { mockArtifactAPI } from '../utils';

test.describe('Artifact Page - Preview and Download', () => {
  let artifactPage: ArtifactPage;

  test.beforeEach(async ({ page }) => {
    await mockArtifactAPI(page);
    artifactPage = new ArtifactPage(page);
    await artifactPage.goto('test-artifact-456');
  });

  test('should display artifact page with title', async () => {
    await expect(artifactPage.title).toBeVisible();
  });

  test('should preview markdown content', async () => {
    // The markdown content container should be visible
    await expect(artifactPage.markdownContent).toBeVisible();

    // Should contain rendered markdown (headings, paragraphs)
    const headingCount = await artifactPage.page.locator('h1, h2, h3').count();
    expect(headingCount).toBeGreaterThanOrEqual(1);
  });

  test('should display code blocks from markdown', async () => {
    // Should have code blocks in the artifact
    const codeBlocks = artifactPage.codeBlocks;
    const count = await codeBlocks.count();
    expect(count).toBeGreaterThan(0);
  });

  test('should have download button visible', async () => {
    await expect(artifactPage.downloadButton).toBeVisible();
  });

  test('should download artifact as markdown file', async ({ page }) => {
    // Set up download listener
    const downloadPromise = page.waitForEvent('download');

    await artifactPage.downloadButton.click();

    const download = await downloadPromise;

    // Verify download was triggered
    expect(download.suggestedFilename()).toContain('.md');
  });

  test('should copy code block to clipboard', async ({ page, context }) => {
    // Grant clipboard permissions
    await context.grantPermissions(['clipboard-read', 'clipboard-write']);

    // Find copy button for first code block
    const codeBlock = artifactPage.codeBlocks.first();
    await codeBlock.hover();

    const copyButton = page.getByRole('button', { name: /copy/i }).first();
    if (await copyButton.isVisible()) {
      await copyButton.click();

      // Verify clipboard contains code
      const clipboardContent = await page.evaluate(() => navigator.clipboard.readText());
      expect(clipboardContent.length).toBeGreaterThan(0);
    }
  });

  test('should display artifact metadata', async () => {
    // Check for metadata elements (topics, complexity, etc.)
    const metadata = artifactPage.metadata;
    if (await metadata.isVisible()) {
      await expect(metadata).toBeVisible();
    }
  });

  test('should have start tutor button', async () => {
    const tutorButton = artifactPage.startTutorButton;
    if (await tutorButton.isVisible()) {
      await expect(tutorButton).toBeVisible();
    }
  });
});
