/**
 * Stage configuration - Maps backend stages to UI representation
 */

import type { AgentStageName, WorkflowStageName } from '@app-types/sse'

import type { AnalysisStage } from '../components/steps/AnalysisProgressCard'

export interface StageConfig {
  title: string
  order: number
  uiStage: AnalysisStage
  /** Whether this stage can be skipped by supervisor routing */
  optional?: boolean
}

/**
 * Configuration for agent stages (displayed in UI)
 * Only includes stages that represent actual agent work
 */
export const STAGE_CONFIG: Record<AgentStageName, StageConfig> = {
  extraction: { title: 'Content Extraction', order: 1, uiStage: 'extracting' },
  embedding: { title: 'Embedding Generation', order: 2, uiStage: 'processing' },
  supervisor_routing: { title: 'Routing to Agents', order: 3, uiStage: 'processing' },
  tech_comparison: { title: 'Tech Comparison', order: 4, uiStage: 'analyzing', optional: true },
  security_audit: { title: 'Security Audit', order: 5, uiStage: 'analyzing', optional: true },
  implementation_planning: {
    title: 'Implementation Planning',
    order: 6,
    uiStage: 'analyzing',
    optional: true,
  },
  performance_audit: { title: 'Performance Audit', order: 7, uiStage: 'analyzing', optional: true },
  code_quality_audit: {
    title: 'Code Quality Audit',
    order: 8,
    uiStage: 'analyzing',
    optional: true,
  },
  trends_analysis: { title: 'Trends Analysis', order: 9, uiStage: 'analyzing', optional: true },
  dependencies_analysis: {
    title: 'Dependencies Analysis',
    order: 10,
    uiStage: 'analyzing',
    optional: true,
  },
  integration_feasibility: {
    title: 'Integration Feasibility',
    order: 11,
    uiStage: 'analyzing',
    optional: true,
  },
  aggregation: { title: 'Aggregating Results', order: 12, uiStage: 'generating' },
  artifact_generation: { title: 'Generating Report', order: 13, uiStage: 'generating' },
}

export const TOTAL_STAGES = Object.keys(STAGE_CONFIG).length

/**
 * Backend agent name to frontend stage name mapping
 * Workaround for issue #88: Backend sends agent names instead of stage names
 * @see https://github.com/ArieGoldkin/SkillForge/issues/88
 */
const AGENT_TO_STAGE_MAP: Record<string, AgentStageName> = {
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
  embedding: 'embedding',
}

/**
 * Workflow-level stages that don't map to UI stages
 * These are used for workflow control but don't represent agent work
 */
const WORKFLOW_STAGES: WorkflowStageName[] = ['workflow', 'pattern_comparison', 'metrics']

/**
 * Normalize backend stage/agent name to frontend stage name
 *
 * @param backendName - Raw stage name from backend SSE event
 * @returns AgentStageName for UI display, WorkflowStageName for workflow control, or null if unknown
 */
export function normalizeStageNameFromBackend(
  backendName: string
): AgentStageName | WorkflowStageName | null {
  // Check if it's a workflow-level stage (not displayed in UI)
  if (WORKFLOW_STAGES.includes(backendName as WorkflowStageName)) {
    return backendName as WorkflowStageName
  }

  // Check if it's already a valid agent stage name
  if (backendName in STAGE_CONFIG) {
    return backendName as AgentStageName
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
 * Type guard to check if a stage name is an agent stage (displayed in UI)
 */
export function isAgentStage(stage: AgentStageName | WorkflowStageName): stage is AgentStageName {
  return stage in STAGE_CONFIG
}

/**
 * Get list of optional agent stages (can be skipped by supervisor)
 */
export function getOptionalStages(): AgentStageName[] {
  return (Object.entries(STAGE_CONFIG) as [AgentStageName, StageConfig][])
    .filter(([, config]) => config.optional)
    .map(([stage]) => stage)
}

/** Stage status entry for the status map */
export interface StageStatusEntry {
  status: 'pending' | 'running' | 'complete' | 'failed' | 'skipped'
  timestamp: string
  details?: Record<string, unknown>
}

/**
 * Map agent type (backend name) to stage name (frontend name)
 */
export function getStageNameFromAgentType(agentType: string): AgentStageName | null {
  // Check direct mapping
  if (agentType in AGENT_TO_STAGE_MAP) {
    return AGENT_TO_STAGE_MAP[agentType]
  }
  // Check if it's already a stage name
  if (agentType in STAGE_CONFIG) {
    return agentType as AgentStageName
  }
  return null
}

/**
 * Mark unselected optional agents as 'skipped' after supervisor completes
 * Bug #165 fix: Shows skipped state instead of pending for non-selected agents
 */
export function markSkippedAgents(
  stageStatuses: Map<AgentStageName, StageStatusEntry>,
  skippedAgentsInfo?: { agents: string[]; selectedAgents?: string[] }
): void {
  const supervisorStatus = stageStatuses.get('supervisor_routing')
  if (supervisorStatus?.status !== 'complete') return

  const selectedAgentStages = new Set<AgentStageName>()
  if (skippedAgentsInfo?.selectedAgents) {
    for (const agentType of skippedAgentsInfo.selectedAgents) {
      const stageName = getStageNameFromAgentType(agentType)
      if (stageName) {
        selectedAgentStages.add(stageName)
      }
    }
  }

  for (const agentStage of getOptionalStages()) {
    if (!stageStatuses.has(agentStage)) {
      // Determine skip reason
      let skipReason = 'Not selected by supervisor'

      // Check if this agent was explicitly skipped
      if (skippedAgentsInfo?.agents) {
        const agentType = Object.entries(AGENT_TO_STAGE_MAP).find(
          ([, stage]) => stage === agentStage
        )?.[0]
        if (agentType && skippedAgentsInfo.agents.includes(agentType)) {
          skipReason = 'Not applicable for this content type'
        } else if (!selectedAgentStages.has(agentStage)) {
          skipReason = 'Not selected by supervisor'
        }
      }

      stageStatuses.set(agentStage, {
        status: 'skipped',
        timestamp: supervisorStatus.timestamp,
        details: {
          skipped_by: 'supervisor_routing',
          skip_reason: skipReason,
        },
      })
    }
  }
}

/**
 * Estimate remaining time based on completed stages
 */
export function estimateTimeRemaining(completedStages: number): string | undefined {
  if (completedStages === 0) {
    return '~2-3 minutes'
  }
  const remaining = TOTAL_STAGES - completedStages
  if (remaining >= 10) {
    return '~1-2 minutes'
  }
  if (remaining <= 3) {
    return '~30 seconds'
  }
  if (remaining <= 6) {
    return '~1 minute'
  }
  if (remaining <= 9) {
    return '~1-2 minutes'
  }
  return '~2-3 minutes'
}
