/**
 * useAnalysisProgress - Transform SSE events into UI-friendly progress data
 *
 * This hook orchestrates 5 composable sub-hooks to transform raw SSE events
 * into structured data for UI components.
 *
 * Architecture (Issue #391):
 * 1. useStageStatusProcessing - Core event processing, builds stage status map
 * 2. useAnalysisMetadata - Extracts metadata, skip reasons, success metrics
 * 3. useProgressSteps - Builds UI-friendly step objects
 * 4. useActivityFeed - Builds agent activity feed
 * 5. useProgressCalculation - Calculates overall progress percentage
 *
 * @module hooks/useAnalysisProgress
 */
import { useEffect, useMemo, useRef } from 'react'

import { isErrorEvent } from '@app-types/sse'
import type { SSEEvent } from '@app-types/sse'
import { selectSetAnalysisMetadata, useSSEStore } from '@stores/sseStore'

import type { AnalysisStage } from '../components/steps/AnalysisProgressCard'
import type { AnalysisStep } from '../components/steps/AnalysisStepList'

import { useActivityFeed } from './useActivityFeed'
import type { AgentActivity } from './useActivityFeed'
import { useAnalysisMetadata } from './useAnalysisMetadata'
import { useProgressCalculation } from './useProgressCalculation'
import { useProgressSteps } from './useProgressSteps'
import { useStageStatusProcessing } from './useStageStatusProcessing'

// ============================================================================
// Exported Types
// ============================================================================

export type ProgressStep = AnalysisStep
export type { AgentActivity }

export interface OverallProgress {
  stage: AnalysisStage
  progress: number
  currentStep: string
  totalSteps: number
  completedSteps: number
  estimatedTimeRemaining?: string
}

export interface AnalysisProgressData {
  overallProgress: OverallProgress
  steps: ProgressStep[]
  activities: AgentActivity[]
  isComplete: boolean
  hasError: boolean
  errorMessage?: string
  artifactId?: string
  traceId?: string // Langfuse trace ID for feedback submission
  hasFailedStages: boolean
  failedStagesCount: number
  analysisMetadata?: {
    title?: string
    contentType?: 'article' | 'video' | 'repo'
    url?: string
    wordCount?: number
  }
  skipReasons?: Record<string, string>
  stageSuccessMetrics?: Map<
    string,
    {
      findingsQuality?: 'high' | 'medium' | 'low'
      coverage?: 'comprehensive' | 'partial' | 'minimal'
      keyInsights?: string[]
    }
  >
}

// ============================================================================
// Main Hook - Orchestrator
// ============================================================================

/**
 * Transforms raw SSE events into structured data for UI components
 *
 * This is the main orchestrator hook that composes 5 sub-hooks:
 * - Stage status processing for core event handling
 * - Metadata extraction for analysis info and skip reasons
 * - Progress steps for step list display
 * - Activity feed for real-time activity stream
 * - Progress calculation for overall percentage
 *
 * @param events - Array of SSE events from the analysis workflow
 * @returns Comprehensive analysis progress data for UI rendering
 *
 * @example
 * ```tsx
 * const { overallProgress, steps, activities, isComplete, artifactId } =
 *   useAnalysisProgress(events)
 *
 * return (
 *   <>
 *     <ProgressBar progress={overallProgress.progress} />
 *     <StepList steps={steps} />
 *     <ActivityFeed activities={activities} />
 *     {isComplete && <CompletionCard artifactId={artifactId} />}
 *   </>
 * )
 * ```
 */
// eslint-disable-next-line max-lines-per-function -- Orchestrator hook composing 5 sub-hooks + store sync
export function useAnalysisProgress(events: SSEEvent[]): AnalysisProgressData {
  // ========================================================================
  // 1. Stage Status Processing - Core event processing
  // ========================================================================
  // Builds stage status map, detects completion, captures artifact/trace IDs
  const { stageStatuses, isComplete, artifactId, traceId, expectedTotalStages } =
    useStageStatusProcessing(events)

  // ========================================================================
  // 2. Metadata Extraction - Analysis metadata and skip info
  // ========================================================================
  // Extracts metadata from extraction stage, skip reasons from supervisor,
  // success metrics from agent completions
  const { analysisMetadata, skipReasons, skippedAgentsInfo, stageSuccessMetrics } =
    useAnalysisMetadata(events)

  // ========================================================================
  // 3. Build Progress Steps - UI-friendly step objects
  // ========================================================================
  // Transforms stage statuses to ProgressStep objects with status mapping,
  // skip reasons, success metrics, and error details
  const steps = useProgressSteps(stageStatuses, skipReasons, stageSuccessMetrics)

  // ========================================================================
  // 4. Build Activity Feed - Agent activity stream
  // ========================================================================
  // Filters and transforms events into AgentActivity objects
  const activities = useActivityFeed(events)

  // ========================================================================
  // 5. Calculate Overall Progress - Progress percentage and status
  // ========================================================================
  // Complex 8-phase calculation based on expected vs actual stages
  const overallProgress = useProgressCalculation(
    stageStatuses,
    steps,
    isComplete,
    expectedTotalStages,
    skippedAgentsInfo
  )

  // ========================================================================
  // 6. Derive Error State - Extract error from error events
  // ========================================================================
  const errorInfo = useMemo(() => {
    const errorEvent = events.find((e) => isErrorEvent(e))
    if (!errorEvent || !isErrorEvent(errorEvent)) {
      return { hasError: false, errorMessage: undefined }
    }
    return {
      hasError: true,
      errorMessage: errorEvent.error ?? errorEvent.details?.error,
    }
  }, [events])

  // ========================================================================
  // 7. Calculate Failed Stages Count
  // ========================================================================
  const { hasFailedStages, failedStagesCount } = useMemo(() => {
    const failedCount = Array.from(stageStatuses.values()).filter(
      (s) => s.status === 'failed'
    ).length
    return { hasFailedStages: failedCount > 0, failedStagesCount: failedCount }
  }, [stageStatuses])

  // ========================================================================
  // 8. Sync to Zustand Store (Issue #396 - Eliminate prop drilling)
  // ========================================================================
  // This enables leaf components (GuideButton, TeachMeButton, etc.) to access
  // derived data directly via selectors instead of through prop chains
  const setAnalysisMetadata = useSSEStore(selectSetAnalysisMetadata)

  // Store previous values to prevent unnecessary store updates
  const prevMetadataRef = useRef<{
    artifactId: string | null
    traceId: string | null
    overallProgress: typeof overallProgress
    hasFailedStages: boolean
    failedStagesCount: number
    analysisMetadata: typeof analysisMetadata
  } | null>(null)

  useEffect(() => {
    const newMetadata = {
      artifactId: artifactId ?? null,
      traceId: traceId ?? null,
      overallProgress,
      hasFailedStages,
      failedStagesCount,
      analysisMetadata: analysisMetadata || undefined,
    }

    // Only update store if values actually changed to prevent infinite loops
    const prevMetadata = prevMetadataRef.current
    if (
      !prevMetadata ||
      prevMetadata.artifactId !== newMetadata.artifactId ||
      prevMetadata.traceId !== newMetadata.traceId ||
      prevMetadata.hasFailedStages !== newMetadata.hasFailedStages ||
      prevMetadata.failedStagesCount !== newMetadata.failedStagesCount ||
      prevMetadata.analysisMetadata !== newMetadata.analysisMetadata ||
      // Deep comparison for overallProgress object
      JSON.stringify(prevMetadata.overallProgress) !== JSON.stringify(newMetadata.overallProgress)
    ) {
      setAnalysisMetadata(newMetadata)
      prevMetadataRef.current = newMetadata
    }
  }, [
    artifactId,
    traceId,
    overallProgress,
    hasFailedStages,
    failedStagesCount,
    analysisMetadata,
    setAnalysisMetadata,
  ])

  // ========================================================================
  // Return Comprehensive Progress Data
  // ========================================================================
  return {
    overallProgress,
    steps,
    activities,
    isComplete,
    hasError: errorInfo.hasError,
    errorMessage: errorInfo.errorMessage,
    artifactId,
    traceId,
    hasFailedStages,
    failedStagesCount,
    analysisMetadata,
    skipReasons,
    stageSuccessMetrics,
  }
}
