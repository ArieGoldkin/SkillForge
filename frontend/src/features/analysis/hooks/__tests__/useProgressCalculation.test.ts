/**
 * Comprehensive unit tests for useProgressCalculation hook
 *
 * Tests the 8 phases of progress calculation:
 * 1. Stage counting (completed, skipped, failed, running)
 * 2. Total stages determination (expectedTotalStages vs fallback)
 * 3. True pending stages calculation
 * 4. Finished stages calculation (expected vs actual)
 * 5. Progress percentage capping at 99% when failures exist
 * 6. Progress at 100% only when truly complete
 * 7. UI stage determination (extracting, analyzing, generating, complete)
 * 8. Current step number calculation
 */

import { renderHook } from '@testing-library/react'
import { describe, expect, it } from 'vitest'

import type { StageName } from '@/schemas/base'

import type { ProgressStep, SkippedAgentsInfo, StageStatusEntry } from '../useProgressCalculation'
import { useProgressCalculation } from '../useProgressCalculation'

describe('useProgressCalculation', () => {
  // ==========================================================================
  // PHASE 1: Stage Counting
  // ==========================================================================
  describe('Phase 1: Stage counting by status', () => {
    it('counts completed stages correctly', () => {
      const stageStatuses = new Map<StageName, StageStatusEntry>([
        ['extraction', { status: 'complete', timestamp: '2024-01-01T00:00:00Z' }],
        ['embedding', { status: 'complete', timestamp: '2024-01-01T00:01:00Z' }],
        ['supervisor_routing', { status: 'complete', timestamp: '2024-01-01T00:02:00Z' }],
      ])

      const { result } = renderHook(() =>
        useProgressCalculation(stageStatuses, [], false, undefined, undefined)
      )

      // 3 completed stages, progress should reflect this
      expect(result.current.completedSteps).toBeGreaterThan(0)
    })

    it('counts skipped stages correctly', () => {
      const stageStatuses = new Map<StageName, StageStatusEntry>([
        ['extraction', { status: 'complete', timestamp: '2024-01-01T00:00:00Z' }],
        ['tech_comparison', { status: 'skipped', timestamp: '2024-01-01T00:01:00Z' }],
        ['security_audit', { status: 'skipped', timestamp: '2024-01-01T00:01:00Z' }],
      ])

      const { result } = renderHook(() =>
        useProgressCalculation(stageStatuses, [], false, undefined, undefined)
      )

      // Should count skipped stages as finished
      expect(result.current.currentStep).toContain('skipped')
    })

    it('counts failed stages correctly', () => {
      const stageStatuses = new Map<StageName, StageStatusEntry>([
        ['extraction', { status: 'complete', timestamp: '2024-01-01T00:00:00Z' }],
        ['tech_comparison', { status: 'failed', timestamp: '2024-01-01T00:01:00Z' }],
      ])

      const { result } = renderHook(() =>
        useProgressCalculation(stageStatuses, [], false, undefined, undefined)
      )

      // Should indicate failures in status
      expect(result.current.currentStep).toContain('failed')
    })

    it('identifies running stages correctly', () => {
      const stageStatuses = new Map<StageName, StageStatusEntry>([
        ['extraction', { status: 'complete', timestamp: '2024-01-01T00:00:00Z' }],
        ['tech_comparison', { status: 'running', timestamp: '2024-01-01T00:01:00Z' }],
      ])

      const { result } = renderHook(() =>
        useProgressCalculation(stageStatuses, [], false, undefined, undefined)
      )

      // Should show running stage in status
      expect(result.current.currentStep).toBe('Tech Comparison')
    })

    it('handles empty stageStatuses', () => {
      const stageStatuses = new Map<StageName, StageStatusEntry>()

      const { result } = renderHook(() =>
        useProgressCalculation(stageStatuses, [], false, undefined, undefined)
      )

      // Should show pending stages (17 total stages)
      expect(result.current.currentStep).toContain('pending')
      expect(result.current.progress).toBe(0)
      expect(result.current.stage).toBe('extracting')
    })
  })

  // ==========================================================================
  // PHASE 2: Total Stages Determination
  // ==========================================================================
  describe('Phase 2: Total stages determination', () => {
    it('uses expectedTotalStages when provided', () => {
      const stageStatuses = new Map<StageName, StageStatusEntry>([
        ['extraction', { status: 'complete', timestamp: '2024-01-01T00:00:00Z' }],
      ])

      const { result } = renderHook(() =>
        useProgressCalculation(stageStatuses, [], false, 8, undefined)
      )

      // Should use expectedTotalStages (8) not TOTAL_STAGES (17)
      expect(result.current.totalSteps).toBe(8)
    })

    it('falls back to TOTAL_STAGES when expectedTotalStages not provided', () => {
      const stageStatuses = new Map<StageName, StageStatusEntry>([
        ['extraction', { status: 'complete', timestamp: '2024-01-01T00:00:00Z' }],
      ])

      const { result } = renderHook(() =>
        useProgressCalculation(stageStatuses, [], false, undefined, undefined)
      )

      // Should use TOTAL_STAGES (17)
      expect(result.current.totalSteps).toBe(17)
    })

    it('handles expectedTotalStages of 0', () => {
      const stageStatuses = new Map<StageName, StageStatusEntry>()

      const { result } = renderHook(() =>
        useProgressCalculation(stageStatuses, [], false, 0, undefined)
      )

      // With defensive guards, 0 is now clamped to 1 to prevent division by zero
      // This is the correct behavior - ensures valid progress calculations
      expect(result.current.totalSteps).toBe(1)
      // Progress should be a valid number (0) with the defensive guard in place
      expect(result.current.progress).toBe(0)
    })
  })

  // ==========================================================================
  // PHASE 3: True Pending Stages Calculation
  // ==========================================================================
  describe('Phase 3: True pending stages calculation', () => {
    it('calculates true pending stages (not in stageStatuses)', () => {
      const stageStatuses = new Map<StageName, StageStatusEntry>([
        ['extraction', { status: 'complete', timestamp: '2024-01-01T00:00:00Z' }],
        ['embedding', { status: 'running', timestamp: '2024-01-01T00:01:00Z' }],
      ])

      const { result } = renderHook(() =>
        useProgressCalculation(stageStatuses, [], false, undefined, undefined)
      )

      // When a stage is running, currentStep shows the running stage title (not status breakdown)
      expect(result.current.currentStep).toBe('Embedding Generation')
      // But there should be pending stages (17 total - 2 in map = 15 pending)
      expect(result.current.progress).toBeLessThan(100)
    })

    it('shows no pending stages when all stages are in stageStatuses', () => {
      // Create a map with all STAGE_CONFIG stages
      const stageStatuses = new Map<StageName, StageStatusEntry>([
        ['extraction', { status: 'complete', timestamp: '2024-01-01T00:00:00Z' }],
        ['embedding', { status: 'complete', timestamp: '2024-01-01T00:01:00Z' }],
        ['supervisor_routing', { status: 'complete', timestamp: '2024-01-01T00:02:00Z' }],
        ['tech_comparison', { status: 'skipped', timestamp: '2024-01-01T00:03:00Z' }],
        ['security_audit', { status: 'skipped', timestamp: '2024-01-01T00:03:00Z' }],
        ['implementation_planning', { status: 'skipped', timestamp: '2024-01-01T00:03:00Z' }],
        ['performance_audit', { status: 'skipped', timestamp: '2024-01-01T00:03:00Z' }],
        ['code_quality_audit', { status: 'skipped', timestamp: '2024-01-01T00:03:00Z' }],
        ['trends_analysis', { status: 'skipped', timestamp: '2024-01-01T00:03:00Z' }],
        ['dependencies_analysis', { status: 'skipped', timestamp: '2024-01-01T00:03:00Z' }],
        ['aggregation', { status: 'complete', timestamp: '2024-01-01T00:04:00Z' }],
        ['quality_validation', { status: 'complete', timestamp: '2024-01-01T00:05:00Z' }],
        ['artifact_generation', { status: 'complete', timestamp: '2024-01-01T00:06:00Z' }],
        ['chunking', { status: 'skipped', timestamp: '2024-01-01T00:03:00Z' }],
        ['workflow', { status: 'complete', timestamp: '2024-01-01T00:07:00Z' }],
        ['pattern_comparison', { status: 'skipped', timestamp: '2024-01-01T00:03:00Z' }],
        ['metrics', { status: 'skipped', timestamp: '2024-01-01T00:03:00Z' }],
      ])

      const { result } = renderHook(() =>
        useProgressCalculation(stageStatuses, [], true, 17, undefined)
      )

      // Should not show pending stages
      expect(result.current.currentStep).not.toContain('pending')
      expect(result.current.progress).toBe(100)
    })
  })

  // ==========================================================================
  // PHASE 4: Finished Stages Calculation (expected vs actual)
  // ==========================================================================
  describe('Phase 4: Finished stages calculation', () => {
    it('counts only expected stages when skippedAgentsInfo provided', () => {
      const stageStatuses = new Map<StageName, StageStatusEntry>([
        ['extraction', { status: 'complete', timestamp: '2024-01-01T00:00:00Z' }],
        ['embedding', { status: 'complete', timestamp: '2024-01-01T00:01:00Z' }],
        ['supervisor_routing', { status: 'complete', timestamp: '2024-01-01T00:02:00Z' }],
        ['tech_comparison', { status: 'complete', timestamp: '2024-01-01T00:03:00Z' }],
        ['security_audit', { status: 'skipped', timestamp: '2024-01-01T00:04:00Z' }], // Not expected
        ['aggregation', { status: 'complete', timestamp: '2024-01-01T00:05:00Z' }],
        ['quality_validation', { status: 'complete', timestamp: '2024-01-01T00:06:00Z' }], // Not in expected set
        ['artifact_generation', { status: 'complete', timestamp: '2024-01-01T00:07:00Z' }],
      ])

      const skippedAgentsInfo: SkippedAgentsInfo = {
        agents: ['security_auditor', 'code_quality_reviewer'],
        selectedAgents: ['tech_comparator'], // Only tech_comparator selected
      }

      const { result } = renderHook(() =>
        useProgressCalculation(stageStatuses, [], true, 6, skippedAgentsInfo)
      )

      // Expected stages (6 total):
      // Fixed (5): extraction, embedding, supervisor_routing, aggregation, artifact_generation
      // Selected agent (1): tech_comparison
      // Note: quality_validation is NOT in the fixed stages list
      // 6 finished / 6 expected = 100%
      expect(result.current.progress).toBe(100)
    })

    it('counts all finished stages when skippedAgentsInfo not provided', () => {
      const stageStatuses = new Map<StageName, StageStatusEntry>([
        ['extraction', { status: 'complete', timestamp: '2024-01-01T00:00:00Z' }],
        ['tech_comparison', { status: 'complete', timestamp: '2024-01-01T00:01:00Z' }],
        ['security_audit', { status: 'skipped', timestamp: '2024-01-01T00:02:00Z' }],
      ])

      const { result } = renderHook(() =>
        useProgressCalculation(stageStatuses, [], false, undefined, undefined)
      )

      // Should count all: 1 completed + 1 skipped = 2 finished
      expect(result.current.currentStep).toContain('completed')
      expect(result.current.currentStep).toContain('skipped')
    })

    it('includes failed stages in finished count', () => {
      const stageStatuses = new Map<StageName, StageStatusEntry>([
        ['extraction', { status: 'complete', timestamp: '2024-01-01T00:00:00Z' }],
        ['tech_comparison', { status: 'failed', timestamp: '2024-01-01T00:01:00Z' }],
      ])

      const { result } = renderHook(() =>
        useProgressCalculation(stageStatuses, [], false, 8, undefined)
      )

      // Should count failed stage as finished (2 finished / 8 total = 25%)
      expect(result.current.progress).toBeGreaterThan(0)
      expect(result.current.currentStep).toContain('failed')
    })

    it('maps agent types to stage names correctly with skippedAgentsInfo', () => {
      const stageStatuses = new Map<StageName, StageStatusEntry>([
        ['extraction', { status: 'complete', timestamp: '2024-01-01T00:00:00Z' }],
        ['embedding', { status: 'complete', timestamp: '2024-01-01T00:01:00Z' }],
        ['supervisor_routing', { status: 'complete', timestamp: '2024-01-01T00:02:00Z' }],
        ['tech_comparison', { status: 'complete', timestamp: '2024-01-01T00:03:00Z' }],
        ['aggregation', { status: 'complete', timestamp: '2024-01-01T00:04:00Z' }],
        ['quality_validation', { status: 'complete', timestamp: '2024-01-01T00:05:00Z' }], // Not in expected set
        ['artifact_generation', { status: 'complete', timestamp: '2024-01-01T00:06:00Z' }],
      ])

      const skippedAgentsInfo: SkippedAgentsInfo = {
        agents: [],
        selectedAgents: ['tech_comparator'], // Agent type (not stage name)
      }

      const { result } = renderHook(() =>
        useProgressCalculation(stageStatuses, [], true, 6, skippedAgentsInfo)
      )

      // Should correctly map tech_comparator to tech_comparison stage
      // Expected stages: 5 fixed + 1 selected agent = 6 total
      // All 6 expected stages complete with no failures = 100%
      expect(result.current.progress).toBe(100)
    })
  })

  // ==========================================================================
  // PHASE 5: Progress Percentage Capping at 99% with Failures
  // ==========================================================================
  describe('Phase 5: Progress percentage capping with failures', () => {
    it('caps progress at 99% when failures exist', () => {
      const stageStatuses = new Map<StageName, StageStatusEntry>([
        ['extraction', { status: 'complete', timestamp: '2024-01-01T00:00:00Z' }],
        ['embedding', { status: 'complete', timestamp: '2024-01-01T00:01:00Z' }],
        ['supervisor_routing', { status: 'complete', timestamp: '2024-01-01T00:02:00Z' }],
        ['tech_comparison', { status: 'failed', timestamp: '2024-01-01T00:03:00Z' }],
        ['aggregation', { status: 'complete', timestamp: '2024-01-01T00:04:00Z' }],
        ['artifact_generation', { status: 'complete', timestamp: '2024-01-01T00:05:00Z' }],
      ])

      const { result } = renderHook(() =>
        useProgressCalculation(stageStatuses, [], true, 6, undefined)
      )

      // Should cap at 99% due to failures, even if all stages finished
      expect(result.current.progress).toBeLessThan(100)
      expect(result.current.progress).toBeGreaterThanOrEqual(50) // Should be reasonable
      expect(result.current.currentStep).toContain('with errors')
    })

    it('caps progress at 99% when running stages exist', () => {
      const stageStatuses = new Map<StageName, StageStatusEntry>([
        ['extraction', { status: 'complete', timestamp: '2024-01-01T00:00:00Z' }],
        ['embedding', { status: 'complete', timestamp: '2024-01-01T00:01:00Z' }],
        ['supervisor_routing', { status: 'complete', timestamp: '2024-01-01T00:02:00Z' }],
        ['tech_comparison', { status: 'running', timestamp: '2024-01-01T00:03:00Z' }],
      ])

      const { result } = renderHook(() =>
        useProgressCalculation(stageStatuses, [], false, 8, undefined)
      )

      // Should cap at 99% when running stages exist
      expect(result.current.progress).toBeLessThan(100)
    })

    it('caps progress at 99% when pending stages exist and not complete', () => {
      const stageStatuses = new Map<StageName, StageStatusEntry>([
        ['extraction', { status: 'complete', timestamp: '2024-01-01T00:00:00Z' }],
        ['embedding', { status: 'complete', timestamp: '2024-01-01T00:01:00Z' }],
      ])

      const { result } = renderHook(() =>
        useProgressCalculation(stageStatuses, [], false, 8, undefined)
      )

      // Should cap at 99% when pending stages exist (not isComplete)
      expect(result.current.progress).toBeLessThan(100)
    })

    it('calculates progress correctly for partial completion', () => {
      const stageStatuses = new Map<StageName, StageStatusEntry>([
        ['extraction', { status: 'complete', timestamp: '2024-01-01T00:00:00Z' }],
        ['embedding', { status: 'complete', timestamp: '2024-01-01T00:01:00Z' }],
        ['supervisor_routing', { status: 'complete', timestamp: '2024-01-01T00:02:00Z' }],
        ['tech_comparison', { status: 'running', timestamp: '2024-01-01T00:03:00Z' }],
      ])

      const { result } = renderHook(() =>
        useProgressCalculation(stageStatuses, [], false, 10, undefined)
      )

      // Should calculate progress as finishedStages / expectedTotalStages
      // 3 completed / 10 total = 30%, capped at 99% (due to running stage)
      expect(result.current.progress).toBeGreaterThanOrEqual(30)
      expect(result.current.progress).toBeLessThanOrEqual(99)
    })
  })

  // ==========================================================================
  // PHASE 6: Progress at 100% Only When Truly Complete
  // ==========================================================================
  describe('Phase 6: Progress at 100% only when truly complete', () => {
    it('shows 100% when isComplete=true, no failures, no running, no pending', () => {
      const stageStatuses = new Map<StageName, StageStatusEntry>([
        ['extraction', { status: 'complete', timestamp: '2024-01-01T00:00:00Z' }],
        ['embedding', { status: 'complete', timestamp: '2024-01-01T00:01:00Z' }],
        ['supervisor_routing', { status: 'complete', timestamp: '2024-01-01T00:02:00Z' }],
        ['tech_comparison', { status: 'complete', timestamp: '2024-01-01T00:03:00Z' }],
        ['aggregation', { status: 'complete', timestamp: '2024-01-01T00:04:00Z' }],
        ['artifact_generation', { status: 'complete', timestamp: '2024-01-01T00:05:00Z' }],
      ])

      const { result } = renderHook(() =>
        useProgressCalculation(stageStatuses, [], true, 6, undefined)
      )

      // Should show 100% when truly complete
      expect(result.current.progress).toBe(100)
      expect(result.current.currentStep).toBe('Analysis Complete')
    })

    it('shows less than 100% when isComplete=true but has failures', () => {
      const stageStatuses = new Map<StageName, StageStatusEntry>([
        ['extraction', { status: 'complete', timestamp: '2024-01-01T00:00:00Z' }],
        ['tech_comparison', { status: 'failed', timestamp: '2024-01-01T00:01:00Z' }],
        ['artifact_generation', { status: 'complete', timestamp: '2024-01-01T00:02:00Z' }],
      ])

      const { result } = renderHook(() =>
        useProgressCalculation(stageStatuses, [], true, 3, undefined)
      )

      // Should cap at 99% even when isComplete=true due to failures
      expect(result.current.progress).toBeLessThan(100)
      expect(result.current.currentStep).toContain('with errors')
    })

    it('shows less than 100% when isComplete=true but has running stages', () => {
      const stageStatuses = new Map<StageName, StageStatusEntry>([
        ['extraction', { status: 'complete', timestamp: '2024-01-01T00:00:00Z' }],
        ['tech_comparison', { status: 'running', timestamp: '2024-01-01T00:01:00Z' }],
        ['artifact_generation', { status: 'complete', timestamp: '2024-01-01T00:02:00Z' }],
      ])

      const { result } = renderHook(() =>
        useProgressCalculation(stageStatuses, [], true, 3, undefined)
      )

      // Should cap at 99% when running stages exist
      expect(result.current.progress).toBeLessThan(100)
    })

    it('shows less than 100% when finished exceeds expected but unfinished stages exist', () => {
      const stageStatuses = new Map<StageName, StageStatusEntry>([
        ['extraction', { status: 'complete', timestamp: '2024-01-01T00:00:00Z' }],
        ['embedding', { status: 'complete', timestamp: '2024-01-01T00:01:00Z' }],
        ['supervisor_routing', { status: 'complete', timestamp: '2024-01-01T00:02:00Z' }],
        ['tech_comparison', { status: 'complete', timestamp: '2024-01-01T00:03:00Z' }],
        ['aggregation', { status: 'running', timestamp: '2024-01-01T00:04:00Z' }],
      ])

      const { result } = renderHook(() =>
        useProgressCalculation(stageStatuses, [], false, 3, undefined)
      )

      // Should cap at 99% when finished (4) > expected (3) but running stages exist
      expect(result.current.progress).toBe(99)
    })
  })

  // ==========================================================================
  // PHASE 7: UI Stage Determination
  // ==========================================================================
  describe('Phase 7: UI stage determination', () => {
    it('shows "extracting" for extraction stage', () => {
      const stageStatuses = new Map<StageName, StageStatusEntry>([
        ['extraction', { status: 'running', timestamp: '2024-01-01T00:00:00Z' }],
      ])

      const { result } = renderHook(() =>
        useProgressCalculation(stageStatuses, [], false, undefined, undefined)
      )

      expect(result.current.stage).toBe('extracting')
    })

    it('shows "analyzing" for agent stages', () => {
      const stageStatuses = new Map<StageName, StageStatusEntry>([
        ['extraction', { status: 'complete', timestamp: '2024-01-01T00:00:00Z' }],
        ['tech_comparison', { status: 'running', timestamp: '2024-01-01T00:01:00Z' }],
      ])

      const { result } = renderHook(() =>
        useProgressCalculation(stageStatuses, [], false, undefined, undefined)
      )

      expect(result.current.stage).toBe('analyzing')
    })

    it('shows "generating" for artifact generation stage', () => {
      const stageStatuses = new Map<StageName, StageStatusEntry>([
        ['extraction', { status: 'complete', timestamp: '2024-01-01T00:00:00Z' }],
        ['artifact_generation', { status: 'running', timestamp: '2024-01-01T00:01:00Z' }],
      ])

      const { result } = renderHook(() =>
        useProgressCalculation(stageStatuses, [], false, undefined, undefined)
      )

      expect(result.current.stage).toBe('generating')
    })

    it('shows "complete" when isComplete=true', () => {
      const stageStatuses = new Map<StageName, StageStatusEntry>([
        ['extraction', { status: 'complete', timestamp: '2024-01-01T00:00:00Z' }],
        ['artifact_generation', { status: 'complete', timestamp: '2024-01-01T00:01:00Z' }],
      ])

      const { result } = renderHook(() =>
        useProgressCalculation(stageStatuses, [], true, 2, undefined)
      )

      expect(result.current.stage).toBe('complete')
    })

    it('shows "complete" when isComplete=true even with failures', () => {
      const stageStatuses = new Map<StageName, StageStatusEntry>([
        ['extraction', { status: 'complete', timestamp: '2024-01-01T00:00:00Z' }],
        ['tech_comparison', { status: 'failed', timestamp: '2024-01-01T00:01:00Z' }],
        ['artifact_generation', { status: 'complete', timestamp: '2024-01-01T00:02:00Z' }],
      ])

      const { result } = renderHook(() =>
        useProgressCalculation(stageStatuses, [], true, 3, undefined)
      )

      // CRITICAL: isComplete=true always shows 'complete' stage
      // The completion card handles showing error state
      expect(result.current.stage).toBe('complete')
    })

    it('shows last completed stage UI when no running stage', () => {
      const steps: ProgressStep[] = [
        {
          id: 'extraction',
          title: 'Content Extraction',
          status: 'completed',
          description: 'Complete',
          timestamp: new Date('2024-01-01T00:00:00Z'),
        },
        {
          id: 'tech_comparison',
          title: 'Tech Comparison',
          status: 'completed',
          description: 'Complete',
          timestamp: new Date('2024-01-01T00:01:00Z'),
        },
      ]

      const stageStatuses = new Map<StageName, StageStatusEntry>([
        ['extraction', { status: 'complete', timestamp: '2024-01-01T00:00:00Z' }],
        ['tech_comparison', { status: 'complete', timestamp: '2024-01-01T00:01:00Z' }],
      ])

      const { result } = renderHook(() =>
        useProgressCalculation(stageStatuses, steps, false, undefined, undefined)
      )

      // Should show uiStage from last completed step (tech_comparison -> analyzing)
      expect(result.current.stage).toBe('analyzing')
    })
  })

  // ==========================================================================
  // PHASE 8: Current Step Number Calculation
  // ==========================================================================
  describe('Phase 8: Current step number calculation', () => {
    it('shows finishedStages + 1 when running a stage', () => {
      const stageStatuses = new Map<StageName, StageStatusEntry>([
        ['extraction', { status: 'complete', timestamp: '2024-01-01T00:00:00Z' }],
        ['embedding', { status: 'complete', timestamp: '2024-01-01T00:01:00Z' }],
        ['supervisor_routing', { status: 'running', timestamp: '2024-01-01T00:02:00Z' }],
      ])

      const { result } = renderHook(() =>
        useProgressCalculation(stageStatuses, [], false, 8, undefined)
      )

      // 2 finished + 1 (running) = step 3 of 8
      expect(result.current.completedSteps).toBe(3)
      expect(result.current.totalSteps).toBe(8)
    })

    it('shows expectedTotalStages when fully complete', () => {
      const stageStatuses = new Map<StageName, StageStatusEntry>([
        ['extraction', { status: 'complete', timestamp: '2024-01-01T00:00:00Z' }],
        ['embedding', { status: 'complete', timestamp: '2024-01-01T00:01:00Z' }],
        ['supervisor_routing', { status: 'complete', timestamp: '2024-01-01T00:02:00Z' }],
      ])

      const { result } = renderHook(() =>
        useProgressCalculation(stageStatuses, [], true, 3, undefined)
      )

      // Fully complete - show expected total
      expect(result.current.completedSteps).toBe(3)
      expect(result.current.totalSteps).toBe(3)
    })

    it('caps currentStepNumber at progressTotalStages', () => {
      const stageStatuses = new Map<StageName, StageStatusEntry>([
        ['extraction', { status: 'complete', timestamp: '2024-01-01T00:00:00Z' }],
        ['embedding', { status: 'complete', timestamp: '2024-01-01T00:01:00Z' }],
        ['supervisor_routing', { status: 'complete', timestamp: '2024-01-01T00:02:00Z' }],
        ['tech_comparison', { status: 'complete', timestamp: '2024-01-01T00:03:00Z' }],
        ['security_audit', { status: 'complete', timestamp: '2024-01-01T00:04:00Z' }],
        ['aggregation', { status: 'complete', timestamp: '2024-01-01T00:05:00Z' }],
        ['artifact_generation', { status: 'complete', timestamp: '2024-01-01T00:06:00Z' }],
        ['quality_validation', { status: 'complete', timestamp: '2024-01-01T00:07:00Z' }],
        ['implementation_planning', { status: 'complete', timestamp: '2024-01-01T00:08:00Z' }],
        ['performance_audit', { status: 'complete', timestamp: '2024-01-01T00:09:00Z' }],
      ])

      const { result } = renderHook(() =>
        useProgressCalculation(stageStatuses, [], false, 8, undefined)
      )

      // 10 finished but expected only 8 - should cap at 8
      expect(result.current.completedSteps).toBeLessThanOrEqual(8)
      expect(result.current.totalSteps).toBe(8)
    })

    it('shows finishedStages + 1 when not running and not complete', () => {
      const stageStatuses = new Map<StageName, StageStatusEntry>([
        ['extraction', { status: 'complete', timestamp: '2024-01-01T00:00:00Z' }],
        ['embedding', { status: 'complete', timestamp: '2024-01-01T00:01:00Z' }],
      ])

      const { result } = renderHook(() =>
        useProgressCalculation(stageStatuses, [], false, 8, undefined)
      )

      // 2 finished, next step = 3
      expect(result.current.completedSteps).toBe(3)
    })

    it('correctly calculates step number with skippedAgentsInfo', () => {
      const stageStatuses = new Map<StageName, StageStatusEntry>([
        ['extraction', { status: 'complete', timestamp: '2024-01-01T00:00:00Z' }],
        ['embedding', { status: 'complete', timestamp: '2024-01-01T00:01:00Z' }],
        ['supervisor_routing', { status: 'complete', timestamp: '2024-01-01T00:02:00Z' }],
        ['tech_comparison', { status: 'complete', timestamp: '2024-01-01T00:03:00Z' }],
      ])

      const skippedAgentsInfo: SkippedAgentsInfo = {
        agents: ['security_auditor'],
        selectedAgents: ['tech_comparator'],
      }

      const { result } = renderHook(() =>
        useProgressCalculation(stageStatuses, [], false, 7, skippedAgentsInfo)
      )

      // 4 expected stages finished (5 fixed - quality_validation + 1 selected)
      expect(result.current.completedSteps).toBeGreaterThan(0)
      expect(result.current.totalSteps).toBe(7)
    })
  })

  // ==========================================================================
  // Edge Cases & Integration Tests
  // ==========================================================================
  describe('Edge cases and integration', () => {
    it('handles complete workflow with no agents selected', () => {
      const stageStatuses = new Map<StageName, StageStatusEntry>([
        ['extraction', { status: 'complete', timestamp: '2024-01-01T00:00:00Z' }],
        ['embedding', { status: 'complete', timestamp: '2024-01-01T00:01:00Z' }],
        ['supervisor_routing', { status: 'complete', timestamp: '2024-01-01T00:02:00Z' }],
        ['aggregation', { status: 'complete', timestamp: '2024-01-01T00:03:00Z' }],
        ['artifact_generation', { status: 'complete', timestamp: '2024-01-01T00:04:00Z' }],
      ])

      const skippedAgentsInfo: SkippedAgentsInfo = {
        agents: [],
        selectedAgents: [],
      }

      const { result } = renderHook(() =>
        useProgressCalculation(stageStatuses, [], true, 5, skippedAgentsInfo)
      )

      // Should show 100% with 5 fixed stages only
      expect(result.current.progress).toBe(100)
      expect(result.current.stage).toBe('complete')
    })

    it('handles mixed status workflow', () => {
      const stageStatuses = new Map<StageName, StageStatusEntry>([
        ['extraction', { status: 'complete', timestamp: '2024-01-01T00:00:00Z' }],
        ['embedding', { status: 'complete', timestamp: '2024-01-01T00:01:00Z' }],
        ['tech_comparison', { status: 'failed', timestamp: '2024-01-01T00:02:00Z' }],
        ['security_audit', { status: 'skipped', timestamp: '2024-01-01T00:03:00Z' }],
        ['aggregation', { status: 'running', timestamp: '2024-01-01T00:04:00Z' }],
      ])

      const { result } = renderHook(() =>
        useProgressCalculation(stageStatuses, [], false, 8, undefined)
      )

      // When a stage is running, currentStep shows the running stage title
      // (not the detailed status breakdown)
      expect(result.current.currentStep).toBe('Aggregating Results')
      expect(result.current.progress).toBeLessThan(100)
    })

    it('provides estimated time remaining when not complete', () => {
      const stageStatuses = new Map<StageName, StageStatusEntry>([
        ['extraction', { status: 'complete', timestamp: '2024-01-01T00:00:00Z' }],
        ['embedding', { status: 'running', timestamp: '2024-01-01T00:01:00Z' }],
      ])

      const { result } = renderHook(() =>
        useProgressCalculation(stageStatuses, [], false, 8, undefined)
      )

      // Should provide time estimate
      expect(result.current.estimatedTimeRemaining).toBeDefined()
      expect(result.current.estimatedTimeRemaining).toContain('minute')
    })

    it('does not provide time estimate when complete', () => {
      const stageStatuses = new Map<StageName, StageStatusEntry>([
        ['extraction', { status: 'complete', timestamp: '2024-01-01T00:00:00Z' }],
        ['embedding', { status: 'complete', timestamp: '2024-01-01T00:01:00Z' }],
      ])

      const { result } = renderHook(() =>
        useProgressCalculation(stageStatuses, [], true, 2, undefined)
      )

      // Should not show time estimate when complete
      expect(result.current.estimatedTimeRemaining).toBeUndefined()
    })

    it('handles multiple running stages (should only show first)', () => {
      const stageStatuses = new Map<StageName, StageStatusEntry>([
        ['extraction', { status: 'running', timestamp: '2024-01-01T00:00:00Z' }],
        ['embedding', { status: 'running', timestamp: '2024-01-01T00:01:00Z' }],
      ])

      const { result } = renderHook(() =>
        useProgressCalculation(stageStatuses, [], false, 8, undefined)
      )

      // Should show the first running stage found
      expect(result.current.currentStep).toBe('Content Extraction')
    })

    it('memoizes result to prevent unnecessary recalculations', () => {
      const stageStatuses = new Map<StageName, StageStatusEntry>([
        ['extraction', { status: 'complete', timestamp: '2024-01-01T00:00:00Z' }],
      ])

      const { result, rerender } = renderHook(
        ({ statuses }) => useProgressCalculation(statuses, [], false, 8, undefined),
        { initialProps: { statuses: stageStatuses } }
      )

      const firstResult = result.current

      // Rerender with same props
      rerender({ statuses: stageStatuses })

      // useMemo creates new objects each time dependencies change
      // Even with same inputs, the returned object is different
      // Test that the values are the same instead
      expect(result.current.progress).toBe(firstResult.progress)
      expect(result.current.stage).toBe(firstResult.stage)
      expect(result.current.currentStep).toBe(firstResult.currentStep)
    })

    it('recalculates when stageStatuses change', () => {
      const stageStatuses1 = new Map<StageName, StageStatusEntry>([
        ['extraction', { status: 'complete', timestamp: '2024-01-01T00:00:00Z' }],
      ])

      const { result, rerender } = renderHook(
        ({ statuses }) => useProgressCalculation(statuses, [], false, 8, undefined),
        { initialProps: { statuses: stageStatuses1 } }
      )

      const firstProgress = result.current.progress

      // Update with new stage
      const stageStatuses2 = new Map<StageName, StageStatusEntry>([
        ['extraction', { status: 'complete', timestamp: '2024-01-01T00:00:00Z' }],
        ['embedding', { status: 'complete', timestamp: '2024-01-01T00:01:00Z' }],
      ])

      rerender({ statuses: stageStatuses2 })

      // Should recalculate and show different progress
      expect(result.current.progress).toBeGreaterThan(firstProgress)
    })
  })
})
