/**
 * Test Configuration & Environment Patterns
 *
 * Central configuration for test execution patterns, environment detection,
 * and testing best practices. Follows 2025 industry standards.
 */

import { TestEnvironment } from './environment'

/**
 * Test execution patterns based on environment and test type
 */
export const TestPatterns = {
  /**
   * Fast feedback patterns (development, pre-commit)
   */
  fastFeedback: {
    include: ['@unit', '@component'],
    exclude: ['@slow', '@e2e', '@integration'],
    timeout: 5000,
    retries: 0,
  },

  /**
   * CI validation patterns (comprehensive but fast)
   */
  ci: {
    include: ['@unit', '@component', '@integration', '@ci'],
    exclude: ['@e2e', '@slow', '@manual'],
    timeout: 10000,
    retries: 2,
    coverage: true,
  },

  /**
   * Full test suite (nightly, release)
   */
  full: {
    include: ['@unit', '@component', '@integration', '@e2e'],
    exclude: ['@manual'],
    timeout: 30000,
    retries: 3,
    coverage: true,
  },

  /**
   * Performance testing (dedicated runs)
   */
  performance: {
    include: ['@slow', '@performance'],
    exclude: [],
    timeout: 60000,
    retries: 1,
  },

  /**
   * E2E only (when infrastructure is available)
   */
  e2e: {
    include: ['@e2e'],
    exclude: [],
    timeout: 30000,
    retries: 1,
    requires: ['E2E_READY=true'],
  },
}

/**
 * Environment-specific test configurations
 */
export const EnvironmentConfigs = {
  development: {
    ...TestPatterns.fastFeedback,
    watch: true,
    ui: true,
  },

  ci: {
    ...TestPatterns.ci,
    bail: 5, // Stop after 5 failures
    shard: process.env.SHARD,
    reporter: 'json',
  },

  staging: {
    ...TestPatterns.full,
    bail: 10,
    reporter: 'verbose',
  },

  production: {
    ...TestPatterns.ci,
    bail: 1, // Strict - fail fast
  },
}

/**
 * Test metadata and categorization helpers
 */
export const TestCategories = {
  /**
   * Component tests - React component behavior
   */
  component: {
    tags: ['@unit', '@component'],
    description: 'React component rendering and interaction tests',
    priority: 'high',
  },

  /**
   * Hook tests - Custom React hooks
   */
  hook: {
    tags: ['@unit', '@hook'],
    description: 'Custom React hook logic and state management',
    priority: 'high',
  },

  /**
   * Store tests - State management
   */
  store: {
    tags: ['@unit', '@store'],
    description: 'Zustand store actions and selectors',
    priority: 'high',
  },

  /**
   * Utility tests - Pure functions
   */
  util: {
    tags: ['@unit', '@util'],
    description: 'Pure utility functions and helpers',
    priority: 'medium',
  },

  /**
   * Integration tests - API/database
   */
  integration: {
    tags: ['@integration'],
    description: 'API calls, database operations, external services',
    priority: 'medium',
    requires: ['database', 'externalAPIs'],
  },

  /**
   * E2E tests - Full user workflows
   */
  e2e: {
    tags: ['@e2e'],
    description: 'Complete user journey from UI to backend',
    priority: 'high',
    requires: ['E2E_READY=true', 'full infrastructure'],
  },

  /**
   * Performance tests - Load and speed
   */
  performance: {
    tags: ['@slow', '@performance'],
    description: 'Performance benchmarks and load testing',
    priority: 'low',
    requires: ['performance environment'],
  },

  /**
   * Critical path tests - Mission critical
   */
  critical: {
    tags: ['@critical', '@ci'],
    description: 'Tests for critical business functionality',
    priority: 'critical',
  },
}

/**
 * Test execution helpers
 */
export const TestExecution = {
  /**
   * Determine if test should run based on environment
   */
  shouldRun: (tags: string[]): boolean => {
    // E2E tests only run when E2E_READY=true
    if (tags.includes('@e2e') && !TestEnvironment.isE2EReady) {
      return false
    }

    // Performance tests only run when explicitly enabled
    if (tags.includes('@slow') && !process.env.RUN_PERFORMANCE_TESTS) {
      return false
    }

    // Development-only tests don't run in CI
    if (tags.includes('@dev') && TestEnvironment.isCI) {
      return false
    }

    return true
  },

  /**
   * Get appropriate timeout for test type
   */
  getTimeout: (tags: string[]): number => {
    if (tags.includes('@slow')) return 30000
    if (tags.includes('@e2e')) return 20000
    if (tags.includes('@integration')) return 10000
    return TestEnvironment.testTimeout
  },

  /**
   * Get retry count for test type
   */
  getRetries: (tags: string[]): number => {
    if (tags.includes('@flaky')) return 3
    if (tags.includes('@e2e')) return 1
    if (TestEnvironment.isCI) return 2
    return 0
  },
}

/**
 * Coverage configuration by test type
 */
export const CoverageConfig = {
  unit: {
    thresholds: {
      branches: 85,
      functions: 90,
      lines: 90,
      statements: 90,
    },
  },

  integration: {
    thresholds: {
      branches: 75,
      functions: 80,
      lines: 80,
      statements: 80,
    },
  },

  e2e: {
    // E2E tests don't typically have code coverage
    thresholds: {},
  },
}

/**
 * Test data patterns for consistent fixtures
 */
export const TestDataPatterns = {
  /**
   * Standard user patterns
   */
  users: {
    admin: { role: 'admin', permissions: ['*'] },
    moderator: { role: 'moderator', permissions: ['read', 'write', 'moderate'] },
    user: { role: 'user', permissions: ['read', 'write'] },
    guest: { role: 'guest', permissions: ['read'] },
  },

  /**
   * Content patterns
   */
  content: {
    article: { type: 'article', wordCount: 1200 },
    video: { type: 'video', duration: 600 },
    repo: { type: 'repo', files: 150 },
  },

  /**
   * API response patterns
   */
  api: {
    success: { status: 200, success: true },
    error: { status: 500, success: false, error: 'Internal server error' },
    unauthorized: { status: 401, success: false, error: 'Unauthorized' },
    notFound: { status: 404, success: false, error: 'Not found' },
  },
}

// Export current environment config
export const currentEnvironment =
  EnvironmentConfigs[
    TestEnvironment.isCI ? 'ci' : TestEnvironment.isE2EReady ? 'staging' : 'development'
  ]
