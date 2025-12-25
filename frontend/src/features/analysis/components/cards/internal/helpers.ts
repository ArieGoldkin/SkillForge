/**
 * Helper functions for AnalysisActionsCard
 */

import type { AnalysisStatus } from '@app-types/api'

export const FAILURE_STATUSES: AnalysisStatus[] = [
  'extraction_failed',
  'analysis_failed',
  'artifact_failed',
  'quality_gate_failed',
  'failed',
]

export const STATUS_LABELS: Record<string, string> = {
  extraction_failed: 'Content Extraction Failed',
  analysis_failed: 'Analysis Failed',
  artifact_failed: 'Artifact Generation Failed',
  quality_gate_failed: 'Quality Gate Failed',
  failed: 'Analysis Failed',
}

export function isFailureStatus(status: AnalysisStatus): boolean {
  return FAILURE_STATUSES.includes(status)
}

export function getStatusLabel(status: AnalysisStatus): string {
  return STATUS_LABELS[status] || 'Analysis Failed'
}

export function getCardDescription(isFailed: boolean): string {
  return isFailed
    ? 'The analysis encountered an error. You can retry up to 3 times.'
    : 'Regenerate the analysis with the latest AI models and prompts.'
}
