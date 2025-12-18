/**
 * ProgressTracker Constants
 * Shared stage configuration and helper functions
 */

import type { StageName, StageStatus } from '@app-types/sse'

/**
 * All available pipeline stages
 * Note: Agents are dynamically selected by supervisor (0-8 agents)
 * Total stages = 5 fixed + N agents (where 0 ≤ N ≤ 8)
 */
export const ALL_STAGES: StageName[] = [
  // Core workflow stages (always present)
  'extraction',
  'embedding',
  'supervisor_routing',
  // Agent stages (dynamically selected, 0-8)
  'tech_comparison',
  'security_audit',
  'implementation_planning', // Used by BOTH implementation_planner AND integration_feasibility
  'performance_audit',
  'code_quality_audit',
  'trends_analysis',
  'dependencies_analysis',
  // Workflow stages
  'aggregation',
  'quality_validation',
  'artifact_generation',
  // Optional stages
  'chunking', // Only if ENABLE_COARSE_TO_FINE=true
  'workflow', // Error handling
  'pattern_comparison',
  'metrics',
]

/**
 * Currently working stages (for testing with real backend)
 */
export const WORKING_STAGES: StageName[] = ['extraction', 'embedding', 'supervisor_routing']

/**
 * Stage configuration with user-friendly labels
 */
export const STAGE_CONFIG: Record<StageName, { label: string }> = {
  // Core workflow stages
  extraction: { label: 'Content Extraction' },
  embedding: { label: 'Embedding Generation' },
  supervisor_routing: { label: 'Agent Routing' },
  aggregation: { label: 'Results Aggregation' },
  quality_validation: { label: 'Quality Validation' },
  artifact_generation: { label: 'Artifact Generation' },
  // Agent stages
  tech_comparison: { label: 'Technology Comparison' },
  security_audit: { label: 'Security Audit' },
  implementation_planning: { label: 'Implementation Planning' }, // Covers both implementation_planner AND integration_feasibility
  performance_audit: { label: 'Performance Analysis' },
  code_quality_audit: { label: 'Code Quality Review' },
  trends_analysis: { label: 'Trends Analysis' },
  dependencies_analysis: { label: 'Dependencies Review' },
  // Optional stages
  chunking: { label: 'Content Chunking' },
  workflow: { label: 'Workflow' },
  pattern_comparison: { label: 'Pattern Comparison' },
  metrics: { label: 'Metrics Collection' },
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
