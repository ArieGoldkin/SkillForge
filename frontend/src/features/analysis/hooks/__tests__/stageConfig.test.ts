/**
 * Tests for stageConfig - Stage configuration and backend name normalization
 *
 * These tests validate the critical mapping between backend agent names
 * and frontend stage names (Issue #88 workaround).
 */

import { describe, expect, it } from 'vitest'

import {
  STAGE_CONFIG,
  TOTAL_STAGES,
  estimateTimeRemaining,
  normalizeStageNameFromBackend,
} from '../stageConfig'

describe('stageConfig', () => {
  describe('STAGE_CONFIG', () => {
    it('contains all 30 stages with correct structure', () => {
      expect(TOTAL_STAGES).toBe(30)

      // Verify each stage has required properties
      Object.entries(STAGE_CONFIG).forEach(([_stageName, config]) => {
        expect(config).toHaveProperty('title')
        expect(config).toHaveProperty('order')
        expect(config).toHaveProperty('uiStage')
        expect(typeof config.title).toBe('string')
        expect(typeof config.order).toBe('number')
        expect(['extracting', 'processing', 'analyzing', 'generating']).toContain(config.uiStage)
      })
    })

    it('has stages in correct order', () => {
      const orderedStages = Object.entries(STAGE_CONFIG)
        .sort(([, a], [, b]) => a.order - b.order)
        .map(([name]) => name)

      expect(orderedStages[0]).toBe('extraction')
      // artifact_generation is order 25, position depends on quality_gate/quality_validation (both order 24)
      // With 30 stages total, artifact_generation should be at index 25 (26th position)
      expect(orderedStages[25]).toBe('artifact_generation')
      expect(orderedStages[orderedStages.length - 1]).toBe('metrics') // Last optional stage
    })
  })

  describe('normalizeStageNameFromBackend', () => {
    describe('direct stage names (already valid)', () => {
      it.each([
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
        'aggregation',
        'quality_gate',
        'quality_validation',
        'artifact_generation',
        'chunking',
        'workflow',
        'pattern_comparison',
        'metrics',
      ])('returns %s unchanged when it is a valid stage name', (stageName) => {
        expect(normalizeStageNameFromBackend(stageName)).toBe(stageName)
      })
    })

    describe('agent name mappings (Issue #88 workaround)', () => {
      it.each([
        ['implementation_planner', 'implementation_planning'],
        ['integration_feasibility', 'implementation_planning'], // Maps to same stage!
        ['tech_comparator', 'tech_comparison'],
        ['security_auditor', 'security_audit'],
        ['performance_auditor', 'performance_audit'],
        ['performance_analyst', 'performance_audit'],
        ['code_quality_reviewer', 'code_quality_audit'],
        ['code_quality_critic', 'code_quality_audit'],
        ['trends_analyst', 'trends_analysis'],
        ['trend_validator', 'trends_analysis'],
        ['dependencies_analyzer', 'dependencies_analysis'],
        ['dependency_mapper', 'dependencies_analysis'],
      ])('maps agent name "%s" to stage name "%s"', (agentName, expectedStage) => {
        expect(normalizeStageNameFromBackend(agentName)).toBe(expectedStage)
      })
    })

    describe('alternative backend names', () => {
      it.each([
        ['supervisor', 'supervisor_routing'],
        ['supervisor_route', 'supervisor_routing'],
        ['embedding', 'embedding'],
      ])('maps alternative name "%s" to "%s"', (altName, expectedStage) => {
        expect(normalizeStageNameFromBackend(altName)).toBe(expectedStage)
      })
    })

    describe('unknown stage names', () => {
      it('returns null for unknown stage names', () => {
        expect(normalizeStageNameFromBackend('unknown_stage')).toBe(null)
        expect(normalizeStageNameFromBackend('random_agent')).toBe(null)
        expect(normalizeStageNameFromBackend('')).toBe(null)
      })
    })
  })

  describe('estimateTimeRemaining', () => {
    describe('with default TOTAL_STAGES (backward compatibility)', () => {
      it('returns ~2-3 minutes when no stages completed', () => {
        expect(estimateTimeRemaining(0)).toBe('~2-3 minutes')
      })

      it('returns ~1-2 minutes when few stages completed', () => {
        expect(estimateTimeRemaining(1)).toBe('~1-2 minutes')
        expect(estimateTimeRemaining(5)).toBe('~1-2 minutes')
      })

      it('returns ~1 minute when mid-way through', () => {
        // With 30 total stages: 30-24=6, 30-25=5, 30-26=4 all fall in "<=6" range
        expect(estimateTimeRemaining(24)).toBe('~1 minute')
        expect(estimateTimeRemaining(25)).toBe('~1 minute')
        expect(estimateTimeRemaining(26)).toBe('~1 minute')
      })

      it('returns ~30 seconds when almost complete', () => {
        // With 30 total stages: 30-27=3, 30-28=2 fall in "<=3" range
        expect(estimateTimeRemaining(27)).toBe('~30 seconds')
        expect(estimateTimeRemaining(28)).toBe('~30 seconds')
      })
    })

    describe('with dynamic totalStages (Issue #443)', () => {
      it('uses dynamic totalStages when provided', () => {
        // With 8 total stages, 5 completed = 3 remaining → "~30 seconds"
        expect(estimateTimeRemaining(5, 8)).toBe('~30 seconds')

        // With 8 total stages, 2 completed = 6 remaining → "~1 minute"
        expect(estimateTimeRemaining(2, 8)).toBe('~1 minute')
      })

      it('calculates correctly for small dynamic totals', () => {
        // Supervisor selected only 3 agents → 5 + 3 = 8 total stages
        const dynamicTotal = 8

        // 0 completed → ~2-3 minutes
        expect(estimateTimeRemaining(0, dynamicTotal)).toBe('~2-3 minutes')

        // 5 completed, 3 remaining → ~30 seconds
        expect(estimateTimeRemaining(5, dynamicTotal)).toBe('~30 seconds')

        // 6 completed, 2 remaining → ~30 seconds
        expect(estimateTimeRemaining(6, dynamicTotal)).toBe('~30 seconds')
      })

      it('calculates correctly for large dynamic totals', () => {
        // Supervisor selected 8 agents → 5 + 8 = 13 total stages
        const dynamicTotal = 13

        // 1 completed, 12 remaining → ~1-2 minutes (>= threshold)
        expect(estimateTimeRemaining(1, dynamicTotal)).toBe('~1-2 minutes')

        // 7 completed, 6 remaining → ~1 minute
        expect(estimateTimeRemaining(7, dynamicTotal)).toBe('~1 minute')

        // 10 completed, 3 remaining → ~30 seconds
        expect(estimateTimeRemaining(10, dynamicTotal)).toBe('~30 seconds')
      })

      it('falls back to TOTAL_STAGES when totalStages is undefined', () => {
        // Without totalStages param, should use TOTAL_STAGES (30)
        // Same behavior as original tests
        expect(estimateTimeRemaining(27, undefined)).toBe('~30 seconds')
        expect(estimateTimeRemaining(24, undefined)).toBe('~1 minute')
      })
    })
  })
})
