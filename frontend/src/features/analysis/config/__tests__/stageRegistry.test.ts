/**
 * Stage Registry Tests
 *
 * Comprehensive test suite for the unified stage registry configuration.
 * Validates registry structure, derived exports, agent mappings, and helper functions.
 *
 * @module features/analysis/config/__tests__/stageRegistry.test
 * @see Issue #397: Create unified stage registry
 */

import type { AgentStageName, StageName } from '@app-types/sse'
import { describe, expect, it } from 'vitest'

import type { AnalysisStage } from '../../components/steps/AnalysisProgressCard'
import {
  AGENT_TO_STAGE_MAP,
  ALL_STAGES,
  getAgentTypesForStage,
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

const EXPECTED_STAGE_COUNT = 17

const EXPECTED_STAGE_NAMES: StageName[] = [
  // Workflow stages (core pipeline)
  'extraction',
  'embedding',
  'supervisor_routing',
  // Agent stages (all optional)
  'tech_comparison',
  'security_audit',
  'implementation_planning',
  'performance_audit',
  'code_quality_audit',
  'trends_analysis',
  'dependencies_analysis',
  // Quality stages
  'aggregation',
  'quality_validation',
  'artifact_generation',
  // Optional workflow stages
  'chunking',
  'workflow',
  'pattern_comparison',
  'metrics',
]

const EXPECTED_OPTIONAL_STAGES: StageName[] = [
  'tech_comparison',
  'security_audit',
  'implementation_planning',
  'performance_audit',
  'code_quality_audit',
  'trends_analysis',
  'dependencies_analysis',
  'chunking',
  'pattern_comparison',
  'metrics',
]

const EXPECTED_WORKING_STAGES: StageName[] = [
  'extraction',
  'embedding',
  'supervisor_routing',
  'aggregation',
  'quality_validation',
  'artifact_generation',
  'workflow',
]

const KNOWN_AGENT_TYPES = [
  'extraction',
  'embedding',
  'supervisor',
  'supervisor_route',
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
  'aggregation',
  'quality_validation',
  'artifact_generation',
  'chunking',
]

// ============================================================================
// 1. Registry Structure Tests
// ============================================================================

describe('Stage Registry Structure', () => {
  describe('Basic Structure', () => {
    it('should have exactly 17 stages defined', () => {
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
    it('should have unique order values (1-17)', () => {
      const orderValues = Object.values(STAGE_REGISTRY).map((entry) => entry.order)

      // Check uniqueness
      const uniqueOrders = new Set(orderValues)
      expect(uniqueOrders.size).toBe(EXPECTED_STAGE_COUNT)

      // Check range
      orderValues.forEach((order) => {
        expect(order).toBeGreaterThanOrEqual(1)
        expect(order).toBeLessThanOrEqual(EXPECTED_STAGE_COUNT)
      })
    })

    it('should have sequential order values with no gaps', () => {
      const orderValues = Object.values(STAGE_REGISTRY).map((entry) => entry.order)
      const sortedOrders = [...orderValues].sort((a, b) => a - b)

      // Should be exactly [1, 2, 3, ..., 17]
      const expectedSequence = Array.from({ length: EXPECTED_STAGE_COUNT }, (_, i) => i + 1)
      expect(sortedOrders).toEqual(expectedSequence)
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

      // Agent stages: 4-10
      const agentOrders = agentStages.map((entry) => entry.order).sort((a, b) => a - b)
      expect(agentOrders).toEqual([4, 5, 6, 7, 8, 9, 10])

      // Quality stages: 11-13
      const qualityOrders = qualityStages.map((entry) => entry.order).sort((a, b) => a - b)
      expect(qualityOrders).toEqual([11, 12, 13])

      // Optional workflow stages: 14-17
      const optionalWorkflowOrders = workflowStages
        .filter((entry) => entry.order >= 14)
        .map((entry) => entry.order)
        .sort((a, b) => a - b)
      expect(optionalWorkflowOrders).toEqual([14, 15, 16, 17])
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

    it('should have exactly 10 optional stages', () => {
      const optionalStages = Object.values(STAGE_REGISTRY).filter((entry) => entry.optional)
      expect(optionalStages).toHaveLength(10)
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

      // At least 13 stages should have agent types (all workflow, agent, and quality stages except workflow/pattern_comparison/metrics)
      expect(stagesWithAgentTypes.length).toBeGreaterThanOrEqual(13)
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
    it('should have correct shape for backward compatibility', () => {
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
    it('should have 17 entries', () => {
      expect(ALL_STAGES).toHaveLength(EXPECTED_STAGE_COUNT)
    })

    it('should be sorted by pipeline order', () => {
      const orders = ALL_STAGES.map((stageName) => STAGE_REGISTRY[stageName].order)

      // Verify ascending order
      for (let i = 1; i < orders.length; i++) {
        expect(orders[i]).toBeGreaterThan(orders[i - 1])
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
    it('should be a Set with 17 entries', () => {
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
    it('should equal 17', () => {
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

    it('should have 10 entries', () => {
      expect(OPTIONAL_STAGES).toHaveLength(10)
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

    it('should have 7 entries', () => {
      expect(WORKING_STAGES).toHaveLength(7)
    })

    it('should only contain non-optional stages', () => {
      WORKING_STAGES.forEach((stageName) => {
        const entry = STAGE_REGISTRY[stageName]
        expect(entry.optional).toBeUndefined()
      })
    })

    it('should be sorted by pipeline order', () => {
      const orders = WORKING_STAGES.map((stageName) => STAGE_REGISTRY[stageName].order)

      // Verify ascending order
      for (let i = 1; i < orders.length; i++) {
        expect(orders[i]).toBeGreaterThan(orders[i - 1])
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
      expect(AGENT_TO_STAGE_MAP['implementation_planner']).toBe('implementation_planning')
      expect(AGENT_TO_STAGE_MAP['integration_feasibility']).toBe('implementation_planning')

      // performance_audit maps to BOTH performance_auditor AND performance_analyst
      expect(AGENT_TO_STAGE_MAP['performance_auditor']).toBe('performance_audit')
      expect(AGENT_TO_STAGE_MAP['performance_analyst']).toBe('performance_audit')

      // code_quality_audit maps to BOTH code_quality_reviewer AND code_quality_critic
      expect(AGENT_TO_STAGE_MAP['code_quality_reviewer']).toBe('code_quality_audit')
      expect(AGENT_TO_STAGE_MAP['code_quality_critic']).toBe('code_quality_audit')

      // trends_analysis maps to BOTH trends_analyst AND trend_validator
      expect(AGENT_TO_STAGE_MAP['trends_analyst']).toBe('trends_analysis')
      expect(AGENT_TO_STAGE_MAP['trend_validator']).toBe('trends_analysis')

      // dependencies_analysis maps to BOTH dependencies_analyzer AND dependency_mapper
      expect(AGENT_TO_STAGE_MAP['dependencies_analyzer']).toBe('dependencies_analysis')
      expect(AGENT_TO_STAGE_MAP['dependency_mapper']).toBe('dependencies_analysis')

      // supervisor_routing maps to BOTH supervisor AND supervisor_route
      expect(AGENT_TO_STAGE_MAP['supervisor']).toBe('supervisor_routing')
      expect(AGENT_TO_STAGE_MAP['supervisor_route']).toBe('supervisor_routing')
    })

    it('should have at least 20 agent type mappings', () => {
      expect(Object.keys(AGENT_TO_STAGE_MAP).length).toBeGreaterThanOrEqual(20)
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

      // Verify ascending order
      for (let i = 1; i < sorted.length; i++) {
        expect(sorted[i].order).toBeGreaterThan(sorted[i - 1].order)
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

    it('should have 10 entries', () => {
      expect(getOptionalStages()).toHaveLength(10)
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

      expect(agentStages.length).toBe(7) // 7 agent stages
      agentStages.forEach((entry) => {
        expect(entry.category).toBe('agent')
        expect(entry.optional).toBe(true) // All agent stages are optional
      })
    })

    it('should filter by quality category correctly', () => {
      const qualityStages = getStagesByCategory('quality')

      expect(qualityStages.length).toBe(3) // aggregation, quality_validation, artifact_generation
      qualityStages.forEach((entry) => {
        expect(entry.category).toBe('quality')
      })
    })

    it('should return stages sorted by order', () => {
      const categories: StageCategory[] = ['workflow', 'agent', 'quality']

      categories.forEach((category) => {
        const stages = getStagesByCategory(category)

        // Verify ascending order
        for (let i = 1; i < stages.length; i++) {
          expect(stages[i].order).toBeGreaterThan(stages[i - 1].order)
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
        'tech_comparison',
        'security_audit',
        'implementation_planning',
        'performance_audit',
        'code_quality_audit',
        'trends_analysis',
        'dependencies_analysis',
      ]

      agentStages.forEach((stageName) => {
        expect(isAgentStage(stageName), `${stageName} should be an agent stage`).toBe(true)
      })
    })

    it('should return true for quality stages', () => {
      // Quality stages are also displayed in UI (not workflow)
      expect(isAgentStage('aggregation')).toBe(true)
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
      expect(getStageOrder('aggregation')).toBe(11)
      expect(getStageOrder('metrics')).toBe(17)
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
      expect(agentStages.length).toBe(7)

      // Quality stages
      const qualityStages = sorted.filter((s) => s.category === 'quality')
      expect(qualityStages.length).toBe(3)
      expect(qualityStages.map((s) => s.id)).toEqual([
        'aggregation',
        'quality_validation',
        'artifact_generation',
      ])
    })

    it('should have correct category distribution', () => {
      const workflowStages = Object.values(STAGE_REGISTRY).filter((s) => s.category === 'workflow')
      const agentStages = Object.values(STAGE_REGISTRY).filter((s) => s.category === 'agent')
      const qualityStages = Object.values(STAGE_REGISTRY).filter((s) => s.category === 'quality')

      expect(workflowStages.length).toBe(7) // 3 core + 4 optional workflow stages
      expect(agentStages.length).toBe(7)
      expect(qualityStages.length).toBe(3)
      expect(workflowStages.length + agentStages.length + qualityStages.length).toBe(
        EXPECTED_STAGE_COUNT
      )
    })
  })

  describe('Backward Compatibility', () => {
    it('should support legacy STAGE_CONFIG format', () => {
      // Legacy code expects this structure
      const legacyConfig = STAGE_CONFIG['extraction']
      expect(legacyConfig).toEqual({
        title: 'Content Extraction',
        order: 1,
        uiStage: 'extracting',
      })
    })

    it('should support legacy optional flag', () => {
      const optionalConfig = STAGE_CONFIG['tech_comparison']
      expect(optionalConfig.optional).toBe(true)

      const requiredConfig = STAGE_CONFIG['extraction']
      expect('optional' in requiredConfig).toBe(false)
    })
  })
})
