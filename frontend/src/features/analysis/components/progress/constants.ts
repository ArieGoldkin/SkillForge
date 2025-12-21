/**
 * ProgressTracker Constants
 * UI-specific helper functions for stage display
 *
 * Stage configuration now comes from stageRegistry.ts
 */

import type { StageName, StageStatus } from '@app-types/sse'

import { ALL_STAGES, getStageTitle } from '../../config/stageRegistry'

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

/**
 * Format status for display
 */
export function formatStatus(status: StageStatus): string {
  switch (status) {
    case 'complete':
      return 'Complete'
    case 'running':
      return 'Running'
    case 'failed':
      return 'Failed'
    case 'skipped':
      return 'Skipped'
    case 'pending':
      return 'Pending'
    case 'synthesizing':
      return 'Synthesizing'
    case 'detecting_conflicts':
      return 'Detecting Conflicts'
    case 'static_fallback':
      return 'Fallback Mode'
    default: {
      // Exhaustive check - if this errors, a new status was added
      const _exhaustiveCheck: never = status
      return String(_exhaustiveCheck)
    }
  }
}

/**
 * Format agent name from snake_case to Title Case
 */
export function formatAgentName(agent: string): string {
  return agent
    .split('_')
    .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
    .join(' ')
}

/**
 * Get badge variant for status
 */
export function getStatusBadgeVariant(
  status: StageStatus
): 'default' | 'success' | 'warning' | 'destructive' | 'secondary' {
  switch (status) {
    case 'complete':
      return 'success'
    case 'running':
    case 'synthesizing':
    case 'detecting_conflicts':
      return 'warning'
    case 'failed':
    case 'static_fallback':
      return 'destructive'
    case 'skipped':
      return 'secondary'
    case 'pending':
      return 'default'
    default: {
      // Exhaustive check - TypeScript will error here if a new status is added
      const exhaustiveCheck: never = status
      // Return default as fallback (unreachable if all cases handled)
      void exhaustiveCheck
      return 'default'
    }
  }
}

// Re-export ALL_STAGES for backward compatibility
export { ALL_STAGES }
