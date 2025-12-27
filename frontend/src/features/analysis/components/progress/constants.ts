/**
 * ProgressTracker Constants
 * UI-specific helper functions for stage display
 *
 * Stage configuration now comes from:
 * - stageRegistry.ts (stage names/titles)
 * - stageStatusConfig.tsx (status icons/badges/labels)
 */

import type { StageName, StageStatus } from '@/schemas/sse'

import { ALL_STAGES, getStageTitle } from '../../config/stageRegistry'

export { ALL_STAGES }

/**
 * Internal state for each stage
 */
export interface StageState {
  name: StageName
  label: string
  status: StageStatus
  agent?: string
  timestamp?: string
  error?: string
  errorCode?: string
}

/**
 * Create initial stage states from stage list
 * Uses registry to get canonical stage titles
 */
export function createInitialStages(stages: StageName[]): StageState[] {
  return stages.map((name) => ({
    name,
    label: getStageTitle(name),
    status: 'pending' as StageStatus,
  }))
}
