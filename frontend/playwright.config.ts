import { defineConfig, devices } from '@playwright/test';

/**
 * Playwright configuration for SkillForge E2E tests.
 * @see https://playwright.dev/docs/test-configuration
 */
export default defineConfig({
  testDir: './e2e/specs',
  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 2 : 0,
  // Increased workers for parallel execution (storageState enables safe parallelization)
  // 4 workers in CI allows 4 tests to run simultaneously, reducing execution time by ~4x
  workers: process.env.CI ? 4 : undefined,

  // Global setup creates storageState.json once, reused by all tests
  // This eliminates repeated navigation/auth steps, reducing test time by 50-70%
  globalSetup: './e2e/global-setup.ts',

  // Snapshot configuration for visual regression testing
  snapshotPathTemplate: '{testDir}/__screenshots__/{testFilePath}/{arg}{ext}',
  updateSnapshots: process.env.CI ? 'missing' : 'none',

  reporter: [
    ['html', { open: 'never' }],
    ['list'],
    ['json', { outputFile: 'test-results/results.json' }],
  ],

  expect: {
    toHaveScreenshot: {
      maxDiffPixelRatio: 0.01,
      threshold: 0.2,
      animations: 'disabled',
    },
  },

  use: {
    // Test environment ports (5174 for frontend, 8501 for backend)
    // Dev environment uses 5173/8500
    baseURL: process.env.PLAYWRIGHT_BASE_URL || 'http://localhost:5174',
    trace: 'on-first-retry',
    screenshot: 'only-on-failure',
    video: 'on-first-retry',
  },

  projects: [
    {
      name: 'chromium',
      use: {
        ...devices['Desktop Chrome'],
        // Reuse storageState to skip navigation/auth steps
        storageState: '.auth/storageState.json',
      },
    },
    {
      name: 'firefox',
      use: {
        ...devices['Desktop Firefox'],
        storageState: '.auth/storageState.json',
      },
    },
    {
      name: 'webkit',
      use: {
        ...devices['Desktop Safari'],
        storageState: '.auth/storageState.json',
      },
    },
    {
      name: 'mobile-chrome',
      use: {
        ...devices['Pixel 5'],
        storageState: '.auth/storageState.json',
      },
    },
    {
      name: 'mobile-safari',
      use: {
        ...devices['iPhone 13'],
        storageState: '.auth/storageState.json',
      },
    },
  ],

  // When PLAYWRIGHT_BASE_URL is provided (e.g., docker-compose test environment), we assume the
  // frontend is already running and skip starting a local dev server.
  webServer: process.env.PLAYWRIGHT_BASE_URL
    ? undefined
    : {
        command: 'npm run dev',
        url: 'http://localhost:5174',
        reuseExistingServer: !process.env.CI,
        timeout: 120000,
      },
});
