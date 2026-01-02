/**
 * Workflow and artifact error explanations
 */
import type { ErrorExplanation } from './types'

export const WORKFLOW_ERRORS: Record<string, ErrorExplanation> = {
  AGGREGATION_FAILED: {
    title: 'Aggregation Failed',
    reason: 'Unable to aggregate findings from multiple agents',
    action: 'Try retrying the analysis. This may be a temporary issue',
    retryable: true,
    severity: 'critical',
  },
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
