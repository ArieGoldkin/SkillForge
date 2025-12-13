/**
 * useAnalysisProgress - Transform SSE events into UI-friendly progress data
 */
import { useMemo } from 'react'

import { isProgressEvent, isCompleteEvent, isErrorEvent } from '@app-types/sse'
import type { SSEEvent, AgentStageName } from '@app-types/sse'

import type { AgentActivity } from '../components/activity/AgentActivityFeed'
import type { AnalysisStage } from '../components/steps/AnalysisProgressCard'
import type { AnalysisStep } from '../components/steps/AnalysisStepList'

import {
  STAGE_CONFIG,
  TOTAL_STAGES,
  estimateTimeRemaining,
  normalizeStageNameFromBackend,
  isAgentStage,
  markSkippedAgents,
  type StageStatusEntry,
} from './stageConfig'
import {
  mapStageStatus,
  getStageDescription,
  getAgentName,
  getActionDescription,
} from './stageHelpers'

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
}

interface ProcessedEvents {
  isComplete: boolean
  hasError: boolean
  errorMessage?: string
  artifactId?: string
  stageStatuses: Map<AgentStageName, StageStatusEntry>
}

function processEvent(
  event: SSEEvent,
  stageStatuses: Map<AgentStageName, StageStatusEntry>,
  state: { isComplete: boolean; artifactId?: string }
): void {
  if (isProgressEvent(event) || isCompleteEvent(event)) {
    const normalizedStage = normalizeStageNameFromBackend(event.stage)
    if (normalizedStage && isAgentStage(normalizedStage)) {
      stageStatuses.set(normalizedStage, {
        status: event.status,
        timestamp: event.timestamp,
        details: event.details,
      })
    }
    // Handle completion: workflow or artifact_generation complete marks analysis done
    if (isCompleteEvent(event)) {
      if (event.stage === 'workflow' || event.stage === 'artifact_generation') {
        state.isComplete = true
      }
      // Capture artifact_id from either workflow or artifact_generation
      if (event.artifact_id) {
        state.artifactId = event.artifact_id
      }
    }
  }
}

function processEvents(events: SSEEvent[]): ProcessedEvents {
  const stageStatuses = new Map<AgentStageName, StageStatusEntry>()
  const state = { isComplete: false, artifactId: undefined as string | undefined }
  let hasError = false
  let errorMessage: string | undefined

  for (const event of events) {
    processEvent(event, stageStatuses, state)
    if (isErrorEvent(event)) {
      hasError = true
      errorMessage = event.error ?? event.details?.error
    }
  }
  markSkippedAgents(stageStatuses)
  return { ...state, hasError, errorMessage, stageStatuses }
}

function buildSteps(stageStatuses: ProcessedEvents['stageStatuses']): ProgressStep[] {
  return Object.entries(STAGE_CONFIG)
    .sort(([, a], [, b]) => a.order - b.order)
    .map(([stageName, config]) => {
      const stageData = stageStatuses.get(stageName as AgentStageName)
      return {
        id: stageName,
        title: config.title,
        status: stageData ? mapStageStatus(stageData.status) : 'pending',
        description: stageData
          ? getStageDescription(stageName as AgentStageName, stageData.status, stageData.details)
          : 'Waiting...',
        timestamp: stageData ? new Date(stageData.timestamp) : undefined,
      }
    })
}

function buildActivities(events: SSEEvent[]): AgentActivity[] {
  return events
    .filter((e) => isProgressEvent(e) || isCompleteEvent(e))
    .map((event, index) => {
      const stage = normalizeStageNameFromBackend(event.stage)
      const isAgent = stage && isAgentStage(stage)
      return {
        id: `${event.stage}-${index}`,
        agentName: isAgent ? getAgentName(stage, event.details) : event.stage,
        action: isAgent ? getActionDescription(stage, event.status, event.details) : event.status,
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
    (s) => s.status === 'complete' || s.status === 'skipped'
  ).length
  const runningStage = Array.from(stageStatuses.entries()).find(([, s]) => s.status === 'running')
  const progress = Math.round((completedStages / TOTAL_STAGES) * 100)

  let currentUIStage: AnalysisStage = 'extracting'
  if (isComplete) {
    currentUIStage = 'complete'
  } else if (runningStage) {
    currentUIStage = STAGE_CONFIG[runningStage[0]]?.uiStage || 'analyzing'
  } else if (completedStages > 0) {
    const lastCompleted = steps.filter((s) => s.status === 'completed').pop()
    if (lastCompleted) {
      currentUIStage = STAGE_CONFIG[lastCompleted.id as AgentStageName]?.uiStage || 'analyzing'
    }
  }

  const currentStepName = runningStage
    ? STAGE_CONFIG[runningStage[0]]?.title
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

/** Transforms raw SSE events into structured data for UI components */
export function useAnalysisProgress(events: SSEEvent[]): AnalysisProgressData {
  return useMemo(() => {
    const { isComplete, hasError, errorMessage, artifactId, stageStatuses } = processEvents(events)
    const steps = buildSteps(stageStatuses)
    const activities = buildActivities(events)
    const overallProgress = calculateOverallProgress(stageStatuses, steps, isComplete)
    return { overallProgress, steps, activities, isComplete, hasError, errorMessage, artifactId }
  }, [events])
}
