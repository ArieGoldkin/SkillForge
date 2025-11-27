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

import type { SSEEvent } from '@app-types/sse'
import type { AnalysisStep, AnalysisStepStatus } from '../components/steps/AnalysisStepList'
import type { AgentActivity } from '../components/activity/AgentActivityFeed'
import { isProgressEvent, isCompleteEvent, isErrorEvent } from '@app-types/sse'
import type { StageName, StageStatus } from '@app-types/sse'
import type { AnalysisStage } from '../components/steps/AnalysisProgressCard'

/**
 * Stage configuration mapping backend stages to UI representation
 */
const STAGE_CONFIG: Record<StageName, { title: string; order: number; uiStage: AnalysisStage }> = {
  extraction: { title: 'Content Extraction', order: 1, uiStage: 'extracting' },
  supervisor_routing: { title: 'Routing to Agents', order: 2, uiStage: 'processing' },
  tech_comparison: { title: 'Tech Comparison', order: 3, uiStage: 'analyzing' },
  security_audit: { title: 'Security Audit', order: 4, uiStage: 'analyzing' },
  implementation_planning: { title: 'Implementation Planning', order: 5, uiStage: 'analyzing' },
  performance_audit: { title: 'Performance Audit', order: 6, uiStage: 'analyzing' },
  code_quality_audit: { title: 'Code Quality Audit', order: 7, uiStage: 'analyzing' },
  trends_analysis: { title: 'Trends Analysis', order: 8, uiStage: 'analyzing' },
  dependencies_analysis: { title: 'Dependencies Analysis', order: 9, uiStage: 'analyzing' },
  aggregation: { title: 'Aggregating Results', order: 10, uiStage: 'generating' },
  artifact_generation: { title: 'Generating Report', order: 11, uiStage: 'generating' },
}

const TOTAL_STAGES = Object.keys(STAGE_CONFIG).length

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

/**
 * Map backend stage status to UI step status
 */
function mapStageStatus(status: StageStatus): AnalysisStepStatus {
  switch (status) {
    case 'complete':
      return 'completed'
    case 'running':
      return 'in-progress'
    case 'failed':
      return 'failed'
    default:
      return 'pending'
  }
}

/**
 * Get description for a stage based on its status
 */
function getStageDescription(
  stage: StageName,
  status: StageStatus,
  details?: Record<string, unknown>
): string {
  if (status === 'complete') {
    if (stage === 'extraction' && details?.word_count) {
      return `Extracted ${details.word_count} words`
    }
    return 'Completed'
  }
  if (status === 'running') {
    if (details?.agent) {
      return `Running ${details.agent}...`
    }
    return 'Processing...'
  }
  if (status === 'failed') {
    return 'Failed'
  }
  return 'Waiting...'
}

/**
 * Generate agent name from stage
 */
function getAgentName(stage: StageName, details?: Record<string, unknown>): string {
  if (details?.agent && typeof details.agent === 'string') {
    // Format agent name: snake_case -> Title Case
    return details.agent
      .split('_')
      .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
      .join(' ')
  }

  // Default agent names based on stage
  const agentNames: Record<StageName, string> = {
    extraction: 'Content Extractor',
    supervisor_routing: 'Supervisor',
    tech_comparison: 'Tech Comparator',
    security_audit: 'Security Auditor',
    implementation_planning: 'Implementation Planner',
    performance_audit: 'Performance Auditor',
    code_quality_audit: 'Code Quality Reviewer',
    trends_analysis: 'Trends Analyst',
    dependencies_analysis: 'Dependencies Analyzer',
    aggregation: 'Aggregator',
    artifact_generation: 'Report Generator',
  }

  return agentNames[stage] || 'Agent'
}

/**
 * Generate action description from event
 */
function getActionDescription(
  stage: StageName,
  status: StageStatus,
  details?: Record<string, unknown>
): string {
  if (status === 'running') {
    const actions: Record<StageName, string> = {
      extraction: 'Extracting content from URL...',
      supervisor_routing: 'Routing analysis to specialized agents...',
      tech_comparison: 'Comparing technology patterns...',
      security_audit: 'Auditing security considerations...',
      implementation_planning: 'Planning implementation steps...',
      performance_audit: 'Analyzing performance patterns...',
      code_quality_audit: 'Reviewing code quality...',
      trends_analysis: 'Analyzing technology trends...',
      dependencies_analysis: 'Analyzing dependencies...',
      aggregation: 'Aggregating agent results...',
      artifact_generation: 'Generating implementation guide...',
    }
    return actions[stage] || 'Processing...'
  }

  if (status === 'complete') {
    if (stage === 'extraction' && details?.word_count) {
      return `Extracted ${details.word_count} words from content`
    }
    if (stage === 'artifact_generation' && details?.artifact_id) {
      return 'Generated implementation guide'
    }
    return `Completed ${STAGE_CONFIG[stage]?.title || stage}`
  }

  return `Started ${STAGE_CONFIG[stage]?.title || stage}`
}

/**
 * useAnalysisProgress hook
 *
 * Transforms raw SSE events into structured data for UI components
 */
export function useAnalysisProgress(events: SSEEvent[]): AnalysisProgressData {
  return useMemo(() => {
    // Track stage statuses
    const stageStatuses = new Map<
      StageName,
      { status: StageStatus; timestamp: string; details?: Record<string, unknown> }
    >()
    let isComplete = false
    let hasError = false
    let errorMessage: string | undefined

    // Process events to build stage status map
    for (const event of events) {
      if (isProgressEvent(event) || isCompleteEvent(event)) {
        stageStatuses.set(event.stage as StageName, {
          status: event.status,
          timestamp: event.timestamp,
          details: event.details,
        })

        if (isCompleteEvent(event)) {
          isComplete = true
        }
      }

      if (isErrorEvent(event)) {
        hasError = true
        errorMessage = event.details.error
      }
    }

    // Build steps array
    const steps: ProgressStep[] = Object.entries(STAGE_CONFIG)
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

    // Build activities array (from events, most recent first)
    const activities: AgentActivity[] = events
      .filter((event) => isProgressEvent(event) || isCompleteEvent(event))
      .map((event, index) => ({
        id: `${event.stage}-${index}`,
        agentName: getAgentName(event.stage as StageName, event.details),
        action: getActionDescription(event.stage as StageName, event.status, event.details),
        timestamp: new Date(event.timestamp),
      }))
      .reverse()

    // Calculate overall progress
    const completedStages = Array.from(stageStatuses.values()).filter(
      (s) => s.status === 'complete'
    ).length
    const runningStage = Array.from(stageStatuses.entries()).find(([, s]) => s.status === 'running')
    const progress = Math.round((completedStages / TOTAL_STAGES) * 100)

    // Determine current UI stage
    let currentUIStage: AnalysisStage = 'extracting'
    if (isComplete) {
      currentUIStage = 'complete'
    } else if (runningStage) {
      currentUIStage = STAGE_CONFIG[runningStage[0] as StageName]?.uiStage || 'analyzing'
    } else if (completedStages > 0) {
      // Find the last completed stage to determine current phase
      const lastCompleted = steps.filter((s) => s.status === 'completed').pop()
      if (lastCompleted) {
        currentUIStage = STAGE_CONFIG[lastCompleted.id as StageName]?.uiStage || 'analyzing'
      }
    }

    // Get current step description
    const currentStepName = runningStage
      ? STAGE_CONFIG[runningStage[0] as StageName]?.title
      : isComplete
        ? 'Analysis Complete'
        : 'Waiting to start...'

    const overallProgress: OverallProgress = {
      stage: currentUIStage,
      progress: isComplete ? 100 : progress,
      currentStep: currentStepName,
      totalSteps: TOTAL_STAGES,
      completedSteps: completedStages,
      estimatedTimeRemaining: isComplete ? undefined : estimateTimeRemaining(completedStages),
    }

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

/**
 * Estimate remaining time based on completed stages
 */
function estimateTimeRemaining(completedStages: number): string | undefined {
  if (completedStages === 0) {
    return '~2-3 minutes'
  }
  const remaining = TOTAL_STAGES - completedStages
  if (remaining <= 2) {
    return '~30 seconds'
  }
  if (remaining <= 5) {
    return '~1 minute'
  }
  return '~1-2 minutes'
}
