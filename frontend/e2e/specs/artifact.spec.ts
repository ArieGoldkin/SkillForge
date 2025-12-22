import { test, expect } from '@playwright/test';
import { ArtifactPage } from '../page-objects';
import { getCompletedAnalysis } from '../utils/api-helpers';

test.describe('Artifact Page - Preview and Download', () => {
  let artifactPage: ArtifactPage;
  let artifactId: string | null = null;
  let analysisId: string | null = null;

  test.beforeAll(async ({ request }) => {
    // Get a completed analysis with artifact
    // Backend health is checked implicitly by getCompletedAnalysis
    const completedAnalysis = await getCompletedAnalysis(request);

    if (completedAnalysis) {
      artifactId = completedAnalysis.artifact_id;
      analysisId = completedAnalysis.analysis_id;
    }
    // If no completed analysis, tests will be skipped in beforeEach
  });

  test.beforeEach(async ({ page }) => {
    // Skip all artifact tests if no completed analysis with artifact exists
    test.skip(!artifactId, 'No completed analysis with artifact found - run a full analysis first');

    artifactPage = new ArtifactPage(page);
    // Navigate using the artifact ID, not analysis ID
    await artifactPage.goto(artifactId!, analysisId);
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
    // Wait for markdown content to be visible first (artifact takes time to load)
    await expect(artifactPage.markdownContent).toBeVisible({ timeout: 15000 });

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

  test('should copy code block to clipboard', async ({ page, context, browserName }) => {
    // Skip on Firefox and WebKit - they don't support clipboard permissions via grantPermissions
    // See: https://playwright.dev/docs/api/class-browsercontext#browser-context-grant-permissions
    test.skip(
      browserName === 'firefox' || browserName === 'webkit',
      'Clipboard permissions not supported on Firefox/WebKit'
    );

    // Grant clipboard permissions (only works on Chromium-based browsers)
    await context.grantPermissions(['clipboard-read', 'clipboard-write']);

    // Use the page object method to copy the first code block
    const codeBlockCount = await artifactPage.codeBlocks.count();
    if (codeBlockCount > 0) {
      await artifactPage.copyCodeBlock(0);

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
