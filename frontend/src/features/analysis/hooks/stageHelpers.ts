/**
 * Stage helper functions - Transform stage data for UI display
 */

import type { StageName, StageStatus } from '@app-types/sse'

import type { AnalysisStepStatus } from '../components/steps/AnalysisStepList'

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
    default:
      return 'pending'
  }
}

/**
 * Get description for a stage based on its status
 */
export function getStageDescription(
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
export function getAgentName(stage: StageName, details?: Record<string, unknown>): string {
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
export function getActionDescription(
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
    const stageConfig = STAGE_CONFIG[stage]
    return `Completed ${stageConfig?.title || stage}`
  }

  const stageConfig = STAGE_CONFIG[stage]
  return `Started ${stageConfig?.title || stage}`
}
