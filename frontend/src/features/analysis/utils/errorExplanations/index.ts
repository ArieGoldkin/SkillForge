/**
 * Error explanations module - combines all error categories
 */
import { AGENT_ERRORS } from './agents'
import { ANALYSIS_ERRORS } from './analysis'
import { EXTRACTION_ERRORS } from './extraction'
import type { ErrorExplanation } from './types'
import { WORKFLOW_ERRORS } from './workflow'

// Re-export type
export type { ErrorExplanation }

/**
 * Combined error explanations from all categories
 */
export const ERROR_EXPLANATIONS: Record<string, ErrorExplanation> = {
  ...EXTRACTION_ERRORS,
  ...ANALYSIS_ERRORS,
  ...AGENT_ERRORS,
  ...WORKFLOW_ERRORS,
}

/**
 * Default error explanation for unmapped error codes
 */
export const DEFAULT_UNKNOWN_EXPLANATION: ErrorExplanation = {
  title: 'Unknown Error',
  reason: 'An unexpected error occurred',
  action: 'Try retrying the analysis. If it persists, contact support',
  retryable: true,
  severity: 'critical',
}
