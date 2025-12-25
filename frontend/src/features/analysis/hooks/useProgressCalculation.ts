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
import { STAGE_CONFIG, getStageNameFromAgentType } from '../config/stageRegistry'

import { TOTAL_STAGES, estimateTimeRemaining } from './stageConfig'

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
  // Accepts both 'running' (from SSE) and 'in-progress' (UI display)
  status: 'pending' | 'running' | 'in-progress' | 'completed' | 'failed' | 'skipped'
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

      // Only count EXPECTED stages that have FINISHED (complete, skipped)
      // Failed stages are tracked separately for error display, not counted toward progress
      // Skipped stages that were never expected don't count
      const expectedSkippedStages = stageStatusEntries.filter(
        ([stage, status]) => expectedStages.has(stage) && status?.status === 'skipped'
      ).length
      finishedStages = expectedCompletedStages + expectedSkippedStages
    } else {
      // Fallback: No supervisor info available, count all finished stages
      // Failed stages are tracked separately for error display, not counted toward progress
      finishedStages = completedStages + skippedStages
    }

    // ========================================================================
    // PHASE 5: Calculate progress percentage (Issue #439: Display-only)
    // ========================================================================
    // IMPORTANT: Progress % is for UI DISPLAY ONLY, not completion gating.
    // Completion is determined by artifact existence (see AnalyzeResult.tsx).
    //
    // When isComplete is true: The backend has finished and artifact exists.
    // We show 100% to align with the completion state, regardless of stage counts.
    // This prevents the desync where 0% progress shows alongside "Complete" badge.

    let progress: number

    if (isComplete) {
      // Issue #439: Backend says complete → show 100% for consistent UI
      // The artifact exists, so the analysis is done regardless of stage counts.
      // hasFailedStages is handled separately in the completion card (error badge).
      progress = 100
    } else {
      // In-progress: Calculate actual progress from finished stages
      // Guard: Ensure division is safe (progressTotalStages guaranteed >= 1 from Phase 2)
      const safeFinishedStages = Number.isFinite(finishedStages) ? finishedStages : 0
      progress = Math.round((safeFinishedStages / progressTotalStages) * 100)

      // Guard: Ensure progress is within valid bounds (0-99 while in progress)
      progress = Math.max(0, Math.min(99, progress))
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

    if (isComplete) {
      // Issue #439: When complete, show expected total (artifact exists)
      currentStepNumber = progressTotalStages
    } else if (runningStage) {
      currentStepNumber = safeFinishedStages + 1 // Currently running a stage
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
      // Issue #439: When isComplete is true, artifact exists → analysis done
      // The completion card handles showing "Complete with Errors" badge
      if (isComplete) {
        return failedStages > 0 ? 'Analysis Complete (with errors)' : 'Analysis Complete'
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
      // Guard: Pass safeFinishedStages and progressTotalStages to estimateTimeRemaining
      // Issue #443: Use dynamic totalStages from backend for accurate time estimation
      estimatedTimeRemaining: isComplete
        ? undefined
        : estimateTimeRemaining(safeFinishedStages, progressTotalStages),
    }
  }, [stageStatuses, steps, isComplete, expectedTotalStages, skippedAgentsInfo])
}
