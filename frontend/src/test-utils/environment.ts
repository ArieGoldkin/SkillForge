/**
 * Environment Detection Utilities for Test Infrastructure (2025 Best Practices)
 *
 * Provides centralized environment capability detection for conditional test execution.
 * Enables environment-aware test skipping and tagging based on runtime capabilities.
 */

/**
 * Environment capability detection for conditional test execution.
 * Centralizes environment checks to enable smart test skipping.
 */
export const environmentCapabilities = {
  /** E2E tests require full application environment (backend, database, etc.) */
  get e2eReady(): boolean {
    return Boolean(
      process.env.E2E_READY === 'true' ||
        process.env.CI === 'true' ||
        process.env.NODE_ENV === 'test-e2e'
    )
  },

  /** CI environment has full infrastructure available */
  get isCI(): boolean {
    return Boolean(
      process.env.CI === 'true' ||
        process.env.GITHUB_ACTIONS === 'true' ||
        process.env.CIRCLECI === 'true' ||
        process.env.JENKINS_HOME
    )
  },

  /** Development environment with local services */
  get isDev(): boolean {
    return process.env.NODE_ENV === 'development'
  },

  /** Production environment (limited test execution) */
  get isProd(): boolean {
    return process.env.NODE_ENV === 'production'
  },

  /** Browser environment for Playwright tests */
  get isBrowser(): boolean {
    return typeof window !== 'undefined'
  },

  /** Node.js environment for unit tests */
  get isNode(): boolean {
    return typeof window === 'undefined'
  },

  /** Performance testing enabled */
  get performanceEnabled(): boolean {
    return Boolean(process.env.PERFORMANCE_TESTING === 'true' || process.env.CI === 'true')
  },

  /** Slow tests allowed (CI environments typically) */
  get slowTestsAllowed(): boolean {
    return Boolean(process.env.RUN_SLOW_TESTS === 'true' || this.isCI)
  },

  /** Manual tests (require human interaction) */
  get manualTestsAllowed(): boolean {
    return Boolean(
      process.env.RUN_MANUAL_TESTS === 'true' && !this.isCI // Never run manual tests in CI
    )
  },
} as const

/**
 * Test execution profiles for different environments.
 * Provides predefined configurations for common testing scenarios.
 */
export const testProfiles = {
  /** Unit tests only (fast, isolated) */
  unit: {
    e2e: false,
    integration: false,
    slow: false,
    manual: false,
  },

  /** Integration tests (requires services) */
  integration: {
    e2e: false,
    integration: true,
    slow: true,
    manual: false,
  },

  /** End-to-end tests (full application) */
  e2e: {
    e2e: true,
    integration: true,
    slow: true,
    manual: false,
  },

  /** CI environment (comprehensive but automated) */
  ci: {
    e2e: true,
    integration: true,
    slow: true,
    manual: false,
  },

  /** Development environment (flexible) */
  dev: {
    e2e: environmentCapabilities.e2eReady,
    integration: true,
    slow: true,
    manual: true,
  },
} as const

/**
 * Get the current test execution profile based on environment.
 */
export function getCurrentTestProfile(): keyof typeof testProfiles {
  if (environmentCapabilities.isCI) return 'ci'
  if (environmentCapabilities.isDev) return 'dev'

  // Default to unit tests in unknown environments
  return 'unit'
}

/**
 * Check if a specific test type should run in the current environment.
 */
export function shouldRunTestType(testType: keyof typeof testProfiles.unit): boolean {
  const profile = getCurrentTestProfile()
  return testProfiles[profile][testType]
}

/**
 * Environment-aware test skipping utilities.
 * Provides semantic functions for common test skipping scenarios.
 */
export const testSkipConditions = {
  /** Skip E2E tests when environment is not ready */
  skipE2E: () => !environmentCapabilities.e2eReady,

  /** Skip slow tests in fast environments */
  skipSlow: () => !environmentCapabilities.slowTestsAllowed,

  /** Skip manual tests in automated environments */
  skipManual: () => !environmentCapabilities.manualTestsAllowed,

  /** Skip performance tests when not enabled */
  skipPerformance: () => !environmentCapabilities.performanceEnabled,

  /** Skip browser-only tests in Node environment */
  skipBrowserOnly: () => !environmentCapabilities.isBrowser,

  /** Skip Node-only tests in browser environment */
  skipNodeOnly: () => !environmentCapabilities.isNode,
} as const
