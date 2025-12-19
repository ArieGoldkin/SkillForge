/**
 * useStageStatusProcessing - Extract and process stage status from SSE events
 *
 * This hook extracts the core event processing logic from useAnalysisProgress,
 * converting raw SSE events into a stage status map with completion detection.
 *
 * @module hooks/useStageStatusProcessing
 */
/* eslint-disable max-lines -- Core event processing logic requires comprehensive event handling, metadata extraction, and state management */

import { useMemo } from 'react'

import { isProgressEvent, isCompleteEvent, isErrorEvent } from '@app-types/sse'
import type { SSEEvent, SSEProgressEvent, StageName } from '@app-types/sse'

import {
  normalizeStageNameFromBackend,
  markSkippedAgents,
  type StageStatusEntry,
} from './stageConfig'

// ============================================================================
// Types
// ============================================================================

/**
 * Result of stage status processing
 * Contains the stage status map and completion metadata
 */
export interface StageStatusResult {
  /** Map of stage names to their current status and details */
  stageStatuses: Map<StageName, StageStatusEntry>
  /** Whether the entire analysis workflow is complete */
  isComplete: boolean
  /** UUID of the generated artifact (if complete) */
  artifactId?: string
  /** Langfuse trace ID for feedback submission (if complete) */
  traceId?: string
  /** Number of agent stages expected (from supervisor routing) */
  expectedTotalStages?: number
  /** Metadata about the analyzed content */
  analysisMetadata?: {
    title?: string
    contentType?: 'article' | 'video' | 'repo'
    url?: string
    wordCount?: number
  }
  /** Map of agent type to skip reason */
  skipReasons?: Record<string, string>
  /** Success metrics for completed stages */
  stageSuccessMetrics?: Map<
    string,
    {
      findingsQuality?: 'high' | 'medium' | 'low'
      coverage?: 'comprehensive' | 'partial' | 'minimal'
      keyInsights?: string[]
    }
  >
}

/**
 * Internal state for event processing
 */
interface ProcessingState {
  isComplete: boolean
  artifactId?: string
  traceId?: string
  expectedTotalStages?: number
}

/**
 * Internal result from processEvents
 */
interface ProcessedEventsResult {
  stageStatuses: Map<StageName, StageStatusEntry>
  state: ProcessingState
  analysisMetadata?: StageStatusResult['analysisMetadata']
  skipReasons?: Record<string, string>
  stageSuccessMetrics?: StageStatusResult['stageSuccessMetrics']
  skippedAgentsInfo?: { agents: string[]; selectedAgents?: string[] }
}

// ============================================================================
// Event Processing
// ============================================================================

/**
 * Process a single SSE event and update stage status map
 *
 * Handles:
 * - Progress events: Update stage status, extract metadata
 * - Complete events: Mark workflow complete, capture artifact_id and trace_id
 * - Error events: Mark stage as failed, preserve error details
 *
 * @param event - SSE event to process
 * @param stageStatuses - Map of stage statuses (mutated in place)
 * @param state - Processing state (mutated in place)
 */
/* eslint-disable max-lines-per-function, complexity -- Function processes multiple event types (progress, complete, error) with different extraction logic for metadata, skip reasons, success metrics, and error details */
function processEvent(
  event: SSEEvent,
  stageStatuses: Map<StageName, StageStatusEntry>,
  state: ProcessingState
): void {
  if (isProgressEvent(event) || isCompleteEvent(event)) {
    const normalizedStage = normalizeStageNameFromBackend(event.stage)
    // Process ALL valid stages, not just agent stages
    if (normalizedStage) {
      const existingStatus = stageStatuses.get(normalizedStage)

      // Don't overwrite failed status with later events (e.g., complete events)
      if (existingStatus?.status === 'failed' && event.status !== 'failed') {
        // Preserve failed status - don't overwrite
        return
      }

      // Merge details from event (including new fields like findings_summary, insights_count, error details, success_metrics)
      const eventDetails = isProgressEvent(event)
        ? {
            ...(event.details ?? {}),
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
        : (event.details ?? {})
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
      // Capture trace_id from complete event for Langfuse feedback tracking
      const traceId = isCompleteEvent(event) ? event.trace_id : undefined
      if (traceId) {
        state.traceId = traceId
      }
    }
  }

  // Handle error events to capture failed status
  if (isErrorEvent(event)) {
    const normalizedStage = normalizeStageNameFromBackend(event.stage)
    // Process ALL valid stages, not just agent stages
    if (normalizedStage) {
      // Only update if status is not already set (preserve failed status)
      const existingStatus = stageStatuses.get(normalizedStage)
      if (!existingStatus || existingStatus.status !== 'failed') {
        stageStatuses.set(normalizedStage, {
          status: 'failed',
          timestamp: event.timestamp,
          details: {
            error: event.error ?? event.details?.error,
            error_code: event.details?.error_code,
            ...(event.details ?? {}),
          },
        })
      }
    }
  }
}

/**
 * Process all SSE events and extract stage statuses, metadata, and completion state
 *
 * Iterates through all events and:
 * 1. Builds stage status map using processEvent
 * 2. Extracts analysis metadata from extraction stage
 * 3. Captures skip reasons from supervisor routing
 * 4. Collects success metrics from agent completions
 * 5. Marks skipped agents after supervisor completes
 *
 * @param events - Array of SSE events to process
 * @returns Processed stage statuses and metadata
 */
/* eslint-disable max-lines-per-function, complexity -- Function processes all SSE events, extracts metadata, skip reasons, success metrics, and builds stage status map with complex conditional logic */
function processEvents(events: SSEEvent[]): ProcessedEventsResult {
  const stageStatuses = new Map<StageName, StageStatusEntry>()
  const state: ProcessingState = {
    isComplete: false,
    artifactId: undefined,
    traceId: undefined,
    expectedTotalStages: undefined,
  }

  let analysisMetadata: StageStatusResult['analysisMetadata']
  let skipReasons: Record<string, string> | undefined
  let skippedAgentsInfo: { agents: string[]; selectedAgents?: string[] } | undefined
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
      if (metadata && typeof metadata === 'object') {
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
          selectedAgents: Array.isArray(selectedAgents) ? selectedAgents : undefined,
        }
      }
      // Capture skip reasons
      const reasons =
        (event as SSEProgressEvent & { skip_reasons?: Record<string, string> }).skip_reasons ||
        event.details?.skip_reasons
      if (reasons && typeof reasons === 'object' && !Array.isArray(reasons)) {
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
      if (metrics && typeof metrics === 'object' && !Array.isArray(metrics)) {
        const normalizedStage = normalizeStageNameFromBackend(event.stage)
        if (normalizedStage) {
          stageSuccessMetrics.set(normalizedStage, {
            findingsQuality: metrics.findings_quality,
            coverage: metrics.coverage,
            keyInsights: Array.isArray(metrics.key_insights) ? metrics.key_insights : undefined,
          })
        }
      }
    }
  }

  // Mark skipped agents after processing all events
  markSkippedAgents(stageStatuses, skippedAgentsInfo)

  return {
    stageStatuses,
    state,
    analysisMetadata,
    skipReasons,
    stageSuccessMetrics: stageSuccessMetrics.size > 0 ? stageSuccessMetrics : undefined,
    skippedAgentsInfo,
  }
}

// ============================================================================
// Hook
// ============================================================================

/**
 * Extract and process stage status from SSE events
 *
 * This hook transforms raw SSE events into a structured stage status map
 * with completion detection and metadata extraction. It's designed to be
 * composable and reusable across different components.
 *
 * **Features:**
 * - Builds stage status map from progress/complete/error events
 * - Detects workflow completion and extracts artifact_id/trace_id
 * - Captures expected_total_stages from supervisor routing
 * - Extracts analysis metadata, skip reasons, and success metrics
 * - Marks unselected agents as 'skipped' after supervisor completes
 * - Preserves failed status (won't overwrite with later events)
 *
 * **Performance:**
 * - Memoized result based on events array reference
 * - Only re-processes when events array changes
 *
 * @param events - Array of SSE events from the analysis workflow
 * @returns Stage status result with completion metadata
 *
 * @example
 * ```tsx
 * const { stageStatuses, isComplete, artifactId, traceId } =
 *   useStageStatusProcessing(events)
 *
 * // Check if a specific stage is complete
 * const extractionStatus = stageStatuses.get('extraction')
 * if (extractionStatus?.status === 'complete') {
 *   console.log('Extraction finished:', extractionStatus.details)
 * }
 *
 * // Render completion state
 * if (isComplete && artifactId) {
 *   return <CompletionCard artifactId={artifactId} traceId={traceId} />
 * }
 * ```
 */
export function useStageStatusProcessing(events: SSEEvent[]): StageStatusResult {
  return useMemo(() => {
    const { stageStatuses, state, analysisMetadata, skipReasons, stageSuccessMetrics } =
      processEvents(events)

    return {
      stageStatuses,
      isComplete: state.isComplete,
      artifactId: state.artifactId,
      traceId: state.traceId,
      expectedTotalStages: state.expectedTotalStages,
      analysisMetadata,
      skipReasons,
      stageSuccessMetrics,
    }
  }, [events])
}
