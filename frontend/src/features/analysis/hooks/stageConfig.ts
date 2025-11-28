/**
 * Stage configuration - Maps backend stages to UI representation
 */

import type { StageName } from '@app-types/sse'

import type { AnalysisStage } from '../components/steps/AnalysisProgressCard'

export interface StageConfig {
  title: string
  order: number
  uiStage: AnalysisStage
}

export const STAGE_CONFIG: Record<StageName, StageConfig> = {
  extraction: { title: 'Content Extraction', order: 1, uiStage: 'extracting' },
  supervisor_routing: { title: 'Routing to Agents', order: 2, uiStage: 'processing' },
  tech_comparison: { title: 'Tech Comparison', order: 3, uiStage: 'analyzing' },
  security_audit: { title: 'Security Audit', order: 4, uiStage: 'analyzing' },
  implementation_planning: { title: 'Implementation Planning', order: 5, uiStage: 'analyzing' },
  performance_audit: { title: 'Performance Audit', order: 6, uiStage: 'analyzing' },
  code_quality_audit: { title: 'Code Quality Audit', order: 7, uiStage: 'analyzing' },
  trends_analysis: { title: 'Trends Analysis', order: 8, uiStage: 'analyzing' },
  dependencies_analysis: { title: 'Dependencies Analysis', order: 9, uiStage: 'analyzing' },
  aggregation: { title: 'Aggregating Results', order: 10, uiStage: 'generating' },
  artifact_generation: { title: 'Generating Report', order: 11, uiStage: 'generating' },
}

export const TOTAL_STAGES = Object.keys(STAGE_CONFIG).length

/**
 * Backend agent name to frontend stage name mapping
 * Workaround for issue #88: Backend sends agent names instead of stage names
 * @see https://github.com/ArieGoldkin/SkillForge/issues/88
 */
const AGENT_TO_STAGE_MAP: Record<string, StageName> = {
  // Direct matches (backend sends correct name)
  extraction: 'extraction',
  aggregation: 'aggregation',
  artifact_generation: 'artifact_generation',

  // Agent names that need mapping
  implementation_planner: 'implementation_planning',
  tech_comparator: 'tech_comparison',
  security_auditor: 'security_audit',
  performance_auditor: 'performance_audit',
  code_quality_reviewer: 'code_quality_audit',
  trends_analyst: 'trends_analysis',
  dependencies_analyzer: 'dependencies_analysis',

  // Alternative names backend might send
  supervisor: 'supervisor_routing',
  supervisor_route: 'supervisor_routing',
  embedding: 'extraction', // embedding is part of extraction phase

  // Sub-agents that are part of larger stages
  integration_feasibility: 'implementation_planning', // part of implementation planning
}

/**
 * Normalize backend stage/agent name to frontend StageName
 * Returns the mapped stage name or the original if it's already valid
 */
export function normalizeStageNameFromBackend(backendName: string): StageName | null {
  // Check if it's already a valid stage name
  if (backendName in STAGE_CONFIG) {
    return backendName as StageName
  }

  // Check the mapping
  if (backendName in AGENT_TO_STAGE_MAP) {
    return AGENT_TO_STAGE_MAP[backendName]
  }

  // Unknown stage - return null to skip
  console.warn(`[SSE] Unknown stage name from backend: ${backendName}`)
  return null
}

/**
 * Estimate remaining time based on completed stages
 */
export function estimateTimeRemaining(completedStages: number): string | undefined {
  if (completedStages === 0) {
    return '~2-3 minutes'
  }
  const remaining = TOTAL_STAGES - completedStages
  if (remaining <= 2) {
    return '~30 seconds'
  }
  if (remaining <= 5) {
    return '~1 minute'
  }
  return '~1-2 minutes'
}
