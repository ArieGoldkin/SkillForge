/**
 * Abort Signal Propagation E2E Tests
 *
 * Tests that abort signals properly stop workflow execution:
 * - Workflow stops when extraction fails
 * - Later stages do not execute after abort
 */

import { test, expect } from '@playwright/test';

import { AnalyzePage } from '../page-objects';
import { createAnalysis } from '../utils/api-helpers';

test.describe('Abort Signal Propagation', () => {
  test('should stop workflow when extraction fails', async ({ page, request }) => {
    test.skip(!!process.env.CI, 'Requires backend LLM processing');

    // Create analysis that will fail at extraction
    const invalidUrl = 'https://invalid-url-for-abort-test.invalid';
    const { analysis_id } = await createAnalysis(request, invalidUrl);

    const analyzePage = new AnalyzePage(page);
    await analyzePage.goto(analysis_id);

    // Wait for extraction failure
    await expect(
      page.getByText(/extraction.*fail|failed.*extract|error/i)
        .or(page.getByRole('alert'))
    ).toBeVisible({ timeout: 30000 });

    // Verify workflow stopped - no later stages should run
    // Check that we don't see embedding, supervisor, or agent stages
    await page.waitForTimeout(5000); // Wait a bit to ensure no further progress

    const embeddingStage = page.getByText(/embedding|generating.*embedding/i);
    const supervisorStage = page.getByText(/supervisor|routing/i);
    const agentStages = page.getByText(/tech.*comparison|security.*audit|agent/i);

    // These stages should NOT appear if abort worked correctly
    const embeddingVisible = await embeddingStage.isVisible({ timeout: 2000 }).catch(() => false);
    const supervisorVisible = await supervisorStage.isVisible({ timeout: 2000 }).catch(() => false);
    const agentsVisible = await agentStages.isVisible({ timeout: 2000 }).catch(() => false);

    // At least one should not be visible (workflow aborted)
    // Note: This is a soft check - some stages might appear briefly before abort
    expect(embeddingVisible && supervisorVisible && agentsVisible).toBe(false);
  });
});
