/**
 * useAnalysisProgress - Transform SSE events into UI-friendly progress data
 *
 * Processes raw SSE events from the backend and provides:
 * - Overall progress calculation
 * - Step-by-step status tracking
 * - Agent activity feed data
 * - Current stage information
 */

import { useMemo } from 'react'

import { isProgressEvent, isCompleteEvent, isErrorEvent } from '@app-types/sse'
import type { SSEEvent, StageName } from '@app-types/sse'

import type { AgentActivity } from '../components/activity/AgentActivityFeed'
import type { AnalysisStage } from '../components/steps/AnalysisProgressCard'
import type { AnalysisStep } from '../components/steps/AnalysisStepList'

import {
  STAGE_CONFIG,
  TOTAL_STAGES,
  estimateTimeRemaining,
  normalizeStageNameFromBackend,
} from './stageConfig'
import {
  mapStageStatus,
  getStageDescription,
  getAgentName,
  getActionDescription,
} from './stageHelpers'

/**
 * Re-export types for backwards compatibility
 */
export type ProgressStep = AnalysisStep
export type { AgentActivity }

/**
 * Overall progress data for AnalysisProgressCard
 */
export interface OverallProgress {
  stage: AnalysisStage
  progress: number
  currentStep: string
  totalSteps: number
  completedSteps: number
  estimatedTimeRemaining?: string
}

/**
 * Return type for useAnalysisProgress hook
 */
export interface AnalysisProgressData {
  overallProgress: OverallProgress
  steps: ProgressStep[]
  activities: AgentActivity[]
  isComplete: boolean
  hasError: boolean
  errorMessage?: string
}

interface ProcessedEvents {
  isComplete: boolean
  hasError: boolean
  errorMessage?: string
  stageStatuses: Map<
    StageName,
    {
      status: 'pending' | 'running' | 'complete' | 'failed'
      timestamp: string
      details?: Record<string, unknown>
    }
  >
}

function processEvents(events: SSEEvent[]): ProcessedEvents {
  const stageStatuses = new Map<
    StageName,
    {
      status: 'pending' | 'running' | 'complete' | 'failed'
      timestamp: string
      details?: Record<string, unknown>
    }
  >()
  let isComplete = false
  let hasError = false
  let errorMessage: string | undefined

  for (const event of events) {
    if (isProgressEvent(event) || isCompleteEvent(event)) {
      // Normalize backend stage/agent name to frontend stage name
      const normalizedStage = normalizeStageNameFromBackend(event.stage)

      if (normalizedStage) {
        stageStatuses.set(normalizedStage, {
          status: event.status,
          timestamp: event.timestamp,
          details: event.details,
        })
      }

      if (isCompleteEvent(event)) {
        isComplete = true
      }
    }

    if (isErrorEvent(event)) {
      hasError = true
      errorMessage = event.details.error
    }
  }

  return { isComplete, hasError, errorMessage, stageStatuses }
}

function buildSteps(stageStatuses: ProcessedEvents['stageStatuses']): ProgressStep[] {
  return Object.entries(STAGE_CONFIG)
    .sort(([, a], [, b]) => a.order - b.order)
    .map(([stageName, config]) => {
      const stageData = stageStatuses.get(stageName as StageName)
      return {
        id: stageName,
        title: config.title,
        status: stageData ? mapStageStatus(stageData.status) : 'pending',
        description: stageData
          ? getStageDescription(stageName as StageName, stageData.status, stageData.details)
          : 'Waiting...',
        timestamp: stageData ? new Date(stageData.timestamp) : undefined,
      }
    })
}

function buildActivities(events: SSEEvent[]): AgentActivity[] {
  return events
    .filter((event) => isProgressEvent(event) || isCompleteEvent(event))
    .map((event, index) => {
      const normalizedStage = normalizeStageNameFromBackend(event.stage)
      return {
        id: `${event.stage}-${index}`,
        agentName: normalizedStage ? getAgentName(normalizedStage, event.details) : event.stage,
        action: normalizedStage
          ? getActionDescription(normalizedStage, event.status, event.details)
          : `${event.status}`,
        timestamp: new Date(event.timestamp),
      }
    })
    .reverse()
}

function calculateOverallProgress(
  stageStatuses: ProcessedEvents['stageStatuses'],
  steps: ProgressStep[],
  isComplete: boolean
): OverallProgress {
  const completedStages = Array.from(stageStatuses.values()).filter(
    (s) => s.status === 'complete'
  ).length
  const runningStage = Array.from(stageStatuses.entries()).find(([, s]) => s.status === 'running')
  const progress = Math.round((completedStages / TOTAL_STAGES) * 100)

  let currentUIStage: AnalysisStage = 'extracting'
  if (isComplete) {
    currentUIStage = 'complete'
  } else if (runningStage) {
    currentUIStage = STAGE_CONFIG[runningStage[0] as StageName]?.uiStage || 'analyzing'
  } else if (completedStages > 0) {
    const lastCompleted = steps.filter((s) => s.status === 'completed').pop()
    if (lastCompleted) {
      currentUIStage = STAGE_CONFIG[lastCompleted.id as StageName]?.uiStage || 'analyzing'
    }
  }

  const currentStepName = runningStage
    ? STAGE_CONFIG[runningStage[0] as StageName]?.title
    : isComplete
      ? 'Analysis Complete'
      : 'Waiting to start...'

  return {
    stage: currentUIStage,
    progress: isComplete ? 100 : progress,
    currentStep: currentStepName,
    totalSteps: TOTAL_STAGES,
    completedSteps: completedStages,
    estimatedTimeRemaining: isComplete ? undefined : estimateTimeRemaining(completedStages),
  }
}

/**
 * useAnalysisProgress hook
 *
 * Transforms raw SSE events into structured data for UI components
 */
export function useAnalysisProgress(events: SSEEvent[]): AnalysisProgressData {
  return useMemo(() => {
    const { isComplete, hasError, errorMessage, stageStatuses } = processEvents(events)
    const steps = buildSteps(stageStatuses)
    const activities = buildActivities(events)
    const overallProgress = calculateOverallProgress(stageStatuses, steps, isComplete)

    return {
      overallProgress,
      steps,
      activities,
      isComplete,
      hasError,
      errorMessage,
    }
  }, [events])
}
