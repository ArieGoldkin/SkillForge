/**
 * ProgressTracker Constants
 * Shared stage configuration and helper functions
 */

import type { AgentStageName, StageStatus } from '@app-types/sse'

/**
 * All available pipeline stages
 */
export const ALL_STAGES: AgentStageName[] = [
  'extraction',
  'embedding',
  'supervisor_routing',
  'tech_comparison',
  'security_audit',
  'implementation_planning',
  'performance_audit',
  'code_quality_audit',
  'trends_analysis',
  'dependencies_analysis',
  'integration_feasibility',
  'aggregation',
  'artifact_generation',
]

/**
 * Currently working stages (for testing with real backend)
 */
export const WORKING_STAGES: AgentStageName[] = ['extraction', 'embedding', 'supervisor_routing']

/**
 * Stage configuration with user-friendly labels
 */
export const STAGE_CONFIG: Record<AgentStageName, { label: string }> = {
  extraction: { label: 'Content Extraction' },
  embedding: { label: 'Embedding Generation' },
  supervisor_routing: { label: 'Agent Routing' },
  tech_comparison: { label: 'Technology Comparison' },
  security_audit: { label: 'Security Audit' },
  implementation_planning: { label: 'Implementation Planning' },
  performance_audit: { label: 'Performance Analysis' },
  code_quality_audit: { label: 'Code Quality Review' },
  trends_analysis: { label: 'Trends Analysis' },
  dependencies_analysis: { label: 'Dependencies Review' },
  integration_feasibility: { label: 'Integration Feasibility' },
  aggregation: { label: 'Results Aggregation' },
  artifact_generation: { label: 'Artifact Generation' },
}

/**
 * Internal state for each stage
 */
export interface StageState {
  name: AgentStageName
  label: string
  status: StageStatus
  agent?: string
  timestamp?: string
  error?: string
}

/**
 * Create initial stage states from stage list
 */
export function createInitialStages(stages: AgentStageName[]): StageState[] {
  return stages.map((name) => ({
    name,
    label: STAGE_CONFIG[name].label,
    status: 'pending' as StageStatus,
  }))
}

/**
 * Format status for display
 */
export function formatStatus(status: StageStatus): string {
  switch (status) {
    case 'complete':
      return 'Complete'
    case 'running':
      return 'Running'
    case 'failed':
      return 'Failed'
    case 'skipped':
      return 'Skipped'
    case 'pending':
      return 'Pending'
  }
}

/**
 * Format agent name from snake_case to Title Case
 */
export function formatAgentName(agent: string): string {
  return agent
    .split('_')
    .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
    .join(' ')
}

/**
 * Get badge variant for status
 */
export function getStatusBadgeVariant(
  status: StageStatus
): 'default' | 'success' | 'warning' | 'destructive' | 'secondary' {
  switch (status) {
    case 'complete':
      return 'success'
    case 'running':
      return 'warning'
    case 'failed':
      return 'destructive'
    case 'skipped':
      return 'secondary'
    case 'pending':
      return 'default'
  }
}
