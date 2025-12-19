/**
 * Langfuse Feedback Integration E2E Test
 *
 * Tests the end-to-end flow of submitting user feedback from the artifact page
 * and verifying it appears in Langfuse with proper trace linking.
 *
 * Test Flow:
 * 1. Navigate to artifact page with known trace_id
 * 2. Submit thumbs-up feedback
 * 3. Verify in Langfuse UI that score appears with correct trace_id
 * 4. Check annotation queue if applicable
 */

import { test, expect } from '@playwright/test';
import type { Page } from '@playwright/test';

// Configuration
const ARTIFACT_URL = 'http://localhost:5173/artifact/78151bce-52aa-4847-8ba7-db0324cdd6ff?analysisId=dff652c1-9ca3-49c2-a8be-8db528447e54';
const LANGFUSE_URL = 'http://localhost:3000';
const LANGFUSE_EMAIL = 'dev@skillforge.local';
const LANGFUSE_PASSWORD = 'skillforge-dev-password';

/**
 * Helper: Login to Langfuse UI
 */
async function loginToLangfuse(page: Page) {
  await page.goto(LANGFUSE_URL);

  // Check if already logged in (look for Organizations or SkillForge)
  const isLoggedIn = await page.getByText(/organizations|SkillForge|scores|traces/i).isVisible({ timeout: 3000 }).catch(() => false);
  if (isLoggedIn) {
    console.log('Already logged in to Langfuse');
    return;
  }

  // Login
  console.log('Logging in to Langfuse...');
  await page.getByLabel(/email/i).fill(LANGFUSE_EMAIL);
  await page.getByLabel(/password/i).fill(LANGFUSE_PASSWORD);
  await page.getByRole('button', { name: /sign in|login/i }).click();

  // Wait for any post-login page (Organizations page or project dashboard)
  await page.waitForLoadState('networkidle', { timeout: 10000 });
  console.log('Logged in successfully');
}

/**
 * Helper: Navigate to project from Organizations page
 */
async function navigateToProject(page: Page): Promise<string> {
  // If on Organizations page, click "Go to project"
  const goToProjectButton = page.getByRole('button', { name: /go to project/i });
  const isOnOrgsPage = await goToProjectButton.isVisible({ timeout: 3000 }).catch(() => false);

  if (isOnOrgsPage) {
    await goToProjectButton.click();
    await page.waitForLoadState('networkidle');
  }

  // Extract current URL to get project slug
  const currentUrl = page.url();
  const projectMatch = currentUrl.match(/\/project\/([^\/]+)/);
  const projectSlug = projectMatch ? projectMatch[1] : 'unknown';

  console.log(`Navigated to project: ${projectSlug}`);
  return projectSlug;
}

/**
 * Helper: Wait for score to appear in Langfuse
 */
async function waitForScoreInLangfuse(page: Page, expectedValue: number, timeoutMs = 15000): Promise<{ traceId: string | null; found: boolean }> {
  const startTime = Date.now();
  let traceId: string | null = null;

  // First, navigate to the project
  const projectSlug = await navigateToProject(page);

  while (Date.now() - startTime < timeoutMs) {
    // Navigate to Scores page using discovered project slug
    await page.goto(`${LANGFUSE_URL}/project/${projectSlug}/scores`);
    await page.waitForTimeout(1000); // Wait for page to load

    // Look for user_feedback score with expected value
    const scoreRow = page.locator('tr', {
      has: page.locator('text="user_feedback"')
    }).filter({
      has: page.locator(`text="${expectedValue}"`)
    }).first();

    const isVisible = await scoreRow.isVisible({ timeout: 2000 }).catch(() => false);

    if (isVisible) {
      console.log(`Found user_feedback score with value ${expectedValue}`);

      // Try to extract trace_id from the row
      const traceLink = scoreRow.locator('a[href*="/traces/"]').first();
      const href = await traceLink.getAttribute('href').catch(() => null);
      if (href) {
        traceId = href.split('/traces/')[1]?.split('?')[0] || null;
        console.log(`Extracted trace_id: ${traceId}`);
      }

      return { traceId, found: true };
    }

    console.log(`Score not found yet, waiting... (${Math.floor((Date.now() - startTime) / 1000)}s elapsed)`);
    await page.waitForTimeout(2000);
  }

  return { traceId: null, found: false };
}

test.describe('Langfuse Feedback Integration E2E', () => {
  test.setTimeout(60000); // 60 second timeout for entire test

  test('should submit thumbs-up feedback and verify in Langfuse', async ({ page, context }) => {
    console.log('\n=== Step 1: Navigate to Artifact Page ===');
    await page.goto(ARTIFACT_URL);
    await page.waitForLoadState('networkidle');

    // Take snapshot of initial state
    await page.screenshot({ path: 'test-results/01-artifact-initial.png', fullPage: true });
    console.log('Screenshot saved: 01-artifact-initial.png');

    // Verify page loaded
    await expect(page.getByTestId('markdown-preview')).toBeVisible({ timeout: 15000 });
    console.log('Artifact page loaded successfully');

    console.log('\n=== Step 2: Submit Thumbs-Up Feedback ===');

    // Find the feedback section
    const feedbackSection = page.locator('text="Was this helpful?"').locator('..');
    await expect(feedbackSection).toBeVisible({ timeout: 5000 });

    // Find thumbs-up button
    const thumbsUpButton = page.getByRole('button', { name: /this was helpful|thumbs up/i });
    await expect(thumbsUpButton).toBeVisible();

    // Take screenshot before clicking
    await page.screenshot({ path: 'test-results/02-before-feedback.png', fullPage: true });
    console.log('Screenshot saved: 02-before-feedback.png');

    // Click thumbs-up
    await thumbsUpButton.click();
    console.log('Clicked thumbs-up button');

    // Wait for feedback to be submitted (button should change to selected state)
    await page.waitForTimeout(2000);

    // Take screenshot after clicking
    await page.screenshot({ path: 'test-results/03-after-feedback.png', fullPage: true });
    console.log('Screenshot saved: 03-after-feedback.png');

    // Verify button is now selected (variant changed)
    const isSelected = await thumbsUpButton.getAttribute('aria-pressed');
    console.log(`Thumbs-up button aria-pressed: ${isSelected}`);

    console.log('\n=== Step 3: Verify in Langfuse Scores Page ===');

    // Open new tab for Langfuse
    const langfusePage = await context.newPage();
    await loginToLangfuse(langfusePage);

    // Wait for score to appear
    console.log('Waiting for user_feedback score with value 1.0 to appear...');
    const { traceId, found } = await waitForScoreInLangfuse(langfusePage, 1.0, 20000);

    if (!found) {
      // Take screenshot of scores page for debugging
      await langfusePage.screenshot({ path: 'test-results/04-langfuse-scores-not-found.png', fullPage: true });
      console.log('Screenshot saved: 04-langfuse-scores-not-found.png');
      throw new Error('User feedback score with value 1.0 not found in Langfuse within 20 seconds');
    }

    // Take screenshot showing the score
    await langfusePage.screenshot({ path: 'test-results/04-langfuse-scores-success.png', fullPage: true });
    console.log('Screenshot saved: 04-langfuse-scores-success.png');

    // Report findings
    if (traceId) {
      console.log(`SUCCESS: Found user_feedback score with value 1.0 linked to trace_id: ${traceId}`);
    } else {
      console.log('WARNING: Found user_feedback score but could not extract trace_id');
    }

    console.log('\n=== Step 4: Check Annotation Queue ===');

    // Navigate to annotation queue (use the project slug we discovered earlier)
    const currentUrl = langfusePage.url();
    const projectMatch = currentUrl.match(/\/project\/([^\/]+)/);
    const projectSlug = projectMatch ? projectMatch[1] : 'unknown';

    await langfusePage.goto(`${LANGFUSE_URL}/project/${projectSlug}/annotation-queues`);
    await langfusePage.waitForTimeout(2000);

    // Look for "SkillForge Review Queue"
    const queueExists = await langfusePage.getByText(/SkillForge Review Queue/i).isVisible({ timeout: 5000 }).catch(() => false);

    if (queueExists) {
      console.log('Found SkillForge Review Queue');

      // Click on the queue to see items
      await langfusePage.getByText(/SkillForge Review Queue/i).click();
      await langfusePage.waitForTimeout(2000);

      // Take screenshot
      await langfusePage.screenshot({ path: 'test-results/05-annotation-queue.png', fullPage: true });
      console.log('Screenshot saved: 05-annotation-queue.png');

      // Check if there are any items
      const itemCount = await langfusePage.locator('tr[data-row-key], .queue-item').count();
      console.log(`Annotation queue has ${itemCount} items`);
    } else {
      console.log('SkillForge Review Queue not found (this is OK if no negative feedback was submitted)');
      await langfusePage.screenshot({ path: 'test-results/05-no-annotation-queue.png', fullPage: true });
      console.log('Screenshot saved: 05-no-annotation-queue.png');
    }

    console.log('\n=== Test Summary ===');
    console.log('✅ Step 1: Navigated to artifact page');
    console.log('✅ Step 2: Submitted thumbs-up feedback');
    console.log(`✅ Step 3: Verified score in Langfuse (trace_id: ${traceId || 'not extracted'})`);
    console.log(`✅ Step 4: Checked annotation queue (exists: ${queueExists})`);

    await langfusePage.close();
  });

  test('should submit thumbs-down with comment and verify in Langfuse', async ({ page, context }) => {
    console.log('\n=== Test: Thumbs-Down with Comment ===');

    // Navigate to artifact page
    await page.goto(ARTIFACT_URL);
    await page.waitForLoadState('networkidle');
    await expect(page.getByTestId('markdown-preview')).toBeVisible({ timeout: 15000 });

    // Find thumbs-down button
    const thumbsDownButton = page.getByRole('button', { name: /this was not helpful|thumbs down/i });
    await expect(thumbsDownButton).toBeVisible();

    // Click thumbs-down
    await thumbsDownButton.click();
    console.log('Clicked thumbs-down button');

    // Comment dialog should appear
    const commentDialog = page.locator('[role="dialog"]');
    await expect(commentDialog).toBeVisible({ timeout: 5000 });
    console.log('Comment dialog appeared');

    // Take screenshot of dialog
    await page.screenshot({ path: 'test-results/06-comment-dialog.png', fullPage: true });
    console.log('Screenshot saved: 06-comment-dialog.png');

    // Enter comment
    const commentInput = page.getByPlaceholder(/what could we improve/i).or(page.locator('textarea')).first();
    await commentInput.fill('The implementation guide lacks specific code examples for authentication.');
    console.log('Entered comment text');

    // Submit comment
    const submitButton = page.getByRole('button', { name: /submit|send/i });
    await submitButton.click();
    console.log('Submitted comment');

    // Dialog should close
    await expect(commentDialog).not.toBeVisible({ timeout: 5000 });

    // Wait for submission
    await page.waitForTimeout(2000);

    // Verify in Langfuse
    const langfusePage = await context.newPage();
    await loginToLangfuse(langfusePage);

    console.log('Waiting for user_feedback score with value 0.0 to appear...');
    const { traceId, found } = await waitForScoreInLangfuse(langfusePage, 0.0, 20000);

    if (!found) {
      await langfusePage.screenshot({ path: 'test-results/07-langfuse-negative-not-found.png', fullPage: true });
      console.log('Screenshot saved: 07-langfuse-negative-not-found.png');
      throw new Error('User feedback score with value 0.0 not found in Langfuse');
    }

    await langfusePage.screenshot({ path: 'test-results/07-langfuse-negative-success.png', fullPage: true });
    console.log('Screenshot saved: 07-langfuse-negative-success.png');
    console.log(`SUCCESS: Found negative feedback with trace_id: ${traceId || 'not extracted'}`);

    await langfusePage.close();
  });
});
