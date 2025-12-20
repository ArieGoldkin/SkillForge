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

// ============================================================================
// DEMO/SHOWCASE DATA CONSTANTS
// ============================================================================

export const DEMO_CONSTANTS = {
  // Sample analysis data
  SAMPLE_WORD_COUNT: 450,
  SAMPLE_AVG_CONFIDENCE: 0.87,
  SAMPLE_PROGRESS_PERCENTAGE: 60,

  // Activity durations (seconds)
  ACTIVITY_DURATION_SHORT: 30, // 30 seconds
  ACTIVITY_DURATION_MEDIUM: 45, // 45 seconds
  ACTIVITY_DURATION_LONG: 120, // 2 minutes

  // Time offsets for demo timestamps (milliseconds)
  TIME_OFFSET_5_SECONDS: 5000,
  TIME_OFFSET_15_SECONDS: 15000,
  TIME_OFFSET_25_SECONDS: 25000,
  TIME_OFFSET_30_SECONDS: 30000,
  TIME_OFFSET_35_SECONDS: 35000,
  TIME_OFFSET_1_MINUTE: 60000,
  TIME_OFFSET_2_MINUTES: 120000,
  TIME_OFFSET_5_MINUTES: 300000,

  // UI limits for demo components
  MAX_ACTIVITY_ITEMS: 10,

  // Duration ranges for filtering (milliseconds)
  DURATION_RANGE_MIN: 0,
  DURATION_RANGE_MAX: 1000, // 1 second max for demo
} as const

// ============================================================================
// UI/SPACING CONSTANTS
// ============================================================================

export const UI_CONSTANTS = {
  // Spacing (Tailwind CSS equivalents)
  SPACING_XS: '0.5rem', // 8px - space-2
  SPACING_SM: '0.75rem', // 12px - space-3
  SPACING_MD: '1rem', // 16px - space-4
  SPACING_LG: '1.5rem', // 24px - space-6
  SPACING_XL: '2rem', // 32px - space-8
  SPACING_2XL: '3rem', // 48px - space-12
  SPACING_3XL: '4rem', // 64px - space-16

  // Common spacing classes
  PADDING_XS: 'p-1', // 4px
  PADDING_SM: 'p-2', // 8px
  PADDING_MD: 'p-4', // 16px
  PADDING_LG: 'p-6', // 24px

  MARGIN_BOTTOM_SM: 'mb-3', // 12px
  MARGIN_Y_XS: 'my-1', // 4px

  // Section padding
  SECTION_PADDING_Y: '5rem', // py-20
  SECTION_PADDING_X: '2rem', // px-8

  // Component dimensions
  ICON_SIZE_SM: '0.75rem', // w-3 h-3
  ICON_SIZE_MD: '1rem', // w-4 h-4
  ICON_SIZE_LG: '2rem', // w-8 h-8
  ICON_SIZE_XL: '4rem', // w-16 h-16

  // Border radius
  BORDER_RADIUS_SM: '0.25rem', // rounded
  BORDER_RADIUS_MD: '0.375rem', // rounded-md
  BORDER_RADIUS_LG: '0.5rem', // rounded-lg
  BORDER_RADIUS_FULL: '9999px', // rounded-full

  // Font sizes (Tailwind equivalents)
  FONT_SIZE_XS: '0.75rem', // text-xs
  FONT_SIZE_SM: '0.875rem', // text-sm
  FONT_SIZE_BASE: '1rem', // text-base
  FONT_SIZE_LG: '1.125rem', // text-lg
  FONT_SIZE_XL: '1.25rem', // text-xl
  FONT_SIZE_2XL: '1.5rem', // text-2xl
  FONT_SIZE_3XL: '1.875rem', // text-3xl
  FONT_SIZE_4XL: '2.25rem', // text-4xl

  // Text colors (semantic)
  TEXT_COLOR_MUTED: 'text-muted-foreground',
  TEXT_COLOR_SECONDARY: 'text-muted-foreground',

  // Button styles
  BUTTON_STYLE_PRIMARY: 'bg-primary text-primary-foreground hover:bg-primary/90',
  BUTTON_STYLE_SECONDARY: 'bg-secondary text-secondary-foreground hover:bg-secondary/80',
  BUTTON_STYLE_DESTRUCTIVE: 'bg-destructive text-destructive-foreground hover:bg-destructive/90',

  // Heights
  INPUT_HEIGHT: '3.5rem', // h-14
  BUTTON_HEIGHT: '2.5rem', // h-10

  // Complex status colors with opacity
  STATUS_STYLE_INFO: 'bg-blue-500/10 text-blue-500 border-blue-500/20',
  STATUS_STYLE_ERROR: 'bg-red-500/10 text-red-500 border-red-500/20',
  STATUS_STYLE_WARNING: 'bg-purple-500/10 text-purple-500 border-purple-500/20',
} as const

// ============================================================================
// VALIDATION CONSTANTS
// ============================================================================

export const VALIDATION_CONSTANTS = {
  // String length limits
  ERROR_MESSAGE_TRUNCATE_LENGTH: 100,
  ERROR_MESSAGE_SHORT_TRUNCATE_LENGTH: 80,
  PREVIEW_TEXT_LENGTH: 50,
  CODE_PREVIEW_LENGTH: 100,

  // Input validation
  MIN_SEARCH_QUERY_LENGTH: 2,
  MAX_SEARCH_QUERY_LENGTH: 200,

  // Content limits
  MAX_WORD_COUNT_DISPLAY: 2500,
} as const

// ============================================================================
// API CONSTANTS
// ============================================================================

export const API_CONSTANTS = {
  // Pagination
  DEFAULT_LIBRARY_LIMIT: 15,
  DEFAULT_SEARCH_LIMIT: 20,

  // Timeouts (milliseconds)
  DEFAULT_TIMEOUT: 30000, // 30 seconds
  LONG_TIMEOUT: 60000, // 1 minute

  // Request limits
  MAX_CONCURRENT_REQUESTS: 5,
} as const

// ============================================================================
// BUSINESS LOGIC CONSTANTS
// ============================================================================

export const BUSINESS_CONSTANTS = {
  // Progress and completion
  PROGRESS_COMPLETE_PERCENTAGE: 100,

  // Priority levels (higher = more important)
  PRIORITY_LEGACY_COMPLETION: 100,

  // Time conversion constants
  MILLISECONDS_PER_SECOND: 1000,

  // Color intensity values (Tailwind CSS)
  COLOR_INTENSITY_MEDIUM: 500, // bg-green-500, text-blue-500, etc.

  // Status colors
  STATUS_COLOR_SUCCESS: 'bg-green-500',
  STATUS_COLOR_ERROR: 'bg-red-500',
  STATUS_COLOR_INFO: 'bg-blue-500',
  STATUS_COLOR_WARNING: 'bg-purple-500',

  // Status text colors
  STATUS_TEXT_SUCCESS: 'text-green-500',
  STATUS_TEXT_ERROR: 'text-red-500',
  STATUS_TEXT_INFO: 'text-blue-500',
  STATUS_TEXT_WARNING: 'text-purple-500',

  // Complex status colors with opacity
  STATUS_STYLE_INFO: 'bg-blue-500/10 text-blue-500 border-blue-500/20',
  STATUS_STYLE_ERROR: 'bg-red-500/10 text-red-500 border-red-500/20',
  STATUS_STYLE_WARNING: 'bg-purple-500/10 text-purple-500 border-purple-500/20',
} as const

// ============================================================================
// COMPONENT CONSTANTS
// ============================================================================

export const COMPONENT_CONSTANTS = {
  // UI element limits
  MAX_ITEMS_DEFAULT: 10,
  MAX_VISIBLE_ACTIVITIES: 10,

  // Debounce delays
  SEARCH_DEBOUNCE_MS: 300,
  FILTER_DEBOUNCE_MS: 300,

  // Animation durations
  TRANSITION_DURATION: 200, // milliseconds
  HOVER_SCALE_DURATION: 200, // milliseconds
} as const
