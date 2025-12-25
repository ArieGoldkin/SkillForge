/**
 * Stage Registry Tests
 *
 * Comprehensive test suite for the unified stage registry configuration.
 * Validates registry structure, derived exports, agent mappings, and helper functions.
 *
 * @module features/analysis/config/__tests__/stageRegistry.test
 * @see Issue #397: Create unified stage registry
 */

import { describe, expect, it } from 'vitest'

import type { AgentStageName, StageName } from '@/schemas/sse'

import type { AnalysisStage } from '../../components/steps/AnalysisProgressCard'
import {
  AGENT_TO_STAGE_MAP,
  ALL_STAGES,
  getAgentsByTier,
  getAgentsUpToTier,
  getAgentTypesForStage,
  getAllTieredAgents,
  getOptionalStages,
  getStageByAgentType,
  getStageOrder,
  getStagesByCategory,
  getStageTitle,
  getSortedStages,
  isAgentStage,
  isValidStage,
  isWorkflowStage,
  normalizeStageNameFromBackend,
  OPTIONAL_STAGES,
  STAGE_CONFIG,
  STAGE_REGISTRY,
  STAGE_TO_AGENT_MAP,
  type StageCategory,
  TOTAL_STAGES,
  VALID_STAGES,
  WORKING_STAGES,
} from '../stageRegistry'

// ============================================================================
// Test Data & Constants
// ============================================================================

const EXPECTED_STAGE_COUNT = 30

const EXPECTED_STAGE_NAMES: StageName[] = [
  // Workflow stages (core pipeline)
  'extraction',
  'embedding',
  'supervisor_routing',
  // Content-based agent stages (all optional)
  'tech_comparison',
  'dependencies_analysis',
  'security_audit',
  'implementation_planning',
  'performance_audit',
  'code_quality_audit',
  'trends_analysis',
  // Tier 1: Universal agents
  'key_insights',
  'pros_cons',
  'audience_fit',
  'actionable',
  // Tier 2: Validation agents
  'fact_validation',
  'source_credibility',
  'freshness_check',
  'alternatives_finding',
  // Tier 3: Research agents
  'deep_research',
  'community_pulse',
  'knowledge_curation',
  'learning_path',
  // Quality stages
  'aggregation',
  'quality_gate',
  'quality_validation',
  'artifact_generation',
  // Optional workflow stages
  'chunking',
  'workflow',
  'pattern_comparison',
  'metrics',
]

const EXPECTED_OPTIONAL_STAGES: StageName[] = [
  // Content-based agents
  'tech_comparison',
  'security_audit',
  'implementation_planning',
  'performance_audit',
  'code_quality_audit',
  'trends_analysis',
  'dependencies_analysis',
  // Tier 1: Universal agents
  'key_insights',
  'pros_cons',
  'audience_fit',
  'actionable',
  // Tier 2: Validation agents
  'fact_validation',
  'source_credibility',
  'freshness_check',
  'alternatives_finding',
  // Tier 3: Research agents
  'deep_research',
  'community_pulse',
  'knowledge_curation',
  'learning_path',
  // Optional workflow stages
  'chunking',
  'pattern_comparison',
  'metrics',
]

const EXPECTED_WORKING_STAGES: StageName[] = [
  'extraction',
  'embedding',
  'supervisor_routing',
  'aggregation',
  'quality_gate',
  'quality_validation',
  'artifact_generation',
  'workflow',
]

const KNOWN_AGENT_TYPES = [
  // Core workflow
  'extraction',
  'embedding',
  'supervisor',
  'supervisor_route',
  // Content-based agents
  'tech_comparator',
  'security_auditor',
  'implementation_planner',
  'integration_feasibility',
  'performance_auditor',
  'performance_analyst',
  'code_quality_reviewer',
  'code_quality_critic',
  'trends_analyst',
  'trend_validator',
  'dependencies_analyzer',
  'dependency_mapper',
  // Tier 1: Universal agents
  'key_insights',
  'pros_cons',
  'audience_fit',
  'actionable',
  // Tier 2: Validation agents
  'fact_validator',
  'source_credibility',
  'freshness_checker',
  'alternatives_finder',
  // Tier 3: Research agents
  'deep_researcher',
  'community_pulse',
  'knowledge_curator',
  'learning_path_advisor',
  // Quality stages
  'aggregation',
  'quality_gate',
  'quality_validation',
  'artifact_generation',
  'chunking',
]

// ============================================================================
// 1. Registry Structure Tests
// ============================================================================

describe('Stage Registry Structure', () => {
  describe('Basic Structure', () => {
    it('should have exactly 30 stages defined', () => {
      const stageCount = Object.keys(STAGE_REGISTRY).length
      expect(stageCount).toBe(EXPECTED_STAGE_COUNT)
    })

    it('should define all expected stage names', () => {
      const registryKeys = Object.keys(STAGE_REGISTRY) as StageName[]
      expect(registryKeys).toHaveLength(EXPECTED_STAGE_COUNT)

      // All expected stages should be present
      EXPECTED_STAGE_NAMES.forEach((stageName) => {
        expect(registryKeys).toContain(stageName)
      })
    })

    it('should not have any unexpected stages', () => {
      const registryKeys = Object.keys(STAGE_REGISTRY) as StageName[]
      const unexpectedStages = registryKeys.filter((key) => !EXPECTED_STAGE_NAMES.includes(key))
      expect(unexpectedStages).toEqual([])
    })
  })

  describe('Required Fields', () => {
    it('should have all required fields for each stage', () => {
      Object.entries(STAGE_REGISTRY).forEach(([key, entry]) => {
        expect(entry.id, `${key} should have id`).toBeDefined()
        expect(entry.title, `${key} should have title`).toBeDefined()
        expect(entry.order, `${key} should have order`).toBeDefined()
        expect(entry.uiStage, `${key} should have uiStage`).toBeDefined()
        expect(entry.category, `${key} should have category`).toBeDefined()

        // Verify types
        expect(typeof entry.id, `${key}.id should be string`).toBe('string')
        expect(typeof entry.title, `${key}.title should be string`).toBe('string')
        expect(typeof entry.order, `${key}.order should be number`).toBe('number')
        expect(typeof entry.uiStage, `${key}.uiStage should be string`).toBe('string')
        expect(typeof entry.category, `${key}.category should be string`).toBe('string')
      })
    })

    it('should have id matching the registry key', () => {
      Object.entries(STAGE_REGISTRY).forEach(([key, entry]) => {
        expect(entry.id).toBe(key)
      })
    })

    it('should have valid category values', () => {
      const validCategories: StageCategory[] = ['workflow', 'agent', 'quality']

      Object.entries(STAGE_REGISTRY).forEach(([key, entry]) => {
        expect(
          validCategories,
          `${key}.category should be one of: ${validCategories.join(', ')}`
        ).toContain(entry.category)
      })
    })

    it('should have valid uiStage values', () => {
      const validUiStages: AnalysisStage[] = [
        'extracting',
        'processing',
        'analyzing',
        'generating',
        'complete',
      ]

      Object.entries(STAGE_REGISTRY).forEach(([key, entry]) => {
        expect(
          validUiStages,
          `${key}.uiStage should be one of: ${validUiStages.join(', ')}`
        ).toContain(entry.uiStage)
      })
    })
  })

  describe('Order Values', () => {
    it('should have order values in valid range (1-29)', () => {
      const orderValues = Object.values(STAGE_REGISTRY).map((entry) => entry.order)

      // Note: quality_gate and quality_validation share order 24, so we have 29 unique orders for 30 stages
      const uniqueOrders = new Set(orderValues)
      expect(uniqueOrders.size).toBe(29) // One duplicate at order 24

      // Check range
      orderValues.forEach((order) => {
        expect(order).toBeGreaterThanOrEqual(1)
        expect(order).toBeLessThanOrEqual(29) // Max order is 29 due to duplicate
      })
    })

    it('should have mostly sequential order values with one duplicate at position 24', () => {
      const orderValues = Object.values(STAGE_REGISTRY).map((entry) => entry.order)
      const sortedOrders = [...orderValues].sort((a, b) => a - b)

      // Should be [1, 2, 3, ..., 23, 24, 24, 25, ..., 29]
      // quality_gate and quality_validation both have order 24
      expect(sortedOrders.filter((o) => o === 24).length).toBe(2) // Two stages at order 24
      expect(sortedOrders[0]).toBe(1)
      expect(sortedOrders[sortedOrders.length - 1]).toBe(29) // Last order is 29
    })

    it('should have correct order ranges by category', () => {
      const workflowStages = Object.values(STAGE_REGISTRY).filter(
        (entry) => entry.category === 'workflow'
      )
      const agentStages = Object.values(STAGE_REGISTRY).filter(
        (entry) => entry.category === 'agent'
      )
      const qualityStages = Object.values(STAGE_REGISTRY).filter(
        (entry) => entry.category === 'quality'
      )

      // Core workflow stages: 1-3
      const coreWorkflowOrders = workflowStages
        .filter((entry) => entry.order <= 3)
        .map((entry) => entry.order)
      expect(coreWorkflowOrders).toEqual([1, 2, 3])

      // Agent stages: 4-22 (7 content-based + 12 tier-based = 19 agents)
      const agentOrders = agentStages.map((entry) => entry.order).sort((a, b) => a - b)
      expect(agentOrders.length).toBe(19) // 7 content-based + 4 tier1 + 4 tier2 + 4 tier3
      expect(agentOrders[0]).toBe(4) // First content-based agent
      expect(agentOrders[agentOrders.length - 1]).toBe(22) // Last tier3 agent

      // Quality stages: 23-25 (4 quality stages, quality_gate and quality_validation share 24)
      const qualityOrders = qualityStages.map((entry) => entry.order).sort((a, b) => a - b)
      expect(qualityOrders.length).toBe(4)
      expect(qualityOrders[0]).toBe(23) // aggregation

      // Optional workflow stages: 26-29 (chunking, workflow, pattern_comparison, metrics)
      const optionalWorkflowOrders = workflowStages
        .filter((entry) => entry.order >= 26)
        .map((entry) => entry.order)
        .sort((a, b) => a - b)
      expect(optionalWorkflowOrders).toEqual([26, 27, 28, 29])
    })
  })

  describe('Optional Stages', () => {
    it('should mark all agent stages as optional', () => {
      const agentStages = Object.values(STAGE_REGISTRY).filter(
        (entry) => entry.category === 'agent'
      )

      agentStages.forEach((entry) => {
        expect(entry.optional, `${entry.id} should be optional`).toBe(true)
      })
    })

    it('should have exactly 22 optional stages', () => {
      const optionalStages = Object.values(STAGE_REGISTRY).filter((entry) => entry.optional)
      expect(optionalStages).toHaveLength(22) // 7 content-based + 12 tier-based + 3 workflow optional
    })

    it('should match expected optional stages list', () => {
      const optionalStageIds = Object.values(STAGE_REGISTRY)
        .filter((entry) => entry.optional)
        .map((entry) => entry.id)
        .sort()

      expect(optionalStageIds).toEqual([...EXPECTED_OPTIONAL_STAGES].sort())
    })
  })

  describe('Agent Types Mapping', () => {
    it('should have agentTypes for most stages', () => {
      const stagesWithAgentTypes = Object.values(STAGE_REGISTRY).filter(
        (entry) => entry.agentTypes && entry.agentTypes.length > 0
      )

      // At least 14 stages should have agent types (all workflow, agent, and quality stages except workflow/pattern_comparison/metrics)
      expect(stagesWithAgentTypes.length).toBeGreaterThanOrEqual(14)
    })

    it('should have non-empty agentTypes arrays when defined', () => {
      Object.entries(STAGE_REGISTRY).forEach(([key, entry]) => {
        if (entry.agentTypes) {
          expect(entry.agentTypes.length, `${key}.agentTypes should not be empty`).toBeGreaterThan(
            0
          )
        }
      })
    })

    it('should have unique agentTypes across all stages', () => {
      const allAgentTypes: string[] = []

      Object.values(STAGE_REGISTRY).forEach((entry) => {
        if (entry.agentTypes) {
          allAgentTypes.push(...entry.agentTypes)
        }
      })

      const uniqueAgentTypes = new Set(allAgentTypes)
      expect(uniqueAgentTypes.size).toBe(allAgentTypes.length)
    })
  })
})

// ============================================================================
// 2. Derived Exports Tests
// ============================================================================

describe('Derived Exports', () => {
  describe('STAGE_CONFIG', () => {
    it('should have correct shape', () => {
      expect(STAGE_CONFIG).toBeDefined()
      expect(typeof STAGE_CONFIG).toBe('object')

      Object.entries(STAGE_CONFIG).forEach(([key, config]) => {
        expect(config.title, `${key} should have title`).toBeDefined()
        expect(config.order, `${key} should have order`).toBeDefined()
        expect(config.uiStage, `${key} should have uiStage`).toBeDefined()

        // optional field should only be present if true
        if ('optional' in config) {
          expect(config.optional).toBe(true)
        }
      })
    })

    it('should have all 17 stages', () => {
      expect(Object.keys(STAGE_CONFIG)).toHaveLength(EXPECTED_STAGE_COUNT)
    })

    it('should match registry data', () => {
      Object.entries(STAGE_CONFIG).forEach(([key, config]) => {
        const registryEntry = STAGE_REGISTRY[key as StageName]
        expect(registryEntry).toBeDefined()

        expect(config.title).toBe(registryEntry.title)
        expect(config.order).toBe(registryEntry.order)
        expect(config.uiStage).toBe(registryEntry.uiStage)

        if (registryEntry.optional) {
          expect(config.optional).toBe(true)
        }
      })
    })
  })

  describe('ALL_STAGES', () => {
    it('should have 30 entries', () => {
      expect(ALL_STAGES).toHaveLength(EXPECTED_STAGE_COUNT)
    })

    it('should be sorted by pipeline order', () => {
      const orders = ALL_STAGES.map((stageName) => STAGE_REGISTRY[stageName].order)

      // Verify ascending or equal order (quality_gate and quality_validation share order 12)
      for (let i = 1; i < orders.length; i++) {
        expect(orders[i]).toBeGreaterThanOrEqual(orders[i - 1])
      }
    })

    it('should match expected stage names', () => {
      expect(ALL_STAGES).toEqual(EXPECTED_STAGE_NAMES)
    })

    it('should start with extraction and end with metrics', () => {
      expect(ALL_STAGES[0]).toBe('extraction')
      expect(ALL_STAGES[ALL_STAGES.length - 1]).toBe('metrics')
    })
  })

  describe('VALID_STAGES', () => {
    it('should be a Set with 30 entries', () => {
      expect(VALID_STAGES).toBeInstanceOf(Set)
      expect(VALID_STAGES.size).toBe(EXPECTED_STAGE_COUNT)
    })

    it('should contain all expected stage names', () => {
      EXPECTED_STAGE_NAMES.forEach((stageName) => {
        expect(VALID_STAGES.has(stageName)).toBe(true)
      })
    })

    it('should provide O(1) lookup performance', () => {
      // Should return instantly for any stage
      expect(VALID_STAGES.has('extraction')).toBe(true)
      expect(VALID_STAGES.has('invalid_stage' as StageName)).toBe(false)
    })
  })

  describe('TOTAL_STAGES', () => {
    it('should equal 30', () => {
      expect(TOTAL_STAGES).toBe(EXPECTED_STAGE_COUNT)
    })

    it('should match ALL_STAGES length', () => {
      expect(TOTAL_STAGES).toBe(ALL_STAGES.length)
    })

    it('should match registry size', () => {
      expect(TOTAL_STAGES).toBe(Object.keys(STAGE_REGISTRY).length)
    })
  })

  describe('OPTIONAL_STAGES', () => {
    it('should contain expected optional stages', () => {
      expect(OPTIONAL_STAGES.sort()).toEqual([...EXPECTED_OPTIONAL_STAGES].sort())
    })

    it('should have 22 entries', () => {
      expect(OPTIONAL_STAGES).toHaveLength(22) // 7 content-based + 12 tier-based + 3 workflow optional
    })

    it('should match registry optional flag', () => {
      const registryOptionalStages = Object.values(STAGE_REGISTRY)
        .filter((entry) => entry.optional)
        .map((entry) => entry.id)
        .sort()

      expect([...OPTIONAL_STAGES].sort()).toEqual(registryOptionalStages)
    })

    it('should include all agent stages', () => {
      const agentStages = Object.values(STAGE_REGISTRY)
        .filter((entry) => entry.category === 'agent')
        .map((entry) => entry.id)

      agentStages.forEach((stageName) => {
        expect(OPTIONAL_STAGES).toContain(stageName)
      })
    })
  })

  describe('WORKING_STAGES', () => {
    it('should contain expected working stages', () => {
      expect([...WORKING_STAGES].sort()).toEqual([...EXPECTED_WORKING_STAGES].sort())
    })

    it('should have 8 entries', () => {
      expect(WORKING_STAGES).toHaveLength(8)
    })

    it('should only contain non-optional stages', () => {
      WORKING_STAGES.forEach((stageName) => {
        const entry = STAGE_REGISTRY[stageName]
        expect(entry.optional).toBeUndefined()
      })
    })

    it('should be sorted by pipeline order', () => {
      const orders = WORKING_STAGES.map((stageName) => STAGE_REGISTRY[stageName].order)

      // Verify ascending or equal order (quality_gate and quality_validation share order 12)
      for (let i = 1; i < orders.length; i++) {
        expect(orders[i]).toBeGreaterThanOrEqual(orders[i - 1])
      }
    })

    it('should not overlap with OPTIONAL_STAGES', () => {
      const overlap = WORKING_STAGES.filter((stage) => OPTIONAL_STAGES.includes(stage))
      expect(overlap).toEqual([])
    })
  })
})

// ============================================================================
// 3. Agent Mapping Tests
// ============================================================================

describe('Agent Mapping', () => {
  describe('AGENT_TO_STAGE_MAP', () => {
    it('should map all known agent types', () => {
      KNOWN_AGENT_TYPES.forEach((agentType) => {
        expect(AGENT_TO_STAGE_MAP[agentType], `Should map ${agentType}`).toBeDefined()
      })
    })

    it('should map to valid stage names', () => {
      Object.values(AGENT_TO_STAGE_MAP).forEach((stageName) => {
        expect(VALID_STAGES.has(stageName)).toBe(true)
      })
    })

    it('should handle multi-agent stages correctly', () => {
      // implementation_planning maps to BOTH implementation_planner AND integration_feasibility
      expect(AGENT_TO_STAGE_MAP.implementation_planner).toBe('implementation_planning')
      expect(AGENT_TO_STAGE_MAP.integration_feasibility).toBe('implementation_planning')

      // performance_audit maps to BOTH performance_auditor AND performance_analyst
      expect(AGENT_TO_STAGE_MAP.performance_auditor).toBe('performance_audit')
      expect(AGENT_TO_STAGE_MAP.performance_analyst).toBe('performance_audit')

      // code_quality_audit maps to BOTH code_quality_reviewer AND code_quality_critic
      expect(AGENT_TO_STAGE_MAP.code_quality_reviewer).toBe('code_quality_audit')
      expect(AGENT_TO_STAGE_MAP.code_quality_critic).toBe('code_quality_audit')

      // trends_analysis maps to BOTH trends_analyst AND trend_validator
      expect(AGENT_TO_STAGE_MAP.trends_analyst).toBe('trends_analysis')
      expect(AGENT_TO_STAGE_MAP.trend_validator).toBe('trends_analysis')

      // dependencies_analysis maps to BOTH dependencies_analyzer AND dependency_mapper
      expect(AGENT_TO_STAGE_MAP.dependencies_analyzer).toBe('dependencies_analysis')
      expect(AGENT_TO_STAGE_MAP.dependency_mapper).toBe('dependencies_analysis')

      // supervisor_routing maps to BOTH supervisor AND supervisor_route
      expect(AGENT_TO_STAGE_MAP.supervisor).toBe('supervisor_routing')
      expect(AGENT_TO_STAGE_MAP.supervisor_route).toBe('supervisor_routing')
    })

    it('should have at least 33 agent type mappings', () => {
      // 21 original + 12 tier-based agents = 33
      expect(Object.keys(AGENT_TO_STAGE_MAP).length).toBeGreaterThanOrEqual(33)
    })
  })

  describe('STAGE_TO_AGENT_MAP', () => {
    it('should have reverse mappings for stages with agent types', () => {
      Object.entries(STAGE_REGISTRY).forEach(([key, entry]) => {
        if (entry.agentTypes && entry.agentTypes.length > 0) {
          expect(
            STAGE_TO_AGENT_MAP[key as StageName],
            `${key} should have reverse mapping`
          ).toBeDefined()
          expect(STAGE_TO_AGENT_MAP[key as StageName]).toEqual(entry.agentTypes)
        }
      })
    })

    it('should match registry agentTypes', () => {
      Object.entries(STAGE_TO_AGENT_MAP).forEach(([stageName, agentTypes]) => {
        const entry = STAGE_REGISTRY[stageName as StageName]
        expect(entry.agentTypes).toEqual(agentTypes)
      })
    })

    it('should have arrays of agent types', () => {
      Object.entries(STAGE_TO_AGENT_MAP).forEach(([stageName, agentTypes]) => {
        expect(Array.isArray(agentTypes), `${stageName} should have array of agent types`).toBe(
          true
        )
        expect(
          agentTypes.length,
          `${stageName} should have at least one agent type`
        ).toBeGreaterThan(0)
      })
    })

    it('should be inverse of AGENT_TO_STAGE_MAP', () => {
      // For each agent type, verify it appears in the stage's agent types array
      Object.entries(AGENT_TO_STAGE_MAP).forEach(([agentType, stageName]) => {
        const stageAgentTypes = STAGE_TO_AGENT_MAP[stageName]
        expect(
          stageAgentTypes,
          `${stageName} should have agent types array for ${agentType}`
        ).toContain(agentType)
      })
    })
  })

  describe('normalizeStageNameFromBackend', () => {
    it('should handle known agent types', () => {
      expect(normalizeStageNameFromBackend('implementation_planner')).toBe(
        'implementation_planning'
      )
      expect(normalizeStageNameFromBackend('security_auditor')).toBe('security_audit')
      expect(normalizeStageNameFromBackend('tech_comparator')).toBe('tech_comparison')
      expect(normalizeStageNameFromBackend('supervisor')).toBe('supervisor_routing')
    })

    it('should handle already-normalized stage names', () => {
      expect(normalizeStageNameFromBackend('extraction')).toBe('extraction')
      expect(normalizeStageNameFromBackend('embedding')).toBe('embedding')
      expect(normalizeStageNameFromBackend('aggregation')).toBe('aggregation')
    })

    it('should return null for unknown agent types', () => {
      expect(normalizeStageNameFromBackend('unknown_agent')).toBeNull()
      expect(normalizeStageNameFromBackend('invalid_stage')).toBeNull()
      expect(normalizeStageNameFromBackend('')).toBeNull()
    })

    it('should handle all known agent types without warnings', () => {
      KNOWN_AGENT_TYPES.forEach((agentType) => {
        const normalized = normalizeStageNameFromBackend(agentType)
        expect(normalized, `Should normalize ${agentType}`).not.toBeNull()
      })
    })

    it('should preserve type safety', () => {
      const result = normalizeStageNameFromBackend('extraction')
      if (result !== null) {
        // TypeScript should know this is StageName
        const stageName: StageName = result
        expect(stageName).toBe('extraction')
      }
    })
  })
})

// ============================================================================
// 4. Helper Function Tests
// ============================================================================

describe('Helper Functions', () => {
  describe('getStageTitle', () => {
    it('should return correct titles for all stages', () => {
      expect(getStageTitle('extraction')).toBe('Content Extraction')
      expect(getStageTitle('embedding')).toBe('Embedding Generation')
      expect(getStageTitle('supervisor_routing')).toBe('Routing to Agents')
      expect(getStageTitle('tech_comparison')).toBe('Tech Comparison')
      expect(getStageTitle('aggregation')).toBe('Aggregating Results')
    })

    it('should return stage name for unknown stages', () => {
      const unknownStage = 'unknown_stage' as StageName
      expect(getStageTitle(unknownStage)).toBe('unknown_stage')
    })

    it('should match registry titles', () => {
      ALL_STAGES.forEach((stageName) => {
        expect(getStageTitle(stageName)).toBe(STAGE_REGISTRY[stageName].title)
      })
    })
  })

  describe('getSortedStages', () => {
    it('should return stages in order', () => {
      const sorted = getSortedStages()
      expect(sorted).toHaveLength(EXPECTED_STAGE_COUNT)

      // Verify ascending or equal order (quality_gate and quality_validation share order 12)
      for (let i = 1; i < sorted.length; i++) {
        expect(sorted[i].order).toBeGreaterThanOrEqual(sorted[i - 1].order)
      }
    })

    it('should start with extraction and end with metrics', () => {
      const sorted = getSortedStages()
      expect(sorted[0].id).toBe('extraction')
      expect(sorted[sorted.length - 1].id).toBe('metrics')
    })

    it('should return full registry entries', () => {
      const sorted = getSortedStages()

      sorted.forEach((entry) => {
        expect(entry.id).toBeDefined()
        expect(entry.title).toBeDefined()
        expect(entry.order).toBeDefined()
        expect(entry.uiStage).toBeDefined()
        expect(entry.category).toBeDefined()
      })
    })
  })

  describe('getOptionalStages', () => {
    it('should return optional stage names', () => {
      const optionalStages = getOptionalStages()
      expect(optionalStages.sort()).toEqual([...EXPECTED_OPTIONAL_STAGES].sort())
    })

    it('should return the same as OPTIONAL_STAGES constant', () => {
      expect(getOptionalStages()).toEqual(OPTIONAL_STAGES)
    })

    it('should have 22 entries', () => {
      expect(getOptionalStages()).toHaveLength(22) // 7 content-based + 12 tier-based + 3 workflow optional
    })
  })

  describe('getStagesByCategory', () => {
    it('should filter by workflow category correctly', () => {
      const workflowStages = getStagesByCategory('workflow')

      expect(workflowStages.length).toBeGreaterThan(0)
      workflowStages.forEach((entry) => {
        expect(entry.category).toBe('workflow')
      })

      // Should include extraction, embedding, supervisor_routing, chunking, workflow, pattern_comparison, metrics
      expect(workflowStages.length).toBe(7)
    })

    it('should filter by agent category correctly', () => {
      const agentStages = getStagesByCategory('agent')

      expect(agentStages.length).toBe(19) // 7 content-based + 12 tier-based agents
      agentStages.forEach((entry) => {
        expect(entry.category).toBe('agent')
        expect(entry.optional).toBe(true) // All agent stages are optional
      })
    })

    it('should filter by quality category correctly', () => {
      const qualityStages = getStagesByCategory('quality')

      expect(qualityStages.length).toBe(4) // aggregation, quality_gate, quality_validation, artifact_generation
      qualityStages.forEach((entry) => {
        expect(entry.category).toBe('quality')
      })
    })

    it('should return stages sorted by order', () => {
      const categories: StageCategory[] = ['workflow', 'agent', 'quality']

      categories.forEach((category) => {
        const stages = getStagesByCategory(category)

        // Verify ascending or equal order (quality category has quality_gate and quality_validation sharing order 12)
        for (let i = 1; i < stages.length; i++) {
          expect(stages[i].order).toBeGreaterThanOrEqual(stages[i - 1].order)
        }
      })
    })

    it('should return empty array for invalid category', () => {
      const invalidCategory = 'invalid' as StageCategory
      const stages = getStagesByCategory(invalidCategory)
      expect(stages).toEqual([])
    })
  })

  describe('isValidStage', () => {
    it('should return true for valid stage names', () => {
      expect(isValidStage('extraction')).toBe(true)
      expect(isValidStage('embedding')).toBe(true)
      expect(isValidStage('tech_comparison')).toBe(true)
      expect(isValidStage('aggregation')).toBe(true)
    })

    it('should return false for invalid stage names', () => {
      expect(isValidStage('unknown_stage')).toBe(false)
      expect(isValidStage('invalid')).toBe(false)
      expect(isValidStage('')).toBe(false)
    })

    it('should work as type guard', () => {
      const maybeStage: string = 'extraction'

      if (isValidStage(maybeStage)) {
        // TypeScript should know this is StageName
        const stageName: StageName = maybeStage
        expect(stageName).toBe('extraction')
      }
    })

    it('should validate all expected stages', () => {
      EXPECTED_STAGE_NAMES.forEach((stageName) => {
        expect(isValidStage(stageName)).toBe(true)
      })
    })
  })

  describe('isAgentStage', () => {
    it('should return true for agent stages', () => {
      const agentStages: AgentStageName[] = [
        // Content-based agents
        'tech_comparison',
        'security_audit',
        'implementation_planning',
        'performance_audit',
        'code_quality_audit',
        'trends_analysis',
        'dependencies_analysis',
        // Tier 1: Universal agents
        'key_insights',
        'pros_cons',
        'audience_fit',
        'actionable',
        // Tier 2: Validation agents
        'fact_validation',
        'source_credibility',
        'freshness_check',
        'alternatives_finding',
        // Tier 3: Research agents
        'deep_research',
        'community_pulse',
        'knowledge_curation',
        'learning_path',
      ]

      agentStages.forEach((stageName) => {
        expect(isAgentStage(stageName), `${stageName} should be an agent stage`).toBe(true)
      })
    })

    it('should return true for quality stages', () => {
      // Quality stages are also displayed in UI (not workflow)
      expect(isAgentStage('aggregation')).toBe(true)
      expect(isAgentStage('quality_gate')).toBe(true)
      expect(isAgentStage('quality_validation')).toBe(true)
      expect(isAgentStage('artifact_generation')).toBe(true)
    })

    it('should return false for workflow stages', () => {
      expect(isAgentStage('extraction')).toBe(false)
      expect(isAgentStage('embedding')).toBe(false)
      expect(isAgentStage('supervisor_routing')).toBe(false)
      expect(isAgentStage('chunking')).toBe(false)
      expect(isAgentStage('workflow')).toBe(false)
    })

    it('should work as type guard', () => {
      const stageName: StageName = 'tech_comparison'

      if (isAgentStage(stageName)) {
        // TypeScript should know this is AgentStageName
        const agentStage: AgentStageName = stageName
        expect(agentStage).toBe('tech_comparison')
      }
    })
  })

  describe('isWorkflowStage', () => {
    it('should return true for workflow stage names', () => {
      expect(isWorkflowStage('workflow')).toBe(true)
      expect(isWorkflowStage('pattern_comparison')).toBe(true)
      expect(isWorkflowStage('metrics')).toBe(true)
    })

    it('should return false for non-workflow stages', () => {
      expect(isWorkflowStage('extraction')).toBe(false)
      expect(isWorkflowStage('tech_comparison')).toBe(false)
      expect(isWorkflowStage('aggregation')).toBe(false)
    })

    it('should only match the 3 specific workflow stages', () => {
      // Note: This function specifically checks for workflow/pattern_comparison/metrics
      // NOT all stages with category: 'workflow'
      const workflowStageNames = ['workflow', 'pattern_comparison', 'metrics']

      ALL_STAGES.forEach((stageName) => {
        if (workflowStageNames.includes(stageName)) {
          expect(isWorkflowStage(stageName)).toBe(true)
        } else {
          expect(isWorkflowStage(stageName)).toBe(false)
        }
      })
    })
  })

  describe('getStageOrder', () => {
    it('should return correct order for all stages', () => {
      expect(getStageOrder('extraction')).toBe(1)
      expect(getStageOrder('embedding')).toBe(2)
      expect(getStageOrder('supervisor_routing')).toBe(3)
      expect(getStageOrder('tech_comparison')).toBe(4)
      // Tier 1 agents are at 11-14
      expect(getStageOrder('key_insights')).toBe(11)
      expect(getStageOrder('actionable')).toBe(14)
      // Tier 2 agents are at 15-18
      expect(getStageOrder('fact_validation')).toBe(15)
      // Tier 3 agents are at 19-22
      expect(getStageOrder('deep_research')).toBe(19)
      // Workflow stages now at 23+
      expect(getStageOrder('aggregation')).toBe(23)
      expect(getStageOrder('metrics')).toBe(29)
    })

    it('should return Infinity for unknown stages', () => {
      const unknownStage = 'unknown_stage' as StageName
      expect(getStageOrder(unknownStage)).toBe(Infinity)
    })

    it('should match registry order values', () => {
      ALL_STAGES.forEach((stageName) => {
        expect(getStageOrder(stageName)).toBe(STAGE_REGISTRY[stageName].order)
      })
    })
  })

  describe('getStageByAgentType', () => {
    it('should return stage entry for known agent types', () => {
      const entry = getStageByAgentType('implementation_planner')
      expect(entry).toBeDefined()
      expect(entry?.id).toBe('implementation_planning')
      expect(entry?.title).toBe('Implementation Planning')
    })

    it('should return undefined for unknown agent types', () => {
      expect(getStageByAgentType('unknown_agent')).toBeUndefined()
    })

    it('should return full registry entry', () => {
      const entry = getStageByAgentType('tech_comparator')
      expect(entry).toBeDefined()

      if (entry) {
        expect(entry.id).toBeDefined()
        expect(entry.title).toBeDefined()
        expect(entry.order).toBeDefined()
        expect(entry.uiStage).toBeDefined()
        expect(entry.category).toBeDefined()
      }
    })

    it('should work for all known agent types', () => {
      KNOWN_AGENT_TYPES.forEach((agentType) => {
        const entry = getStageByAgentType(agentType)
        expect(entry, `Should find stage for ${agentType}`).toBeDefined()
      })
    })
  })

  describe('getAgentTypesForStage', () => {
    it('should return agent types for stages that have them', () => {
      expect(getAgentTypesForStage('extraction')).toEqual(['extraction'])
      expect(getAgentTypesForStage('supervisor_routing')).toEqual([
        'supervisor',
        'supervisor_route',
      ])
      expect(getAgentTypesForStage('tech_comparison')).toEqual(['tech_comparator'])
    })

    it('should return empty array for stages without agent types', () => {
      expect(getAgentTypesForStage('workflow')).toEqual([])
      expect(getAgentTypesForStage('pattern_comparison')).toEqual([])
    })

    it('should handle multi-agent stages', () => {
      // implementation_planning has 2 agent types
      expect(getAgentTypesForStage('implementation_planning')).toEqual([
        'implementation_planner',
        'integration_feasibility',
      ])

      // performance_audit has 2 agent types
      expect(getAgentTypesForStage('performance_audit')).toEqual([
        'performance_auditor',
        'performance_analyst',
      ])
    })

    it('should match registry agentTypes', () => {
      ALL_STAGES.forEach((stageName) => {
        const agentTypes = getAgentTypesForStage(stageName)
        const registryAgentTypes = STAGE_REGISTRY[stageName].agentTypes ?? []
        expect(agentTypes).toEqual(registryAgentTypes)
      })
    })

    it('should return empty array for unknown stages', () => {
      const unknownStage = 'unknown_stage' as StageName
      expect(getAgentTypesForStage(unknownStage)).toEqual([])
    })
  })
})

// ============================================================================
// 5. Integration Tests
// ============================================================================

describe('Integration Tests', () => {
  describe('Registry Consistency', () => {
    it('should have matching counts across exports', () => {
      expect(Object.keys(STAGE_REGISTRY).length).toBe(EXPECTED_STAGE_COUNT)
      expect(Object.keys(STAGE_CONFIG).length).toBe(EXPECTED_STAGE_COUNT)
      expect(ALL_STAGES.length).toBe(EXPECTED_STAGE_COUNT)
      expect(VALID_STAGES.size).toBe(EXPECTED_STAGE_COUNT)
      expect(TOTAL_STAGES).toBe(EXPECTED_STAGE_COUNT)
    })

    it('should have optional + working stages equal total stages', () => {
      expect(OPTIONAL_STAGES.length + WORKING_STAGES.length).toBe(EXPECTED_STAGE_COUNT)
    })

    it('should have no overlap between optional and working stages', () => {
      const overlap = OPTIONAL_STAGES.filter((stage) => WORKING_STAGES.includes(stage))
      expect(overlap).toEqual([])
    })
  })

  describe('Complete Pipeline Flow', () => {
    it('should cover complete pipeline from extraction to artifact generation', () => {
      const sorted = getSortedStages()

      // First stage: extraction
      expect(sorted[0].id).toBe('extraction')
      expect(sorted[0].category).toBe('workflow')

      // Agent routing stage
      const routingStage = sorted.find((s) => s.id === 'supervisor_routing')
      expect(routingStage).toBeDefined()

      // Agent stages (optional)
      const agentStages = sorted.filter((s) => s.category === 'agent')
      expect(agentStages.length).toBe(19) // 7 content-based + 12 tier-based

      // Quality stages
      const qualityStages = sorted.filter((s) => s.category === 'quality')
      expect(qualityStages.length).toBe(4)
      // Note: quality_gate and quality_validation may share order 12, so we just check they're all present
      const qualityIds = qualityStages.map((s) => s.id)
      expect(qualityIds).toContain('aggregation')
      expect(qualityIds).toContain('quality_gate')
      expect(qualityIds).toContain('quality_validation')
      expect(qualityIds).toContain('artifact_generation')
    })

    it('should have correct category distribution', () => {
      const workflowStages = Object.values(STAGE_REGISTRY).filter((s) => s.category === 'workflow')
      const agentStages = Object.values(STAGE_REGISTRY).filter((s) => s.category === 'agent')
      const qualityStages = Object.values(STAGE_REGISTRY).filter((s) => s.category === 'quality')

      expect(workflowStages.length).toBe(7) // 3 core + 4 optional workflow stages
      expect(agentStages.length).toBe(19) // 7 content-based + 12 tier-based
      expect(qualityStages.length).toBe(4) // aggregation, quality_gate, quality_validation, artifact_generation
      expect(workflowStages.length + agentStages.length + qualityStages.length).toBe(
        EXPECTED_STAGE_COUNT
      )
    })
  })

  describe('Backward Compatibility', () => {
    it('should support legacy STAGE_CONFIG format', () => {
      // Legacy code expects this structure
      const legacyConfig = STAGE_CONFIG.extraction
      expect(legacyConfig).toEqual({
        title: 'Content Extraction',
        order: 1,
        uiStage: 'extracting',
      })
    })

    it('should support legacy optional flag', () => {
      const optionalConfig = STAGE_CONFIG.tech_comparison
      expect(optionalConfig.optional).toBe(true)

      const requiredConfig = STAGE_CONFIG.extraction
      expect('optional' in requiredConfig).toBe(false)
    })
  })
})

// ============================================================================
// 6. Tier-Based Agent Tests
// ============================================================================

describe('Tier-Based Agent Functions', () => {
  describe('getAgentsByTier', () => {
    it('should return Tier 1 (Universal) agents correctly', () => {
      const tier1 = getAgentsByTier(1)
      expect(tier1).toHaveLength(4)
      expect(tier1.map((s) => s.id)).toEqual([
        'key_insights',
        'pros_cons',
        'audience_fit',
        'actionable',
      ])
    })

    it('should return Tier 2 (Validation) agents correctly', () => {
      const tier2 = getAgentsByTier(2)
      expect(tier2).toHaveLength(4)
      expect(tier2.map((s) => s.id)).toEqual([
        'fact_validation',
        'source_credibility',
        'freshness_check',
        'alternatives_finding',
      ])
    })

    it('should return Tier 3 (Research) agents correctly', () => {
      const tier3 = getAgentsByTier(3)
      expect(tier3).toHaveLength(4)
      expect(tier3.map((s) => s.id)).toEqual([
        'deep_research',
        'community_pulse',
        'knowledge_curation',
        'learning_path',
      ])
    })

    it('should return agents sorted by order', () => {
      const tier1 = getAgentsByTier(1)
      const orders = tier1.map((s) => s.order)
      for (let i = 1; i < orders.length; i++) {
        expect(orders[i]).toBeGreaterThan(orders[i - 1])
      }
    })
  })

  describe('getAgentsUpToTier', () => {
    it('should return only Tier 1 agents for maxTier=1', () => {
      const agents = getAgentsUpToTier(1)
      expect(agents).toHaveLength(4)
      agents.forEach((agent) => {
        expect(agent.tier).toBe(1)
      })
    })

    it('should return Tier 1 + Tier 2 agents for maxTier=2', () => {
      const agents = getAgentsUpToTier(2)
      expect(agents).toHaveLength(8)
      agents.forEach((agent) => {
        expect(agent.tier).toBeLessThanOrEqual(2)
      })
    })

    it('should return all tiered agents for maxTier=3', () => {
      const agents = getAgentsUpToTier(3)
      expect(agents).toHaveLength(12)
      agents.forEach((agent) => {
        expect(agent.tier).toBeLessThanOrEqual(3)
      })
    })

    it('should return agents sorted by order', () => {
      const agents = getAgentsUpToTier(3)
      const orders = agents.map((s) => s.order)
      for (let i = 1; i < orders.length; i++) {
        expect(orders[i]).toBeGreaterThan(orders[i - 1])
      }
    })
  })

  describe('getAllTieredAgents', () => {
    it('should return all 12 tiered agents', () => {
      const agents = getAllTieredAgents()
      expect(agents).toHaveLength(12)
    })

    it('should not include content-based agents', () => {
      const agents = getAllTieredAgents()
      const ids = agents.map((s) => s.id)
      expect(ids).not.toContain('tech_comparison')
      expect(ids).not.toContain('security_audit')
      expect(ids).not.toContain('implementation_planning')
    })

    it('should return agents sorted by order', () => {
      const agents = getAllTieredAgents()
      const orders = agents.map((s) => s.order)
      for (let i = 1; i < orders.length; i++) {
        expect(orders[i]).toBeGreaterThan(orders[i - 1])
      }
    })
  })

  describe('Tier Agent Type Mappings', () => {
    it('should map Tier 1 agent types to stage names', () => {
      expect(AGENT_TO_STAGE_MAP.key_insights).toBe('key_insights')
      expect(AGENT_TO_STAGE_MAP.pros_cons).toBe('pros_cons')
      expect(AGENT_TO_STAGE_MAP.audience_fit).toBe('audience_fit')
      expect(AGENT_TO_STAGE_MAP.actionable).toBe('actionable')
    })

    it('should map Tier 2 agent types to stage names', () => {
      expect(AGENT_TO_STAGE_MAP.fact_validator).toBe('fact_validation')
      expect(AGENT_TO_STAGE_MAP.source_credibility).toBe('source_credibility')
      expect(AGENT_TO_STAGE_MAP.freshness_checker).toBe('freshness_check')
      expect(AGENT_TO_STAGE_MAP.alternatives_finder).toBe('alternatives_finding')
    })

    it('should map Tier 3 agent types to stage names', () => {
      expect(AGENT_TO_STAGE_MAP.deep_researcher).toBe('deep_research')
      expect(AGENT_TO_STAGE_MAP.community_pulse).toBe('community_pulse')
      expect(AGENT_TO_STAGE_MAP.knowledge_curator).toBe('knowledge_curation')
      expect(AGENT_TO_STAGE_MAP.learning_path_advisor).toBe('learning_path')
    })
  })

  describe('Tier Property in Registry', () => {
    it('should have tier property only for tiered agents', () => {
      const tieredAgents = Object.values(STAGE_REGISTRY).filter((entry) => entry.tier !== undefined)
      expect(tieredAgents).toHaveLength(12)
    })

    it('should not have tier property for content-based agents', () => {
      expect(STAGE_REGISTRY.tech_comparison.tier).toBeUndefined()
      expect(STAGE_REGISTRY.security_audit.tier).toBeUndefined()
      expect(STAGE_REGISTRY.implementation_planning.tier).toBeUndefined()
    })

    it('should not have tier property for workflow stages', () => {
      expect(STAGE_REGISTRY.extraction.tier).toBeUndefined()
      expect(STAGE_REGISTRY.embedding.tier).toBeUndefined()
      expect(STAGE_REGISTRY.supervisor_routing.tier).toBeUndefined()
    })

    it('should have correct tier values for each tiered agent', () => {
      // Tier 1
      expect(STAGE_REGISTRY.key_insights.tier).toBe(1)
      expect(STAGE_REGISTRY.pros_cons.tier).toBe(1)
      expect(STAGE_REGISTRY.audience_fit.tier).toBe(1)
      expect(STAGE_REGISTRY.actionable.tier).toBe(1)

      // Tier 2
      expect(STAGE_REGISTRY.fact_validation.tier).toBe(2)
      expect(STAGE_REGISTRY.source_credibility.tier).toBe(2)
      expect(STAGE_REGISTRY.freshness_check.tier).toBe(2)
      expect(STAGE_REGISTRY.alternatives_finding.tier).toBe(2)

      // Tier 3
      expect(STAGE_REGISTRY.deep_research.tier).toBe(3)
      expect(STAGE_REGISTRY.community_pulse.tier).toBe(3)
      expect(STAGE_REGISTRY.knowledge_curation.tier).toBe(3)
      expect(STAGE_REGISTRY.learning_path.tier).toBe(3)
    })
  })
})
