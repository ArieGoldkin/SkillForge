import type { Page } from '@playwright/test';

/**
 * Wait for a specific network request to complete.
 */
export async function waitForRequest(page: Page, urlPattern: string | RegExp) {
  return page.waitForRequest((request) => {
    const url = request.url();
    return typeof urlPattern === 'string' ? url.includes(urlPattern) : urlPattern.test(url);
  });
}

/**
 * Wait for a specific network response.
 */
export async function waitForResponse(page: Page, urlPattern: string | RegExp) {
  return page.waitForResponse((response) => {
    const url = response.url();
    return typeof urlPattern === 'string' ? url.includes(urlPattern) : urlPattern.test(url);
  });
}

/**
 * Wait for all network activity to settle.
 */
export async function waitForNetworkIdle(page: Page, timeout = 5000) {
  await page.waitForLoadState('networkidle', { timeout });
}

/**
 * Get the clipboard contents (requires page context).
 */
export async function getClipboardContent(page: Page): Promise<string> {
  return page.evaluate(() => navigator.clipboard.readText());
}

/**
 * Set viewport for responsive testing.
 */
export async function setMobileViewport(page: Page) {
  await page.setViewportSize({ width: 375, height: 667 });
}

export async function setTabletViewport(page: Page) {
  await page.setViewportSize({ width: 768, height: 1024 });
}

export async function setDesktopViewport(page: Page) {
  await page.setViewportSize({ width: 1280, height: 720 });
}

/**
 * Generate a unique test ID.
 */
export function generateTestId(): string {
  return `test-${Date.now()}-${Math.random().toString(36).substring(2, 9)}`;
}

/**
 * Wait with a timeout and custom message.
 */
export async function waitWithTimeout<T>(
  promise: Promise<T>,
  timeoutMs: number,
  message: string
): Promise<T> {
  const timeoutPromise = new Promise<never>((_, reject) => {
    setTimeout(() => reject(new Error(`Timeout: ${message}`)), timeoutMs);
  });

  return Promise.race([promise, timeoutPromise]);
}

/**
 * Retry a function with exponential backoff.
 */
export async function retryWithBackoff<T>(
  fn: () => Promise<T>,
  maxRetries = 3,
  baseDelay = 1000
): Promise<T> {
  let lastError: Error | undefined;

  for (let i = 0; i < maxRetries; i++) {
    try {
      return await fn();
    } catch (error) {
      lastError = error as Error;
      if (i < maxRetries - 1) {
        const delay = baseDelay * Math.pow(2, i);
        await new Promise((resolve) => setTimeout(resolve, delay));
      }
    }
  }

  throw lastError;
}
