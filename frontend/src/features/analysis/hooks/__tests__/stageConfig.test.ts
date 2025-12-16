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
    it('contains all 17 stages with correct structure', () => {
      expect(TOTAL_STAGES).toBe(17)

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
      // artifact_generation is order 13, but optional stages come after (up to order 17)
      expect(orderedStages[12]).toBe('artifact_generation') // 13th stage (index 12)
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
    it('returns ~2-3 minutes when no stages completed', () => {
      expect(estimateTimeRemaining(0)).toBe('~2-3 minutes')
    })

    it('returns ~1-2 minutes when few stages completed', () => {
      expect(estimateTimeRemaining(1)).toBe('~1-2 minutes')
      expect(estimateTimeRemaining(5)).toBe('~1-2 minutes')
    })

    it('returns ~1 minute when mid-way through', () => {
      expect(estimateTimeRemaining(11)).toBe('~1 minute')
      expect(estimateTimeRemaining(13)).toBe('~1 minute')
    })

    it('returns ~30 seconds when almost complete', () => {
      expect(estimateTimeRemaining(14)).toBe('~30 seconds')
      expect(estimateTimeRemaining(15)).toBe('~30 seconds')
    })
  })
})
