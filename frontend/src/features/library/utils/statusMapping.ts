import type { AnalysisStatus } from '@app-types/api'

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
    status === 'generating_artifact' ||
    status === 'running' ||
    status === 'in-progress'
  ) {
    return 'in-progress'
  }

  // Cancelled maps to 'not-started' (user action)
  if (status === 'cancelled') return 'not-started'

  // Default to in-progress for unknown statuses
  return 'in-progress'
}
