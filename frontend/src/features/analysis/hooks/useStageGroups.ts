/**
 * useStageGroups - Compute hierarchical group statuses from stage statuses
 *
 * This hook transforms flat stage status map into grouped accordion sections
 * with computed group-level status and progress.
 *
 * @module features/analysis/hooks/useStageGroups
 */

import { useMemo } from 'react'

import type { StageName } from '@/schemas/base'

import { assertNever } from '@lib/utils'

import { STAGE_GROUPS, STAGE_TO_GROUP_MAP } from '../config/stageGroups'
import type { GroupStatus, GroupStatusMeta, StageGroup } from '../types/accordion'

import type { StageStatusEntry } from './stageConfig'

// ============================================================================
// Types
// ============================================================================

/**
 * Group with computed status and metadata
 */
export interface StageGroupWithStatus {
  /** The base group configuration */
  group: StageGroup
  /** Computed status metadata */
  status: GroupStatusMeta
}

// ============================================================================
// Helper Functions
// ============================================================================

/**
 * Status flag accumulator for group status computation
 */
interface StatusFlags {
  hasRunning: boolean
  hasFailed: boolean
  hasComplete: boolean
  hasPending: boolean
  hasSkipped: boolean
}

/**
 * Check if a stage status represents a running state
 */
function isRunningStatus(status: string): boolean {
  return status === 'running' || status === 'synthesizing' || status === 'detecting_conflicts'
}

/**
 * Check if a stage status represents a failed state
 */
function isFailedStatus(status: string): boolean {
  return status === 'failed' || status === 'static_fallback'
}

/**
 * Accumulate status flags from stage statuses
 */
function accumulateStatusFlags(
  stages: StageName[],
  stageStatuses: Map<StageName, StageStatusEntry>
): StatusFlags {
  const flags: StatusFlags = {
    hasRunning: false,
    hasFailed: false,
    hasComplete: false,
    hasPending: false,
    hasSkipped: false,
  }

  for (const stageName of stages) {
    const stageStatus = stageStatuses.get(stageName)
    const status = stageStatus?.status ?? 'pending'

    if (isRunningStatus(status)) {
      flags.hasRunning = true
    } else if (isFailedStatus(status)) {
      flags.hasFailed = true
    } else if (status === 'complete') {
      flags.hasComplete = true
    } else if (status === 'skipped') {
      flags.hasSkipped = true
    } else if (status === 'pending') {
      flags.hasPending = true
    }
  }

  return flags
}

/**
 * Derive group status from accumulated status flags
 */
function deriveGroupStatus(flags: StatusFlags): GroupStatus {
  // Priority order for status determination
  if (flags.hasFailed) return 'failed'
  if (flags.hasRunning) return 'in-progress'
  if (flags.hasComplete && !flags.hasPending && !flags.hasSkipped) return 'completed'
  if (flags.hasComplete && flags.hasSkipped) return 'partial'
  if (flags.hasSkipped && !flags.hasComplete && !flags.hasPending) return 'completed' // All skipped = completed
  return 'pending'
}

/**
 * Compute group status from member stage statuses
 *
 * Status derivation logic:
 * - 'pending': All stages are pending
 * - 'in-progress': At least one stage is running
 * - 'completed': All stages are complete (or skipped if optional)
 * - 'failed': At least one stage failed
 * - 'partial': Mixed complete/skipped (some complete, some skipped)
 *
 * @param stages - Stage names in the group
 * @param stageStatuses - Map of all stage statuses
 * @returns Computed GroupStatus
 */
function computeGroupStatus(
  stages: StageName[],
  stageStatuses: Map<StageName, StageStatusEntry>
): GroupStatus {
  const flags = accumulateStatusFlags(stages, stageStatuses)
  return deriveGroupStatus(flags)
}

/**
 * Compute group progress percentage
 *
 * Progress = (completed + skipped) / total * 100
 * Skipped stages count as "done" for progress calculation
 *
 * @param stages - Stage names in the group
 * @param stageStatuses - Map of all stage statuses
 * @returns Progress percentage (0-100)
 */
function computeGroupProgress(
  stages: StageName[],
  stageStatuses: Map<StageName, StageStatusEntry>
): number {
  let completed = 0
  const total = stages.length

  for (const stageName of stages) {
    const stageStatus = stageStatuses.get(stageName)
    const status = stageStatus?.status ?? 'pending'

    if (status === 'complete' || status === 'skipped') {
      completed++
    }
  }

  return total > 0 ? Math.round((completed / total) * 100) : 0
}

/**
 * Compute detailed group status metadata
 *
 * @param group - The stage group configuration
 * @param stageStatuses - Map of all stage statuses
 * @returns GroupStatusMeta with counts and computed status
 */
function computeGroupStatusMeta(
  group: StageGroup,
  stageStatuses: Map<StageName, StageStatusEntry>
): GroupStatusMeta {
  const stages = group.stages
  let completed = 0
  let failed = 0
  let skipped = 0
  let running = 0

  for (const stageName of stages) {
    const stageStatus = stageStatuses.get(stageName)
    const status = stageStatus?.status ?? 'pending'

    switch (status) {
      case 'complete':
        completed++
        break
      case 'failed':
      case 'static_fallback':
        failed++
        break
      case 'skipped':
        skipped++
        break
      case 'running':
      case 'synthesizing':
      case 'detecting_conflicts':
        running++
        break
      case 'pending':
        // Pending stages don't contribute to any counter
        break
      default:
        assertNever(status)
    }
  }

  const total = stages.length
  const groupStatus = computeGroupStatus(stages, stageStatuses)
  const progress = computeGroupProgress(stages, stageStatuses)

  return {
    status: groupStatus,
    completed,
    total,
    failed,
    skipped,
    running,
    progress,
  }
}

// ============================================================================
// Hook
// ============================================================================

/**
 * Compute hierarchical group statuses from flat stage status map
 *
 * Groups stages into 7 logical categories with computed status and progress:
 * 1. Core Workflow (3 stages)
 * 2. Content Analysis (7 stages)
 * 3. Tier 1: Universal Agents (4 stages)
 * 4. Tier 2: Validation Agents (4 stages)
 * 5. Tier 3: Research Agents (4 stages)
 * 6. Quality Pipeline (4 stages)
 * 7. Optional Stages (4 stages)
 *
 * @param stageStatuses - Map of stage names to their current status
 * @returns Array of groups with computed statuses, in display order
 *
 * @example
 * ```tsx
 * const groups = useStageGroups(stageStatuses)
 *
 * return groups.map((groupWithStatus) => (
 *   <AccordionItem key={groupWithStatus.group.id}>
 *     <AccordionTrigger>
 *       {groupWithStatus.group.label} - {groupWithStatus.status.progress}%
 *     </AccordionTrigger>
 *     <AccordionContent>
 *       {groupWithStatus.group.stages.map((stage) => (
 *         <StageItem key={stage} name={stage} />
 *       ))}
 *     </AccordionContent>
 *   </AccordionItem>
 * ))
 * ```
 */
export function useStageGroups(
  stageStatuses: Map<StageName, StageStatusEntry>
): StageGroupWithStatus[] {
  return useMemo(() => {
    // Defensive guard: provide empty Map if stageStatuses is undefined
    // This can happen when viewing completed analyses from library
    const safeStatuses = stageStatuses ?? new Map<StageName, StageStatusEntry>()
    return STAGE_GROUPS.map((group) => ({
      group,
      status: computeGroupStatusMeta(group, safeStatuses),
    }))
  }, [stageStatuses])
}

/**
 * Get the group that contains a specific stage
 *
 * @param stageName - The stage to look up
 * @returns The group configuration or undefined if not found
 */
export function useStageGroup(stageName: StageName): StageGroup | undefined {
  return useMemo(() => {
    const groupId = STAGE_TO_GROUP_MAP.get(stageName)
    if (!groupId) return undefined
    return STAGE_GROUPS.find((g) => g.id === groupId)
  }, [stageName])
}
