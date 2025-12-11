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
   * Wait for the page to fully load (network idle).
   */
  async waitForPageLoad() {
    await this.page.waitForLoadState('networkidle');
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
