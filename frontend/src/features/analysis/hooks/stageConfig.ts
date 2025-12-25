/**
 * Stage configuration - Business logic functions using the stage registry
 *
 * This file provides helper functions that ADD VALUE on top of the registry:
 * - markSkippedAgents: Complex logic for determining skip reasons
 * - estimateTimeRemaining: Time estimation based on stage progress
 *
 * All base configuration (STAGE_CONFIG, mappings, etc.) is imported from
 * the stage registry to maintain a single source of truth.
 *
 * @see ../config/stageRegistry.ts for the complete stage registry
 */

import type { StageName, StageStatus } from '@/schemas/sse'

import { COMPONENT_CONSTANTS } from '@/lib/constants'

// Import from the stage registry
import {
  AGENT_TO_STAGE_MAP,
  STAGE_CONFIG,
  TOTAL_STAGES,
  getOptionalStages,
  normalizeStageNameFromBackend,
} from '../config/stageRegistry'

// Re-export stage registry constants for convenience
export { STAGE_CONFIG, TOTAL_STAGES, normalizeStageNameFromBackend }

/** Stage status entry for the status map */
export interface StageStatusEntry {
  status: StageStatus
  timestamp: string
  details?: Record<string, unknown>
}

/**
 * Mark unselected optional agents as 'skipped' after supervisor completes
 * Bug #165 fix: Shows skipped state instead of pending for non-selected agents
 *
 * This function contains complex business logic for:
 * 1. Determining which agents were not selected by the supervisor
 * 2. Distinguishing between "not applicable" vs "not selected" skip reasons
 * 3. Setting appropriate skip status and timestamp
 */
export function markSkippedAgents(
  stageStatuses: Map<StageName, StageStatusEntry>,
  skippedAgentsInfo?: { agents: string[]; selectedAgents?: string[] }
): void {
  const supervisorStatus = stageStatuses.get('supervisor_routing')
  if (supervisorStatus?.status !== 'complete') return

  // Build set of stages that were selected by supervisor
  const selectedAgentStages = new Set<StageName>()
  if (skippedAgentsInfo?.selectedAgents) {
    for (const agentType of skippedAgentsInfo.selectedAgents) {
      const stageName = AGENT_TO_STAGE_MAP[agentType]
      if (stageName) {
        selectedAgentStages.add(stageName)
      }
    }
  }

  // Mark all optional stages that weren't selected as skipped
  for (const agentStage of getOptionalStages()) {
    if (!stageStatuses.has(agentStage)) {
      // Determine skip reason
      let skipReason = 'Not selected by supervisor'

      // Check if this agent was explicitly skipped
      if (skippedAgentsInfo?.agents) {
        const agentType = Object.entries(AGENT_TO_STAGE_MAP).find(
          ([, stage]) => stage === agentStage
        )?.[0]
        if (agentType && skippedAgentsInfo.agents.includes(agentType)) {
          skipReason = 'Not applicable for this content type'
        } else if (!selectedAgentStages.has(agentStage)) {
          skipReason = 'Not selected by supervisor'
        }
      }

      stageStatuses.set(agentStage, {
        status: 'skipped',
        timestamp: supervisorStatus.timestamp,
        details: {
          skipped_by: 'supervisor_routing',
          skip_reason: skipReason,
        },
      })
    }
  }
}

/**
 * Estimate remaining time based on completed stages
 *
 * This function contains business logic for time estimation based on
 * empirical analysis workflow duration data.
 *
 * @param completedStages - Number of stages that have completed
 * @param totalStages - Dynamic total stages from supervisor (Issue #443)
 *                      Falls back to TOTAL_STAGES constant if not provided
 */
export function estimateTimeRemaining(
  completedStages: number,
  totalStages?: number
): string | undefined {
  if (completedStages === 0) {
    return '~2-3 minutes'
  }
  // Issue #443: Use dynamic totalStages from backend when available
  const effectiveTotalStages = totalStages ?? TOTAL_STAGES
  const remaining = effectiveTotalStages - completedStages
  if (remaining >= COMPONENT_CONSTANTS.TIME_ESTIMATION_HIGH_REMAINING_THRESHOLD) {
    return '~1-2 minutes'
  }
  if (remaining <= 3) {
    return '~30 seconds'
  }
  if (remaining <= 6) {
    return '~1 minute'
  }
  if (remaining <= 9) {
    return '~1-2 minutes'
  }
  return '~2-3 minutes'
}
