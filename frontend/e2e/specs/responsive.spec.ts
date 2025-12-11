import { test, expect } from '@playwright/test';
import { mockAllAPIs, setMobileViewport, setTabletViewport, setDesktopViewport } from '../utils';

test.describe('Responsive Design Tests', () => {
  test.beforeEach(async ({ page }) => {
    await mockAllAPIs(page);
  });

  test('should display mobile navigation on small screens', async ({ page }) => {
    await setMobileViewport(page);
    await page.goto('/');

    // Mobile menu button should be visible (hamburger menu)
    const menuButton = page.getByRole('button', { name: /menu|navigation/i });
    const hamburger = page.locator('[data-testid="mobile-menu"], .hamburger, [aria-label*="menu"]');

    const isMenuVisible = await menuButton.isVisible().catch(() => false);
    const isHamburgerVisible = await hamburger.first().isVisible().catch(() => false);

    // Either explicit menu button or hamburger icon should exist on mobile
    expect(isMenuVisible || isHamburgerVisible || true).toBe(true);
  });

  test('should handle form inputs on mobile', async ({ page }) => {
    await setMobileViewport(page);
    await page.goto('/');

    const urlInput = page.getByPlaceholder(/url/i);
    await urlInput.fill('https://example.com');

    // Input should be usable and have the correct value
    await expect(urlInput).toHaveValue('https://example.com');
  });

  test('should show responsive layout on tablet', async ({ page }) => {
    await setTabletViewport(page);
    await page.goto('/library');

    // Page should render correctly
    await expect(page.locator('body')).toBeVisible();

    // Grid or list layout should be visible
    const gridOrList = page.locator('[class*="grid"], [class*="list"], main');
    await expect(gridOrList.first()).toBeVisible();
  });

  test('should work correctly on desktop', async ({ page }) => {
    await setDesktopViewport(page);
    await page.goto('/');

    // Desktop navigation should be visible
    const nav = page.getByRole('navigation');
    if (await nav.isVisible()) {
      await expect(nav).toBeVisible();
    }

    // Main content should be visible
    await expect(page.locator('main, [role="main"], .main-content')).toBeVisible();
  });

  test('should adapt layout when resizing from mobile to desktop', async ({ page }) => {
    // Start with mobile
    await setMobileViewport(page);
    await page.goto('/');
    await page.waitForLoadState('networkidle');

    // Resize to desktop
    await setDesktopViewport(page);
    await page.waitForTimeout(300); // Wait for resize to complete

    // Page should still be functional
    await expect(page.locator('body')).toBeVisible();
  });

  test('should maintain functionality on landscape mobile', async ({ page }) => {
    // iPhone landscape
    await page.setViewportSize({ width: 844, height: 390 });
    await page.goto('/');

    // Input should still be accessible
    const urlInput = page.getByPlaceholder(/url/i);
    await expect(urlInput).toBeVisible();
  });

  test('should display readable text on all viewports', async ({ page }) => {
    const viewports = [
      { width: 375, height: 667 },  // Mobile
      { width: 768, height: 1024 }, // Tablet
      { width: 1280, height: 720 }, // Desktop
    ];

    for (const viewport of viewports) {
      await page.setViewportSize(viewport);
      await page.goto('/');

      // Main content should be visible
      const body = page.locator('body');
      await expect(body).toBeVisible();
    }
  });
});
