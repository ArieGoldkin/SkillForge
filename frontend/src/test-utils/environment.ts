/**
 * Test Environment Detection & Configuration
 *
 * Centralizes environment detection for intelligent test execution.
 * Follows 2025 testing best practices for environment-aware testing.
 */

export interface TestEnvironmentConfig {
  // Execution Modes
  isCI: boolean
  isE2EReady: boolean
  isDevelopment: boolean
  isProduction: boolean

  // Infrastructure Availability
  hasDatabase: boolean
  hasRedis: boolean
  hasExternalAPIs: boolean
  hasBrowser: boolean

  // Performance Settings
  slowTestThreshold: number
  testTimeout: number

  // Feature Flags
  enablePerformanceMonitoring: boolean
  enableVisualRegression: boolean
  enableA11yTesting: boolean
}

/**
 * Centralized test environment detection
 * Automatically detects available infrastructure and execution context
 */
export const TestEnvironment: TestEnvironmentConfig = {
  // Execution context detection
  isCI: process.env.CI === 'true',
  isE2EReady: process.env.E2E_READY === 'true',
  isDevelopment: process.env.NODE_ENV !== 'production',
  isProduction: process.env.NODE_ENV === 'production',

  // Infrastructure detection
  hasDatabase: Boolean(process.env.DATABASE_URL),
  hasRedis: Boolean(process.env.REDIS_URL),
  hasExternalAPIs: Boolean(process.env.API_BASE_URL),
  hasBrowser: typeof window !== 'undefined' || process.env.VITEST_BROWSER === 'true',

  // Performance thresholds (CI vs local)
  slowTestThreshold: process.env.CI ? 5000 : 2000,
  testTimeout: process.env.CI ? 10000 : 5000,

  // Feature flags
  enablePerformanceMonitoring: process.env.PERFORMANCE_MONITORING !== 'false',
  enableVisualRegression: process.env.VISUAL_REGRESSION === 'true',
  enableA11yTesting: process.env.A11Y_TESTING === 'true',
}

/**
 * Environment-aware test utilities
 * Provides conditional test execution based on environment capabilities
 */
export const conditionalTest = {
  /**
   * Only run test in E2E environment
   * @param name Test name
   * @param fn Test function
   * @returns Conditional test runner
   */
  e2e: (name: string, fn: () => void | Promise<void>) => {
    return TestEnvironment.isE2EReady ? it(name, fn) : (it.skip(name, fn) as void)
  },

  /**
   * Only run test with database available
   */
  withDatabase: (name: string, fn: () => void | Promise<void>) => {
    return TestEnvironment.hasDatabase ? it(name, fn) : it.skip(name, fn)
  },

  /**
   * Only run test with external APIs available
   */
  withExternalAPIs: (name: string, fn: () => void | Promise<void>) => {
    return TestEnvironment.hasExternalAPIs ? it(name, fn) : it.skip(name, fn)
  },

  /**
   * Performance tests (skip in CI unless explicitly enabled)
   */
  performance: (name: string, fn: () => void | Promise<void>) => {
    const shouldRun = !TestEnvironment.isCI || process.env.RUN_PERFORMANCE_TESTS === 'true'
    return shouldRun ? it(name, fn) : it.skip(name, fn)
  },

  /**
   * Browser-dependent tests
   */
  browser: (name: string, fn: () => void | Promise<void>) => {
    return TestEnvironment.hasBrowser ? it(name, fn) : it.skip(name, fn)
  },

  /**
   * Development-only tests (skip in CI)
   */
  devOnly: (name: string, fn: () => void | Promise<void>) => {
    return TestEnvironment.isDevelopment ? it(name, fn) : it.skip(name, fn)
  },

  /**
   * CI-only tests (skip in development)
   */
  ciOnly: (name: string, fn: () => void | Promise<void>) => {
    return TestEnvironment.isCI ? it(name, fn) : it.skip(name, fn)
  },
}

/**
 * Test metadata for advanced reporting
 */
export interface TestMetadata {
  category: 'unit' | 'integration' | 'e2e' | 'performance'
  estimatedDuration: number // milliseconds
  requires: string[] // Required services/environments
  flaky: boolean // Known to be unreliable
  priority: 'low' | 'medium' | 'high' | 'critical'
  tags: string[] // Additional tags
}

/**
 * Performance monitoring utilities
 */
export const PerformanceMonitor = {
  /**
   * Check for performance regressions
   */
  checkRegression: (testName: string, duration: number, baseline?: number) => {
    if (!baseline) return

    const regressionThreshold = 1.2 // 20% regression
    if (duration > baseline * regressionThreshold) {
      console.warn(
        `🐌 Performance regression in ${testName}: ${duration}ms vs ${baseline}ms baseline`
      )
      if (TestEnvironment.isCI) {
        throw new Error(`Performance regression detected in ${testName}`)
      }
    }
  },

  /**
   * Mark slow tests
   */
  markSlowTest: (testName: string, duration: number) => {
    if (duration > TestEnvironment.slowTestThreshold) {
      console.warn(`🐌 Slow test detected: ${testName} (${duration}ms)`)
    }
  },
}

/**
 * Test data factories with environment awareness
 */
export const createTestData = {
  /**
   * Create user data based on environment
   */
  user: () => ({
    id: TestEnvironment.isE2EReady ? 'real-user-123' : 'mock-user-123',
    email: TestEnvironment.isE2EReady ? process.env.TEST_USER_EMAIL : 'test@example.com',
    name: 'Test User',
    token: TestEnvironment.isE2EReady ? process.env.TEST_API_TOKEN : 'mock-token',
  }),

  /**
   * Create analysis data
   */
  analysis: () => ({
    id: 'test-analysis-id',
    url: 'https://example.com',
    title: 'Test Analysis',
    status: 'completed',
    wordCount: 1200,
  }),

  /**
   * Create API response mocks
   */
  apiResponse: (overrides: Record<string, unknown> = {}) => ({
    success: true,
    data: {},
    timestamp: new Date().toISOString(),
    ...overrides,
  }),
}

// Environment validation for CI
if (TestEnvironment.isCI) {
  console.log('🧪 CI Test Environment Detected')
  console.log(`  E2E Ready: ${TestEnvironment.isE2EReady}`)
  console.log(`  Database: ${TestEnvironment.hasDatabase}`)
  console.log(`  External APIs: ${TestEnvironment.hasExternalAPIs}`)
  console.log(`  Timeout: ${TestEnvironment.testTimeout}ms`)
}
