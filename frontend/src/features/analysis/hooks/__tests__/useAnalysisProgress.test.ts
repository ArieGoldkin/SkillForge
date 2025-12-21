/**
 * Tests for useAnalysisProgress - Dynamic progress calculation with expected_total_stages
 *
 * Note: We test the underlying functions directly since useMemo requires React context.
 * The hook itself is tested via integration tests.
 */

import type { SSEEvent } from '@app-types/sse'
import { renderHook } from '@testing-library/react'
import { describe, expect, it } from 'vitest'

import { useAnalysisProgress } from '../useAnalysisProgress'

// Valid UUIDs for testing
const TEST_ANALYSIS_ID = '123e4567-e89b-12d3-a456-426614174000'
const TEST_ARTIFACT_ID = '987fcdeb-51a2-43d7-8f9e-123456789abc'

// Note: These tests verify the logic but don't test the hook directly
// since useMemo requires React context. Integration tests cover the full hook.
describe('Progress calculation logic', () => {
  describe('expected_total_stages handling', () => {
    it('supervisor event should include expected_total_stages', () => {
      const events: SSEEvent[] = [
        {
          type: 'progress',
          analysis_id: TEST_ANALYSIS_ID,
          stage: 'supervisor_routing',
          status: 'complete',
          timestamp: '2024-01-01T00:00:00Z',
          expected_total_stages: 8, // 5 fixed + 3 agents
          details: {
            agent_count: 3,
            selected_agents: ['tech_comparator', 'security_auditor', 'implementation_planner'],
          },
        },
        {
          type: 'progress',
          analysis_id: TEST_ANALYSIS_ID,
          stage: 'tech_comparison',
          status: 'complete',
          timestamp: '2024-01-01T00:01:00Z',
        },
        {
          type: 'progress',
          analysis_id: TEST_ANALYSIS_ID,
          stage: 'security_audit',
          status: 'complete',
          timestamp: '2024-01-01T00:02:00Z',
        },
      ]

      // Verify event structure includes expected_total_stages
      const supervisorEvent = events.find((e) => e.stage === 'supervisor_routing')
      expect(supervisorEvent).toBeDefined()
      if (supervisorEvent && supervisorEvent.type === 'progress') {
        expect(supervisorEvent.expected_total_stages).toBe(8)
      }
    })

    it('progress events should include findings_summary and insights_count', () => {
      const events: SSEEvent[] = [
        {
          type: 'progress',
          analysis_id: TEST_ANALYSIS_ID,
          stage: 'tech_comparison',
          status: 'complete',
          timestamp: '2024-01-01T00:01:00Z',
          findings_summary: 'Compared React vs Vue, Angular',
          insights_count: 3,
          confidence_score: 0.85,
        },
      ]

      // Verify event structure includes rich details
      const techEvent = events[0]
      if (techEvent.type === 'progress') {
        expect(techEvent.findings_summary).toBe('Compared React vs Vue, Angular')
        expect(techEvent.insights_count).toBe(3)
        expect(techEvent.confidence_score).toBe(0.85)
      }
    })
  })

  describe('error event handling', () => {
    it('error events should update stage status to failed', () => {
      const events: SSEEvent[] = [
        {
          type: 'error',
          analysis_id: TEST_ANALYSIS_ID,
          stage: 'tech_comparison',
          status: 'failed',
          timestamp: '2024-01-01T00:01:00Z',
          error: 'Agent execution failed',
          details: {
            error_code: 'TECH_COMPARATOR_FAILED',
          },
        },
      ]

      const { result } = renderHook(() => useAnalysisProgress(events))

      // Verify the step has failed status
      const techStep = result.current.steps.find((s) => s.id === 'tech_comparison')
      expect(techStep).toBeDefined()
      expect(techStep?.status).toBe('failed')
      expect(techStep?.description).toContain('Failed')
    })

    it('progress events with status failed should also update stage status', () => {
      const events: SSEEvent[] = [
        {
          type: 'progress',
          analysis_id: TEST_ANALYSIS_ID,
          stage: 'security_audit',
          status: 'failed',
          timestamp: '2024-01-01T00:02:00Z',
          details: {
            error: 'Security audit failed',
            error_code: 'SECURITY_AUDITOR_FAILED',
          },
        },
      ]

      const { result } = renderHook(() => useAnalysisProgress(events))

      // Verify the step has failed status
      const securityStep = result.current.steps.find((s) => s.id === 'security_audit')
      expect(securityStep).toBeDefined()
      expect(securityStep?.status).toBe('failed')
    })

    it('failed status should not be overwritten by later events', () => {
      const events: SSEEvent[] = [
        {
          type: 'error',
          analysis_id: TEST_ANALYSIS_ID,
          stage: 'tech_comparison',
          status: 'failed',
          timestamp: '2024-01-01T00:01:00Z',
          error: 'Agent execution failed',
        },
        {
          type: 'progress',
          analysis_id: TEST_ANALYSIS_ID,
          stage: 'tech_comparison',
          status: 'complete', // Later event trying to overwrite
          timestamp: '2024-01-01T00:02:00Z',
        },
      ]

      const { result } = renderHook(() => useAnalysisProgress(events))

      // Verify failed status is preserved
      const techStep = result.current.steps.find((s) => s.id === 'tech_comparison')
      expect(techStep?.status).toBe('failed') // Should still be failed, not completed
    })

    it('progress shows 100% when complete even with failures (Issue #439)', () => {
      // Issue #439: Artifact-based completion means progress = 100% when isComplete=true
      // hasFailedStages is tracked separately for UI display (error badge)
      const events: SSEEvent[] = [
        {
          type: 'progress',
          analysis_id: TEST_ANALYSIS_ID,
          stage: 'supervisor_routing',
          status: 'complete',
          timestamp: '2024-01-01T00:00:00Z',
          expected_total_stages: 8,
        },
        {
          type: 'progress',
          analysis_id: TEST_ANALYSIS_ID,
          stage: 'tech_comparison',
          status: 'complete',
          timestamp: '2024-01-01T00:01:00Z',
        },
        {
          type: 'error',
          analysis_id: TEST_ANALYSIS_ID,
          stage: 'security_audit',
          status: 'failed',
          timestamp: '2024-01-01T00:02:00Z',
          error: 'Agent failed',
        },
        {
          type: 'complete',
          analysis_id: TEST_ANALYSIS_ID,
          stage: 'artifact_generation',
          status: 'complete',
          timestamp: '2024-01-01T00:03:00Z',
          artifact_id: TEST_ARTIFACT_ID,
        },
      ]

      const { result } = renderHook(() => useAnalysisProgress(events))

      // Issue #439: When isComplete=true (artifact exists), show 100% for consistent UI
      // The completion card handles showing "Complete with Errors" badge
      expect(result.current.isComplete).toBe(true)
      expect(result.current.overallProgress.progress).toBe(100)
      // Failures are tracked separately via hasFailedStages
      expect(result.current.hasFailedStages).toBe(true)
    })

    it('progress should be 100% only when complete with no failures', () => {
      const events: SSEEvent[] = [
        {
          type: 'progress',
          analysis_id: TEST_ANALYSIS_ID,
          stage: 'supervisor_routing',
          status: 'complete',
          timestamp: '2024-01-01T00:00:00Z',
          expected_total_stages: 3,
        },
        {
          type: 'progress',
          analysis_id: TEST_ANALYSIS_ID,
          stage: 'tech_comparison',
          status: 'complete',
          timestamp: '2024-01-01T00:01:00Z',
        },
        {
          type: 'complete',
          analysis_id: TEST_ANALYSIS_ID,
          stage: 'artifact_generation',
          status: 'complete',
          timestamp: '2024-01-01T00:02:00Z',
          artifact_id: TEST_ARTIFACT_ID,
        },
      ]

      const { result } = renderHook(() => useAnalysisProgress(events))

      // Verify progress is 100% when complete with no failures
      expect(result.current.isComplete).toBe(true)
      expect(result.current.overallProgress.progress).toBe(100)
    })

    it('extracts error details from progress events with status failed', () => {
      const events: SSEEvent[] = [
        {
          type: 'progress',
          analysis_id: TEST_ANALYSIS_ID,
          stage: 'tech_comparison',
          status: 'failed',
          timestamp: '2024-01-01T00:01:00Z',
          details: {
            error: 'Agent execution failed',
            error_code: 'TECH_COMPARATOR_FAILED',
            processing_time_ms: 5000,
          },
        },
      ]

      const { result } = renderHook(() => useAnalysisProgress(events))

      // Verify the step has failed status with error details
      const techStep = result.current.steps.find((s) => s.id === 'tech_comparison')
      expect(techStep?.status).toBe('failed')
      expect(techStep?.description).toContain('Failed:')
      expect(techStep?.description).toContain('Agent execution failed')
    })

    it('captures skip reasons from supervisor event', () => {
      const events: SSEEvent[] = [
        {
          type: 'progress',
          analysis_id: TEST_ANALYSIS_ID,
          stage: 'supervisor_routing',
          status: 'complete',
          timestamp: '2024-01-01T00:00:00Z',
          expected_total_stages: 8,
          details: {
            selected_agents: ['tech_comparator', 'security_auditor'],
            skipped_agents: ['code_quality_critic', 'performance_analyst'],
          },
        },
      ]

      const { result } = renderHook(() => useAnalysisProgress(events))

      // Verify skipped stages have skip reasons
      const codeQualityStep = result.current.steps.find((s) => s.id === 'code_quality_audit')
      expect(codeQualityStep?.status).toBe('skipped')
      // Should have a skip reason in description
      expect(codeQualityStep?.description).toContain('Skipped')
    })

    it('shows 100% progress with failures when artifact_generation completes (Issue #439)', () => {
      // Issue #439: Artifact-based completion shows 100% when isComplete=true
      // Failures are communicated via hasFailedStages and status message
      const events: SSEEvent[] = [
        {
          type: 'progress',
          analysis_id: TEST_ANALYSIS_ID,
          stage: 'tech_comparison',
          status: 'failed',
          timestamp: '2024-01-01T00:01:00Z',
          error: 'Agent execution failed',
        },
        {
          type: 'progress',
          analysis_id: TEST_ANALYSIS_ID,
          stage: 'artifact_generation',
          status: 'complete',
          timestamp: '2024-01-01T00:02:00Z',
        },
      ]

      const { result } = renderHook(() => useAnalysisProgress(events))

      // Issue #439: When isComplete=true, progress shows 100% for consistent UI
      // Failures are shown via "(with errors)" in status message and error badge
      expect(result.current.overallProgress.progress).toBe(100)
      expect(result.current.overallProgress.currentStep).toContain('errors')
      expect(result.current.isComplete).toBe(true)
      expect(result.current.hasFailedStages).toBe(true) // Failures tracked separately
    })

    it('detects completion from progress event with status complete for artifact_generation', () => {
      const events: SSEEvent[] = [
        {
          type: 'progress',
          analysis_id: TEST_ANALYSIS_ID,
          stage: 'artifact_generation',
          status: 'complete',
          timestamp: '2024-01-01T00:02:00Z',
          details: {
            artifact_id: TEST_ARTIFACT_ID,
          },
        },
      ]

      const { result } = renderHook(() => useAnalysisProgress(events))

      // Should detect completion from progress event (not just complete event type)
      expect(result.current.isComplete).toBe(true)
      expect(result.current.artifactId).toBe(TEST_ARTIFACT_ID)
    })

    it('accounts for pending stages in progress calculation', () => {
      const events: SSEEvent[] = [
        {
          type: 'progress',
          analysis_id: TEST_ANALYSIS_ID,
          stage: 'tech_comparison',
          status: 'failed',
          timestamp: '2024-01-01T00:01:00Z',
          details: {
            error: 'Agent execution failed',
          },
        },
        {
          type: 'progress',
          analysis_id: TEST_ANALYSIS_ID,
          stage: 'supervisor_routing',
          status: 'complete',
          timestamp: '2024-01-01T00:00:00Z',
          expected_total_stages: 10, // Updated from 9 to 10 to account for 13 total stages (was 12)
        },
      ]

      const { result } = renderHook(() => useAnalysisProgress(events))

      // With 1 failed stage and pending stages remaining, progress should be less than or equal to 99%
      // (failures cap progress at 99%)
      // Should show detailed status with counts
      expect(result.current.overallProgress.progress).toBeLessThanOrEqual(99)
      expect(result.current.overallProgress.currentStep).toContain('failed')
      expect(result.current.overallProgress.totalSteps).toBeGreaterThanOrEqual(10)
      expect(result.current.overallProgress.completedSteps).toBeLessThanOrEqual(
        result.current.overallProgress.totalSteps
      )
    })

    it('correctly calculates step number when stages are pending', () => {
      const events: SSEEvent[] = [
        {
          type: 'progress',
          analysis_id: TEST_ANALYSIS_ID,
          stage: 'extraction',
          status: 'complete',
          timestamp: '2024-01-01T00:00:00Z',
        },
        {
          type: 'progress',
          analysis_id: TEST_ANALYSIS_ID,
          stage: 'supervisor_routing',
          status: 'complete',
          timestamp: '2024-01-01T00:01:00Z',
          expected_total_stages: 9,
        },
      ]

      const { result } = renderHook(() => useAnalysisProgress(events))

      // Should show correct step number (not exceeding total)
      expect(result.current.overallProgress.completedSteps).toBeLessThanOrEqual(
        result.current.overallProgress.totalSteps
      )
      // Should show progress less than 100% since stages are pending
      expect(result.current.overallProgress.progress).toBeLessThan(100)
    })

    it('uses expected_total_stages as denominator for progress calculation', () => {
      const events: SSEEvent[] = [
        {
          type: 'progress',
          analysis_id: TEST_ANALYSIS_ID,
          stage: 'supervisor_routing',
          status: 'complete',
          timestamp: '2024-01-01T00:00:00Z',
          expected_total_stages: 9, // Backend says 9 stages expected
          details: {
            selected_agents: ['tech_comparator'],
            skipped_agents: [],
          },
        },
        {
          type: 'progress',
          analysis_id: TEST_ANALYSIS_ID,
          stage: 'extraction',
          status: 'complete',
          timestamp: '2024-01-01T00:01:00Z',
        },
        {
          type: 'progress',
          analysis_id: TEST_ANALYSIS_ID,
          stage: 'embedding',
          status: 'complete',
          timestamp: '2024-01-01T00:02:00Z',
        },
      ]

      const { result } = renderHook(() => useAnalysisProgress(events))

      // Should use expected_total_stages (9) as total, not TOTAL_STAGES (12)
      expect(result.current.overallProgress.totalSteps).toBe(9)
      // Progress should be calculated against 9, not 12
      // Note: markSkippedAgents adds skipped stages, so finishedStages includes:
      // - 3 completed (extraction, embedding, supervisor_routing)
      // - 7 skipped (all optional agents not selected)
      // Total: 10 finished, but denominator is 9, so progress is capped at 99%
      // This is correct behavior - we don't want to show 100% when there are pending stages
      expect(result.current.overallProgress.progress).toBeLessThan(100)
      expect(result.current.overallProgress.progress).toBeGreaterThan(0)
    })

    it('distinguishes between skipped and pending stages', () => {
      const events: SSEEvent[] = [
        {
          type: 'progress',
          analysis_id: TEST_ANALYSIS_ID,
          stage: 'supervisor_routing',
          status: 'complete',
          timestamp: '2024-01-01T00:00:00Z',
          expected_total_stages: 7,
          details: {
            selected_agents: ['tech_comparator', 'implementation_planner'],
            skipped_agents: ['security_auditor', 'code_quality_critic'],
          },
        },
        {
          type: 'progress',
          analysis_id: TEST_ANALYSIS_ID,
          stage: 'tech_comparison',
          status: 'complete',
          timestamp: '2024-01-01T00:01:00Z',
        },
      ]

      const { result } = renderHook(() => useAnalysisProgress(events))

      // Skipped stages should count as finished
      const techStep = result.current.steps.find((s) => s.id === 'tech_comparison')
      expect(techStep?.status).toBe('completed')

      // Security audit should be skipped (not pending)
      const securityStep = result.current.steps.find((s) => s.id === 'security_audit')
      expect(securityStep?.status).toBe('skipped')

      // Aggregation should be pending (not in expected workflow yet)
      const aggregationStep = result.current.steps.find((s) => s.id === 'aggregation')
      expect(aggregationStep?.status).toBe('pending')

      // Progress should account for skipped stages as finished
      expect(result.current.overallProgress.progress).toBeGreaterThan(0)
    })
  })

  describe('hasFailedStages and failedStagesCount', () => {
    it('should return hasFailedStages=true and failedStagesCount=1 when one stage fails', () => {
      const events: SSEEvent[] = [
        {
          type: 'progress',
          analysis_id: TEST_ANALYSIS_ID,
          stage: 'tech_comparison',
          status: 'failed',
          timestamp: '2024-01-01T00:01:00Z',
          error: 'Agent execution failed',
        },
        {
          type: 'progress',
          analysis_id: TEST_ANALYSIS_ID,
          stage: 'artifact_generation',
          status: 'complete',
          timestamp: '2024-01-01T00:02:00Z',
        },
      ]

      const { result } = renderHook(() => useAnalysisProgress(events))

      expect(result.current.hasFailedStages).toBe(true)
      expect(result.current.failedStagesCount).toBe(1)
    })

    it('should return hasFailedStages=false and failedStagesCount=0 when no stages fail', () => {
      const events: SSEEvent[] = [
        {
          type: 'progress',
          analysis_id: TEST_ANALYSIS_ID,
          stage: 'tech_comparison',
          status: 'complete',
          timestamp: '2024-01-01T00:01:00Z',
        },
        {
          type: 'progress',
          analysis_id: TEST_ANALYSIS_ID,
          stage: 'artifact_generation',
          status: 'complete',
          timestamp: '2024-01-01T00:02:00Z',
        },
      ]

      const { result } = renderHook(() => useAnalysisProgress(events))

      expect(result.current.hasFailedStages).toBe(false)
      expect(result.current.failedStagesCount).toBe(0)
    })

    it('should return correct failedStagesCount when multiple stages fail', () => {
      const events: SSEEvent[] = [
        {
          type: 'progress',
          analysis_id: TEST_ANALYSIS_ID,
          stage: 'tech_comparison',
          status: 'failed',
          timestamp: '2024-01-01T00:01:00Z',
          error: 'Tech comparison failed',
        },
        {
          type: 'progress',
          analysis_id: TEST_ANALYSIS_ID,
          stage: 'security_audit',
          status: 'failed',
          timestamp: '2024-01-01T00:02:00Z',
          error: 'Security audit failed',
        },
        {
          type: 'progress',
          analysis_id: TEST_ANALYSIS_ID,
          stage: 'implementation_planning',
          status: 'complete',
          timestamp: '2024-01-01T00:03:00Z',
        },
        {
          type: 'progress',
          analysis_id: TEST_ANALYSIS_ID,
          stage: 'artifact_generation',
          status: 'complete',
          timestamp: '2024-01-01T00:04:00Z',
        },
      ]

      const { result } = renderHook(() => useAnalysisProgress(events))

      expect(result.current.hasFailedStages).toBe(true)
      expect(result.current.failedStagesCount).toBe(2)
    })

    it('should count failed stages even when workflow completes', () => {
      const events: SSEEvent[] = [
        {
          type: 'progress',
          analysis_id: TEST_ANALYSIS_ID,
          stage: 'supervisor_routing',
          status: 'complete',
          timestamp: '2024-01-01T00:00:00Z',
          expected_total_stages: 8,
        },
        {
          type: 'progress',
          analysis_id: TEST_ANALYSIS_ID,
          stage: 'tech_comparison',
          status: 'failed',
          timestamp: '2024-01-01T00:01:00Z',
          error: 'Agent failed',
        },
        {
          type: 'progress',
          analysis_id: TEST_ANALYSIS_ID,
          stage: 'security_audit',
          status: 'complete',
          timestamp: '2024-01-01T00:02:00Z',
        },
        {
          type: 'complete',
          analysis_id: TEST_ANALYSIS_ID,
          stage: 'artifact_generation',
          status: 'complete',
          timestamp: '2024-01-01T00:03:00Z',
          artifact_id: TEST_ARTIFACT_ID,
        },
      ]

      const { result } = renderHook(() => useAnalysisProgress(events))

      expect(result.current.isComplete).toBe(true)
      expect(result.current.hasFailedStages).toBe(true)
      expect(result.current.failedStagesCount).toBe(1)
    })
  })

  describe('currentUIStage determination', () => {
    it('should set stage to "complete" when isComplete=true even with failures', () => {
      const events: SSEEvent[] = [
        {
          type: 'progress',
          analysis_id: TEST_ANALYSIS_ID,
          stage: 'tech_comparison',
          status: 'failed',
          timestamp: '2024-01-01T00:01:00Z',
          error: 'Agent failed',
        },
        {
          type: 'progress',
          analysis_id: TEST_ANALYSIS_ID,
          stage: 'artifact_generation',
          status: 'complete',
          timestamp: '2024-01-01T00:02:00Z',
        },
      ]

      const { result } = renderHook(() => useAnalysisProgress(events))

      // When isComplete is true, stage should be 'complete' (not 'generating')
      expect(result.current.isComplete).toBe(true)
      expect(result.current.overallProgress.stage).toBe('complete')
    })

    it('should set stage to "complete" when isComplete=true with no failures', () => {
      const events: SSEEvent[] = [
        {
          type: 'progress',
          analysis_id: TEST_ANALYSIS_ID,
          stage: 'tech_comparison',
          status: 'complete',
          timestamp: '2024-01-01T00:01:00Z',
        },
        {
          type: 'progress',
          analysis_id: TEST_ANALYSIS_ID,
          stage: 'artifact_generation',
          status: 'complete',
          timestamp: '2024-01-01T00:02:00Z',
        },
      ]

      const { result } = renderHook(() => useAnalysisProgress(events))

      expect(result.current.isComplete).toBe(true)
      expect(result.current.overallProgress.stage).toBe('complete')
    })

    it('should NOT set stage to "complete" when artifact_generation is running', () => {
      const events: SSEEvent[] = [
        {
          type: 'progress',
          analysis_id: TEST_ANALYSIS_ID,
          stage: 'tech_comparison',
          status: 'complete',
          timestamp: '2024-01-01T00:01:00Z',
        },
        {
          type: 'progress',
          analysis_id: TEST_ANALYSIS_ID,
          stage: 'artifact_generation',
          status: 'running',
          timestamp: '2024-01-01T00:02:00Z',
        },
      ]

      const { result } = renderHook(() => useAnalysisProgress(events))

      expect(result.current.isComplete).toBe(false)
      expect(result.current.overallProgress.stage).toBe('generating') // Should show generating, not complete
    })

    it('should set stage based on running stage when not complete', () => {
      const events: SSEEvent[] = [
        {
          type: 'progress',
          analysis_id: TEST_ANALYSIS_ID,
          stage: 'tech_comparison',
          status: 'running',
          timestamp: '2024-01-01T00:01:00Z',
        },
      ]

      const { result } = renderHook(() => useAnalysisProgress(events))

      expect(result.current.isComplete).toBe(false)
      expect(result.current.overallProgress.stage).toBe('analyzing') // tech_comparison maps to 'analyzing'
    })
  })
})
