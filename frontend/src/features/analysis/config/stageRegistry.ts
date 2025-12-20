/* eslint-disable max-lines -- Single source of truth consolidates all stage definitions, mappings, derived exports, and helper functions to eliminate the 661 lines of duplication across 3 files (Issue #397) */
/**
 * Stage Registry - Single Source of Truth for Pipeline Stage Configuration
 *
 * This file consolidates all stage-related configuration into one registry,
 * providing a single source of truth for stage metadata, display properties,
 * agent mappings, and derived exports.
 *
 * @module features/analysis/config/stageRegistry
 * @see Issue #397: Create unified stage registry
 */

import type { AgentStageName, StageName, WorkflowStageName } from '@app-types/sse'

import { logger } from '@/lib/logger'
import { STAGE_ORDER_CONSTANTS } from '@/lib/constants'

import type { AnalysisStage } from '../components/steps/AnalysisProgressCard'

// ============================================================================
// Type Definitions
// ============================================================================

/**
 * Category of stage in the pipeline
 * - workflow: Core pipeline stages that manage flow (extraction, embedding, routing, etc.)
 * - agent: Analysis agents selected by supervisor (tech_comparison, security_audit, etc.)
 * - quality: Final pipeline stages (aggregation, validation, generation)
 */
export type StageCategory = 'workflow' | 'agent' | 'quality'

/**
 * Complete stage registry entry with all metadata
 */
export interface StageRegistryEntry {
  /** Unique stage identifier (matches StageName) */
  id: StageName
  /** Canonical display title for UI */
  title: string
  /** Pipeline order (1-17, unique) */
  order: number
  /** UI grouping for progress visualization */
  uiStage: AnalysisStage
  /** Whether this stage can be skipped by supervisor routing */
  optional?: boolean
  /** Stage category for filtering and grouping */
  category: StageCategory
  /** Backend agent type names that map to this stage */
  agentTypes?: string[]
}

// ============================================================================
// Stage Registry - Complete Stage Metadata
// ============================================================================

/**
 * Complete stage registry with all 17 pipeline stages
 *
 * Order breakdown:
 * - 1-3:   Core workflow (extraction, embedding, routing)
 * - 4-10:  Agent analysis (7 agents, all optional)
 * - 11-13: Quality pipeline (aggregation, validation, generation)
 * - 14-17: Optional workflow stages (chunking, workflow, pattern_comparison, metrics)
 */
export const STAGE_REGISTRY: Record<StageName, StageRegistryEntry> = {
  // ===== WORKFLOW STAGES (Core Pipeline Flow) =====
  extraction: {
    id: 'extraction',
    title: 'Content Extraction',
    order: STAGE_ORDER_CONSTANTS.STAGE_EXTRACTION,
    uiStage: 'extracting',
    category: 'workflow',
    agentTypes: ['extraction'],
  },
  embedding: {
    id: 'embedding',
    title: 'Embedding Generation',
    order: STAGE_ORDER_CONSTANTS.STAGE_CHUNKING,
    uiStage: 'processing',
    category: 'workflow',
    agentTypes: ['embedding'],
  },
  supervisor_routing: {
    id: 'supervisor_routing',
    title: 'Routing to Agents',
    order: STAGE_ORDER_CONSTANTS.STAGE_EMBEDDING,
    uiStage: 'processing',
    category: 'workflow',
    agentTypes: ['supervisor', 'supervisor_route'],
  },

  // ===== AGENT STAGES (Analysis Agents - All Optional) =====
  tech_comparison: {
    id: 'tech_comparison',
    title: 'Tech Comparison',
    order: STAGE_ORDER_CONSTANTS.STAGE_AGENT_CONTENT_ANALYSIS,
    uiStage: 'analyzing',
    optional: true,
    category: 'agent',
    agentTypes: ['tech_comparator'],
  },
  security_audit: {
    id: 'security_audit',
    title: 'Security Audit',
    order: STAGE_ORDER_CONSTANTS.STAGE_AGENT_SECURITY_AUDITOR,
    uiStage: 'analyzing',
    optional: true,
    category: 'agent',
    agentTypes: ['security_auditor'],
  },
  implementation_planning: {
    id: 'implementation_planning',
    title: 'Implementation Planning',
    order: STAGE_ORDER_CONSTANTS.STAGE_AGENT_IMPLEMENTATION_PLANNER,
    uiStage: 'analyzing',
    optional: true,
    category: 'agent',
    // Maps to BOTH implementation_planner AND integration_feasibility
    agentTypes: ['implementation_planner', 'integration_feasibility'],
  },
  performance_audit: {
    id: 'performance_audit',
    title: 'Performance Audit',
    order: STAGE_ORDER_CONSTANTS.STAGE_AGENT_CODE_QUALITY,
    uiStage: 'analyzing',
    optional: true,
    category: 'agent',
    agentTypes: ['performance_auditor', 'performance_analyst'],
  },
  code_quality_audit: {
    id: 'code_quality_audit',
    title: 'Code Quality Audit',
    order: STAGE_ORDER_CONSTANTS.STAGE_AGENT_PERFORMANCE_OPTIMIZER,
    uiStage: 'analyzing',
    optional: true,
    category: 'agent',
    agentTypes: ['code_quality_reviewer', 'code_quality_critic'],
  },
  trends_analysis: {
    id: 'trends_analysis',
    title: 'Trends Analysis',
    order: STAGE_ORDER_CONSTANTS.STAGE_AGENT_TESTING_STRATEGIST,
    uiStage: 'analyzing',
    optional: true,
    category: 'agent',
    agentTypes: ['trends_analyst', 'trend_validator'],
  },
  dependencies_analysis: {
    id: 'dependencies_analysis',
    title: 'Dependencies Analysis',
    order: STAGE_ORDER_CONSTANTS.STAGE_AGENT_TESTING_STRATEGIST,
    uiStage: 'analyzing',
    optional: true,
    category: 'agent',
    agentTypes: ['dependencies_analyzer', 'dependency_mapper'],
  },

  // ===== QUALITY STAGES (Final Pipeline Stages) =====
  aggregation: {
    id: 'aggregation',
    title: 'Aggregating Results',
    order: STAGE_ORDER_CONSTANTS.STAGE_QUALITY_AGGREGATION,
    uiStage: 'generating',
    category: 'quality',
    agentTypes: ['aggregation'],
  },
  quality_validation: {
    id: 'quality_validation',
    title: 'Quality Validation',
    order: STAGE_ORDER_CONSTANTS.STAGE_QUALITY_VALIDATION,
    uiStage: 'generating',
    category: 'quality',
    agentTypes: ['quality_validation'],
  },
  artifact_generation: {
    id: 'artifact_generation',
    title: 'Generating Report',
    order: STAGE_ORDER_CONSTANTS.STAGE_QUALITY_GENERATION,
    uiStage: 'generating',
    category: 'quality',
    agentTypes: ['artifact_generation'],
  },

  // ===== OPTIONAL WORKFLOW STAGES =====
  chunking: {
    id: 'chunking',
    title: 'Content Chunking',
    order: STAGE_ORDER_CONSTANTS.STAGE_ARTIFACT_CHUNKING,
    uiStage: 'processing',
    optional: true,
    category: 'workflow',
    agentTypes: ['chunking'],
  },
  workflow: {
    id: 'workflow',
    title: 'Workflow',
    order: STAGE_ORDER_CONSTANTS.STAGE_ARTIFACT_WORKFLOW,
    uiStage: 'processing',
    category: 'workflow',
  },
  pattern_comparison: {
    id: 'pattern_comparison',
    title: 'Pattern Comparison',
    order: STAGE_ORDER_CONSTANTS.STAGE_ARTIFACT_PATTERN_COMPARISON,
    uiStage: 'analyzing',
    optional: true,
    category: 'workflow',
  },
  metrics: {
    id: 'metrics',
    title: 'Metrics Collection',
    order: STAGE_ORDER_CONSTANTS.STAGE_ARTIFACT_METRICS,
    uiStage: 'generating',
    optional: true,
    category: 'workflow',
  },
}

// ============================================================================
// Derived Exports - Computed from Registry
// ============================================================================

/**
 * Stage configuration compatible with existing code
 * Maps to the old STAGE_CONFIG format for backward compatibility
 */
export const STAGE_CONFIG: Record<
  StageName,
  { title: string; order: number; uiStage: AnalysisStage; optional?: boolean }
> = Object.fromEntries(
  Object.entries(STAGE_REGISTRY).map(([key, entry]) => [
    key,
    {
      title: entry.title,
      order: entry.order,
      uiStage: entry.uiStage,
      ...(entry.optional && { optional: entry.optional }),
    },
  ])
) as Record<StageName, { title: string; order: number; uiStage: AnalysisStage; optional?: boolean }>

/**
 * All stage names in pipeline order
 */
export const ALL_STAGES: StageName[] = Object.values(STAGE_REGISTRY)
  .sort((a, b) => a.order - b.order)
  .map((entry) => entry.id)

/**
 * Set of valid stage names for O(1) lookup
 */
export const VALID_STAGES: Set<StageName> = new Set(ALL_STAGES)

/**
 * Map backend agent type names to frontend stage names
 * Inverse of agentTypes in registry entries
 */
export const AGENT_TO_STAGE_MAP: Record<string, AgentStageName> = Object.entries(STAGE_REGISTRY)
  .filter(([, entry]) => entry.agentTypes)
  .flatMap(([, entry]) => entry.agentTypes!.map((agentType) => [agentType, entry.id]))
  .reduce(
    (acc, [agentType, stageId]) => {
      acc[agentType] = stageId as AgentStageName
      return acc
    },
    {} as Record<string, AgentStageName>
  )

/**
 * Map frontend stage names to backend agent types
 * Forward mapping from registry entries
 */
export const STAGE_TO_AGENT_MAP: Record<StageName, string[]> = Object.fromEntries(
  Object.entries(STAGE_REGISTRY)
    .filter(([, entry]) => entry.agentTypes)
    .map(([key, entry]) => [key, entry.agentTypes!])
) as Record<StageName, string[]>

/**
 * Total number of stages in pipeline
 */
export const TOTAL_STAGES = ALL_STAGES.length

/**
 * Optional stages that can be skipped by supervisor
 */
export const OPTIONAL_STAGES: StageName[] = Object.values(STAGE_REGISTRY)
  .filter((entry) => entry.optional)
  .map((entry) => entry.id)

/**
 * Core workflow stages (for progress calculation)
 * Stages that are always present in the pipeline
 */
export const WORKING_STAGES: StageName[] = Object.values(STAGE_REGISTRY)
  .filter((entry) => !entry.optional)
  .sort((a, b) => a.order - b.order)
  .map((entry) => entry.id)

// ============================================================================
// Helper Functions
// ============================================================================

/**
 * Get canonical display title for a stage
 *
 * @param name - Stage name
 * @returns Display title, or the name itself if not found
 */
export function getStageTitle(name: StageName): string {
  return STAGE_REGISTRY[name]?.title ?? name
}

/**
 * Get all stages sorted by pipeline order
 *
 * @returns Array of stage entries in order
 */
export function getSortedStages(): StageRegistryEntry[] {
  return Object.values(STAGE_REGISTRY).sort((a, b) => a.order - b.order)
}

/**
 * Get optional stage names
 *
 * @returns Array of optional stage names
 */
export function getOptionalStages(): StageName[] {
  return OPTIONAL_STAGES
}

/**
 * Get stages by category
 *
 * @param category - Stage category to filter by
 * @returns Array of stage entries in the category
 */
export function getStagesByCategory(category: StageCategory): StageRegistryEntry[] {
  return Object.values(STAGE_REGISTRY)
    .filter((entry) => entry.category === category)
    .sort((a, b) => a.order - b.order)
}

/**
 * Normalize backend stage/agent name to frontend stage name
 *
 * Handles:
 * - Backend agent type names (e.g., 'implementation_planner' → 'implementation_planning')
 * - Backend stage aliases (e.g., 'supervisor' → 'supervisor_routing')
 * - Already-normalized stage names (pass through)
 *
 * @param backendName - Raw stage/agent name from backend SSE event
 * @returns Frontend StageName or null if unknown
 */
export function normalizeStageNameFromBackend(backendName: string): StageName | null {
  // Check if it's already a valid stage name
  if (VALID_STAGES.has(backendName as StageName)) {
    return backendName as StageName
  }

  // Check agent type mapping
  if (backendName in AGENT_TO_STAGE_MAP) {
    return AGENT_TO_STAGE_MAP[backendName]
  }

  // Unknown stage - log warning
  logger.warn('Unknown backend stage/agent name received', {
    backendName,
    availableStages: Object.keys(STAGE_CONFIG),
    availableAgents: Object.keys(AGENT_TO_STAGE_MAP),
  })
  return null
}

/**
 * Type guard: Check if a string is a valid stage name
 *
 * @param name - String to check
 * @returns True if name is a valid StageName
 */
export function isValidStage(name: string): name is StageName {
  return VALID_STAGES.has(name as StageName)
}

/**
 * Type guard: Check if a stage name is an agent stage (displayed in UI)
 *
 * @param stage - Stage name to check
 * @returns True if stage is an AgentStageName
 */
export function isAgentStage(stage: StageName): stage is AgentStageName {
  const entry = STAGE_REGISTRY[stage]
  return entry !== undefined && entry.category !== 'workflow'
}

/**
 * Type guard: Check if a stage name is a workflow stage
 *
 * @param stage - Stage name to check
 * @returns True if stage is a WorkflowStageName
 */
export function isWorkflowStage(stage: StageName): stage is WorkflowStageName {
  const workflowStages: WorkflowStageName[] = ['workflow', 'pattern_comparison', 'metrics']
  return workflowStages.includes(stage as WorkflowStageName)
}

/**
 * Get stage order number
 *
 * @param name - Stage name
 * @returns Pipeline order number, or Infinity if not found
 */
export function getStageOrder(name: StageName): number {
  return STAGE_REGISTRY[name]?.order ?? Infinity
}

/**
 * Get stage by backend agent type
 *
 * @param agentType - Backend agent type name
 * @returns Stage registry entry or undefined if not found
 */
export function getStageByAgentType(agentType: string): StageRegistryEntry | undefined {
  const stageName = AGENT_TO_STAGE_MAP[agentType]
  return stageName ? STAGE_REGISTRY[stageName] : undefined
}

/**
 * Get all agent types for a stage
 *
 * @param stageName - Frontend stage name
 * @returns Array of backend agent type names, or empty array if none
 */
export function getAgentTypesForStage(stageName: StageName): string[] {
  return STAGE_REGISTRY[stageName]?.agentTypes ?? []
}

/**
 * Map agent type (backend name) to stage name (frontend name)
 *
 * @param agentType - Backend agent type name
 * @returns Frontend stage name or null if not found
 */
export function getStageNameFromAgentType(agentType: string): AgentStageName | null {
  // Check direct mapping
  if (agentType in AGENT_TO_STAGE_MAP) {
    return AGENT_TO_STAGE_MAP[agentType]
  }
  // Check if it's already a stage name
  if (VALID_STAGES.has(agentType as StageName)) {
    return agentType as AgentStageName
  }
  return null
}
