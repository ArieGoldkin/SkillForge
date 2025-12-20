/**
 * Stage helper functions - Transform stage data for UI display
 */
/* eslint-disable max-lines -- File contains multiple helper functions for stage descriptions with rich detail extraction */
import type { StageName, StageStatus } from '@app-types/sse'

import type { AnalysisStepStatus } from '../components/steps/AnalysisStepList'
import { TIME_CONSTANTS } from '@/lib/constants'

import { STAGE_CONFIG } from './stageConfig'

/**
 * Map backend stage status to UI step status
 */
export function mapStageStatus(status: StageStatus): AnalysisStepStatus {
  switch (status) {
    case 'complete':
      return 'completed'
    case 'running':
      return 'in-progress'
    case 'failed':
      return 'failed'
    case 'skipped':
      return 'skipped'
    default:
      return 'pending'
  }
}

/**
 * Get description for a stage based on its status
 */
/* eslint-disable max-lines-per-function, complexity -- Function handles multiple status types (complete, running, failed, skipped) with rich details (success_metrics, findings_summary, insights_count, error details, skip_reasons) which requires multiple conditional branches */
export function getStageDescription(
  stage: StageName,
  status: StageStatus,
  details?: Record<string, unknown>
): string {
  if (status === 'complete') {
    if (stage === 'extraction' && details?.word_count) {
      return `Extracted ${details.word_count} words`
    }

    // Use success_metrics if available (from SSE event)
    const successMetrics = details?.success_metrics as
      | {
          findings_quality?: 'high' | 'medium' | 'low'
          coverage?: 'comprehensive' | 'partial' | 'minimal'
          key_insights?: string[]
        }
      | undefined

    if (successMetrics) {
      const quality = successMetrics.findings_quality
      const coverage = successMetrics.coverage
      const keyInsights = successMetrics.key_insights

      // Build description from success metrics
      const parts: string[] = []
      if (quality === 'high') {
        parts.push('High quality analysis')
      } else if (quality === 'medium') {
        parts.push('Moderate quality analysis')
      }
      if (coverage === 'comprehensive') {
        parts.push('comprehensive coverage')
      } else if (coverage === 'partial') {
        parts.push('partial coverage')
      }
      if (keyInsights && keyInsights.length > 0) {
        parts.push(`${keyInsights.length} key insight${keyInsights.length === 1 ? '' : 's'}`)
      }
      if (parts.length > 0) {
        return parts.join(', ')
      }
    }

    // Use rich details if available: findings_summary > insights_count > generic
    if (details?.findings_summary && typeof details.findings_summary === 'string') {
      return details.findings_summary
    }
    if (details?.insights_count && typeof details.insights_count === 'number') {
      return `Found ${details.insights_count} ${details.insights_count === 1 ? 'insight' : 'insights'}`
    }
    return 'Completed'
  }
  if (status === 'running') {
    // Use agent from details if available
    if (details?.agent && typeof details.agent === 'string') {
      return `Running ${details.agent}...`
    }
    return 'Processing...'
  }
  if (status === 'failed') {
    // Show error message from details if available
    if (details?.error && typeof details.error === 'string') {
      const errorMsg =
        details.error.length > 100 ? `${details.error.substring(0, 100)}...` : details.error
      return `Failed: ${errorMsg}`
    }
    if (details?.error_code && typeof details.error_code === 'string') {
      return `Failed: ${details.error_code}`
    }
    // Show processing time if available
    if (details?.processing_time_ms && typeof details.processing_time_ms === 'number') {
      const seconds = Math.round(details.processing_time_ms / TIME_CONSTANTS.SECOND)
      return `Failed after ${seconds}s`
    }
    return 'Failed'
  }
  if (status === 'skipped') {
    // Show skip reason if available
    if (details?.skip_reason && typeof details.skip_reason === 'string') {
      return `Skipped: ${details.skip_reason}`
    }
    if (details?.skipped_by === 'supervisor_routing') {
      return 'Skipped by supervisor (not selected for this analysis)'
    }
    return 'Skipped by supervisor'
  }
  return 'Waiting...'
}

/**
 * Generate agent name from stage
 */
export function getAgentName(stage: StageName, details?: Record<string, unknown>): string {
  if (details?.agent && typeof details.agent === 'string' && details.agent.length > 0) {
    // Format agent name: snake_case -> Title Case
    return details.agent
      .split('_')
      .filter((word) => word.length > 0) // Guard against empty strings from split
      .map((word) => (word[0]?.toUpperCase() ?? '') + word.slice(1))
      .join(' ')
  }

  // Default agent names based on stage
  const agentNames: Record<StageName, string> = {
    // Core workflow stages
    extraction: 'Content Extractor',
    embedding: 'Embedding Generator',
    supervisor_routing: 'Supervisor',
    aggregation: 'Aggregator',
    quality_validation: 'Quality Validator',
    artifact_generation: 'Report Generator',
    // Agent stages
    tech_comparison: 'Tech Comparator',
    security_audit: 'Security Auditor',
    implementation_planning: 'Implementation Planner', // Covers BOTH implementation_planner AND integration_feasibility
    performance_audit: 'Performance Auditor',
    code_quality_audit: 'Code Quality Reviewer',
    trends_analysis: 'Trends Analyst',
    dependencies_analysis: 'Dependencies Analyzer',
    // Optional stages
    chunking: 'Content Chunker',
    workflow: 'Workflow',
    pattern_comparison: 'Pattern Comparator',
    metrics: 'Metrics Collector',
  }

  return agentNames[stage] || 'Agent'
}

const RUNNING_ACTIONS: Record<StageName, string> = {
  // Core workflow stages
  extraction: 'Extracting content from URL...',
  embedding: 'Generating embeddings...',
  supervisor_routing: 'Routing analysis to specialized agents...',
  aggregation: 'Aggregating agent results...',
  quality_validation: 'Validating quality standards...',
  artifact_generation: 'Generating implementation guide...',
  // Agent stages
  tech_comparison: 'Comparing technology patterns...',
  security_audit: 'Auditing security considerations...',
  implementation_planning: 'Planning implementation steps...', // Covers BOTH implementation_planner AND integration_feasibility
  performance_audit: 'Analyzing performance patterns...',
  code_quality_audit: 'Reviewing code quality...',
  trends_analysis: 'Analyzing technology trends...',
  dependencies_analysis: 'Analyzing dependencies...',
  // Optional stages
  chunking: 'Chunking content...',
  workflow: 'Managing workflow...',
  pattern_comparison: 'Comparing patterns...',
  metrics: 'Collecting metrics...',
}

/* eslint-disable complexity -- Function handles multiple stage types with different detail extraction logic */
function getCompleteAction(stage: StageName, details?: Record<string, unknown>): string {
  if (stage === 'extraction' && details?.word_count) {
    return `Extracted ${details.word_count} words from content`
  }
  if (stage === 'embedding') {
    return 'Generated semantic embeddings'
  }
  if (stage === 'artifact_generation' && details?.artifact_id) {
    return 'Generated implementation guide'
  }
  // Use rich details if available: findings_summary > insights_count > generic
  if (details?.findings_summary && typeof details.findings_summary === 'string') {
    return details.findings_summary
  }
  if (details?.insights_count && typeof details.insights_count === 'number') {
    return `Found ${details.insights_count} ${details.insights_count === 1 ? 'insight' : 'insights'}`
  }
  return `Completed ${STAGE_CONFIG[stage]?.title || stage}`
}

/** Generate action description from event */
/* eslint-disable complexity -- Function handles multiple status types with different detail extraction logic for each */
export function getActionDescription(
  stage: StageName,
  status: StageStatus,
  details?: Record<string, unknown>
): string {
  const stageTitle = STAGE_CONFIG[stage]?.title || stage
  switch (status) {
    case 'running':
      return RUNNING_ACTIONS[stage] || 'Processing...'
    case 'complete':
      return getCompleteAction(stage, details)
    case 'failed':
      // Show error message from details if available
      if (details?.error && typeof details.error === 'string') {
        const errorMsg =
          details.error.length > 80 ? `${details.error.substring(0, 80)}...` : details.error
        return `Failed: ${errorMsg}`
      }
      if (details?.error_code && typeof details.error_code === 'string') {
        return `Failed: ${details.error_code}`
      }
      // Show processing time if available
      if (details?.processing_time_ms && typeof details.processing_time_ms === 'number') {
        const seconds = Math.round(details.processing_time_ms / TIME_CONSTANTS.SECOND)
        return `Failed after ${seconds}s`
      }
      return `Failed ${stageTitle}`
    case 'skipped':
      // Show skip reason if available
      if (details?.skip_reason && typeof details.skip_reason === 'string') {
        return `Skipped: ${details.skip_reason}`
      }
      return `Skipped ${stageTitle}`
    default:
      return `Started ${stageTitle}`
  }
}
