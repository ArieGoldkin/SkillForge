/**
 * useAnalysisProgress - Transform SSE events into UI-friendly progress data
 */
/* eslint-disable max-lines -- Hook processes complex SSE events and builds comprehensive progress data with metadata, skip reasons, and success metrics */
import { useMemo } from 'react'

import { isProgressEvent, isCompleteEvent, isErrorEvent } from '@app-types/sse'
import type { SSEEvent, SSEProgressEvent, StageName } from '@app-types/sse'

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
  getStageNameFromAgentType,
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
  hasFailedStages: boolean // NEW: Indicates if any stages failed
  failedStagesCount: number // NEW: Count of failed stages
  analysisMetadata?: {
    title?: string
    contentType?: 'article' | 'video' | 'repo'
    url?: string
    wordCount?: number
  }
  skipReasons?: Record<string, string> // agent_type -> reason
  stageSuccessMetrics?: Map<
    string,
    {
      findingsQuality?: 'high' | 'medium' | 'low'
      coverage?: 'comprehensive' | 'partial' | 'minimal'
      keyInsights?: string[]
    }
  >
}

interface ProcessedEvents {
  isComplete: boolean
  hasError: boolean
  errorMessage?: string
  artifactId?: string
  expectedTotalStages?: number
  stageStatuses: Map<StageName, StageStatusEntry>
  skippedAgentsInfo?: { agents: string[]; selectedAgents?: string[] }
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

/* eslint-disable max-lines-per-function, complexity -- Function processes multiple event types (progress, complete, error) with different extraction logic for metadata, skip reasons, success metrics, and error details */
function processEvent(
  event: SSEEvent,
  stageStatuses: Map<StageName, StageStatusEntry>,
  state: { isComplete: boolean; artifactId?: string; expectedTotalStages?: number }
): void {
  if (isProgressEvent(event) || isCompleteEvent(event)) {
    const normalizedStage = normalizeStageNameFromBackend(event.stage)
    if (normalizedStage && isAgentStage(normalizedStage)) {
      const existingStatus = stageStatuses.get(normalizedStage)

      // Don't overwrite failed status with later events (e.g., complete events)
      if (existingStatus?.status === 'failed' && event.status !== 'failed') {
        // Preserve failed status - don't overwrite
        return
      }

      // Merge details from event (including new fields like findings_summary, insights_count, error details, success_metrics)
      const eventDetails = isProgressEvent(event)
        ? {
            ...event.details,
            findings_summary: event.findings_summary ?? event.details?.findings_summary,
            insights_count: event.insights_count ?? event.details?.insights_count,
            confidence_score: event.confidence_score ?? event.details?.confidence_score,
            // Extract error details for failed progress events (only from details)
            error: event.details?.error,
            error_code: event.details?.error_code,
            processing_time_ms: event.details?.processing_time_ms,
            // Extract success_metrics for completed events
            success_metrics: event.success_metrics ?? event.details?.success_metrics,
          }
        : event.details
      stageStatuses.set(normalizedStage, {
        status: event.status,
        timestamp: event.timestamp,
        details: eventDetails,
      })
    }
    // Capture expected_total_stages from supervisor event
    if (isProgressEvent(event) && event.stage === 'supervisor_routing') {
      const expectedStages = event.expected_total_stages ?? event.details?.expected_total_stages
      if (expectedStages !== undefined) {
        state.expectedTotalStages = expectedStages
      }
    }
    // Handle completion: workflow or artifact_generation complete marks analysis done
    // Backend sends both 'complete' event type AND 'progress' events with status='complete'
    const isCompletionEvent =
      isCompleteEvent(event) ||
      (isProgressEvent(event) &&
        event.status === 'complete' &&
        (event.stage === 'workflow' || event.stage === 'artifact_generation'))

    if (isCompletionEvent) {
      state.isComplete = true
      // Capture artifact_id from either workflow or artifact_generation
      const artifactId = isCompleteEvent(event)
        ? event.artifact_id
        : isProgressEvent(event)
          ? (event.details?.artifact_id as string | undefined)
          : undefined
      if (artifactId) {
        state.artifactId = artifactId
      }
    }
  }

  // Handle error events to capture failed status
  if (isErrorEvent(event)) {
    const normalizedStage = normalizeStageNameFromBackend(event.stage)
    if (normalizedStage && isAgentStage(normalizedStage)) {
      // Only update if status is not already set (preserve failed status)
      const existingStatus = stageStatuses.get(normalizedStage)
      if (!existingStatus || existingStatus.status !== 'failed') {
        stageStatuses.set(normalizedStage, {
          status: 'failed',
          timestamp: event.timestamp,
          details: {
            error: event.error ?? event.details?.error,
            error_code: event.details?.error_code,
            ...event.details,
          },
        })
      }
    }
  }
}

/* eslint-disable max-lines-per-function, complexity -- Function processes all SSE events, extracts metadata, skip reasons, success metrics, and builds stage status map with complex conditional logic */
function processEvents(events: SSEEvent[]): ProcessedEvents {
  const stageStatuses = new Map<StageName, StageStatusEntry>()
  const state = {
    isComplete: false,
    artifactId: undefined as string | undefined,
    expectedTotalStages: undefined as number | undefined,
  }
  let hasError = false
  let errorMessage: string | undefined
  let skippedAgentsInfo: { agents: string[]; selectedAgents?: string[] } | undefined
  let analysisMetadata: ProcessedEvents['analysisMetadata']
  let skipReasons: Record<string, string> | undefined
  const stageSuccessMetrics = new Map<
    string,
    {
      findingsQuality?: 'high' | 'medium' | 'low'
      coverage?: 'comprehensive' | 'partial' | 'minimal'
      keyInsights?: string[]
    }
  >()

  for (const event of events) {
    processEvent(event, stageStatuses, state)

    // Capture analysis metadata from extraction event
    if (isProgressEvent(event) && event.stage === 'extraction' && event.status === 'complete') {
      const metadata = event.analysis_metadata || event.details?.analysis_metadata
      if (metadata) {
        analysisMetadata = {
          title: metadata.title,
          contentType: metadata.content_type,
          url: metadata.url,
          wordCount: metadata.word_count,
        }
      }
    }

    // Capture skipped agents info and skip reasons from supervisor event
    if (
      isProgressEvent(event) &&
      event.stage === 'supervisor_routing' &&
      event.status === 'complete'
    ) {
      // Access fields that may be at top level or in details (SSE event structure)
      const skippedAgents =
        event.details?.skipped_agents ||
        (event as SSEProgressEvent & { skipped_agents?: string[] }).skipped_agents
      const selectedAgents =
        event.details?.selected_agents ||
        (event as SSEProgressEvent & { selected_agents?: string[] }).selected_agents
      if (skippedAgents && Array.isArray(skippedAgents)) {
        skippedAgentsInfo = {
          agents: skippedAgents,
          selectedAgents: selectedAgents as string[] | undefined,
        }
      }
      // Capture skip reasons
      const reasons =
        (event as SSEProgressEvent & { skip_reasons?: Record<string, string> }).skip_reasons ||
        event.details?.skip_reasons
      if (reasons && typeof reasons === 'object') {
        skipReasons = reasons as Record<string, string>
      }
    }

    // Capture success metrics from agent completion events
    if (
      isProgressEvent(event) &&
      event.status === 'complete' &&
      event.stage !== 'extraction' &&
      event.stage !== 'embedding' &&
      event.stage !== 'supervisor_routing' &&
      event.stage !== 'aggregation' &&
      event.stage !== 'artifact_generation'
    ) {
      const metrics =
        (
          event as SSEProgressEvent & {
            success_metrics?: {
              findings_quality?: string
              coverage?: string
              key_insights?: string[]
            }
          }
        ).success_metrics || event.details?.success_metrics
      if (metrics && typeof metrics === 'object') {
        const normalizedStage = normalizeStageNameFromBackend(event.stage)
        if (normalizedStage) {
          stageSuccessMetrics.set(normalizedStage, {
            findingsQuality: metrics.findings_quality,
            coverage: metrics.coverage,
            keyInsights: metrics.key_insights,
          })
        }
      }
    }

    if (isErrorEvent(event)) {
      hasError = true
      errorMessage = event.error ?? event.details?.error
    }
  }
  markSkippedAgents(stageStatuses, skippedAgentsInfo)
  return {
    ...state,
    hasError,
    errorMessage,
    stageStatuses,
    skippedAgentsInfo,
    analysisMetadata,
    skipReasons,
    stageSuccessMetrics: stageSuccessMetrics.size > 0 ? stageSuccessMetrics : undefined,
  }
}

/* eslint-disable max-lines-per-function -- Function builds step objects with success metrics, skip reasons, and error details extraction */
function buildSteps(
  stageStatuses: ProcessedEvents['stageStatuses'],
  skipReasons?: Record<string, string>,
  stageSuccessMetrics?: Map<
    string,
    {
      findingsQuality?: 'high' | 'medium' | 'low'
      coverage?: 'comprehensive' | 'partial' | 'minimal'
      keyInsights?: string[]
    }
  >
): ProgressStep[] {
  // Build reverse map: stage name -> agent type (for skip reasons lookup)
  // Use AGENT_TO_STAGE_MAP in reverse
  // Note: implementation_planning stage is used by BOTH implementation_planner AND integration_feasibility agents
  const STAGE_TO_AGENT_MAP: Record<StageName, string> = {
    tech_comparison: 'tech_comparator',
    security_audit: 'security_auditor',
    implementation_planning: 'implementation_planner', // Also used by integration_feasibility agent
    performance_audit: 'performance_analyst',
    code_quality_audit: 'code_quality_critic',
    trends_analysis: 'trend_validator',
    dependencies_analysis: 'dependency_mapper',
    extraction: 'extraction',
    embedding: 'embedding',
    supervisor_routing: 'supervisor_routing',
    aggregation: 'aggregation',
    artifact_generation: 'artifact_generation',
    quality_validation: 'quality_validation',
    chunking: 'chunking',
    workflow: 'workflow',
    pattern_comparison: 'pattern_comparison',
    metrics: 'metrics',
  }

  return Object.entries(STAGE_CONFIG)
    .sort(([, a], [, b]) => a.order - b.order)
    .map(([stageName, config]) => {
      const stageData = stageStatuses.get(stageName as StageName)
      const agentStageName = stageName as StageName
      const agentType = STAGE_TO_AGENT_MAP[agentStageName]

      // Get skip reason if stage is skipped
      // First check details.skip_reason (from markSkippedAgents), then skipReasons dict
      const skipReason =
        stageData?.status === 'skipped'
          ? (stageData.details?.skip_reason as string | undefined) ||
            (skipReasons && agentType ? skipReasons[agentType] : undefined) ||
            'Not selected by supervisor'
          : undefined

      // Get success metrics if stage is complete
      const successMetrics =
        stageData?.status === 'complete' && stageSuccessMetrics
          ? stageSuccessMetrics.get(agentStageName)
          : undefined

      // Get error details if stage failed
      const errorDetails =
        stageData?.status === 'failed' && stageData.details
          ? {
              error:
                (stageData.details.error as string) ||
                (stageData.details.error_code as string) ||
                'Unknown error',
              errorCode: stageData.details.error_code as string | undefined,
              processingTime: stageData.details.processing_time_ms as number | undefined,
            }
          : undefined

      return {
        id: stageName,
        title: config.title,
        status: stageData ? mapStageStatus(stageData.status) : 'pending',
        description: stageData
          ? getStageDescription(agentStageName, stageData.status, stageData.details)
          : 'Waiting...',
        timestamp: stageData ? new Date(stageData.timestamp) : undefined,
        successMetrics,
        skipReason,
        errorDetails,
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

/* eslint-disable max-lines-per-function, max-params, complexity -- Function calculates complex progress with multiple conditions: expected vs actual stages, failed stages, running stages, pending stages, and true completion state */
function calculateOverallProgress(
  stageStatuses: ProcessedEvents['stageStatuses'],
  steps: ProgressStep[],
  isComplete: boolean,
  expectedTotalStages?: number,
  skippedAgentsInfo?: { agents: string[]; selectedAgents?: string[] }
): OverallProgress {
  // Count stages by status - only count stages that have actually been processed
  const completedStages = Array.from(stageStatuses.values()).filter(
    (s) => s.status === 'complete'
  ).length
  const skippedStages = Array.from(stageStatuses.values()).filter(
    (s) => s.status === 'skipped'
  ).length
  const failedStages = Array.from(stageStatuses.values()).filter(
    (s) => s.status === 'failed'
  ).length
  const runningStages = Array.from(stageStatuses.values()).filter(
    (s) => s.status === 'running'
  ).length

  const runningStage = Array.from(stageStatuses.entries()).find(([, s]) => s.status === 'running')

  // PHASE 1: Use expected_total_stages from backend (for accuracy)
  // This is the single source of truth for progress calculation
  const progressTotalStages = expectedTotalStages ?? TOTAL_STAGES

  // PHASE 1: Fix pending stage detection
  // True pending: stages in STAGE_CONFIG but not in stageStatuses
  // These are stages that haven't started yet (not skipped, not running, not complete, not failed)
  const allStageNames = Object.keys(STAGE_CONFIG) as StageName[]
  const truePendingStages = allStageNames.filter((stage) => !stageStatuses.has(stage))
  const truePendingCount = truePendingStages.length

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
    const expectedCompletedStages = Array.from(stageStatuses.entries()).filter(
      ([stage, status]) => expectedStages.has(stage) && status.status === 'complete'
    ).length
    const expectedFailedStages = Array.from(stageStatuses.entries()).filter(
      ([stage, status]) => expectedStages.has(stage) && status.status === 'failed'
    ).length

    // Only count EXPECTED stages that have FINISHED (complete, failed)
    // Skipped stages that were never expected don't count
    finishedStages = expectedCompletedStages + expectedFailedStages
  } else {
    // Fallback: No supervisor info available, count all finished stages (old behavior)
    // This maintains backward compatibility with tests and early events
    finishedStages = completedStages + failedStages + skippedStages
  }

  // Debug: Log calculation for troubleshooting
  // console.log('Progress calc:', { completedStages, failedStages, skippedStages, finishedStages,
  //   runningStages, unprocessedStagesCount, totalUnfinishedStages, totalStages, isComplete })

  // PHASE 1: Fix progress calculation
  // Progress = finished / expected_total_stages (not TOTAL_STAGES)
  // This ensures progress reflects actual workflow completion, not just all possible stages
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
    progress = Math.round((finishedStages / progressTotalStages) * 100)
    // Cap at 99% if there are failures, running, or unfinished expected stages
    if (failedStages > 0 || hasUnfinishedExpectedStages) {
      progress = Math.min(progress, 99) // Cap at 99% when not fully complete
    }
    // Safety: if finished exceeds expected total but there are unfinished stages, cap at 99%
    if (finishedStages > progressTotalStages && hasUnfinishedExpectedStages) {
      progress = 99
    }
  }

  let currentUIStage: AnalysisStage = 'extracting'
  // CRITICAL: Determine UI stage based on completion state
  // When isComplete is true (artifact generated), always show 'complete' stage
  // This prevents showing "Generating" when analysis is actually done, even if there are failures
  if (isComplete) {
    // Analysis is complete (artifact generated) - always show as complete
    // The completion card will handle showing error state if there are failures
    currentUIStage = 'complete'
  } else if (runningStage) {
    // Currently running a stage
    currentUIStage = STAGE_CONFIG[runningStage[0]]?.uiStage || 'analyzing'
  } else if (completedStages > 0) {
    // Some stages completed, show the last completed stage's UI stage
    const lastCompleted = steps.filter((s) => s.status === 'completed').pop()
    if (lastCompleted) {
      currentUIStage = STAGE_CONFIG[lastCompleted.id as StageName]?.uiStage || 'analyzing'
    }
  }

  // PHASE 1: Fix step number calculation
  // Current step: finished stages + 1 if running, else finished
  // Use progressTotalStages (expected_total_stages) as total, not displayTotalStages
  // hasUnfinishedExpectedStages is already defined above
  let currentStepNumber: number
  if (runningStage) {
    currentStepNumber = finishedStages + 1 // Currently running a stage
  } else if (isComplete && failedStages === 0 && !hasUnfinishedExpectedStages) {
    currentStepNumber = progressTotalStages // Fully complete - show expected total
  } else {
    currentStepNumber = finishedStages + 1 // Next step to be processed
  }
  // CRITICAL: Cap at progressTotalStages (not displayTotalStages) to fix "Step 10 of 9" issue
  currentStepNumber = Math.min(currentStepNumber, progressTotalStages)

  // PHASE 2: Enhanced status messages with detailed breakdown
  const buildStatusMessage = (): string => {
    // Check if truly complete (same logic as progress calculation)
    // hasUnfinishedExpectedStages is already defined above
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

  return {
    stage: currentUIStage,
    progress,
    currentStep: currentStepName,
    totalSteps: progressTotalStages, // Use expected_total_stages for "Step X of Y" display
    completedSteps: currentStepNumber, // Current step number for "Step X of Y" display
    estimatedTimeRemaining: isComplete ? undefined : estimateTimeRemaining(finishedStages),
  }
}

/** Transforms raw SSE events into structured data for UI components */
export function useAnalysisProgress(events: SSEEvent[]): AnalysisProgressData {
  return useMemo(() => {
    const {
      isComplete,
      hasError,
      errorMessage,
      artifactId,
      expectedTotalStages,
      stageStatuses,
      skippedAgentsInfo: processedSkippedAgentsInfo,
      analysisMetadata,
      skipReasons,
      stageSuccessMetrics,
    } = processEvents(events)
    const steps = buildSteps(stageStatuses, skipReasons, stageSuccessMetrics)
    const activities = buildActivities(events)
    const overallProgress = calculateOverallProgress(
      stageStatuses,
      steps,
      isComplete,
      expectedTotalStages,
      processedSkippedAgentsInfo
    )

    // Count failed stages for completion card display
    const failedStagesCount = Array.from(stageStatuses.values()).filter(
      (s) => s.status === 'failed'
    ).length
    const hasFailedStages = failedStagesCount > 0

    return {
      overallProgress,
      steps,
      activities,
      isComplete,
      hasError,
      errorMessage,
      artifactId,
      hasFailedStages,
      failedStagesCount,
      analysisMetadata,
      skipReasons,
      stageSuccessMetrics,
    }
  }, [events])
}
