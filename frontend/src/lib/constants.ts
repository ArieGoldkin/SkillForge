/**
 * Shared constants for the SkillForge frontend application.
 *
 * Centralizes magic numbers, timeouts, limits, and other hardcoded values
 * to improve maintainability and reduce duplication.
 */

// ============================================================================
// TIME CONSTANTS (milliseconds)
// ============================================================================

export const TIME_CONSTANTS = {
  // Standard time units
  SECOND: 1000,
  MINUTE: 60 * 1000,
  HOUR: 60 * 60 * 1000,

  // Query stale times
  QUERY_STALE_TIME: 60 * 1000, // 1 minute

  // Test timeouts
  TEST_TIMEOUT_CI: 10000, // 10 seconds in CI
  TEST_TIMEOUT_LOCAL: 5000, // 5 seconds locally
  SLOW_TEST_THRESHOLD_CI: 5000, // 5 seconds
  SLOW_TEST_THRESHOLD_LOCAL: 2000, // 2 seconds

  // Performance thresholds
  PERFORMANCE_REGRESSION_THRESHOLD: 1.2, // 20% regression allowed
} as const

// ============================================================================
// COUNT/LIMIT CONSTANTS
// ============================================================================

export const LIMIT_CONSTANTS = {
  // Test configuration
  MAX_TEST_FAILURES: 10,
  PERFORMANCE_TEST_ITERATIONS_CI: 50,
  PERFORMANCE_TEST_ITERATIONS_LOCAL: 10,

  // SSE event limits
  MAX_EVENTS: 500,
  SSE_RECONNECT_ATTEMPTS: 3,
  SSE_RECONNECT_DELAY_INITIAL: 1000, // 1 second
  SSE_RECONNECT_DELAY_MAX: 4000, // 4 seconds

  // Performance monitoring
  PERFORMANCE_FAILURE_RATE_THRESHOLD: 0.1, // 10%
  RERENDER_HOTSPOT_THRESHOLD: 20,
  PERFORMANCE_REGRESSION_PERCENTAGE: 50,

  // Component rendering limits
  EXPECTED_MAX_COMPONENT_RENDERS: 100,
  EXPECTED_MAX_EXECUTION_TIME: 500, // milliseconds
} as const

// ============================================================================
// MEMORY CONSTANTS
// ============================================================================

export const MEMORY_CONSTANTS = {
  // Memory usage thresholds (as percentage of MAX_EVENTS)
  WARNING_THRESHOLD: 0.7, // 70%
  CRITICAL_THRESHOLD: 0.9, // 90%
  EMERGENCY_THRESHOLD: 0.95, // 95% - force cleanup

  // Memory conversion
  BYTES_PER_MB: 1024 * 1024,
} as const

// ============================================================================
// CONTENT CONSTANTS
// ============================================================================

export const CONTENT_CONSTANTS = {
  // Sample content for testing
  SAMPLE_WORD_COUNT: 1200,
  SAMPLE_USER_ID_REAL: 'real-user-123',
  SAMPLE_USER_ID_MOCK: 'mock-user-123',
  SAMPLE_ANALYSIS_ID: 'test-analysis-id',
} as const

// ============================================================================
// RETRY CONSTANTS
// ============================================================================

export const RETRY_CONSTANTS = {
  // Query retries
  QUERY_RETRY_COUNT: 1,

  // Test retries
  TEST_RETRY_CI: 2,
  TEST_RETRY_LOCAL: 0,
} as const

// ============================================================================
// EVENT RETENTION POLICIES (Issue #404)
// ============================================================================

export const EVENT_RETENTION_POLICIES = {
  // Keep all critical events (errors, completion)
  critical: -1, // Never expire (milliseconds)
  // Keep progress events for 10 minutes during active analysis
  progress: 10 * 60 * 1000, // 10 minutes
  // Keep activity events for 5 minutes
  activity: 5 * 60 * 1000, // 5 minutes
} as const

// ============================================================================
// LEGACY CONSTANTS (to be migrated)
// ============================================================================

/**
 * These constants are kept for backward compatibility during migration.
 * They should be replaced with the new structured constants above.
 *
 * @deprecated Use TIME_CONSTANTS, LIMIT_CONSTANTS, etc. instead
 */
export const LEGACY_CONSTANTS = {
  // Time constants (use TIME_CONSTANTS instead)
  SECOND: 1000,
  MINUTE: 60 * 1000,

  // Limits (use LIMIT_CONSTANTS instead)
  MAX_EVENTS: 500,

  // Content (use CONTENT_CONSTANTS instead)
  SAMPLE_WORD_COUNT: 1200,
} as const
