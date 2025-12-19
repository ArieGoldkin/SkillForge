/* eslint-disable max-lines-per-function -- Complex step transformation with comprehensive null guards requires extended logic */
/**
 * useProgressSteps - Build UI-friendly progress steps from stage statuses
 *
 * Extracts step building logic from useAnalysisProgress to improve maintainability
 * and reduce complexity.
 *
 * @module useProgressSteps
 */

import { useMemo } from 'react'

import type { StageName } from '@app-types/sse'

import type { SuccessMetrics } from '@/schemas/sse'

import { STAGE_CONFIG } from './stageConfig'
import { mapStageStatus, getStageDescription } from './stageHelpers'

// ============================================================================
// Types
// ============================================================================

/**
 * Stage status information from SSE events
 */
export interface StageStatusEntry {
  status: 'pending' | 'running' | 'complete' | 'failed' | 'skipped'
  timestamp: string
  details?: {
    findings_summary?: string
    insights_count?: number
    confidence_score?: number
    error?: string
    error_code?: string
    processing_time_ms?: number
    skip_reason?: string
    [key: string]: unknown
  }
}

/**
 * UI-friendly progress step representation
 */
export interface ProgressStep {
  id: string
  title: string
  status: 'pending' | 'in-progress' | 'completed' | 'failed' | 'skipped'
  description: string
  timestamp?: Date
  successMetrics?: SuccessMetrics
  skipReason?: string
  errorDetails?: {
    error: string
    errorCode?: string
    processingTime?: number
  }
}

// ============================================================================
// Constants
// ============================================================================

/**
 * Maps stage names to their corresponding agent types for skip reason lookup
 *
 * Note: implementation_planning stage is used by BOTH implementation_planner
 * AND integration_feasibility agents, so we map it to implementation_planner
 * as the primary agent type.
 */
const STAGE_TO_AGENT_MAP: Record<StageName, string> = {
  // Agent stages
  tech_comparison: 'tech_comparator',
  security_audit: 'security_auditor',
  implementation_planning: 'implementation_planner',
  performance_audit: 'performance_analyst',
  code_quality_audit: 'code_quality_critic',
  trends_analysis: 'trend_validator',
  dependencies_analysis: 'dependency_mapper',
  // Workflow stages
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

// ============================================================================
// Hook
// ============================================================================

/**
 * Build UI-friendly progress steps from stage status map
 *
 * Transforms backend stage statuses into UI-friendly step objects with:
 * - Status mapping (backend 'complete' → UI 'completed', 'running' → 'in-progress')
 * - Skip reason extraction (from stage details or skip reasons dict)
 * - Success metrics extraction for completed stages
 * - Error details extraction for failed stages
 *
 * @param stageStatuses - Map of stage names to their current status
 * @param skipReasons - Optional dict of agent types to skip reasons
 * @param stageSuccessMetrics - Optional map of stage names to success metrics
 * @returns Array of progress steps sorted by stage order
 *
 * @example
 * ```tsx
 * const steps = useProgressSteps(stageStatuses, skipReasons, successMetrics)
 * return <AnalysisStepList steps={steps} />
 * ```
 */
export function useProgressSteps(
  stageStatuses: Map<StageName, StageStatusEntry>,
  skipReasons?: Record<string, string>,
  stageSuccessMetrics?: Map<string, SuccessMetrics>
): ProgressStep[] {
  return useMemo(() => {
    /* eslint-disable complexity -- Function builds step objects with skip reasons, success metrics, and error details extraction, requiring multiple conditional branches */
    return Object.entries(STAGE_CONFIG)
      .sort(([, a], [, b]) => a.order - b.order)
      .map(([stageName, config]) => {
        const stageData = stageStatuses.get(stageName as StageName)
        const agentStageName = stageName as StageName
        const agentType = STAGE_TO_AGENT_MAP[agentStageName]

        // Extract skip reason if stage is skipped
        // Priority: details.skip_reason > skipReasons dict > default message
        const skipReason =
          stageData?.status === 'skipped'
            ? (stageData.details?.skip_reason as string | undefined) ||
              (skipReasons && agentType ? skipReasons[agentType] : undefined) ||
              'Not selected by supervisor'
            : undefined

        // Extract success metrics if stage is complete
        const successMetrics =
          stageData?.status === 'complete' && stageSuccessMetrics
            ? stageSuccessMetrics.get(agentStageName)
            : undefined

        // Extract error details if stage failed
        const errorDetails =
          stageData?.status === 'failed' && stageData?.details
            ? {
                error:
                  (stageData.details.error as string) ||
                  (stageData.details.error_code as string) ||
                  'Unknown error',
                errorCode: stageData.details.error_code as string | undefined,
                processingTime: stageData.details.processing_time_ms as number | undefined,
              }
            : undefined

        // Guard against invalid timestamps
        let parsedTimestamp: Date | undefined
        if (stageData?.timestamp) {
          try {
            const timestamp = new Date(stageData.timestamp)
            // Check if timestamp is valid
            parsedTimestamp = !isNaN(timestamp.getTime()) ? timestamp : undefined
          } catch {
            parsedTimestamp = undefined
          }
        }

        return {
          id: stageName,
          title: config.title,
          status: stageData ? mapStageStatus(stageData.status) : 'pending',
          description: stageData
            ? getStageDescription(agentStageName, stageData.status, stageData.details)
            : 'Waiting...',
          timestamp: parsedTimestamp,
          successMetrics,
          skipReason,
          errorDetails,
        }
      })
  }, [stageStatuses, skipReasons, stageSuccessMetrics])
}
