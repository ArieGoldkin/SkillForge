/**
 * Error code formatting utilities
 *
 * Converts backend error codes to human-readable messages for UI display.
 */

/**
 * Maps backend error codes to human-readable messages
 */
const ERROR_CODE_MAP: Record<string, string> = {
  // Extraction errors
  HTTP_404: 'Page Not Found',
  HTTP_5XX: 'Server Error',
  TIMEOUT: 'Request Timeout',
  ERROR_PAGE: 'Error Page Detected',
  REDIRECT_LOOP: 'Redirect Loop',
  NETWORK_ERROR: 'Network Error',
  EXTRACTION_FAILED: 'Extraction Failed',
  EXTRACTION_ERROR: 'Extraction Error',
  // Embedding errors
  EMBEDDING_FAILED: 'Embedding Generation Failed',
  EMBEDDING_ERROR: 'Embedding Error',
  // Analysis errors
  ANALYSIS_FAILED: 'Analysis Failed',
  QUALITY_GATE_FAILED: 'Quality Gate Failed',
  QUALITY_VALIDATION_FAILED: 'Quality Validation Failed',
  // Agent errors
  TECH_COMPARATOR_FAILED: 'Tech Comparison Failed',
  SECURITY_AUDITOR_FAILED: 'Security Audit Failed',
  IMPLEMENTATION_PLANNER_FAILED: 'Implementation Planning Failed',
  PERFORMANCE_ANALYST_FAILED: 'Performance Analysis Failed',
  CODE_QUALITY_CRITIC_FAILED: 'Code Quality Review Failed',
  TREND_VALIDATOR_FAILED: 'Trend Analysis Failed',
  DEPENDENCY_MAPPER_FAILED: 'Dependency Mapping Failed',
  INTEGRATION_FEASIBILITY_FAILED: 'Integration Feasibility Check Failed',
  // Aggregation errors
  AGGREGATION_FAILED: 'Aggregation Failed',
  // Artifact errors
  ARTIFACT_FAILED: 'Artifact Generation Failed',
  ARTIFACT_GENERATION_FAILED: 'Artifact Generation Failed',
  // Generic
  UNKNOWN: 'Unknown Error',
  WORKFLOW_FAILED: 'Workflow Failed',
}

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
 *
 * @param errorCode - Backend error code
 * @returns Badge variant for error display
 */
export function getErrorCodeBadgeVariant(
  errorCode: string | undefined | null
): 'default' | 'destructive' | 'secondary' {
  if (!errorCode) {
    return 'secondary'
  }

  // Critical errors get destructive variant
  const criticalErrors = [
    'EXTRACTION_FAILED',
    'ANALYSIS_FAILED',
    'ARTIFACT_FAILED',
    'QUALITY_GATE_FAILED',
    'WORKFLOW_FAILED',
  ]

  if (criticalErrors.includes(errorCode)) {
    return 'destructive'
  }

  return 'default'
}
