import type { Page, Locator } from '@playwright/test';

/**
 * Base page object class providing common functionality for all page objects.
 * Uses the Page Object Model pattern for maintainable E2E tests.
 */
export abstract class BasePage {
  constructor(public readonly page: Page) {}

  /**
   * Navigate to a path relative to baseURL.
   */
  async navigate(path: string = '/') {
    await this.page.goto(path);
    await this.waitForPageLoad();
  }

  /**
   * Wait for the page to be ready for interaction.
   * Uses 'domcontentloaded' instead of 'networkidle' because:
   * - SSE streams keep connections open indefinitely, blocking networkidle
   * - domcontentloaded is sufficient for React hydration
   * - Specific UI states should use element-based waits instead
   */
  async waitForPageLoad() {
    await this.page.waitForLoadState('domcontentloaded');
  }

  /**
   * Wait for the page to be fully loaded including all resources.
   * Use this only when you specifically need all resources loaded
   * and no SSE/streaming connections are expected.
   */
  async waitForFullLoad() {
    await this.page.waitForLoadState('load');
  }

  /**
   * Wait for an element to become visible.
   */
  async waitForElement(locator: Locator, timeout = 10000) {
    await locator.waitFor({ state: 'visible', timeout });
  }

  /**
   * Get element by data-testid attribute.
   */
  protected getByTestId(testId: string): Locator {
    return this.page.getByTestId(testId);
  }

  /**
   * Get element by ARIA role.
   */
  protected getByRole(
    role: Parameters<Page['getByRole']>[0],
    options?: Parameters<Page['getByRole']>[1]
  ): Locator {
    return this.page.getByRole(role, options);
  }

  /**
   * Get element by placeholder text.
   */
  protected getByPlaceholder(text: string | RegExp): Locator {
    return this.page.getByPlaceholder(text);
  }

  /**
   * Get element by visible text.
   */
  protected getByText(text: string | RegExp): Locator {
    return this.page.getByText(text);
  }

  /**
   * Take a screenshot for debugging.
   */
  async takeScreenshot(name: string) {
    await this.page.screenshot({ path: `test-results/screenshots/${name}.png` });
  }
}
