/**
 * useAnalysisMetadata - Extract analysis metadata from SSE events
 *
 * Processes SSE events to extract:
 * - Analysis metadata (title, contentType, url, wordCount) from extraction stage
 * - Skipped agents and selected agents from supervisor stage
 * - Skip reasons from supervisor event
 * - Success metrics from agent completion events
 *
 * @module features/analysis/hooks
 */

/* eslint-disable max-lines -- Additional lines required for defensive null guards to prevent crashes */

import { useMemo } from 'react'

import { isProgressEvent } from '@app-types/sse'
import type { SSEEvent, SSEProgressEvent, SuccessMetrics } from '@app-types/sse'

import { normalizeStageNameFromBackend } from './stageConfig'

// ============================================================================
// Types
// ============================================================================

/**
 * Information about agents that were skipped by the supervisor
 */
export interface SkippedAgentsInfo {
  /** Agent types that were skipped */
  agents: string[]
  /** Agent types that were selected (optional) */
  selectedAgents?: string[]
}

/**
 * Result returned by useAnalysisMetadata hook
 */
export interface AnalysisMetadataResult {
  /** Metadata extracted from the content analysis (title, type, url, word count) */
  analysisMetadata?: {
    title?: string
    contentType?: 'article' | 'video' | 'repo'
    url?: string
    wordCount?: number
  }
  /** Mapping of agent type to skip reason (why agent was not selected) */
  skipReasons?: Record<string, string>
  /** Information about skipped and selected agents */
  skippedAgentsInfo?: SkippedAgentsInfo
  /** Success metrics reported by each stage/agent upon completion */
  stageSuccessMetrics: Map<
    string,
    {
      findingsQuality?: 'high' | 'medium' | 'low'
      coverage?: 'comprehensive' | 'partial' | 'minimal'
      keyInsights?: string[]
    }
  >
}

// ============================================================================
// Metadata Extraction Helpers
// ============================================================================

/**
 * Extract analysis metadata from extraction stage complete event
 *
 * Handles snake_case to camelCase conversion for metadata fields.
 *
 * @param event - Progress event from extraction stage
 * @returns Extracted metadata with camelCase field names, or undefined if not available
 */
function extractAnalysisMetadata(
  event: SSEProgressEvent
): AnalysisMetadataResult['analysisMetadata'] | undefined {
  if (!event || typeof event !== 'object') {
    return undefined
  }

  const metadata = event.analysis_metadata || event.details?.analysis_metadata
  if (!metadata || typeof metadata !== 'object') {
    return undefined
  }

  return {
    title: metadata.title,
    contentType: metadata.content_type,
    url: metadata.url,
    wordCount: metadata.word_count,
  }
}

/**
 * Extract skipped agents information from supervisor routing stage
 *
 * The supervisor event may have skipped_agents and selected_agents
 * at the top level or nested in details.
 *
 * @param event - Progress event from supervisor_routing stage
 * @returns Skipped agents info, or undefined if not available
 */
function extractSkippedAgentsInfo(event: SSEProgressEvent): SkippedAgentsInfo | undefined {
  if (!event || typeof event !== 'object') {
    return undefined
  }

  // Access fields that may be at top level or in details (SSE event structure)
  const skippedAgents =
    event.details?.skipped_agents ||
    (event as SSEProgressEvent & { skipped_agents?: string[] }).skipped_agents
  const selectedAgents =
    event.details?.selected_agents ||
    (event as SSEProgressEvent & { selected_agents?: string[] }).selected_agents

  if (!skippedAgents || !Array.isArray(skippedAgents)) {
    return undefined
  }

  return {
    agents: skippedAgents,
    selectedAgents: Array.isArray(selectedAgents) ? selectedAgents : undefined,
  }
}

/**
 * Extract skip reasons from supervisor routing stage
 *
 * Maps agent type to reason why it was skipped.
 *
 * @param event - Progress event from supervisor_routing stage
 * @returns Skip reasons map, or undefined if not available
 */
function extractSkipReasons(event: SSEProgressEvent): Record<string, string> | undefined {
  if (!event || typeof event !== 'object') {
    return undefined
  }

  const reasons =
    (event as SSEProgressEvent & { skip_reasons?: Record<string, string> }).skip_reasons ||
    event.details?.skip_reasons

  if (!reasons || typeof reasons !== 'object' || Array.isArray(reasons)) {
    return undefined
  }

  return reasons as Record<string, string>
}

/**
 * Extract success metrics from agent completion event
 *
 * Success metrics include findings quality, coverage, and key insights.
 * Only extracted from agent stage completion events (not infrastructure stages).
 *
 * @param event - Progress event from agent stage
 * @returns Success metrics with snake_case to camelCase conversion, or undefined
 */
function extractSuccessMetrics(event: SSEProgressEvent): SuccessMetrics | undefined {
  if (!event || typeof event !== 'object') {
    return undefined
  }

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

  if (!metrics || typeof metrics !== 'object' || Array.isArray(metrics)) {
    return undefined
  }

  return {
    findings_quality: metrics.findings_quality,
    coverage: metrics.coverage,
    key_insights: Array.isArray(metrics.key_insights) ? metrics.key_insights : undefined,
  }
}

/**
 * Check if stage is an agent stage (not infrastructure stage)
 *
 * Infrastructure stages: extraction, embedding, supervisor_routing, aggregation, artifact_generation
 * Agent stages: tech_comparison, security_audit, implementation_planning, etc.
 *
 * @param stageName - Name of the stage
 * @returns True if stage is an agent stage
 */
function isAgentStage(stageName: string): boolean {
  if (!stageName || typeof stageName !== 'string') {
    return false
  }

  const infrastructureStages = [
    'extraction',
    'embedding',
    'supervisor_routing',
    'aggregation',
    'artifact_generation',
  ]
  return !infrastructureStages.includes(stageName)
}

// ============================================================================
// Hook Implementation
// ============================================================================

/**
 * Extract analysis metadata from SSE events
 *
 * Processes the event stream to extract:
 * 1. Analysis metadata (title, contentType, url, wordCount) from extraction stage
 * 2. Skipped agents and selected agents from supervisor stage
 * 3. Skip reasons (why agents were not selected) from supervisor stage
 * 4. Success metrics from individual agent completion events
 *
 * All extractions are memoized based on the events array.
 *
 * @param events - Array of SSE events from the analysis workflow
 * @returns Extracted metadata, skip info, and success metrics
 *
 * @example
 * ```tsx
 * const { analysisMetadata, skipReasons, stageSuccessMetrics } = useAnalysisMetadata(events)
 *
 * // Access analysis metadata
 * console.log(analysisMetadata?.title) // "Introduction to RAG"
 * console.log(analysisMetadata?.contentType) // "article"
 *
 * // Check why an agent was skipped
 * console.log(skipReasons?.tech_comparator) // "No technology comparisons needed"
 *
 * // Get success metrics for a stage
 * const metrics = stageSuccessMetrics.get('implementation_planning')
 * console.log(metrics?.findingsQuality) // "high"
 * console.log(metrics?.keyInsights) // ["Step-by-step implementation plan", ...]
 * ```
 */
/* eslint-disable max-lines-per-function, complexity -- Hook processes multiple event types (extraction, supervisor, agent completion) with conditional extraction logic for metadata, skip reasons, and success metrics */
export function useAnalysisMetadata(events: SSEEvent[]): AnalysisMetadataResult {
  return useMemo(() => {
    let analysisMetadata: AnalysisMetadataResult['analysisMetadata']
    let skipReasons: Record<string, string> | undefined
    let skippedAgentsInfo: SkippedAgentsInfo | undefined
    const stageSuccessMetrics = new Map<
      string,
      {
        findingsQuality?: 'high' | 'medium' | 'low'
        coverage?: 'comprehensive' | 'partial' | 'minimal'
        keyInsights?: string[]
      }
    >()

    // Guard against undefined or non-array events
    if (!events || !Array.isArray(events)) {
      return {
        analysisMetadata,
        skipReasons,
        skippedAgentsInfo,
        stageSuccessMetrics,
      }
    }

    for (const event of events) {
      // Guard against null/undefined events in array
      if (!event || typeof event !== 'object') {
        continue
      }

      // Extract analysis metadata from extraction stage
      if (isProgressEvent(event) && event.stage === 'extraction' && event.status === 'complete') {
        const metadata = extractAnalysisMetadata(event)
        if (metadata) {
          analysisMetadata = metadata
        }
      }

      // Extract skipped agents info and skip reasons from supervisor stage
      if (
        isProgressEvent(event) &&
        event.stage === 'supervisor_routing' &&
        event.status === 'complete'
      ) {
        const skippedInfo = extractSkippedAgentsInfo(event)
        if (skippedInfo) {
          skippedAgentsInfo = skippedInfo
        }

        const reasons = extractSkipReasons(event)
        if (reasons) {
          skipReasons = reasons
        }
      }

      // Extract success metrics from agent completion events
      if (
        isProgressEvent(event) &&
        event.status === 'complete' &&
        event.stage &&
        isAgentStage(event.stage)
      ) {
        const metrics = extractSuccessMetrics(event)
        if (metrics) {
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
    }

    return {
      analysisMetadata,
      skipReasons,
      skippedAgentsInfo,
      stageSuccessMetrics,
    }
  }, [events])
}
