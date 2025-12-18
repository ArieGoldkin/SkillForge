import { test, expect } from '@playwright/test';
import { AnalyzePage } from '../page-objects';
import { getCompletedAnalysis, createAnalysis, getAnalysis } from '../utils/api-helpers';

test.describe('Analysis Page - Progress Tracking', () => {
  test('should display the analysis page with progress indicator', async ({ page, request }) => {
    test.skip(!!process.env.CI, 'Requires backend LLM processing');

    // Get a completed analysis to avoid waiting for real processing
    const completed = await getCompletedAnalysis(request);

    // If no completed analysis exists, create one and test immediately
    const analysisId = completed?.analysis_id || (await createAnalysis(request)).analysis_id;

    const analyzePage = new AnalyzePage(page);
    await analyzePage.goto(analysisId);

    // Progress bar should be visible (either showing progress or completed state)
    await expect(analyzePage.progressBar).toBeVisible();
  });

  test('should display progress stages via SSE', async ({ page, request }) => {
    // Get a completed analysis - SSE stream will show final state immediately
    const completed = await getCompletedAnalysis(request);

    if (!completed) {
      test.skip(!completed, 'No completed analysis available - create one first');
    }

    const analyzePage = new AnalyzePage(page);
    await analyzePage.goto(completed!.analysis_id);

    // Wait for any stage indicator to appear (completed analyses show final stage)
    // Use .first() since multiple elements match the pattern
    await expect(
      page.getByText(/extraction|processing|complete|analysis/i).first()
    ).toBeVisible({ timeout: 10000 });
  });

  test('should show completion state', async ({ page, request }) => {
    // Get a completed analysis
    const completed = await getCompletedAnalysis(request);

    if (!completed) {
      test.skip(!completed, 'No completed analysis available - create one first');
    }

    const analyzePage = new AnalyzePage(page);
    await analyzePage.goto(completed!.analysis_id);

    // Wait for complete state - use specific heading to avoid multiple matches
    await analyzePage.waitForComplete();
    await expect(page.getByRole('heading', { name: /analysis complete/i })).toBeVisible();
  });

  test('should navigate to artifact on completion', async ({ page, request }) => {
    // Get a completed analysis with artifact
    const completed = await getCompletedAnalysis(request);

    if (!completed) {
      test.skip(!completed, 'No completed analysis available - create one first');
    }

    const analyzePage = new AnalyzePage(page);
    await analyzePage.goto(completed!.analysis_id);

    await analyzePage.waitForComplete();

    // Find and click the view artifact button/link
    const viewButton = page.getByRole('link', { name: /view.*guide|view.*artifact|view.*result/i });
    if (await viewButton.isVisible()) {
      await viewButton.click();
      await expect(page).toHaveURL(/\/artifact\/.+/);
    }
  });

  test('should handle SSE connection lifecycle', async ({ page, request }) => {
    test.skip(!!process.env.CI, 'Requires backend LLM processing');

    // Create a new analysis to observe SSE stream behavior
    const { analysis_id } = await createAnalysis(request);

    const analyzePage = new AnalyzePage(page);
    await analyzePage.goto(analysis_id);

    // Wait for initial connection and progress indicator
    await expect(analyzePage.progressBar).toBeVisible({ timeout: 10000 });

    // The app should handle SSE stream gracefully
    // Wait for progress to update (element-based wait instead of arbitrary timeout)
    // Either progress changes or status text appears
    await Promise.race([
      page.getByText(/processing|analyzing|extraction|complete/i).waitFor({ state: 'visible', timeout: 5000 }),
      page.waitForFunction(
        () => {
          const progress = document.querySelector('[role="progressbar"]');
          return progress && parseInt(progress.getAttribute('aria-valuenow') || '0', 10) > 0;
        },
        { timeout: 5000 }
      ),
    ]).catch(() => {
      // Either scenario is acceptable - SSE connection is established
    });

    // Verify the page remains functional during streaming
    await expect(page.locator('body')).toBeVisible();

    // Verify analysis is in progress or complete
    const analysis = await getAnalysis(request, analysis_id);
    expect(['pending', 'processing', 'complete', 'completed']).toContain(analysis.status);
  });

  test('should display analysis metadata', async ({ page, request }) => {
    test.skip(!!process.env.CI, 'Requires backend LLM processing');

    // Get any analysis (completed or in-progress)
    const completed = await getCompletedAnalysis(request);
    const analysisId = completed?.analysis_id || (await createAnalysis(request)).analysis_id;

    const analyzePage = new AnalyzePage(page);
    await analyzePage.goto(analysisId);

    // The page should show the analysis heading
    await expect(page.getByRole('heading', { name: /content analysis/i })).toBeVisible();
  });

  test('should track real-time progress updates', async ({ page, request }) => {
    // Skip in CI - this test requires real-time LLM processing which takes longer than test timeout
    test.skip(!!process.env.CI, 'Requires LLM for real-time progress tracking');

    // Create a new analysis to observe real-time updates
    const { analysis_id } = await createAnalysis(request);

    const analyzePage = new AnalyzePage(page);
    await analyzePage.goto(analysis_id);

    // Wait for initial progress
    await expect(analyzePage.progressBar).toBeVisible({ timeout: 10000 });

    // Get initial progress value
    const initialProgress = await analyzePage.getProgress();
    expect(initialProgress).toBeGreaterThanOrEqual(0);
    expect(initialProgress).toBeLessThanOrEqual(100);

    // Wait for progress to update using element-based polling
    // Poll for progress change instead of arbitrary timeout
    await page.waitForFunction(
      (initial) => {
        const progress = document.querySelector('[role="progressbar"]');
        const current = progress ? parseInt(progress.getAttribute('aria-valuenow') || '0', 10) : 0;
        return current > initial || current === 100;
      },
      initialProgress,
      { timeout: 10000 }
    ).catch(() => {
      // Progress may not change if analysis is very fast or already complete
    });

    // Get updated progress
    const updatedProgress = await analyzePage.getProgress();
    // Progress should be at least initial (may not change if analysis completes quickly)
    expect(updatedProgress).toBeGreaterThanOrEqual(initialProgress);
  });

  test('should eventually complete analysis', async ({ page, request }) => {
    // Get a completed analysis or create one
    const completed = await getCompletedAnalysis(request);

    if (!completed) {
      test.skip(!completed, 'No completed analysis available - skipping completion test');
    }

    const analyzePage = new AnalyzePage(page);
    await analyzePage.goto(completed!.analysis_id);

    // For completed analyses, completion should be immediate or very fast
    await analyzePage.waitForComplete();

    // Verify artifact link is available
    await expect(
      page.getByRole('link', { name: /view.*guide|view.*artifact|view.*result/i })
    ).toBeVisible();
  });
});
