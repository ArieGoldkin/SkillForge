/**
 * Tests for useProgressSteps - Transform stage statuses to UI-friendly steps
 *
 * This hook extracts step building logic from useAnalysisProgress.
 * Tests validate:
 * - Empty stageStatuses map returns pending steps
 * - Status mapping (running -> in-progress, complete -> completed)
 * - Skip reason extraction (stage details -> skipReasons dict -> default)
 * - Success metrics extraction for completed stages
 * - Error details extraction for failed stages
 * - Steps sorted by STAGE_CONFIG order
 * - Correct title and description for each stage
 */

import type { StageName } from '@app-types/sse'
import { renderHook } from '@testing-library/react'
import { describe, expect, it } from 'vitest'

import type { SuccessMetrics } from '@/schemas/sse'

import type { StageStatusEntry } from '../useProgressSteps'
import { useProgressSteps } from '../useProgressSteps'

// Valid UUIDs for testing
const TEST_TIMESTAMP = '2024-01-01T00:00:00Z'

describe('useProgressSteps', () => {
  describe('empty stageStatuses map', () => {
    it('returns all stages as pending when stageStatuses is empty', () => {
      const stageStatuses = new Map<StageName, StageStatusEntry>()

      const { result } = renderHook(() => useProgressSteps(stageStatuses))

      // Should return all stages with pending status
      expect(result.current.length).toBeGreaterThan(0)
      result.current.forEach((step) => {
        expect(step.status).toBe('pending')
        expect(step.description).toBe('Waiting...')
        expect(step.timestamp).toBeUndefined()
      })
    })

    it('returns steps with correct titles and IDs', () => {
      const stageStatuses = new Map<StageName, StageStatusEntry>()

      const { result } = renderHook(() => useProgressSteps(stageStatuses))

      // Verify some key stages have correct titles
      const extractionStep = result.current.find((s) => s.id === 'extraction')
      expect(extractionStep?.title).toBe('Content Extraction')

      const techComparisonStep = result.current.find((s) => s.id === 'tech_comparison')
      expect(techComparisonStep?.title).toBe('Tech Comparison')

      const artifactStep = result.current.find((s) => s.id === 'artifact_generation')
      expect(artifactStep?.title).toBe('Generating Report')
    })
  })

  describe('status mapping', () => {
    it('maps backend "running" to UI "in-progress"', () => {
      const stageStatuses = new Map<StageName, StageStatusEntry>([
        [
          'tech_comparison',
          {
            status: 'running',
            timestamp: TEST_TIMESTAMP,
          },
        ],
      ])

      const { result } = renderHook(() => useProgressSteps(stageStatuses))

      const techStep = result.current.find((s) => s.id === 'tech_comparison')
      expect(techStep?.status).toBe('in-progress')
    })

    it('maps backend "complete" to UI "completed"', () => {
      const stageStatuses = new Map<StageName, StageStatusEntry>([
        [
          'security_audit',
          {
            status: 'complete',
            timestamp: TEST_TIMESTAMP,
          },
        ],
      ])

      const { result } = renderHook(() => useProgressSteps(stageStatuses))

      const securityStep = result.current.find((s) => s.id === 'security_audit')
      expect(securityStep?.status).toBe('completed')
    })

    it('maps backend "failed" to UI "failed"', () => {
      const stageStatuses = new Map<StageName, StageStatusEntry>([
        [
          'implementation_planning',
          {
            status: 'failed',
            timestamp: TEST_TIMESTAMP,
          },
        ],
      ])

      const { result } = renderHook(() => useProgressSteps(stageStatuses))

      const implStep = result.current.find((s) => s.id === 'implementation_planning')
      expect(implStep?.status).toBe('failed')
    })

    it('maps backend "skipped" to UI "skipped"', () => {
      const stageStatuses = new Map<StageName, StageStatusEntry>([
        [
          'performance_audit',
          {
            status: 'skipped',
            timestamp: TEST_TIMESTAMP,
          },
        ],
      ])

      const { result } = renderHook(() => useProgressSteps(stageStatuses))

      const perfStep = result.current.find((s) => s.id === 'performance_audit')
      expect(perfStep?.status).toBe('skipped')
    })

    it('maps backend "pending" to UI "pending"', () => {
      const stageStatuses = new Map<StageName, StageStatusEntry>([
        [
          'code_quality_audit',
          {
            status: 'pending',
            timestamp: TEST_TIMESTAMP,
          },
        ],
      ])

      const { result } = renderHook(() => useProgressSteps(stageStatuses))

      const codeQualityStep = result.current.find((s) => s.id === 'code_quality_audit')
      expect(codeQualityStep?.status).toBe('pending')
    })
  })

  describe('skip reason extraction', () => {
    it('extracts skip reason from stage details.skip_reason', () => {
      const stageStatuses = new Map<StageName, StageStatusEntry>([
        [
          'security_audit',
          {
            status: 'skipped',
            timestamp: TEST_TIMESTAMP,
            details: {
              skip_reason: 'Not applicable for this content type',
            },
          },
        ],
      ])

      const { result } = renderHook(() => useProgressSteps(stageStatuses))

      const securityStep = result.current.find((s) => s.id === 'security_audit')
      expect(securityStep?.skipReason).toBe('Not applicable for this content type')
      expect(securityStep?.description).toContain('Skipped: Not applicable for this content type')
    })

    it('extracts skip reason from skipReasons dictionary', () => {
      const stageStatuses = new Map<StageName, StageStatusEntry>([
        [
          'tech_comparison',
          {
            status: 'skipped',
            timestamp: TEST_TIMESTAMP,
          },
        ],
      ])

      const skipReasons = {
        tech_comparator: 'Content does not require technology comparison',
      }

      const { result } = renderHook(() => useProgressSteps(stageStatuses, skipReasons))

      const techStep = result.current.find((s) => s.id === 'tech_comparison')
      expect(techStep?.skipReason).toBe('Content does not require technology comparison')
    })

    it('prioritizes stage details.skip_reason over skipReasons dictionary', () => {
      const stageStatuses = new Map<StageName, StageStatusEntry>([
        [
          'implementation_planning',
          {
            status: 'skipped',
            timestamp: TEST_TIMESTAMP,
            details: {
              skip_reason: 'Stage-specific reason from details',
            },
          },
        ],
      ])

      const skipReasons = {
        implementation_planner: 'Generic reason from dict',
      }

      const { result } = renderHook(() => useProgressSteps(stageStatuses, skipReasons))

      const implStep = result.current.find((s) => s.id === 'implementation_planning')
      // Should use details.skip_reason, not skipReasons dict
      expect(implStep?.skipReason).toBe('Stage-specific reason from details')
    })

    it('uses default "Not selected by supervisor" when no skip reason available', () => {
      const stageStatuses = new Map<StageName, StageStatusEntry>([
        [
          'performance_audit',
          {
            status: 'skipped',
            timestamp: TEST_TIMESTAMP,
          },
        ],
      ])

      const { result } = renderHook(() => useProgressSteps(stageStatuses))

      const perfStep = result.current.find((s) => s.id === 'performance_audit')
      expect(perfStep?.skipReason).toBe('Not selected by supervisor')
    })

    it('does not extract skip reason for non-skipped stages', () => {
      const stageStatuses = new Map<StageName, StageStatusEntry>([
        [
          'security_audit',
          {
            status: 'complete',
            timestamp: TEST_TIMESTAMP,
            details: {
              skip_reason: 'This should be ignored since status is not skipped',
            },
          },
        ],
      ])

      const { result } = renderHook(() => useProgressSteps(stageStatuses))

      const securityStep = result.current.find((s) => s.id === 'security_audit')
      expect(securityStep?.skipReason).toBeUndefined()
    })
  })

  describe('success metrics extraction', () => {
    it('extracts success metrics for completed stages', () => {
      const stageStatuses = new Map<StageName, StageStatusEntry>([
        [
          'tech_comparison',
          {
            status: 'complete',
            timestamp: TEST_TIMESTAMP,
          },
        ],
      ])

      const successMetrics = new Map<string, SuccessMetrics>([
        [
          'tech_comparison',
          {
            findings_quality: 'high',
            coverage: 'comprehensive',
            key_insights: ['React performs better', 'Vue has simpler syntax'],
          },
        ],
      ])

      const { result } = renderHook(() =>
        useProgressSteps(stageStatuses, undefined, successMetrics)
      )

      const techStep = result.current.find((s) => s.id === 'tech_comparison')
      expect(techStep?.successMetrics).toBeDefined()
      expect(techStep?.successMetrics?.findings_quality).toBe('high')
      expect(techStep?.successMetrics?.coverage).toBe('comprehensive')
      expect(techStep?.successMetrics?.key_insights).toHaveLength(2)
    })

    it('does not extract success metrics for non-completed stages', () => {
      const stageStatuses = new Map<StageName, StageStatusEntry>([
        [
          'security_audit',
          {
            status: 'running',
            timestamp: TEST_TIMESTAMP,
          },
        ],
      ])

      const successMetrics = new Map<string, SuccessMetrics>([
        [
          'security_audit',
          {
            findings_quality: 'medium',
            coverage: 'partial',
          },
        ],
      ])

      const { result } = renderHook(() =>
        useProgressSteps(stageStatuses, undefined, successMetrics)
      )

      const securityStep = result.current.find((s) => s.id === 'security_audit')
      // Should not extract success metrics for running stage
      expect(securityStep?.successMetrics).toBeUndefined()
    })

    it('handles missing success metrics gracefully', () => {
      const stageStatuses = new Map<StageName, StageStatusEntry>([
        [
          'implementation_planning',
          {
            status: 'complete',
            timestamp: TEST_TIMESTAMP,
          },
        ],
      ])

      // No success metrics provided
      const { result } = renderHook(() => useProgressSteps(stageStatuses, undefined, undefined))

      const implStep = result.current.find((s) => s.id === 'implementation_planning')
      expect(implStep?.successMetrics).toBeUndefined()
    })
  })

  describe('error details extraction', () => {
    it('extracts error details for failed stages', () => {
      const stageStatuses = new Map<StageName, StageStatusEntry>([
        [
          'tech_comparison',
          {
            status: 'failed',
            timestamp: TEST_TIMESTAMP,
            details: {
              error: 'Agent execution failed',
              error_code: 'TECH_COMPARATOR_FAILED',
              processing_time_ms: 5000,
            },
          },
        ],
      ])

      const { result } = renderHook(() => useProgressSteps(stageStatuses))

      const techStep = result.current.find((s) => s.id === 'tech_comparison')
      expect(techStep?.errorDetails).toBeDefined()
      expect(techStep?.errorDetails?.error).toBe('Agent execution failed')
      expect(techStep?.errorDetails?.errorCode).toBe('TECH_COMPARATOR_FAILED')
      expect(techStep?.errorDetails?.processingTime).toBe(5000)
    })

    it('uses error_code as error message when error not available', () => {
      const stageStatuses = new Map<StageName, StageStatusEntry>([
        [
          'security_audit',
          {
            status: 'failed',
            timestamp: TEST_TIMESTAMP,
            details: {
              error_code: 'SECURITY_AUDITOR_FAILED',
            },
          },
        ],
      ])

      const { result } = renderHook(() => useProgressSteps(stageStatuses))

      const securityStep = result.current.find((s) => s.id === 'security_audit')
      expect(securityStep?.errorDetails).toBeDefined()
      expect(securityStep?.errorDetails?.error).toBe('SECURITY_AUDITOR_FAILED')
      expect(securityStep?.errorDetails?.errorCode).toBe('SECURITY_AUDITOR_FAILED')
    })

    it('uses "Unknown error" when no error details available', () => {
      const stageStatuses = new Map<StageName, StageStatusEntry>([
        [
          'implementation_planning',
          {
            status: 'failed',
            timestamp: TEST_TIMESTAMP,
            details: {
              processing_time_ms: 3000,
            },
          },
        ],
      ])

      const { result } = renderHook(() => useProgressSteps(stageStatuses))

      const implStep = result.current.find((s) => s.id === 'implementation_planning')
      expect(implStep?.errorDetails).toBeDefined()
      expect(implStep?.errorDetails?.error).toBe('Unknown error')
      expect(implStep?.errorDetails?.errorCode).toBeUndefined()
      expect(implStep?.errorDetails?.processingTime).toBe(3000)
    })

    it('does not extract error details for non-failed stages', () => {
      const stageStatuses = new Map<StageName, StageStatusEntry>([
        [
          'performance_audit',
          {
            status: 'complete',
            timestamp: TEST_TIMESTAMP,
            details: {
              error: 'This should be ignored since status is not failed',
              error_code: 'IGNORED_ERROR',
            },
          },
        ],
      ])

      const { result } = renderHook(() => useProgressSteps(stageStatuses))

      const perfStep = result.current.find((s) => s.id === 'performance_audit')
      expect(perfStep?.errorDetails).toBeUndefined()
    })

    it('handles failed stage with empty details object', () => {
      const stageStatuses = new Map<StageName, StageStatusEntry>([
        [
          'code_quality_audit',
          {
            status: 'failed',
            timestamp: TEST_TIMESTAMP,
            details: {},
          },
        ],
      ])

      const { result } = renderHook(() => useProgressSteps(stageStatuses))

      const codeQualityStep = result.current.find((s) => s.id === 'code_quality_audit')
      expect(codeQualityStep?.errorDetails).toBeDefined()
      expect(codeQualityStep?.errorDetails?.error).toBe('Unknown error')
    })
  })

  describe('steps sorted by STAGE_CONFIG order', () => {
    it('returns steps in STAGE_CONFIG order', () => {
      const stageStatuses = new Map<StageName, StageStatusEntry>([
        ['artifact_generation', { status: 'complete', timestamp: TEST_TIMESTAMP }],
        ['extraction', { status: 'complete', timestamp: TEST_TIMESTAMP }],
        ['tech_comparison', { status: 'running', timestamp: TEST_TIMESTAMP }],
        ['supervisor_routing', { status: 'complete', timestamp: TEST_TIMESTAMP }],
      ])

      const { result } = renderHook(() => useProgressSteps(stageStatuses))

      // Find indices of known stages
      const extractionIndex = result.current.findIndex((s) => s.id === 'extraction')
      const supervisorIndex = result.current.findIndex((s) => s.id === 'supervisor_routing')
      const techComparisonIndex = result.current.findIndex((s) => s.id === 'tech_comparison')
      const artifactIndex = result.current.findIndex((s) => s.id === 'artifact_generation')

      // Verify order matches STAGE_CONFIG
      expect(extractionIndex).toBeLessThan(supervisorIndex)
      expect(supervisorIndex).toBeLessThan(techComparisonIndex)
      expect(techComparisonIndex).toBeLessThan(artifactIndex)
    })

    it('maintains order even with mixed statuses', () => {
      const stageStatuses = new Map<StageName, StageStatusEntry>([
        ['aggregation', { status: 'running', timestamp: TEST_TIMESTAMP }],
        ['extraction', { status: 'complete', timestamp: TEST_TIMESTAMP }],
        ['security_audit', { status: 'skipped', timestamp: TEST_TIMESTAMP }],
        ['implementation_planning', { status: 'failed', timestamp: TEST_TIMESTAMP }],
      ])

      const { result } = renderHook(() => useProgressSteps(stageStatuses))

      // Extraction (order 1) should come before security_audit (order 5)
      const extractionIndex = result.current.findIndex((s) => s.id === 'extraction')
      const securityIndex = result.current.findIndex((s) => s.id === 'security_audit')
      expect(extractionIndex).toBeLessThan(securityIndex)

      // Security_audit (order 5) should come before implementation_planning (order 6)
      const implIndex = result.current.findIndex((s) => s.id === 'implementation_planning')
      expect(securityIndex).toBeLessThan(implIndex)

      // Implementation_planning (order 6) should come before aggregation (order 11)
      const aggregationIndex = result.current.findIndex((s) => s.id === 'aggregation')
      expect(implIndex).toBeLessThan(aggregationIndex)
    })
  })

  describe('stage descriptions', () => {
    it('uses getStageDescription for description text', () => {
      const stageStatuses = new Map<StageName, StageStatusEntry>([
        [
          'extraction',
          {
            status: 'complete',
            timestamp: TEST_TIMESTAMP,
            details: {
              word_count: 1500,
            },
          },
        ],
      ])

      const { result } = renderHook(() => useProgressSteps(stageStatuses))

      const extractionStep = result.current.find((s) => s.id === 'extraction')
      expect(extractionStep?.description).toBe('Extracted 1500 words')
    })

    it('uses findings_summary in description when available', () => {
      const stageStatuses = new Map<StageName, StageStatusEntry>([
        [
          'tech_comparison',
          {
            status: 'complete',
            timestamp: TEST_TIMESTAMP,
            details: {
              findings_summary: 'Compared React vs Vue, Angular',
            },
          },
        ],
      ])

      const { result } = renderHook(() => useProgressSteps(stageStatuses))

      const techStep = result.current.find((s) => s.id === 'tech_comparison')
      expect(techStep?.description).toBe('Compared React vs Vue, Angular')
    })

    it('uses insights_count in description when findings_summary not available', () => {
      const stageStatuses = new Map<StageName, StageStatusEntry>([
        [
          'security_audit',
          {
            status: 'complete',
            timestamp: TEST_TIMESTAMP,
            details: {
              insights_count: 5,
            },
          },
        ],
      ])

      const { result } = renderHook(() => useProgressSteps(stageStatuses))

      const securityStep = result.current.find((s) => s.id === 'security_audit')
      expect(securityStep?.description).toBe('Found 5 insights')
    })

    it('uses "Waiting..." for pending stages', () => {
      const stageStatuses = new Map<StageName, StageStatusEntry>()

      const { result } = renderHook(() => useProgressSteps(stageStatuses))

      const techStep = result.current.find((s) => s.id === 'tech_comparison')
      expect(techStep?.description).toBe('Waiting...')
    })
  })

  describe('timestamp handling', () => {
    it('converts ISO timestamp string to Date object', () => {
      const stageStatuses = new Map<StageName, StageStatusEntry>([
        [
          'tech_comparison',
          {
            status: 'complete',
            timestamp: '2024-01-15T10:30:45Z',
          },
        ],
      ])

      const { result } = renderHook(() => useProgressSteps(stageStatuses))

      const techStep = result.current.find((s) => s.id === 'tech_comparison')
      expect(techStep?.timestamp).toBeInstanceOf(Date)
      expect(techStep?.timestamp?.toISOString()).toBe('2024-01-15T10:30:45.000Z')
    })

    it('leaves timestamp undefined for stages without status', () => {
      const stageStatuses = new Map<StageName, StageStatusEntry>()

      const { result } = renderHook(() => useProgressSteps(stageStatuses))

      const techStep = result.current.find((s) => s.id === 'tech_comparison')
      expect(techStep?.timestamp).toBeUndefined()
    })
  })

  describe('memoization', () => {
    it('returns same reference when inputs unchanged', () => {
      const stageStatuses = new Map<StageName, StageStatusEntry>([
        ['extraction', { status: 'complete', timestamp: TEST_TIMESTAMP }],
      ])

      const { result, rerender } = renderHook(() => useProgressSteps(stageStatuses))

      const firstResult = result.current
      rerender()
      const secondResult = result.current

      // Should return same reference due to useMemo
      expect(firstResult).toBe(secondResult)
    })

    it('returns new reference when stageStatuses changes', () => {
      const stageStatuses1 = new Map<StageName, StageStatusEntry>([
        ['extraction', { status: 'complete', timestamp: TEST_TIMESTAMP }],
      ])

      const { result, rerender } = renderHook(({ statuses }) => useProgressSteps(statuses), {
        initialProps: { statuses: stageStatuses1 },
      })

      const firstResult = result.current

      const stageStatuses2 = new Map<StageName, StageStatusEntry>([
        ['extraction', { status: 'complete', timestamp: TEST_TIMESTAMP }],
        ['tech_comparison', { status: 'running', timestamp: TEST_TIMESTAMP }],
      ])

      rerender({ statuses: stageStatuses2 })
      const secondResult = result.current

      // Should return new reference when stageStatuses changes
      expect(firstResult).not.toBe(secondResult)
    })

    it('returns new reference when skipReasons changes', () => {
      const stageStatuses = new Map<StageName, StageStatusEntry>([
        ['tech_comparison', { status: 'skipped', timestamp: TEST_TIMESTAMP }],
      ])

      const { result, rerender } = renderHook(
        ({ skipReasons }) => useProgressSteps(stageStatuses, skipReasons),
        {
          initialProps: { skipReasons: undefined },
        }
      )

      const firstResult = result.current

      const newSkipReasons = { tech_comparator: 'Not needed' }
      rerender({ skipReasons: newSkipReasons })
      const secondResult = result.current

      // Should return new reference when skipReasons changes
      expect(firstResult).not.toBe(secondResult)
    })

    it('returns new reference when stageSuccessMetrics changes', () => {
      const stageStatuses = new Map<StageName, StageStatusEntry>([
        ['tech_comparison', { status: 'complete', timestamp: TEST_TIMESTAMP }],
      ])

      const { result, rerender } = renderHook(
        ({ metrics }) => useProgressSteps(stageStatuses, undefined, metrics),
        {
          initialProps: { metrics: undefined },
        }
      )

      const firstResult = result.current

      const newMetrics = new Map<string, SuccessMetrics>([
        ['tech_comparison', { findings_quality: 'high', coverage: 'comprehensive' }],
      ])
      rerender({ metrics: newMetrics })
      const secondResult = result.current

      // Should return new reference when stageSuccessMetrics changes
      expect(firstResult).not.toBe(secondResult)
    })
  })

  describe('complex scenarios', () => {
    it('handles workflow with multiple completed, running, and skipped stages', () => {
      const stageStatuses = new Map<StageName, StageStatusEntry>([
        ['extraction', { status: 'complete', timestamp: '2024-01-01T00:00:00Z' }],
        ['embedding', { status: 'complete', timestamp: '2024-01-01T00:01:00Z' }],
        ['supervisor_routing', { status: 'complete', timestamp: '2024-01-01T00:02:00Z' }],
        [
          'tech_comparison',
          {
            status: 'complete',
            timestamp: '2024-01-01T00:03:00Z',
            details: { findings_summary: 'Analyzed 3 frameworks' },
          },
        ],
        [
          'security_audit',
          {
            status: 'skipped',
            timestamp: '2024-01-01T00:04:00Z',
            details: { skip_reason: 'Not applicable' },
          },
        ],
        ['implementation_planning', { status: 'running', timestamp: '2024-01-01T00:05:00Z' }],
      ])

      const { result } = renderHook(() => useProgressSteps(stageStatuses))

      // Verify completed stages
      const extractionStep = result.current.find((s) => s.id === 'extraction')
      expect(extractionStep?.status).toBe('completed')

      const techStep = result.current.find((s) => s.id === 'tech_comparison')
      expect(techStep?.status).toBe('completed')
      expect(techStep?.description).toBe('Analyzed 3 frameworks')

      // Verify skipped stage
      const securityStep = result.current.find((s) => s.id === 'security_audit')
      expect(securityStep?.status).toBe('skipped')
      expect(securityStep?.skipReason).toBe('Not applicable')

      // Verify running stage
      const implStep = result.current.find((s) => s.id === 'implementation_planning')
      expect(implStep?.status).toBe('in-progress')

      // Verify pending stages
      const aggregationStep = result.current.find((s) => s.id === 'aggregation')
      expect(aggregationStep?.status).toBe('pending')
    })

    it('handles failed stage with all error details', () => {
      const stageStatuses = new Map<StageName, StageStatusEntry>([
        [
          'performance_audit',
          {
            status: 'failed',
            timestamp: TEST_TIMESTAMP,
            details: {
              error: 'Performance analysis timeout',
              error_code: 'PERFORMANCE_TIMEOUT',
              processing_time_ms: 30000,
            },
          },
        ],
      ])

      const { result } = renderHook(() => useProgressSteps(stageStatuses))

      const perfStep = result.current.find((s) => s.id === 'performance_audit')
      expect(perfStep?.status).toBe('failed')
      expect(perfStep?.errorDetails?.error).toBe('Performance analysis timeout')
      expect(perfStep?.errorDetails?.errorCode).toBe('PERFORMANCE_TIMEOUT')
      expect(perfStep?.errorDetails?.processingTime).toBe(30000)
      expect(perfStep?.description).toContain('Failed: Performance analysis timeout')
    })

    it('handles stage with success metrics and detailed insights', () => {
      const stageStatuses = new Map<StageName, StageStatusEntry>([
        [
          'code_quality_audit',
          {
            status: 'complete',
            timestamp: TEST_TIMESTAMP,
            details: {
              findings_summary: 'Analyzed code quality patterns',
              insights_count: 8,
            },
          },
        ],
      ])

      const successMetrics = new Map<string, SuccessMetrics>([
        [
          'code_quality_audit',
          {
            findings_quality: 'high',
            coverage: 'comprehensive',
            key_insights: [
              'Good separation of concerns',
              'Strong type safety',
              'Comprehensive error handling',
            ],
          },
        ],
      ])

      const { result } = renderHook(() =>
        useProgressSteps(stageStatuses, undefined, successMetrics)
      )

      const codeQualityStep = result.current.find((s) => s.id === 'code_quality_audit')
      expect(codeQualityStep?.status).toBe('completed')
      expect(codeQualityStep?.description).toBe('Analyzed code quality patterns')
      expect(codeQualityStep?.successMetrics?.findings_quality).toBe('high')
      expect(codeQualityStep?.successMetrics?.coverage).toBe('comprehensive')
      expect(codeQualityStep?.successMetrics?.key_insights).toHaveLength(3)
    })
  })
})
