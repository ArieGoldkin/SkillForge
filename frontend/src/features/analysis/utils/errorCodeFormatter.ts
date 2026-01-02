/**
 * Error code formatting utilities
 *
 * Converts backend error codes to human-readable messages for UI display.
 */

import {
  DEFAULT_UNKNOWN_EXPLANATION,
  ERROR_EXPLANATIONS,
  type ErrorExplanation,
} from './errorExplanations/index'

// Re-export the type for consumers
export type { ErrorExplanation }

/**
 * Maps backend error codes to human-readable messages (backward compatibility)
 */
const ERROR_CODE_MAP: Record<string, string> = Object.fromEntries(
  Object.entries(ERROR_EXPLANATIONS).map(([code, explanation]) => [code, explanation.title])
)

/**
 * Format error code to human-readable message
 *
 * @param errorCode - Backend error code (e.g., "EXTRACTION_FAILED", "NETWORK_ERROR")
 * @returns Human-readable error message (e.g., "Extraction Failed", "Network Error")
 *
 * @example
 * ```ts
 * formatErrorCode("EXTRACTION_FAILED") // "Extraction Failed"
 * formatErrorCode("UNKNOWN") // "Unknown Error"
 * formatErrorCode("CUSTOM_CODE") // "CUSTOM_CODE" (fallback to original)
 * ```
 */
export function formatErrorCode(errorCode: string | undefined | null): string {
  if (!errorCode) {
    return 'Unknown Error'
  }

  // Check if we have a mapping for this error code
  const mapped = ERROR_CODE_MAP[errorCode]
  if (mapped) {
    return mapped
  }

  // Fallback: Convert snake_case or SCREAMING_SNAKE_CASE to Title Case
  return errorCode
    .split('_')
    .map((word) => word.charAt(0).toUpperCase() + word.slice(1).toLowerCase())
    .join(' ')
}

/**
 * Get error code badge variant based on error type
 */
export function getErrorCodeBadgeVariant(
  errorCode: string | undefined | null
): 'default' | 'destructive' | 'secondary' {
  if (!errorCode) {
    return 'secondary'
  }

  const explanation = getErrorExplanation(errorCode)
  return explanation.severity === 'critical' ? 'destructive' : 'default'
}

/**
 * Get full error explanation with user-friendly details
 */
export function getErrorExplanation(errorCode: string | undefined | null): ErrorExplanation {
  if (!errorCode) {
    return DEFAULT_UNKNOWN_EXPLANATION
  }

  const explanation = ERROR_EXPLANATIONS[errorCode]
  if (explanation) {
    return explanation
  }

  // Fallback for unmapped error codes
  return {
    title: formatErrorCode(errorCode),
    reason: 'An error occurred during this stage',
    action: 'Try retrying the analysis',
    retryable: true,
    severity: 'non-critical',
  }
}

/**
 * Check if error is retryable
 */
export function isErrorRetryable(errorCode: string | undefined | null): boolean {
  if (!errorCode) {
    return true
  }

  return getErrorExplanation(errorCode).retryable
}

/**
 * Check if error is critical
 */
export function isErrorCritical(errorCode: string | undefined | null): boolean {
  if (!errorCode) {
    return true
  }

  return getErrorExplanation(errorCode).severity === 'critical'
}
