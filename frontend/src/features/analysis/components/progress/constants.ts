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
      return 'warning'
    case 'failed':
      return 'destructive'
    case 'skipped':
      return 'secondary'
    case 'pending':
      return 'default'
  }
}

// Re-export ALL_STAGES for backward compatibility
export { ALL_STAGES }
