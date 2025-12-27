/**
 * Langfuse Feedback Integration E2E Test
 *
 * Tests the end-to-end flow of submitting user feedback from the artifact page
 * and verifying it appears in Langfuse with proper trace linking.
 *
 * Test Flow:
 * 1. Navigate to artifact page with known trace_id
 * 2. Submit thumbs-up feedback
 * 3. Verify via Langfuse API that score appears with correct trace_id
 *
 * Configuration:
 * - Uses e2e/config/langfuse.config.ts for dynamic configuration
 * - In CI: Uses seeded artifact data from seed_e2e_langfuse_data.py
 * - Locally: Uses default UUIDs (requires manual artifact setup)
 */

import { test, expect } from '@playwright/test';

import { langfuseConfig, getArtifactUrl } from '../config/langfuse.config';
import { logTestStep, logger } from '../utils';

// Configuration from dynamic config
const ARTIFACT_URL = getArtifactUrl();
const LANGFUSE_URL = langfuseConfig.langfuseUrl;

// Langfuse API credentials - MUST be provided via environment variables
// In CI: Set via docker-compose.e2e-langfuse.yml (pk-lf-ci-e2e-test / sk-lf-ci-e2e-test-secret)
// Locally: Export LANGFUSE_PUBLIC_KEY and LANGFUSE_SECRET_KEY before running tests
const LANGFUSE_PUBLIC_KEY = process.env.LANGFUSE_PUBLIC_KEY;
const LANGFUSE_SECRET_KEY = process.env.LANGFUSE_SECRET_KEY;

interface LangfuseScore {
  id: string;
  name: string;
  value: number;
  traceId: string;
  comment: string | null;
  createdAt: string;
}

interface LangfuseScoresResponse {
  data: LangfuseScore[];
  meta: { totalItems: number };
}

/**
 * Helper: Verify score exists in Langfuse via REST API
 * This is more reliable than UI scraping which can break with UI changes
 */
async function verifyScoreInLangfuseAPI(
  expectedValue: number,
  traceId: string,
  timeoutMs = 15000
): Promise<{ score: LangfuseScore | null; found: boolean }> {
  const startTime = Date.now();
  const authHeader = Buffer.from(`${LANGFUSE_PUBLIC_KEY}:${LANGFUSE_SECRET_KEY}`).toString('base64');

  while (Date.now() - startTime < timeoutMs) {
    try {
      const response = await fetch(
        `${LANGFUSE_URL}/api/public/scores?name=user_feedback&traceId=${traceId}`,
        {
          headers: {
            'Authorization': `Basic ${authHeader}`,
          },
        }
      );

      if (!response.ok) {
        logger.warn('Langfuse API returned non-OK status, retrying', {
          status: response.status,
          elapsed: Math.floor((Date.now() - startTime) / 1000),
        });
        await new Promise(resolve => setTimeout(resolve, 2000));
        continue;
      }

      const data: LangfuseScoresResponse = await response.json();

      // Find score with expected value
      const matchingScore = data.data.find(
        score => score.name === 'user_feedback' && score.value === expectedValue
      );

      if (matchingScore) {
        logger.info('Found user_feedback score via API', {
          scoreId: matchingScore.id,
          traceId: matchingScore.traceId,
          value: expectedValue,
        });
        return { score: matchingScore, found: true };
      }

      logger.debug('Score not found yet, waiting', {
        totalScores: data.meta.totalItems,
        elapsed: Math.floor((Date.now() - startTime) / 1000),
        expectedValue,
      });
    } catch (error) {
      logger.warn('Langfuse API error, retrying', {
        error: error instanceof Error ? error.message : String(error),
        elapsed: Math.floor((Date.now() - startTime) / 1000),
      });
    }

    await new Promise(resolve => setTimeout(resolve, 2000));
  }

  return { score: null, found: false };
}

// Get trace_id from config for API verification
const TRACE_ID = langfuseConfig.traceId || 'e2e-trace-langfuse-integration-test';

// Check if Langfuse credentials are configured
const isLangfuseConfigured = !!(LANGFUSE_PUBLIC_KEY && LANGFUSE_SECRET_KEY);

test.describe('Langfuse Feedback Integration E2E', () => {
  test.setTimeout(60000); // 60 second timeout for entire test

  // Skip all tests if Langfuse credentials aren't configured
  test.skip(!isLangfuseConfigured, 'Langfuse API credentials not configured. Set LANGFUSE_PUBLIC_KEY and LANGFUSE_SECRET_KEY environment variables.');

  // These tests require Langfuse to be running and configured
  // In CI: Uses docker-compose.e2e-langfuse.yml overlay with seeded data
  // Locally: Requires Langfuse dev stack running + credentials exported

  test('should submit thumbs-up feedback and verify in Langfuse', async ({ page }) => {
    logTestStep('Navigate to Artifact Page', {
      artifactUrl: ARTIFACT_URL,
      traceId: TRACE_ID,
    });

    // With storageState, direct navigation to artifact URL is faster (skips baseURL navigation)
    await page.goto(ARTIFACT_URL);
    await page.waitForLoadState('domcontentloaded');

    // Verify page loaded
    await expect(page.getByTestId('markdown-preview')).toBeVisible({ timeout: 15000 });
    logger.info('Artifact page loaded successfully');

    logTestStep('Submit Thumbs-Up Feedback');

    // Scroll to bottom to find feedback section (it's below the markdown content)
    await page.evaluate(() => window.scrollTo(0, document.body.scrollHeight));

    // Wait for feedback section to be in viewport after scroll
    const feedbackSection = page.locator('text="Was this helpful?"').locator('..');
    await expect(feedbackSection).toBeVisible({ timeout: 5000 });

    // Find thumbs-up button
    const thumbsUpButton = page.getByRole('button', { name: /this was helpful|thumbs up/i });
    await expect(thumbsUpButton).toBeVisible();

    // Click thumbs-up
    await thumbsUpButton.click();
    logger.info('Clicked thumbs-up button');

    // Wait for feedback to be submitted by checking aria-pressed attribute
    await expect(thumbsUpButton).toHaveAttribute('aria-pressed', 'true', { timeout: 5000 });

    // Verify button is now selected
    const isSelected = await thumbsUpButton.getAttribute('aria-pressed');
    logger.info('Thumbs-up button state', { ariaPressed: isSelected });

    logTestStep('Verify Score in Langfuse via API');

    // Use API verification instead of brittle UI scraping
    const { score, found } = await verifyScoreInLangfuseAPI(1, TRACE_ID, 15000);

    if (!found) {
      throw new Error(`User feedback score with value 1 not found in Langfuse for trace ${TRACE_ID}`);
    }

    logger.info('Test summary', {
      step1: 'Navigated to artifact page',
      step2: 'Submitted thumbs-up feedback',
      step3: 'Verified score in Langfuse via API',
      scoreId: score?.id,
      traceId: score?.traceId,
    });
  });

  test('should submit thumbs-down with comment and verify in Langfuse', async ({ page }) => {
    logTestStep('Thumbs-Down with Comment', {
      artifactUrl: ARTIFACT_URL,
      traceId: TRACE_ID,
    });

    // Navigate to artifact page
    await page.goto(ARTIFACT_URL);
    await page.waitForLoadState('domcontentloaded');
    await expect(page.getByTestId('markdown-preview')).toBeVisible({ timeout: 15000 });

    // Scroll to bottom to find feedback section
    await page.evaluate(() => window.scrollTo(0, document.body.scrollHeight));

    // Find thumbs-down button
    const thumbsDownButton = page.getByRole('button', { name: /this was not helpful|thumbs down/i });
    await expect(thumbsDownButton).toBeVisible();

    // Click thumbs-down
    await thumbsDownButton.click();
    logger.info('Clicked thumbs-down button');

    // Comment dialog should appear
    const commentDialog = page.locator('[role="dialog"]');
    await expect(commentDialog).toBeVisible({ timeout: 5000 });
    logger.info('Comment dialog appeared');

    // Enter comment
    const commentInput = page.getByPlaceholder(/what could we improve/i).or(page.locator('textarea')).first();
    await commentInput.fill('E2E test comment - testing negative feedback flow');
    logger.info('Entered comment text');

    // Submit comment
    const submitButton = page.getByRole('button', { name: /submit|send/i });
    await submitButton.click();
    logger.info('Submitted comment');

    // Dialog should close
    await expect(commentDialog).not.toBeVisible({ timeout: 5000 });

    // Wait for submission by checking thumbs-down button state
    await expect(thumbsDownButton).toHaveAttribute('aria-pressed', 'true', { timeout: 5000 });

    logTestStep('Verify Score in Langfuse via API');

    // Use API verification
    const { score, found } = await verifyScoreInLangfuseAPI(0, TRACE_ID, 15000);

    if (!found) {
      throw new Error(`User feedback score with value 0 not found in Langfuse for trace ${TRACE_ID}`);
    }

    logger.info('Test summary', {
      step1: 'Submitted thumbs-down feedback with comment',
      step2: 'Verified score in Langfuse via API',
      scoreId: score?.id,
      traceId: score?.traceId,
      comment: score?.comment || '(none)',
    });
  });
});
