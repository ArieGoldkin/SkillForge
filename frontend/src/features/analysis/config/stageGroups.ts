/**
 * Stage Groups Configuration for Hierarchical Accordion
 *
 * Defines the 7 logical groups for organizing 30 pipeline stages
 * into collapsible accordion sections.
 *
 * @module features/analysis/config/stageGroups
 */

import {
  ActivityIcon,
  AlertTriangleIcon,
  BrainCircuitIcon,
  CheckCircle2Icon,
  FilterIcon,
  LayoutGridIcon,
  SearchCheckIcon,
} from 'lucide-react'

import type { StageName } from '@/schemas/base'

import type { StageGroup } from '../types/accordion'

// ============================================================================
// Stage Group Definitions
// ============================================================================

/**
 * STAGE_GROUPS - The 7 logical groups for the hierarchical accordion
 *
 * Order:
 * 1. Core Workflow (3 stages) - extraction, embedding, supervisor_routing
 * 2. Content Analysis (7 stages) - Content-based agents (all optional)
 * 3. Tier 1: Universal (4 stages) - Always run in Quick+ mode
 * 4. Tier 2: Validation (4 stages) - Run in Standard+ mode
 * 5. Tier 3: Research (4 stages) - Run in Deep Dive mode
 * 6. Quality Pipeline (4 stages) - aggregation, quality_gate, quality_validation, artifact_generation
 * 7. Optional Stages (4 stages) - chunking, workflow, pattern_comparison, metrics
 */
export const STAGE_GROUPS: StageGroup[] = [
  // ===== GROUP 1: CORE WORKFLOW =====
  {
    id: 'core-workflow',
    label: 'Core Workflow',
    icon: LayoutGridIcon,
    stages: ['extraction', 'embedding', 'supervisor_routing'],
    description: 'Initial content processing and agent routing',
    optional: false,
  },

  // ===== GROUP 2: CONTENT ANALYSIS =====
  {
    id: 'content-analysis',
    label: 'Content Analysis',
    icon: BrainCircuitIcon,
    stages: [
      'tech_comparison',
      'security_audit',
      'implementation_planning',
      'performance_audit',
      'code_quality_audit',
      'trends_analysis',
      'dependencies_analysis',
    ],
    description: 'Content-specific analysis agents (supervisor selects 0-7 agents)',
    optional: true,
  },

  // ===== GROUP 3: TIER 1 - UNIVERSAL AGENTS =====
  {
    id: 'tier1-universal',
    label: 'Tier 1: Universal Agents',
    icon: ActivityIcon,
    stages: ['key_insights', 'pros_cons', 'audience_fit', 'actionable'],
    description: 'Essential insights for all content (Quick+ mode)',
    modes: ['quick', 'standard', 'deep'],
    optional: false,
  },

  // ===== GROUP 4: TIER 2 - VALIDATION AGENTS =====
  {
    id: 'tier2-validation',
    label: 'Tier 2: Validation Agents',
    icon: SearchCheckIcon,
    stages: ['fact_validation', 'source_credibility', 'freshness_check', 'alternatives_finding'],
    description: 'Fact-checking and source validation (Standard+ mode)',
    modes: ['standard', 'deep'],
    optional: false,
  },

  // ===== GROUP 5: TIER 3 - RESEARCH AGENTS =====
  {
    id: 'tier3-research',
    label: 'Tier 3: Research Agents',
    icon: FilterIcon,
    stages: ['deep_research', 'community_pulse', 'knowledge_curation', 'learning_path'],
    description: 'Deep research and community insights (Deep Dive mode only)',
    modes: ['deep'],
    optional: false,
  },

  // ===== GROUP 6: QUALITY PIPELINE =====
  {
    id: 'quality-pipeline',
    label: 'Quality Pipeline',
    icon: CheckCircle2Icon,
    stages: ['aggregation', 'quality_gate', 'quality_validation', 'artifact_generation'],
    description: 'Final synthesis, validation, and report generation',
    optional: false,
  },

  // ===== GROUP 7: OPTIONAL STAGES =====
  {
    id: 'optional-stages',
    label: 'Optional Stages',
    icon: AlertTriangleIcon,
    stages: ['chunking', 'workflow', 'pattern_comparison', 'metrics'],
    description: 'Optional workflow and diagnostic stages',
    optional: true,
  },
]

// ============================================================================
// Derived Exports
// ============================================================================

/**
 * Map of group IDs to StageGroup objects for O(1) lookup
 */
export const STAGE_GROUP_MAP = new Map<string, StageGroup>(
  STAGE_GROUPS.map((group) => [group.id, group])
)

/**
 * Map of stage names to their parent group ID
 */
export const STAGE_TO_GROUP_MAP = new Map<StageName, string>(
  STAGE_GROUPS.flatMap((group) => group.stages.map((stage) => [stage, group.id] as const))
)

/**
 * Get the parent group for a stage
 *
 * @param stageName - The stage name to look up
 * @returns The StageGroup object or undefined if not found
 */
export function getGroupForStage(stageName: StageName): StageGroup | undefined {
  const groupId = STAGE_TO_GROUP_MAP.get(stageName)
  return groupId ? STAGE_GROUP_MAP.get(groupId) : undefined
}

/**
 * Get all stage names for a group
 *
 * @param groupId - The group ID to look up
 * @returns Array of stage names in that group, or empty array if not found
 */
export function getStagesForGroup(groupId: string): StageName[] {
  return STAGE_GROUP_MAP.get(groupId)?.stages ?? []
}

/**
 * Check if a group is active for a given analysis mode
 *
 * @param groupId - The group ID to check
 * @param mode - The analysis mode (quick/standard/deep)
 * @returns True if the group is active in that mode
 */
export function isGroupActiveInMode(groupId: string, mode: 'quick' | 'standard' | 'deep'): boolean {
  const group = STAGE_GROUP_MAP.get(groupId)
  if (!group) return false

  // If group has no mode restrictions, it's active in all modes
  if (!group.modes) return true

  // Check if current mode is in the group's allowed modes
  return group.modes.includes(mode)
}
