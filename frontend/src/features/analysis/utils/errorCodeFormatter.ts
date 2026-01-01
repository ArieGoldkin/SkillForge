/**
 * Error code formatting utilities
 *
 * Converts backend error codes to human-readable messages for UI display.
 */

/**
 * Error explanation with user-friendly message, reason, and action
 */
export interface ErrorExplanation {
  title: string
  reason: string
  action: string
  retryable: boolean
  severity: 'critical' | 'non-critical'
}

/**
 * Maps backend error codes to user-friendly explanations
 */
const ERROR_EXPLANATIONS: Record<string, ErrorExplanation> = {
  // Extraction errors
  HTTP_404: {
    title: 'Page Not Found',
    reason: 'The URL you provided could not be found (404 error)',
    action: 'Check the URL and try again, or the page may have been removed',
    retryable: true,
    severity: 'critical',
  },
  HTTP_5XX: {
    title: 'Server Error',
    reason: 'The website server returned an error (5xx status code)',
    action: 'The website may be temporarily down. Try again in a few minutes',
    retryable: true,
    severity: 'critical',
  },
  TIMEOUT: {
    title: 'Request Timeout',
    reason: 'The request took too long to complete',
    action: 'The website may be slow. Try again or check your internet connection',
    retryable: true,
    severity: 'critical',
  },
  ERROR_PAGE: {
    title: 'Error Page Detected',
    reason: 'The website returned an error page instead of content',
    action: 'The URL may be invalid or the content is unavailable. Try a different URL',
    retryable: false,
    severity: 'critical',
  },
  REDIRECT_LOOP: {
    title: 'Redirect Loop',
    reason: 'The website has a redirect loop that prevents content extraction',
    action: 'This URL cannot be analyzed. Try accessing the final destination URL directly',
    retryable: false,
    severity: 'critical',
  },
  NETWORK_ERROR: {
    title: 'Network Error',
    reason: 'Unable to connect to the website',
    action: 'Check your internet connection and try again',
    retryable: true,
    severity: 'critical',
  },
  EXTRACTION_FAILED: {
    title: 'Content Extraction Failed',
    reason: 'Unable to extract content from the URL',
    action: 'The page may not be accessible or may require authentication. Try a different URL',
    retryable: true,
    severity: 'critical',
  },
  EXTRACTION_ERROR: {
    title: 'Extraction Error',
    reason: 'An error occurred while extracting content',
    action: 'Try again or use a different URL',
    retryable: true,
    severity: 'critical',
  },
  // Embedding errors
  EMBEDDING_FAILED: {
    title: 'Embedding Generation Failed',
    reason: 'Unable to generate embeddings for the content',
    action: 'This may be a temporary issue. Try retrying the analysis',
    retryable: true,
    severity: 'critical',
  },
  EMBEDDING_ERROR: {
    title: 'Embedding Error',
    reason: 'An error occurred while generating embeddings',
    action: 'Try retrying the analysis',
    retryable: true,
    severity: 'critical',
  },
  // Analysis errors
  ANALYSIS_FAILED: {
    title: 'Analysis Failed',
    reason: 'The analysis workflow encountered an error',
    action:
      'Try retrying the analysis. If it persists, the content may not be suitable for analysis',
    retryable: true,
    severity: 'critical',
  },
  QUALITY_GATE_FAILED: {
    title: 'Quality Gate Failed',
    reason: 'The analysis did not meet quality standards',
    action: 'The content may be too short or unclear. Try analyzing a different URL',
    retryable: true,
    severity: 'critical',
  },
  QUALITY_VALIDATION_FAILED: {
    title: 'Quality Validation Failed',
    reason: 'The analysis results did not pass quality validation',
    action: 'Try retrying the analysis or use a different content source',
    retryable: true,
    severity: 'critical',
  },
  // Agent errors (non-critical - analysis can continue)
  TECH_COMPARATOR_FAILED: {
    title: 'Technology Comparison Failed',
    reason: 'Unable to compare technologies from this content',
    action:
      'This stage requires technology comparisons. The analysis will continue without this stage',
    retryable: true,
    severity: 'non-critical',
  },
  SECURITY_AUDITOR_FAILED: {
    title: 'Security Audit Failed',
    reason: 'Unable to perform security analysis on this content',
    action:
      'This stage requires security-related content. The analysis will continue without this stage',
    retryable: true,
    severity: 'non-critical',
  },
  IMPLEMENTATION_PLANNER_FAILED: {
    title: 'Implementation Planning Failed',
    reason: 'Unable to generate implementation plan from this content',
    action:
      'This stage requires implementation details. The analysis will continue without this stage',
    retryable: true,
    severity: 'non-critical',
  },
  PERFORMANCE_ANALYST_FAILED: {
    title: 'Performance Analysis Failed',
    reason: 'Unable to analyze performance aspects from this content',
    action:
      'This stage requires performance metrics. The analysis will continue without this stage',
    retryable: true,
    severity: 'non-critical',
  },
  CODE_QUALITY_CRITIC_FAILED: {
    title: 'Code Quality Review Failed',
    reason: 'Unable to review code quality from this content',
    action: 'This stage requires code examples. The analysis will continue without this stage',
    retryable: true,
    severity: 'non-critical',
  },
  TREND_VALIDATOR_FAILED: {
    title: 'Trend Analysis Failed',
    reason: 'Unable to validate technology trends from this content',
    action: 'This stage requires technology trends. The analysis will continue without this stage',
    retryable: true,
    severity: 'non-critical',
  },
  DEPENDENCY_MAPPER_FAILED: {
    title: 'Dependency Mapping Failed',
    reason: 'Unable to map dependencies from this content',
    action:
      'This stage requires dependency information. The analysis will continue without this stage',
    retryable: true,
    severity: 'non-critical',
  },
  INTEGRATION_FEASIBILITY_FAILED: {
    title: 'Integration Feasibility Check Failed',
    reason: 'Unable to assess integration feasibility from this content',
    action:
      'This stage requires integration details. The analysis will continue without this stage',
    retryable: true,
    severity: 'non-critical',
  },
  // Aggregation errors
  AGGREGATION_FAILED: {
    title: 'Aggregation Failed',
    reason: 'Unable to aggregate findings from multiple agents',
    action: 'Try retrying the analysis. This may be a temporary issue',
    retryable: true,
    severity: 'critical',
  },
  // Artifact errors
  ARTIFACT_FAILED: {
    title: 'Artifact Generation Failed',
    reason: 'Unable to generate the final analysis artifact',
    action: 'Try retrying the analysis. The content may be too complex',
    retryable: true,
    severity: 'critical',
  },
  ARTIFACT_GENERATION_FAILED: {
    title: 'Artifact Generation Failed',
    reason: 'Unable to generate the final analysis artifact',
    action: 'Try retrying the analysis',
    retryable: true,
    severity: 'critical',
  },
  // Generic
  UNKNOWN: {
    title: 'Unknown Error',
    reason: 'An unexpected error occurred',
    action: 'Try retrying the analysis. If it persists, contact support',
    retryable: true,
    severity: 'critical',
  },
  WORKFLOW_FAILED: {
    title: 'Workflow Failed',
    reason: 'The analysis workflow encountered an error',
    action: 'Try retrying the analysis. This may be a temporary issue',
    retryable: true,
    severity: 'critical',
  },
  WORKFLOW_STARTUP_FAILED: {
    title: 'Workflow Startup Failed',
    reason: 'Unable to start the analysis workflow',
    action: 'Try creating a new analysis. This may be a temporary system issue',
    retryable: true,
    severity: 'critical',
  },
  WORKFLOW_EXECUTION_FAILED: {
    title: 'Workflow Execution Failed',
    reason: 'The analysis workflow failed during execution',
    action: 'Try retrying the analysis',
    retryable: true,
    severity: 'critical',
  },
}

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

  const explanation = getErrorExplanation(errorCode)
  return explanation.severity === 'critical' ? 'destructive' : 'default'
}

/**
 * Get full error explanation with user-friendly details
 *
 * @param errorCode - Backend error code
 * @returns Error explanation with title, reason, action, and retryability
 */
export function getErrorExplanation(errorCode: string | undefined | null): ErrorExplanation {
  if (!errorCode) {
    return {
      title: 'Unknown Error',
      reason: 'An unexpected error occurred',
      action: 'Try retrying the analysis. If it persists, contact support',
      retryable: true,
      severity: 'critical',
    }
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
 *
 * @param errorCode - Backend error code
 * @returns Whether the error can be retried
 */
export function isErrorRetryable(errorCode: string | undefined | null): boolean {
  if (!errorCode) {
    return true
  }

  return getErrorExplanation(errorCode).retryable
}

/**
 * Check if error is critical
 *
 * @param errorCode - Backend error code
 * @returns Whether the error is critical (blocks analysis completion)
 */
export function isErrorCritical(errorCode: string | undefined | null): boolean {
  if (!errorCode) {
    return true
  }

  return getErrorExplanation(errorCode).severity === 'critical'
}
