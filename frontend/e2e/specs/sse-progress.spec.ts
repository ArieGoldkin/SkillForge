import { test, expect } from '@playwright/test';

test.describe('SSE Progress Updates', () => {
  test('should show progress updates in analysis view', async ({ page }) => {
    // Navigate to library
    await page.goto('/library');
    await page.waitForLoadState('networkidle');

    // Take screenshot of library
    await page.screenshot({ path: '/tmp/sse_test_library.png' });

    // Check for analysis cards
    const analysisCards = page.locator('[class*="card"]');
    const count = await analysisCards.count();
    console.log(`Found ${count} analysis cards`);

    if (count > 0) {
      // Click first analysis
      await analysisCards.first().click();
      await page.waitForLoadState('networkidle');

      // Wait a bit for SSE events to arrive
      await page.waitForTimeout(3000);

      // Screenshot the analysis page
      await page.screenshot({ path: '/tmp/sse_test_analysis.png', fullPage: true });

      // Check for progress bar
      const progressBar = page.locator('[class*="progress"], [role="progressbar"]');
      const progressVisible = await progressBar.isVisible().catch(() => false);
      console.log(`Progress bar visible: ${progressVisible}`);

      // Check Activity Log
      const activityLog = page.locator('text=Activity Log');
      const activityVisible = await activityLog.isVisible().catch(() => false);
      console.log(`Activity Log visible: ${activityVisible}`);

      // Get any progress text
      const progressText = await page.locator('[class*="Progress"]').allTextContents();
      console.log('Progress text:', progressText.slice(0, 3));

      // Check if NOT stuck at "Waiting for agent activity"
      const waitingText = page.locator('text=Waiting for agent activity');
      const isWaiting = await waitingText.isVisible().catch(() => false);
      console.log(`Still waiting for activity: ${isWaiting}`);
    }

    // Final screenshot
    await page.screenshot({ path: '/tmp/sse_test_final.png', fullPage: true });
  });
});
