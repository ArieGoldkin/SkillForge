/**
 * Stage helper functions - Transform stage data for UI display
 */

import type { AgentStageName, StageStatus } from '@app-types/sse'

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
    case 'skipped':
      return 'skipped'
    default:
      return 'pending'
  }
}

/**
 * Get description for a stage based on its status
 */
export function getStageDescription(
  stage: AgentStageName,
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
  if (status === 'skipped') {
    return 'Skipped by supervisor'
  }
  return 'Waiting...'
}

/**
 * Generate agent name from stage
 */
export function getAgentName(stage: AgentStageName, details?: Record<string, unknown>): string {
  if (details?.agent && typeof details.agent === 'string') {
    // Format agent name: snake_case -> Title Case
    return details.agent
      .split('_')
      .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
      .join(' ')
  }

  // Default agent names based on stage
  const agentNames: Record<AgentStageName, string> = {
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

const RUNNING_ACTIONS: Record<AgentStageName, string> = {
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

function getCompleteAction(stage: AgentStageName, details?: Record<string, unknown>): string {
  if (stage === 'extraction' && details?.word_count) {
    return `Extracted ${details.word_count} words from content`
  }
  if (stage === 'artifact_generation' && details?.artifact_id) {
    return 'Generated implementation guide'
  }
  return `Completed ${STAGE_CONFIG[stage]?.title || stage}`
}

/** Generate action description from event */
export function getActionDescription(
  stage: AgentStageName,
  status: StageStatus,
  details?: Record<string, unknown>
): string {
  const stageTitle = STAGE_CONFIG[stage]?.title || stage
  switch (status) {
    case 'running':
      return RUNNING_ACTIONS[stage] || 'Processing...'
    case 'complete':
      return getCompleteAction(stage, details)
    case 'skipped':
      return `Skipped ${stageTitle}`
    default:
      return `Started ${stageTitle}`
  }
}
