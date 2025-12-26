import type { AnalysisStatus, FilterStatus } from '@app-types/api'

import type { SkillStatus } from '../components/SkillCard'

/**
 * Maps backend AnalysisStatus to frontend SkillStatus.
 * Handles all possible analysis statuses including lifecycle states and failures.
 */
export function mapAnalysisStatusToSkillStatus(status: AnalysisStatus): SkillStatus {
  // Complete status
  if (status === 'complete' || status === 'completed') return 'completed'

  // All failure statuses map to 'failed'
  if (
    status === 'failed' ||
    status === 'extraction_failed' ||
    status === 'analysis_failed' ||
    status === 'artifact_failed' ||
    status === 'quality_gate_failed'
  ) {
    return 'failed'
  }

  // All lifecycle states map to 'in-progress'
  if (
    status === 'pending' ||
    status === 'extracting' ||
    status === 'analyzing' ||
    status === 'generating_artifact'
  ) {
    return 'in-progress'
  }

  // Cancelled maps to 'not-started' (user action)
  if (status === 'cancelled') return 'not-started'

  // Default to in-progress for unknown statuses
  return 'in-progress'
}

/**
 * Maps backend AnalysisStatus to FilterStatus for filter comparisons.
 * FilterStatus is the simplified status used by the backend filter API.
 */
export function mapAnalysisStatusToFilterStatus(status: AnalysisStatus): FilterStatus {
  // Complete status
  if (status === 'complete' || status === 'completed') return 'complete'

  // All failure statuses map to 'failed'
  if (
    status === 'failed' ||
    status === 'extraction_failed' ||
    status === 'analysis_failed' ||
    status === 'artifact_failed' ||
    status === 'quality_gate_failed'
  ) {
    return 'failed'
  }

  // All lifecycle states map to 'running'
  if (status === 'extracting' || status === 'analyzing' || status === 'generating_artifact') {
    return 'running'
  }

  // Pending and cancelled map to 'pending'
  if (status === 'pending' || status === 'cancelled') return 'pending'

  // Default to 'running' for unknown statuses
  return 'running'
}
