/**
 * useProgressCalculation - Extracted progress calculation logic
 *
 * Calculates overall analysis progress based on stage statuses, completion state,
 * and expected total stages. This hook was extracted from the 662-line useAnalysisProgress
 * hook to improve maintainability and testability.
 *
 * Algorithm (8 phases):
 * 1. Count stages by status (completed, skipped, failed, running)
 * 2. Determine total stages (expectedTotalStages OR fallback to TOTAL_STAGES)
 * 3. Calculate "true pending" stages (stages not yet started)
 * 4. Calculate finished stages (expected vs actual)
 * 5. Calculate progress percentage (cap at 99% if failures exist)
 * 6. Determine current UI stage (extracting/analyzing/generating/complete)
 * 7. Calculate current step number for display
 * 8. Build status message with breakdown
 */
import { useMemo } from 'react'

import type { StageName, StageStatus } from '@/schemas/base'

import type { AnalysisStage } from '../components/steps/AnalysisProgressCard'

import {
  STAGE_CONFIG,
  TOTAL_STAGES,
  estimateTimeRemaining,
  getStageNameFromAgentType,
} from './stageConfig'

// ============================================================================
// Types
// ============================================================================

/** Stage status entry containing status, timestamp, and optional details */
export interface StageStatusEntry {
  status: StageStatus
  timestamp: string
  details?: Record<string, unknown>
}

/** Progress step for UI display */
export interface ProgressStep {
  id: string
  title: string
  status: 'pending' | 'running' | 'completed' | 'failed' | 'skipped'
  description: string
  timestamp?: Date
  successMetrics?: {
    findingsQuality?: 'high' | 'medium' | 'low'
    coverage?: 'comprehensive' | 'partial' | 'minimal'
    keyInsights?: string[]
  }
  skipReason?: string
  errorDetails?: {
    error?: string
    errorCode?: string
    processingTime?: number
  }
}

/** Information about skipped agents from supervisor routing */
export interface SkippedAgentsInfo {
  agents: string[]
  selectedAgents?: string[]
}

/** Overall progress calculation result */
export interface OverallProgress {
  stage: AnalysisStage
  progress: number
  currentStep: string
  totalSteps: number
  completedSteps: number
  estimatedTimeRemaining?: string
}

// ============================================================================
// Hook
// ============================================================================

/**
 * Calculate overall analysis progress from stage statuses
 *
 * @param stageStatuses - Map of stage names to status entries
 * @param steps - Array of progress steps for UI display
 * @param isComplete - Whether the analysis has completed
 * @param expectedTotalStages - Expected total stages from backend (for accuracy)
 * @param skippedAgentsInfo - Information about skipped agents from supervisor
 * @returns Overall progress calculation with stage, percentage, and step info
 */
/* eslint-disable max-lines-per-function, max-params, complexity -- Complex progress calculation with 8 phases: count stages by status, determine total stages, calculate pending stages, calculate finished stages, calculate progress percentage (cap at 99% if failures), determine current UI stage, calculate current step number, build status message */
export function useProgressCalculation(
  stageStatuses: Map<StageName, StageStatusEntry>,
  steps: ProgressStep[],
  isComplete: boolean,
  expectedTotalStages?: number,
  skippedAgentsInfo?: SkippedAgentsInfo
): OverallProgress {
  return useMemo(() => {
    // ========================================================================
    // PHASE 1: Count stages by status
    // ========================================================================
    // Only count stages that have actually been processed (exist in stageStatuses map)

    // Guard: Ensure stageStatuses is a Map and has values
    const stageStatusArray = stageStatuses ? Array.from(stageStatuses.values()) : []

    const completedStages = stageStatusArray.filter((s) => s?.status === 'complete').length

    const skippedStages = stageStatusArray.filter((s) => s?.status === 'skipped').length

    const failedStages = stageStatusArray.filter((s) => s?.status === 'failed').length

    const runningStages = stageStatusArray.filter((s) => s?.status === 'running').length

    const runningStage = stageStatuses
      ? Array.from(stageStatuses.entries()).find(([, s]) => s?.status === 'running')
      : undefined

    // ========================================================================
    // PHASE 2: Determine total stages
    // ========================================================================
    // Use expected_total_stages from backend (single source of truth)
    // Fallback to TOTAL_STAGES constant if not provided

    // Guard: Ensure progressTotalStages is a positive number (prevent division by zero)
    const progressTotalStages = Math.max(1, expectedTotalStages ?? TOTAL_STAGES)

    // ========================================================================
    // PHASE 3: Calculate "true pending" stages
    // ========================================================================
    // True pending: stages in STAGE_CONFIG but not in stageStatuses
    // These are stages that haven't started yet (not skipped, not running, not complete, not failed)

    const allStageNames = Object.keys(STAGE_CONFIG) as StageName[]
    // Guard: Ensure stageStatuses exists before calling .has()
    const truePendingStages = allStageNames.filter((stage) => !stageStatuses?.has(stage))
    const truePendingCount = truePendingStages.length

    // ========================================================================
    // PHASE 4: Calculate finished stages (expected vs actual)
    // ========================================================================
    // CRITICAL: Only count stages that were EXPECTED (part of the workflow)
    // Skipped stages that were never selected by supervisor should NOT count toward progress
    // If skippedAgentsInfo is available, only count expected stages. Otherwise, count all finished stages.

    let finishedStages: number

    if (skippedAgentsInfo?.selectedAgents) {
      // We have supervisor info - only count expected stages
      const expectedStages = new Set<StageName>()

      // Always include fixed stages (extraction, embedding, supervisor_routing, aggregation, artifact_generation)
      expectedStages.add('extraction')
      expectedStages.add('embedding')
      expectedStages.add('supervisor_routing')
      expectedStages.add('aggregation')
      expectedStages.add('artifact_generation')

      // Add selected agents to expected stages
      // Map agent types to stage names (e.g., 'tech_comparator' -> 'tech_comparison')
      for (const agentType of skippedAgentsInfo.selectedAgents) {
        const stageName = getStageNameFromAgentType(agentType)
        if (stageName) {
          expectedStages.add(stageName)
        }
      }

      // Count only expected stages that have finished
      // Guard: Ensure stageStatuses exists
      const stageStatusEntries = stageStatuses ? Array.from(stageStatuses.entries()) : []

      const expectedCompletedStages = stageStatusEntries.filter(
        ([stage, status]) => expectedStages.has(stage) && status?.status === 'complete'
      ).length

      const expectedFailedStages = stageStatusEntries.filter(
        ([stage, status]) => expectedStages.has(stage) && status?.status === 'failed'
      ).length

      // Only count EXPECTED stages that have FINISHED (complete, failed)
      // Skipped stages that were never expected don't count
      finishedStages = expectedCompletedStages + expectedFailedStages
    } else {
      // Fallback: No supervisor info available, count all finished stages (old behavior)
      // This maintains backward compatibility with tests and early events
      finishedStages = completedStages + failedStages + skippedStages
    }

    // ========================================================================
    // PHASE 5: Calculate progress percentage
    // ========================================================================
    // Progress = finished / expected_total_stages (not TOTAL_STAGES)
    // This ensures progress reflects actual workflow completion, not just all possible stages
    // Cap at 99% if there are failures, running stages, or unfinished expected stages

    let progress: number

    // Check if truly complete: all expected stages finished, no failures, no running
    // Note: truePendingCount includes stages not in expected workflow (from STAGE_CONFIG but not selected)
    // So we only check if expected stages are finished, not all possible stages
    const allExpectedStagesFinished = finishedStages >= progressTotalStages

    // Only check for pending stages that are part of the expected workflow
    // If isComplete is true, the backend has finished, so pending stages are likely not part of expected workflow
    const hasUnfinishedExpectedStages = runningStages > 0 || (truePendingCount > 0 && !isComplete)

    const isTrulyComplete =
      isComplete && failedStages === 0 && !hasUnfinishedExpectedStages && allExpectedStagesFinished

    if (isTrulyComplete) {
      // Only show 100% if truly complete with no failures and all expected stages finished
      progress = 100
    } else {
      // Calculate actual progress: finished stages / expected_total_stages
      // Guard: Ensure division is safe (progressTotalStages guaranteed >= 1 from Phase 2)
      // Guard: Ensure finishedStages is a number (could be NaN from failed calculations)
      const safeFinishedStages = Number.isFinite(finishedStages) ? finishedStages : 0
      progress = Math.round((safeFinishedStages / progressTotalStages) * 100)

      // Guard: Ensure progress is within valid bounds (0-100)
      progress = Math.max(0, Math.min(100, progress))

      // Cap at 99% if there are failures, running, or unfinished expected stages
      if (failedStages > 0 || hasUnfinishedExpectedStages) {
        progress = Math.min(progress, 99) // Cap at 99% when not fully complete
      }

      // Safety: if finished exceeds expected total but there are unfinished stages, cap at 99%
      if (finishedStages > progressTotalStages && hasUnfinishedExpectedStages) {
        progress = 99
      }
    }

    // ========================================================================
    // PHASE 6: Determine current UI stage
    // ========================================================================
    // CRITICAL: When isComplete is true (artifact generated), always show 'complete' stage
    // This prevents showing "Generating" when analysis is actually done, even if there are failures

    let currentUIStage: AnalysisStage = 'extracting'

    if (isComplete) {
      // Analysis is complete (artifact generated) - always show as complete
      // The completion card will handle showing error state if there are failures
      currentUIStage = 'complete'
    } else if (runningStage) {
      // Currently running a stage
      // Guard: Ensure runningStage exists and has valid structure
      currentUIStage = STAGE_CONFIG[runningStage[0]]?.uiStage || 'analyzing'
    } else if (completedStages > 0) {
      // Some stages completed, show the last completed stage's UI stage
      // Guard: Ensure steps array exists and has elements
      const lastCompleted = steps?.filter((s) => s?.status === 'completed').pop()
      if (lastCompleted?.id) {
        currentUIStage = STAGE_CONFIG[lastCompleted.id as StageName]?.uiStage || 'analyzing'
      }
    }

    // ========================================================================
    // PHASE 7: Calculate current step number
    // ========================================================================
    // Current step: finished stages + 1 if running, else finished
    // Use progressTotalStages (expected_total_stages) as total, not displayTotalStages

    let currentStepNumber: number

    // Guard: Ensure finishedStages is a valid number
    const safeFinishedStages = Number.isFinite(finishedStages) ? finishedStages : 0

    if (runningStage) {
      currentStepNumber = safeFinishedStages + 1 // Currently running a stage
    } else if (isComplete && failedStages === 0 && !hasUnfinishedExpectedStages) {
      currentStepNumber = progressTotalStages // Fully complete - show expected total
    } else {
      currentStepNumber = safeFinishedStages + 1 // Next step to be processed
    }

    // CRITICAL: Cap at progressTotalStages (not displayTotalStages) to fix "Step 10 of 9" issue
    // Guard: Ensure currentStepNumber is within valid bounds (1 to progressTotalStages)
    currentStepNumber = Math.max(1, Math.min(currentStepNumber, progressTotalStages))

    // ========================================================================
    // PHASE 8: Build status message
    // ========================================================================
    // Enhanced status messages with detailed breakdown of completed/failed/skipped/running/pending stages

    const buildStatusMessage = (): string => {
      // Check if truly complete (same logic as progress calculation)
      if (isComplete && failedStages === 0 && !hasUnfinishedExpectedStages) {
        return 'Analysis Complete'
      }

      if (runningStage) {
        return STAGE_CONFIG[runningStage[0]]?.title || 'Processing...'
      }

      // Build detailed status with counts
      const parts: string[] = []
      if (completedStages > 0) {
        parts.push(`${completedStages} completed`)
      }
      if (failedStages > 0) {
        parts.push(`${failedStages} failed`)
      }
      if (skippedStages > 0) {
        parts.push(`${skippedStages} skipped`)
      }
      if (runningStages > 0) {
        parts.push(`${runningStages} running`)
      }
      if (truePendingCount > 0) {
        parts.push(`${truePendingCount} pending`)
      }

      if (parts.length > 0) {
        const statusText = parts.join(', ')
        // Add "with errors" suffix if there are failures
        if (failedStages > 0) {
          return `${statusText} (with errors)`
        }
        return statusText
      }

      return 'Waiting to start...'
    }

    const currentStepName = buildStatusMessage()

    // ========================================================================
    // Return overall progress
    // ========================================================================
    return {
      stage: currentUIStage,
      progress,
      currentStep: currentStepName,
      totalSteps: progressTotalStages, // Use expected_total_stages for "Step X of Y" display
      completedSteps: currentStepNumber, // Current step number for "Step X of Y" display
      // Guard: Pass safeFinishedStages to estimateTimeRemaining to prevent issues
      estimatedTimeRemaining: isComplete ? undefined : estimateTimeRemaining(safeFinishedStages),
    }
  }, [stageStatuses, steps, isComplete, expectedTotalStages, skippedAgentsInfo])
}
