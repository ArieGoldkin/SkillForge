/**
 * ProgressTracker Constants
 * Shared stage configuration and helper functions
 */

import type { StageName, StageStatus } from '@app-types/sse'

/**
 * All available pipeline stages
 */
export const ALL_STAGES: StageName[] = [
  'extraction',
  'supervisor_routing',
  'tech_comparison',
  'security_audit',
  'implementation_planning',
  'performance_audit',
  'code_quality_audit',
  'trends_analysis',
  'dependencies_analysis',
  'aggregation',
  'artifact_generation',
]

/**
 * Currently working stages (for testing with real backend)
 */
export const WORKING_STAGES: StageName[] = ['extraction', 'supervisor_routing']

/**
 * Stage configuration with user-friendly labels
 */
export const STAGE_CONFIG: Record<StageName, { label: string }> = {
  extraction: { label: 'Content Extraction' },
  supervisor_routing: { label: 'Agent Routing' },
  tech_comparison: { label: 'Technology Comparison' },
  security_audit: { label: 'Security Audit' },
  implementation_planning: { label: 'Implementation Planning' },
  performance_audit: { label: 'Performance Analysis' },
  code_quality_audit: { label: 'Code Quality Review' },
  trends_analysis: { label: 'Trends Analysis' },
  dependencies_analysis: { label: 'Dependencies Review' },
  aggregation: { label: 'Results Aggregation' },
  artifact_generation: { label: 'Artifact Generation' },
}

/**
 * Internal state for each stage
 */
export interface StageState {
  name: StageName
  label: string
  status: StageStatus
  agent?: string
  timestamp?: string
  error?: string
}

/**
 * Create initial stage states from stage list
 */
export function createInitialStages(stages: StageName[]): StageState[] {
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
): 'default' | 'success' | 'warning' | 'destructive' {
  switch (status) {
    case 'complete':
      return 'success'
    case 'running':
      return 'warning'
    case 'failed':
      return 'destructive'
    case 'pending':
      return 'default'
  }
}
