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

  // Time conversion constants
  SECONDS_PER_MINUTE: 60,
  MINUTES_PER_HOUR: 60,

  // Query stale times
  QUERY_STALE_TIME: 60 * 1000, // 1 minute

  // Test timeouts
  TEST_TIMEOUT_CI: 10000, // 10 seconds in CI
  TEST_TIMEOUT_LOCAL: 5000, // 5 seconds locally
  SLOW_TEST_THRESHOLD_CI: 5000, // 5 seconds
  SLOW_TEST_THRESHOLD_LOCAL: 2000, // 2 seconds

  // Performance thresholds
  PERFORMANCE_REGRESSION_THRESHOLD: 1.2, // 20% regression allowed

  // Mock API delays
  MOCK_API_DELAY: 1500, // 1.5 seconds for demo responses
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
// ROUTING PRIORITIES
// ============================================================================

export const ROUTING_PRIORITIES = {
  // Analysis render router priorities (higher = higher priority)
  LEGACY_COMPLETION: 100, // Legacy completion (highest priority)
  MODERN_COMPLETION: 90, // Modern completion (SSE-based)
  LOADING_STATES: 80, // Loading states (active analysis phases)
  ERROR_STATES: 70, // Error states (analysis failed)
  LOADING_COMPLETION: 60, // Loading completion (analysis finished via loading state)
  DEFAULT_ANALYSIS_UI: 10, // Default analysis UI (fallback)
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

  PADDING_Y_LG: 'py-20', // 80px section padding
  PADDING_X_MD: 'px-8', // 32px horizontal padding
  PADDING_Y_MD: 'py-16', // 64px section padding

  MARGIN_BOTTOM_SM: 'mb-3', // 12px
  MARGIN_BOTTOM_LG: 'mb-16', // 64px
  MARGIN_BOTTOM_MD: 'mb-12', // 48px
  MARGIN_Y_XS: 'my-1', // 4px

  // Dimensions
  WIDTH_XS: 'w-3', // 12px
  WIDTH_XS_MEDIUM: 'w-3.5', // 14px
  WIDTH_SM: 'w-4', // 16px
  WIDTH_MD: 'w-12', // 48px
  WIDTH_LG: 'w-16', // 64px

  HEIGHT_XS: 'h-3', // 12px
  HEIGHT_XS_MEDIUM: 'h-3.5', // 14px
  HEIGHT_SM: 'h-4', // 16px
  HEIGHT_MD: 'h-6', // 24px
  HEIGHT_LG: 'h-12', // 48px
  HEIGHT_XL: 'h-14', // 56px
  HEIGHT_2XL: 'h-16', // 64px

  // Specific component dimensions
  ICON_SIZE_MD: 'w-12 h-12', // 48px icon
  ICON_SIZE_LG: 'w-16 h-16', // 64px icon

  // Button styles
  BUTTON_PADDING: 'px-4 py-2',
  BUTTON_GAP: 'gap-2',
  BUTTON_HOVER: 'hover:scale-105',
  BUTTON_TRANSITION: 'transition-all',

  // Flexbox utilities
  FLEX_START: 'flex items-start',
  FLEX_BETWEEN: 'justify-between',
  FLEX_ITEMS_CENTER: 'items-center',
  FLEX_GAP_SM: 'gap-2',
  FLEX_GAP_MD: 'gap-3',

  // Layout utilities
  FLEX_CENTER: 'flex items-center justify-center',
  TEXT_CENTER: 'text-center',
  SHRINK_NONE: 'shrink-0',

  // Background utilities
  BG_MUTED_OPACITY: 'bg-muted/50',

  // Section padding
  SECTION_PADDING_Y: '5rem', // py-20
  SECTION_PADDING_X: '2rem', // px-8

  // Component dimensions
  ICON_SIZE_SM: '0.75rem', // w-3 h-3
  ICON_FONT_SIZE_MD: '1rem', // w-4 h-4
  ICON_FONT_SIZE_LG: '2rem', // w-8 h-8
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

  // Layout constraints (Tailwind CSS)
  LAYOUT_MAX_WIDTH_7XL: 'max-w-7xl',
  LAYOUT_MARGIN_X_AUTO: 'mx-auto',
} as const

// ============================================================================
// COMPONENT CONSTANTS
// ============================================================================

export const COMPONENT_CONSTANTS = {
  // UI element limits
  MAX_ITEMS_DEFAULT: 10,
  MAX_VISIBLE_ACTIVITIES: 10,
  MAX_VISIBLE_ITEMS_50: 50,
  MAX_VISIBLE_ITEMS_100: 100,

  // Debounce delays
  SEARCH_DEBOUNCE_MS: 300,
  FILTER_DEBOUNCE_MS: 300,

  // Animation durations
  TRANSITION_DURATION: 200, // milliseconds
  HOVER_SCALE_DURATION: 200, // milliseconds

  // Size limits
  SIZE_LIMIT_10: 10,
  SIZE_LIMIT_20: 20,
  SIZE_LIMIT_50: 50,
  SIZE_LIMIT_100: 100,
  SIZE_LIMIT_500: 500,
  SIZE_LIMIT_1000: 1000,

  // Content truncation limits
  ERROR_MESSAGE_TRUNCATE_LENGTH: 100,

  // Library/Skill filter defaults
  SKILL_DURATION_FILTER_MAX: 1000, // milliseconds

  // Percentage limits
  PERCENTAGE_80: 80,
  PERCENTAGE_90: 90,
  PERCENTAGE_95: 95,

  // Time limits
  TIME_LIMIT_30: 30, // seconds
  TIME_LIMIT_60: 60, // seconds
  TIME_LIMIT_5000: 5000, // milliseconds

  // Dimension values
  DIMENSION_12: 12,
  DIMENSION_16: 16,
  DIMENSION_20: 20,
  DIMENSION_48: 48,
  DIMENSION_80: 80,

  // Data truncation limits
  DATA_TRUNCATION_LIMIT: 500,

  // Time estimation thresholds
  TIME_ESTIMATION_HIGH_REMAINING_THRESHOLD: 10, // If 10+ stages remain, estimate 1-2 minutes

  // Diagram spacing (Mermaid)
  DIAGRAM_NODE_SPACING: 80,
  DIAGRAM_RANK_SPACING: 80,
  DIAGRAM_WRAPPING_WIDTH: 300, // Wider wrapping to prevent truncation in diamonds
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

  PADDING_Y_LG: 'py-20', // 80px section padding
  PADDING_X_MD: 'px-8', // 32px horizontal padding
  PADDING_Y_MD: 'py-16', // 64px section padding

  MARGIN_BOTTOM_SM: 'mb-3', // 12px
  MARGIN_BOTTOM_LG: 'mb-16', // 64px
  MARGIN_BOTTOM_MD: 'mb-12', // 48px
  MARGIN_Y_XS: 'my-1', // 4px

  // Dimensions
  WIDTH_XS: 'w-3', // 12px
  WIDTH_XS_MEDIUM: 'w-3.5', // 14px
  WIDTH_SM: 'w-4', // 16px
  WIDTH_MD: 'w-12', // 48px
  WIDTH_LG: 'w-16', // 64px

  HEIGHT_XS: 'h-3', // 12px
  HEIGHT_XS_MEDIUM: 'h-3.5', // 14px
  HEIGHT_SM: 'h-4', // 16px
  HEIGHT_MD: 'h-6', // 24px
  HEIGHT_LG: 'h-12', // 48px
  HEIGHT_XL: 'h-14', // 56px
  HEIGHT_2XL: 'h-16', // 64px

  // Specific component dimensions
  ICON_SIZE_MD: 'w-12 h-12', // 48px icon
  ICON_SIZE_LG: 'w-16 h-16', // 64px icon

  // Button styles
  BUTTON_PADDING: 'px-4 py-2',
  BUTTON_GAP: 'gap-2',
  BUTTON_HOVER: 'hover:scale-105',
  BUTTON_TRANSITION: 'transition-all',

  // Flexbox utilities
  FLEX_START: 'flex items-start',
  FLEX_BETWEEN: 'justify-between',
  FLEX_ITEMS_CENTER: 'items-center',
  FLEX_GAP_SM: 'gap-2',
  FLEX_GAP_MD: 'gap-3',

  // Layout utilities
  FLEX_CENTER: 'flex items-center justify-center',
  TEXT_CENTER: 'text-center',
  SHRINK_NONE: 'shrink-0',

  // Background utilities
  BG_MUTED_OPACITY: 'bg-muted/50',

  // Section padding
  SECTION_PADDING_Y: '5rem', // py-20
  SECTION_PADDING_X: '2rem', // px-8

  // Component dimensions
  ICON_SIZE_SM: '0.75rem', // w-3 h-3
  ICON_FONT_SIZE_MD: '1rem', // w-4 h-4
  ICON_FONT_SIZE_LG: '2rem', // w-8 h-8
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

  // Layout constraints (Tailwind CSS)
  LAYOUT_MAX_WIDTH_7XL: 'max-w-7xl',
  LAYOUT_MARGIN_X_AUTO: 'mx-auto',
} as const

// ============================================================================
// STAGE ORDER CONSTANTS
// ============================================================================

export const STAGE_ORDER_CONSTANTS = {
  // Pipeline stages (1-17)
  STAGE_EXTRACTION: 1,
  STAGE_CHUNKING: 2,
  STAGE_EMBEDDING: 3,
  STAGE_AGENT_CONTENT_ANALYSIS: 4,
  STAGE_AGENT_TECHNICAL_WRITER: 5,
  STAGE_AGENT_SECURITY_AUDITOR: 6,
  STAGE_AGENT_IMPLEMENTATION_PLANNER: 7,
  STAGE_AGENT_CODE_QUALITY: 8,
  STAGE_AGENT_PERFORMANCE_OPTIMIZER: 9,
  STAGE_AGENT_TESTING_STRATEGIST: 10,
  STAGE_QUALITY_AGGREGATION: 11,
  STAGE_QUALITY_VALIDATION: 12,
  STAGE_QUALITY_GENERATION: 13,
  STAGE_ARTIFACT_CHUNKING: 14,
  STAGE_ARTIFACT_WORKFLOW: 15,
  STAGE_ARTIFACT_PATTERN_COMPARISON: 16,
  STAGE_ARTIFACT_METRICS: 17,
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
// DATABASE DEFAULT CONSTANTS
// ============================================================================

export const DB_DEFAULTS = {
  // Agent examples
  AGENT_EXAMPLE_QUALITY_SCORE: 1.0,

  // Artifacts
  ARTIFACT_INITIAL_VERSION: 1,
  ARTIFACT_INITIAL_DOWNLOAD_COUNT: 0,

  // Analysis status
  ANALYSIS_STATUS_PENDING: 'pending',

  // Tutoring sessions
  TUTORING_SESSION_STATUS_ACTIVE: 'active',
  TUTORING_SESSION_CURRENT_SECTION: 0,
  TUTORING_SESSION_CURRENT_LESSON: 0,
  TUTORING_SESSION_PHASE_SYLLABUS_GENERATION: 'syllabus_generation',
  TUTORING_SESSION_USER_LEVEL_INTERMEDIATE: 'intermediate',
  TUTORING_SESSION_UNDERSTANDING_SCORES_EMPTY: '{}',
  ARTIFACT_METADATA_EMPTY: '{}',

  // Boolean defaults
  BOOLEAN_FALSE: false,
} as const

// ============================================================================
// ROUTING PRIORITIES
// ============================================================================

export const ROUTING_PRIORITIES = {
  // Analysis render router priorities (higher = higher priority)
  LEGACY_COMPLETION: 100, // Legacy completion (highest priority)
  MODERN_COMPLETION: 90, // Modern completion (SSE-based)
  LOADING_STATES: 80, // Loading states (active analysis phases)
  ERROR_STATES: 70, // Error states (analysis failed)
  LOADING_COMPLETION: 60, // Loading completion (analysis finished via loading state)
  DEFAULT_ANALYSIS_UI: 10, // Default analysis UI (fallback)
} as const

// ============================================================================
// COMPONENT CONSTANTS
// ============================================================================

export const COMPONENT_CONSTANTS = {
  // UI element limits
  MAX_ITEMS_DEFAULT: 10,
  MAX_VISIBLE_ACTIVITIES: 10,
  MAX_VISIBLE_ITEMS_50: 50,
  MAX_VISIBLE_ITEMS_100: 100,

  // Debounce delays
  SEARCH_DEBOUNCE_MS: 300,
  FILTER_DEBOUNCE_MS: 300,

  // Animation durations
  TRANSITION_DURATION: 200, // milliseconds
  HOVER_SCALE_DURATION: 200, // milliseconds

  // Size limits
  SIZE_LIMIT_10: 10,
  SIZE_LIMIT_20: 20,
  SIZE_LIMIT_50: 50,
  SIZE_LIMIT_100: 100,
  SIZE_LIMIT_500: 500,
  SIZE_LIMIT_1000: 1000,

  // Time estimation thresholds
  TIME_ESTIMATION_HIGH_REMAINING_THRESHOLD: 10, // If 10+ stages remain, estimate 1-2 minutes

  // Percentage limits
  PERCENTAGE_80: 80,
  PERCENTAGE_90: 90,
  PERCENTAGE_95: 95,

  // Time limits
  TIME_LIMIT_30: 30, // seconds
  TIME_LIMIT_60: 60, // seconds
  TIME_LIMIT_5000: 5000, // milliseconds

  // Dimension values
  DIMENSION_12: 12,
  DIMENSION_16: 16,
  DIMENSION_20: 20,
  DIMENSION_48: 48,
  DIMENSION_80: 80,

  // Data truncation limits
  DATA_TRUNCATION_LIMIT: 500,

  // Diagram spacing (Mermaid)
  DIAGRAM_NODE_SPACING: 80,
  DIAGRAM_RANK_SPACING: 80,
} as const
