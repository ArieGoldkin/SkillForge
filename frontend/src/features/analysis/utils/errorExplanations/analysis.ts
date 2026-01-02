/**
 * Analysis and embedding error explanations
 */
import type { ErrorExplanation } from './types'

export const ANALYSIS_ERRORS: Record<string, ErrorExplanation> = {
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
}
