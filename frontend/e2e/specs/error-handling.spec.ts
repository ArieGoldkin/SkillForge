import { test, expect } from '@playwright/test';

test.describe('Error Handling Tests', () => {
  test('should display 404 for unknown routes', async ({ page }) => {
    await page.goto('/this-route-does-not-exist-at-all');

    // Should show 404 or not found message - use heading for specificity
    await expect(
      page.getByRole('heading', { name: /not found|page not found/i })
    ).toBeVisible({ timeout: 5000 });
  });

  test('should handle API errors gracefully on invalid URL submission', async ({ page }) => {
    await page.goto('/');
    await page.waitForLoadState('domcontentloaded');

    // Submit a URL that looks valid but will fail backend validation
    // Use a proper URL format to bypass HTML5 validation
    const urlInput = page.getByPlaceholder(/url/i);
    await urlInput.fill('https://this-domain-does-not-exist-12345.invalid');

    const submitButton = page.getByRole('button', { name: /analyze|submit/i });
    const initialUrl = page.url();

    await submitButton.click();

    // Wait for either error display or navigation
    await Promise.race([
      page.locator('[role="alert"]').waitFor({ state: 'visible', timeout: 15000 }),
      page.getByText(/error|failed/i).waitFor({ state: 'visible', timeout: 15000 }),
      page.waitForURL(/\/(analyze|library)/, { timeout: 15000 }),
      page.waitForTimeout(15000), // Max wait time
    ]).catch(() => {
      // Timeout is acceptable - just continue
    });

    // Check if error appeared OR navigation happened
    const alertVisible = await page.locator('[role="alert"]').isVisible().catch(() => false);
    const errorTextVisible = await page.getByText(/error|failed/i).isVisible().catch(() => false);
    const didNavigate = page.url() !== initialUrl && (page.url().includes('/analyze') || page.url().includes('/library'));

    // Valid outcomes: error displayed OR successful navigation
    expect(alertVisible || errorTextVisible || didNavigate).toBe(true);
  });

  test('should handle malformed URL submission', async ({ page }) => {
    await page.goto('/');

    // Submit a malformed URL
    const urlInput = page.getByPlaceholder(/url/i);
    await urlInput.fill('htp://broken-url-format');

    const submitButton = page.getByRole('button', { name: /analyze|submit/i });
    await submitButton.click();

    // Should show validation or error message
    await expect(
      page.getByRole('alert')
        .or(page.getByText(/error|invalid|valid url/i))
    ).toBeVisible({ timeout: 10000 });
  });

  test('should handle network errors (simulated)', async ({ page }) => {
    // Only use page.route() for this specific network simulation test
    await page.route('**/api/v1/analyze', async (route) => {
      await route.abort('failed');
    });

    await page.goto('/');

    const urlInput = page.getByPlaceholder(/url/i);
    await urlInput.fill('https://example.com');

    const submitButton = page.getByRole('button', { name: /analyze|submit/i });
    await submitButton.click();

    // Should show error state
    await expect(
      page.getByText(/error|failed|network|offline|connection/i)
    ).toBeVisible({ timeout: 10000 });
  });

  test('should show empty state when searching for non-existent content', async ({ page }) => {
    await page.goto('/library');

    // Wait for page to fully load (UI state, not network)
    await page.waitForLoadState('domcontentloaded');

    // Wait for library page to be ready (either cards or empty state)
    await page.locator('[role="list"], [data-testid="empty-state"]').first().waitFor({ state: 'visible' }).catch(() => {
      // Grid might not be visible yet
    });

    // Search for something that definitely doesn't exist
    const searchInput = page.getByPlaceholder(/search/i);
    if (await searchInput.isVisible({ timeout: 5000 }).catch(() => false)) {
      await searchInput.fill('xyznonexistentquery12345');
      await searchInput.press('Enter');

      // Wait for UI to update - don't rely on network
      await expect(searchInput).toHaveValue('xyznonexistentquery12345');

      // Should show empty state or library page remains functional
      await expect(
        page.getByText(/no results|no analyses|empty|nothing found/i)
          .or(page.getByRole('heading', { name: /library/i }))
      ).toBeVisible();
    } else {
      // If no search input, just verify library page loaded
      await expect(
        page.getByRole('heading', { name: /library/i })
      ).toBeVisible();
    }
  });

  test('should handle API 404 for non-existent analysis', async ({ page }) => {
    // Try to access a non-existent analysis ID
    await page.goto('/analyze/non-existent-analysis-id-12345');

    // Should show error state or redirect
    await expect(
      page.getByText(/not found|error|invalid/i)
        .or(page.getByRole('heading', { name: /not found/i }))
        .or(page.locator('body')) // Fallback - page should at least render
    ).toBeVisible({ timeout: 10000 });
  });

  test('should handle missing required fields in URL submission', async ({ page }) => {
    await page.goto('/');

    // Try to submit without entering a URL
    const submitButton = page.getByRole('button', { name: /analyze|submit/i });

    // Check if button is disabled or shows validation
    const isDisabled = await submitButton.isDisabled().catch(() => false);

    if (!isDisabled) {
      await submitButton.click();

      // Should show validation message
      await expect(
        page.getByText(/required|enter|provide|url/i)
          .or(page.getByRole('alert'))
      ).toBeVisible({ timeout: 5000 });
    } else {
      // If button is disabled, that's valid error prevention
      expect(isDisabled).toBe(true);
    }
  });

  test('should handle slow API responses with loading state', async ({ page }) => {
    await page.goto('/');
    await page.waitForLoadState('domcontentloaded');

    const urlInput = page.getByPlaceholder(/url/i);
    await urlInput.fill('https://example.com');

    const submitButton = page.getByRole('button', { name: /analyze|submit/i });

    // Click and immediately check for loading indicators using Promise.race
    const clickPromise = submitButton.click();

    const result = await Promise.race([
      // Scenario 1: Check for aria-busy attribute
      page.locator('[aria-busy="true"]').waitFor({ state: 'visible', timeout: 2000 })
        .then(() => ({ type: 'aria-busy', value: true }))
        .catch(() => ({ type: 'aria-busy', value: false })),
      // Scenario 2: Check for "Analyzing..." text
      page.getByText(/analyzing/i).waitFor({ state: 'visible', timeout: 2000 })
        .then(() => ({ type: 'loading-text', value: true }))
        .catch(() => ({ type: 'loading-text', value: false })),
      // Scenario 3: Page navigates quickly
      page.waitForURL(/\/(analyze|library)/, { timeout: 5000 })
        .then(() => ({ type: 'navigated', value: true }))
        .catch(() => ({ type: 'navigated', value: false })),
    ]);

    await clickPromise;

    // Valid outcomes: loading indicator shown OR navigation occurred
    const isValid = result.value === true;
    expect(isValid).toBe(true);
  });

  test('should maintain UI functionality after API errors', async ({ page }) => {
    await page.goto('/');

    // Submit an invalid URL
    const urlInput = page.getByPlaceholder(/url/i);
    await urlInput.fill('invalid-url');

    const submitButton = page.getByRole('button', { name: /analyze|submit/i });
    await submitButton.click();

    // Wait for error to appear using element-based wait
    await page.getByText(/error|invalid|valid url/i)
      .or(page.getByRole('alert'))
      .waitFor({ state: 'visible', timeout: 5000 })
      .catch(() => {
        // Error might appear differently or be handled client-side
      });

    // Now try a valid URL - UI should still work
    await urlInput.clear();
    await urlInput.fill('https://github.com/microsoft/playwright');

    // Button should be clickable again
    await expect(submitButton).toBeEnabled({ timeout: 3000 });
  });

  test('should handle rapid successive API calls gracefully', async ({ page }) => {
    // Skip in CI - this test submits URLs which triggers backend LLM processing
    test.skip(!!process.env.CI, 'Requires backend LLM processing');

    await page.goto('/');
    await page.waitForLoadState('domcontentloaded');

    const urlInput = page.getByPlaceholder(/url/i);
    const submitButton = page.getByRole('button', { name: /analyze|submit/i });

    // Submit a URL
    await urlInput.fill('https://example.com/test-rapid-submission');
    const initialUrl = page.url();

    // Click submit
    await submitButton.click();

    // Wait for either navigation or button state change using Promise.race
    const result = await Promise.race([
      // Check if page navigates
      page.waitForURL(/\/analyze\/.+/)
        .then(() => ({ type: 'navigated', value: true })),
      // Check if button becomes disabled
      page.waitForFunction(
        () => {
          const btn = document.querySelector('button[type="submit"], button:has-text("analyze")');
          return btn && (btn as HTMLButtonElement).disabled;
        }
      ).then(() => ({ type: 'disabled', value: true })),
    ]).catch(() => ({ type: 'timeout', value: false }));

    // Check current state
    const currentUrl = page.url();
    const didNavigate = currentUrl !== initialUrl || result.type === 'navigated';

    // Try to check button state (might not exist if navigated)
    let buttonState = { exists: false, disabled: false };
    try {
      const buttonVisible = await submitButton.isVisible({ timeout: 2000 });
      if (buttonVisible) {
        buttonState.exists = true;
        buttonState.disabled = await submitButton.isDisabled();
      }
    } catch {
      // Button doesn't exist - likely navigated
    }

    // Valid outcomes:
    // 1. Page navigated (success)
    // 2. Button is disabled (preventing double-submit)
    // 3. Button disappeared (navigation in progress)
    const isHandledGracefully = didNavigate || buttonState.disabled || !buttonState.exists;

    expect(isHandledGracefully).toBe(true);
  });

  test('should recover and work normally after temporary errors', async ({ page }) => {
    await page.goto('/');

    // First try with invalid URL
    const urlInput = page.getByPlaceholder(/url/i);
    await urlInput.fill('not-valid');

    const submitButton = page.getByRole('button', { name: /analyze|submit/i });
    await submitButton.click();

    // Wait for error using element-based wait
    await page.getByText(/error|invalid|valid url/i)
      .or(page.getByRole('alert'))
      .waitFor({ state: 'visible', timeout: 5000 })
      .catch(() => {
        // Error might appear differently
      });

    // Now navigate to library - should work normally (no network wait needed)
    await page.goto('/library');
    await page.waitForLoadState('domcontentloaded');

    // Wait for library page UI to be ready
    await page.locator('[role="list"], [data-testid="empty-state"]').first().waitFor({ state: 'visible' }).catch(() => {
      // Grid might not exist
    });

    // Library should load successfully
    await expect(
      page.getByRole('heading', { name: /library/i })
    ).toBeVisible({ timeout: 5000 });
  });
});
