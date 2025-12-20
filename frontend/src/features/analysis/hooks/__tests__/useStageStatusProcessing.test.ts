/**
 * Tests for useStageStatusProcessing - Event processing and stage status extraction
 *
 * This hook processes raw SSE events to build stage status map, extract metadata,
 * and detect workflow completion.
 */

import type { SSEEvent } from '@app-types/sse'
import { renderHook } from '@testing-library/react'
import { describe, expect, it } from 'vitest'

import { useStageStatusProcessing } from '../useStageStatusProcessing'

// Valid UUIDs for testing
const TEST_ANALYSIS_ID = '123e4567-e89b-12d3-a456-426614174000'
const TEST_ARTIFACT_ID = '987fcdeb-51a2-43d7-8f9e-123456789abc'
const TEST_TRACE_ID = '550e8400-e29b-41d4-a716-446655440000'

describe('useStageStatusProcessing', () => {
  describe('empty events array', () => {
    it('should return empty stage statuses and no completion', () => {
      const events: SSEEvent[] = []

      const { result } = renderHook(() => useStageStatusProcessing(events))

      expect(result.current.stageStatuses.size).toBe(0)
      expect(result.current.isComplete).toBe(false)
      expect(result.current.artifactId).toBeUndefined()
      expect(result.current.traceId).toBeUndefined()
      expect(result.current.expectedTotalStages).toBeUndefined()
      expect(result.current.analysisMetadata).toBeUndefined()
      expect(result.current.skipReasons).toBeUndefined()
      expect(result.current.stageSuccessMetrics).toBeUndefined()
    })
  })

  describe('progress events updating stage status', () => {
    it('should process progress events and update stage status', () => {
      const events: SSEEvent[] = [
        {
          type: 'progress',
          analysis_id: TEST_ANALYSIS_ID,
          stage: 'extraction',
          status: 'running',
          timestamp: '2024-01-01T00:00:00Z',
        },
        {
          type: 'progress',
          analysis_id: TEST_ANALYSIS_ID,
          stage: 'extraction',
          status: 'complete',
          timestamp: '2024-01-01T00:01:00Z',
        },
      ]

      const { result } = renderHook(() => useStageStatusProcessing(events))

      expect(result.current.stageStatuses.size).toBe(1)
      const extractionStatus = result.current.stageStatuses.get('extraction')
      expect(extractionStatus).toBeDefined()
      expect(extractionStatus?.status).toBe('complete')
      expect(extractionStatus?.timestamp).toBe('2024-01-01T00:01:00Z')
    })

    it('should merge event details including findings_summary and insights_count', () => {
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

      const { result } = renderHook(() => useStageStatusProcessing(events))

      const techStatus = result.current.stageStatuses.get('tech_comparison')
      expect(techStatus?.details?.findings_summary).toBe('Compared React vs Vue, Angular')
      expect(techStatus?.details?.insights_count).toBe(3)
      expect(techStatus?.details?.confidence_score).toBe(0.85)
    })

    it('should extract details from both top-level and details object', () => {
      const events: SSEEvent[] = [
        {
          type: 'progress',
          analysis_id: TEST_ANALYSIS_ID,
          stage: 'security_audit',
          status: 'complete',
          timestamp: '2024-01-01T00:02:00Z',
          findings_summary: 'Top-level summary',
          details: {
            processing_time_ms: 5000,
            additional_data: 'Extra info',
          },
        },
      ]

      const { result } = renderHook(() => useStageStatusProcessing(events))

      const securityStatus = result.current.stageStatuses.get('security_audit')
      expect(securityStatus?.details?.findings_summary).toBe('Top-level summary')
      expect(securityStatus?.details?.processing_time_ms).toBe(5000)
      expect(securityStatus?.details?.additional_data).toBe('Extra info')
    })
  })

  describe('complete events detecting completion and capturing artifact_id', () => {
    it('should detect completion from complete event type', () => {
      const events: SSEEvent[] = [
        {
          type: 'complete',
          analysis_id: TEST_ANALYSIS_ID,
          stage: 'artifact_generation',
          status: 'complete',
          timestamp: '2024-01-01T00:05:00Z',
          artifact_id: TEST_ARTIFACT_ID,
        },
      ]

      const { result } = renderHook(() => useStageStatusProcessing(events))

      expect(result.current.isComplete).toBe(true)
      expect(result.current.artifactId).toBe(TEST_ARTIFACT_ID)
    })

    it('should detect completion from progress event with status complete for artifact_generation', () => {
      const events: SSEEvent[] = [
        {
          type: 'progress',
          analysis_id: TEST_ANALYSIS_ID,
          stage: 'artifact_generation',
          status: 'complete',
          timestamp: '2024-01-01T00:05:00Z',
          details: {
            artifact_id: TEST_ARTIFACT_ID,
          },
        },
      ]

      const { result } = renderHook(() => useStageStatusProcessing(events))

      expect(result.current.isComplete).toBe(true)
      expect(result.current.artifactId).toBe(TEST_ARTIFACT_ID)
    })

    it('should detect completion from progress event with status complete for workflow stage', () => {
      const events: SSEEvent[] = [
        {
          type: 'progress',
          analysis_id: TEST_ANALYSIS_ID,
          stage: 'workflow',
          status: 'complete',
          timestamp: '2024-01-01T00:06:00Z',
          details: {
            artifact_id: TEST_ARTIFACT_ID,
          },
        },
      ]

      const { result } = renderHook(() => useStageStatusProcessing(events))

      expect(result.current.isComplete).toBe(true)
      expect(result.current.artifactId).toBe(TEST_ARTIFACT_ID)
    })

    it('should capture artifact_id from complete event', () => {
      const events: SSEEvent[] = [
        {
          type: 'complete',
          analysis_id: TEST_ANALYSIS_ID,
          stage: 'workflow',
          status: 'complete',
          timestamp: '2024-01-01T00:06:00Z',
          artifact_id: TEST_ARTIFACT_ID,
        },
      ]

      const { result } = renderHook(() => useStageStatusProcessing(events))

      expect(result.current.artifactId).toBe(TEST_ARTIFACT_ID)
    })
  })

  describe('complete events capturing trace_id for Langfuse feedback', () => {
    it('should capture trace_id from complete event', () => {
      const events: SSEEvent[] = [
        {
          type: 'complete',
          analysis_id: TEST_ANALYSIS_ID,
          stage: 'artifact_generation',
          status: 'complete',
          timestamp: '2024-01-01T00:05:00Z',
          artifact_id: TEST_ARTIFACT_ID,
          trace_id: TEST_TRACE_ID,
        },
      ]

      const { result } = renderHook(() => useStageStatusProcessing(events))

      expect(result.current.isComplete).toBe(true)
      expect(result.current.traceId).toBe(TEST_TRACE_ID)
    })

    it('should not capture trace_id from progress events', () => {
      const events: SSEEvent[] = [
        {
          type: 'progress',
          analysis_id: TEST_ANALYSIS_ID,
          stage: 'artifact_generation',
          status: 'complete',
          timestamp: '2024-01-01T00:05:00Z',
          details: {
            artifact_id: TEST_ARTIFACT_ID,
          },
        },
      ]

      const { result } = renderHook(() => useStageStatusProcessing(events))

      expect(result.current.isComplete).toBe(true)
      expect(result.current.traceId).toBeUndefined()
    })
  })

  describe('error events marking stages as failed', () => {
    it('should mark stage as failed from error event', () => {
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

      const { result } = renderHook(() => useStageStatusProcessing(events))

      const techStatus = result.current.stageStatuses.get('tech_comparison')
      expect(techStatus?.status).toBe('failed')
      expect(techStatus?.details?.error).toBe('Agent execution failed')
      expect(techStatus?.details?.error_code).toBe('TECH_COMPARATOR_FAILED')
    })

    it('should mark stage as failed from progress event with status failed', () => {
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
            processing_time_ms: 5000,
          },
        },
      ]

      const { result } = renderHook(() => useStageStatusProcessing(events))

      const securityStatus = result.current.stageStatuses.get('security_audit')
      expect(securityStatus?.status).toBe('failed')
      expect(securityStatus?.details?.error).toBe('Security audit failed')
      expect(securityStatus?.details?.error_code).toBe('SECURITY_AUDITOR_FAILED')
      expect(securityStatus?.details?.processing_time_ms).toBe(5000)
    })

    it('should extract error from top-level error field in error events', () => {
      const events: SSEEvent[] = [
        {
          type: 'error',
          analysis_id: TEST_ANALYSIS_ID,
          stage: 'implementation_planning',
          status: 'failed',
          timestamp: '2024-01-01T00:03:00Z',
          error: 'Implementation planning timeout',
        },
      ]

      const { result } = renderHook(() => useStageStatusProcessing(events))

      const implStatus = result.current.stageStatuses.get('implementation_planning')
      expect(implStatus?.status).toBe('failed')
      expect(implStatus?.details?.error).toBe('Implementation planning timeout')
    })
  })

  describe('failed status preservation (not overwritten by later events)', () => {
    it('should not overwrite failed status with later complete event', () => {
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

      const { result } = renderHook(() => useStageStatusProcessing(events))

      const techStatus = result.current.stageStatuses.get('tech_comparison')
      expect(techStatus?.status).toBe('failed')
      expect(techStatus?.timestamp).toBe('2024-01-01T00:01:00Z') // Original timestamp preserved
    })

    it('should not overwrite failed status with later running event', () => {
      const events: SSEEvent[] = [
        {
          type: 'progress',
          analysis_id: TEST_ANALYSIS_ID,
          stage: 'security_audit',
          status: 'failed',
          timestamp: '2024-01-01T00:02:00Z',
          details: {
            error: 'Security audit failed',
          },
        },
        {
          type: 'progress',
          analysis_id: TEST_ANALYSIS_ID,
          stage: 'security_audit',
          status: 'running',
          timestamp: '2024-01-01T00:03:00Z',
        },
      ]

      const { result } = renderHook(() => useStageStatusProcessing(events))

      const securityStatus = result.current.stageStatuses.get('security_audit')
      expect(securityStatus?.status).toBe('failed')
    })

    it('should allow failed status to be set again by another error event', () => {
      const events: SSEEvent[] = [
        {
          type: 'error',
          analysis_id: TEST_ANALYSIS_ID,
          stage: 'performance_audit',
          status: 'failed',
          timestamp: '2024-01-01T00:04:00Z',
          error: 'First failure',
        },
        {
          type: 'error',
          analysis_id: TEST_ANALYSIS_ID,
          stage: 'performance_audit',
          status: 'failed',
          timestamp: '2024-01-01T00:05:00Z',
          error: 'Second failure',
        },
      ]

      const { result } = renderHook(() => useStageStatusProcessing(events))

      const perfStatus = result.current.stageStatuses.get('performance_audit')
      expect(perfStatus?.status).toBe('failed')
      // Should preserve first error (not update since status is already failed)
      expect(perfStatus?.timestamp).toBe('2024-01-01T00:04:00Z')
    })
  })

  describe('expectedTotalStages extraction from supervisor_routing', () => {
    it('should extract expected_total_stages from top-level field', () => {
      const events: SSEEvent[] = [
        {
          type: 'progress',
          analysis_id: TEST_ANALYSIS_ID,
          stage: 'supervisor_routing',
          status: 'complete',
          timestamp: '2024-01-01T00:00:00Z',
          expected_total_stages: 8,
          details: {
            selected_agents: ['tech_comparator', 'security_auditor', 'implementation_planner'],
          },
        },
      ]

      const { result } = renderHook(() => useStageStatusProcessing(events))

      expect(result.current.expectedTotalStages).toBe(8)
    })

    it('should extract expected_total_stages from details object', () => {
      const events: SSEEvent[] = [
        {
          type: 'progress',
          analysis_id: TEST_ANALYSIS_ID,
          stage: 'supervisor_routing',
          status: 'complete',
          timestamp: '2024-01-01T00:00:00Z',
          details: {
            expected_total_stages: 10,
            selected_agents: ['tech_comparator'],
          },
        },
      ]

      const { result } = renderHook(() => useStageStatusProcessing(events))

      expect(result.current.expectedTotalStages).toBe(10)
    })

    it('should use top-level expected_total_stages over details if both present', () => {
      const events: SSEEvent[] = [
        {
          type: 'progress',
          analysis_id: TEST_ANALYSIS_ID,
          stage: 'supervisor_routing',
          status: 'complete',
          timestamp: '2024-01-01T00:00:00Z',
          expected_total_stages: 9, // Top-level
          details: {
            expected_total_stages: 12, // Details
          },
        },
      ]

      const { result } = renderHook(() => useStageStatusProcessing(events))

      // Top-level should take precedence (undefined coalescing in code)
      expect(result.current.expectedTotalStages).toBe(9)
    })

    it('should not extract expected_total_stages from non-supervisor events', () => {
      const events: SSEEvent[] = [
        {
          type: 'progress',
          analysis_id: TEST_ANALYSIS_ID,
          stage: 'extraction',
          status: 'complete',
          timestamp: '2024-01-01T00:00:00Z',
          details: {
            expected_total_stages: 15, // Should be ignored
          },
        },
      ]

      const { result } = renderHook(() => useStageStatusProcessing(events))

      expect(result.current.expectedTotalStages).toBeUndefined()
    })
  })

  describe('analysisMetadata extraction from extraction stage', () => {
    it('should extract analysis metadata from extraction complete event', () => {
      const events: SSEEvent[] = [
        {
          type: 'progress',
          analysis_id: TEST_ANALYSIS_ID,
          stage: 'extraction',
          status: 'complete',
          timestamp: '2024-01-01T00:01:00Z',
          analysis_metadata: {
            title: 'Building RAG Systems with LangChain',
            content_type: 'article',
            url: 'https://example.com/rag-systems',
            word_count: 2500,
          },
        },
      ]

      const { result } = renderHook(() => useStageStatusProcessing(events))

      expect(result.current.analysisMetadata).toEqual({
        title: 'Building RAG Systems with LangChain',
        contentType: 'article',
        url: 'https://example.com/rag-systems',
        wordCount: 2500,
      })
    })

    it('should extract analysis metadata from details object', () => {
      const events: SSEEvent[] = [
        {
          type: 'progress',
          analysis_id: TEST_ANALYSIS_ID,
          stage: 'extraction',
          status: 'complete',
          timestamp: '2024-01-01T00:01:00Z',
          details: {
            analysis_metadata: {
              title: 'Video Tutorial: Next.js 14',
              content_type: 'video',
              url: 'https://youtube.com/watch?v=abc',
              word_count: 500,
            },
          },
        },
      ]

      const { result } = renderHook(() => useStageStatusProcessing(events))

      expect(result.current.analysisMetadata).toEqual({
        title: 'Video Tutorial: Next.js 14',
        contentType: 'video',
        url: 'https://youtube.com/watch?v=abc',
        wordCount: 500,
      })
    })

    it('should handle partial metadata', () => {
      const events: SSEEvent[] = [
        {
          type: 'progress',
          analysis_id: TEST_ANALYSIS_ID,
          stage: 'extraction',
          status: 'complete',
          timestamp: '2024-01-01T00:01:00Z',
          analysis_metadata: {
            title: 'Partial Metadata',
            // Missing content_type, url, word_count
          },
        },
      ]

      const { result } = renderHook(() => useStageStatusProcessing(events))

      expect(result.current.analysisMetadata).toEqual({
        title: 'Partial Metadata',
        contentType: undefined,
        url: undefined,
        wordCount: undefined,
      })
    })

    it('should only extract metadata from extraction stage with complete status', () => {
      const events: SSEEvent[] = [
        {
          type: 'progress',
          analysis_id: TEST_ANALYSIS_ID,
          stage: 'extraction',
          status: 'running', // Not complete
          timestamp: '2024-01-01T00:00:00Z',
          analysis_metadata: {
            title: 'Should be ignored',
            content_type: 'article',
          },
        },
        {
          type: 'progress',
          analysis_id: TEST_ANALYSIS_ID,
          stage: 'tech_comparison',
          status: 'complete',
          timestamp: '2024-01-01T00:02:00Z',
          analysis_metadata: {
            title: 'Wrong stage',
            content_type: 'article',
          },
        },
      ]

      const { result } = renderHook(() => useStageStatusProcessing(events))

      expect(result.current.analysisMetadata).toBeUndefined()
    })
  })

  describe('skipReasons extraction from supervisor event', () => {
    it('should extract skip reasons from top-level field', () => {
      const events: SSEEvent[] = [
        {
          type: 'progress',
          analysis_id: TEST_ANALYSIS_ID,
          stage: 'supervisor_routing',
          status: 'complete',
          timestamp: '2024-01-01T00:00:00Z',
          skip_reasons: {
            performance_auditor: 'No performance-critical code detected',
            code_quality_critic: 'Content is documentation, not code',
          },
          details: {
            selected_agents: ['tech_comparator', 'security_auditor'],
            skipped_agents: ['performance_auditor', 'code_quality_critic'],
          },
        },
      ]

      const { result } = renderHook(() => useStageStatusProcessing(events))

      expect(result.current.skipReasons).toEqual({
        performance_auditor: 'No performance-critical code detected',
        code_quality_critic: 'Content is documentation, not code',
      })
    })

    it('should extract skip reasons from details object', () => {
      const events: SSEEvent[] = [
        {
          type: 'progress',
          analysis_id: TEST_ANALYSIS_ID,
          stage: 'supervisor_routing',
          status: 'complete',
          timestamp: '2024-01-01T00:00:00Z',
          details: {
            skip_reasons: {
              trends_analyst: 'Not a trending topic analysis',
            },
            selected_agents: ['implementation_planner'],
            skipped_agents: ['trends_analyst'],
          },
        },
      ]

      const { result } = renderHook(() => useStageStatusProcessing(events))

      expect(result.current.skipReasons).toEqual({
        trends_analyst: 'Not a trending topic analysis',
      })
    })

    it('should only extract skip reasons from supervisor_routing with complete status', () => {
      const events: SSEEvent[] = [
        {
          type: 'progress',
          analysis_id: TEST_ANALYSIS_ID,
          stage: 'supervisor_routing',
          status: 'running', // Not complete
          timestamp: '2024-01-01T00:00:00Z',
          skip_reasons: {
            test_agent: 'Should be ignored',
          },
        },
      ]

      const { result } = renderHook(() => useStageStatusProcessing(events))

      expect(result.current.skipReasons).toBeUndefined()
    })
  })

  describe('stageSuccessMetrics collection from agent completions', () => {
    it('should collect success metrics from agent completion events', () => {
      const events: SSEEvent[] = [
        {
          type: 'progress',
          analysis_id: TEST_ANALYSIS_ID,
          stage: 'tech_comparison',
          status: 'complete',
          timestamp: '2024-01-01T00:01:00Z',
          success_metrics: {
            findings_quality: 'high',
            coverage: 'comprehensive',
            key_insights: ['React has better ecosystem', 'Vue has simpler learning curve'],
          },
        },
      ]

      const { result } = renderHook(() => useStageStatusProcessing(events))

      expect(result.current.stageSuccessMetrics).toBeDefined()
      const techMetrics = result.current.stageSuccessMetrics?.get('tech_comparison')
      expect(techMetrics).toEqual({
        findingsQuality: 'high',
        coverage: 'comprehensive',
        keyInsights: ['React has better ecosystem', 'Vue has simpler learning curve'],
      })
    })

    it('should collect success metrics from details object', () => {
      const events: SSEEvent[] = [
        {
          type: 'progress',
          analysis_id: TEST_ANALYSIS_ID,
          stage: 'security_audit',
          status: 'complete',
          timestamp: '2024-01-01T00:02:00Z',
          details: {
            success_metrics: {
              findings_quality: 'medium',
              coverage: 'partial',
              key_insights: ['No critical vulnerabilities found'],
            },
          },
        },
      ]

      const { result } = renderHook(() => useStageStatusProcessing(events))

      const securityMetrics = result.current.stageSuccessMetrics?.get('security_audit')
      expect(securityMetrics).toEqual({
        findingsQuality: 'medium',
        coverage: 'partial',
        keyInsights: ['No critical vulnerabilities found'],
      })
    })

    it('should collect metrics from multiple agent stages', () => {
      const events: SSEEvent[] = [
        {
          type: 'progress',
          analysis_id: TEST_ANALYSIS_ID,
          stage: 'tech_comparison',
          status: 'complete',
          timestamp: '2024-01-01T00:01:00Z',
          success_metrics: {
            findings_quality: 'high',
            coverage: 'comprehensive',
          },
        },
        {
          type: 'progress',
          analysis_id: TEST_ANALYSIS_ID,
          stage: 'implementation_planning',
          status: 'complete',
          timestamp: '2024-01-01T00:03:00Z',
          success_metrics: {
            findings_quality: 'medium',
            coverage: 'partial',
            key_insights: ['Use feature flags', 'Gradual rollout recommended'],
          },
        },
      ]

      const { result } = renderHook(() => useStageStatusProcessing(events))

      expect(result.current.stageSuccessMetrics?.size).toBe(2)
      expect(result.current.stageSuccessMetrics?.get('tech_comparison')).toBeDefined()
      expect(result.current.stageSuccessMetrics?.get('implementation_planning')).toBeDefined()
    })

    it('should not collect metrics from non-agent stages', () => {
      const events: SSEEvent[] = [
        {
          type: 'progress',
          analysis_id: TEST_ANALYSIS_ID,
          stage: 'extraction',
          status: 'complete',
          timestamp: '2024-01-01T00:00:00Z',
          success_metrics: {
            findings_quality: 'high',
            coverage: 'comprehensive',
          },
        },
        {
          type: 'progress',
          analysis_id: TEST_ANALYSIS_ID,
          stage: 'supervisor_routing',
          status: 'complete',
          timestamp: '2024-01-01T00:01:00Z',
          success_metrics: {
            findings_quality: 'high',
            coverage: 'comprehensive',
          },
        },
        {
          type: 'progress',
          analysis_id: TEST_ANALYSIS_ID,
          stage: 'aggregation',
          status: 'complete',
          timestamp: '2024-01-01T00:04:00Z',
          success_metrics: {
            findings_quality: 'high',
            coverage: 'comprehensive',
          },
        },
        {
          type: 'progress',
          analysis_id: TEST_ANALYSIS_ID,
          stage: 'artifact_generation',
          status: 'complete',
          timestamp: '2024-01-01T00:05:00Z',
          success_metrics: {
            findings_quality: 'high',
            coverage: 'comprehensive',
          },
        },
      ]

      const { result } = renderHook(() => useStageStatusProcessing(events))

      expect(result.current.stageSuccessMetrics).toBeUndefined()
    })

    it('should only collect metrics from complete status events', () => {
      const events: SSEEvent[] = [
        {
          type: 'progress',
          analysis_id: TEST_ANALYSIS_ID,
          stage: 'tech_comparison',
          status: 'running', // Not complete
          timestamp: '2024-01-01T00:01:00Z',
          success_metrics: {
            findings_quality: 'high',
            coverage: 'comprehensive',
          },
        },
      ]

      const { result } = renderHook(() => useStageStatusProcessing(events))

      expect(result.current.stageSuccessMetrics).toBeUndefined()
    })

    it('should handle partial success metrics', () => {
      const events: SSEEvent[] = [
        {
          type: 'progress',
          analysis_id: TEST_ANALYSIS_ID,
          stage: 'performance_audit',
          status: 'complete',
          timestamp: '2024-01-01T00:04:00Z',
          success_metrics: {
            findings_quality: 'low',
            // Missing coverage and key_insights
          },
        },
      ]

      const { result } = renderHook(() => useStageStatusProcessing(events))

      const perfMetrics = result.current.stageSuccessMetrics?.get('performance_audit')
      expect(perfMetrics).toEqual({
        findingsQuality: 'low',
        coverage: undefined,
        keyInsights: undefined,
      })
    })
  })

  describe('complex workflows', () => {
    it('should handle complete workflow with all features', () => {
      const events: SSEEvent[] = [
        {
          type: 'progress',
          analysis_id: TEST_ANALYSIS_ID,
          stage: 'extraction',
          status: 'complete',
          timestamp: '2024-01-01T00:00:00Z',
          analysis_metadata: {
            title: 'Building Microservices',
            content_type: 'article',
            url: 'https://example.com/microservices',
            word_count: 5000,
          },
        },
        {
          type: 'progress',
          analysis_id: TEST_ANALYSIS_ID,
          stage: 'supervisor_routing',
          status: 'complete',
          timestamp: '2024-01-01T00:01:00Z',
          expected_total_stages: 9,
          skip_reasons: {
            trends_analyst: 'Not applicable',
          },
          details: {
            selected_agents: ['tech_comparator', 'security_auditor', 'implementation_planner'],
            skipped_agents: ['trends_analyst'],
          },
        },
        {
          type: 'progress',
          analysis_id: TEST_ANALYSIS_ID,
          stage: 'tech_comparison',
          status: 'complete',
          timestamp: '2024-01-01T00:02:00Z',
          success_metrics: {
            findings_quality: 'high',
            coverage: 'comprehensive',
            key_insights: ['Microservices vs Monolith tradeoffs'],
          },
        },
        {
          type: 'error',
          analysis_id: TEST_ANALYSIS_ID,
          stage: 'security_audit',
          status: 'failed',
          timestamp: '2024-01-01T00:03:00Z',
          error: 'Security audit timeout',
        },
        {
          type: 'progress',
          analysis_id: TEST_ANALYSIS_ID,
          stage: 'implementation_planning',
          status: 'complete',
          timestamp: '2024-01-01T00:04:00Z',
          success_metrics: {
            findings_quality: 'medium',
            coverage: 'partial',
          },
        },
        {
          type: 'complete',
          analysis_id: TEST_ANALYSIS_ID,
          stage: 'artifact_generation',
          status: 'complete',
          timestamp: '2024-01-01T00:05:00Z',
          artifact_id: TEST_ARTIFACT_ID,
          trace_id: TEST_TRACE_ID,
        },
      ]

      const { result } = renderHook(() => useStageStatusProcessing(events))

      // Verify completion
      expect(result.current.isComplete).toBe(true)
      expect(result.current.artifactId).toBe(TEST_ARTIFACT_ID)
      expect(result.current.traceId).toBe(TEST_TRACE_ID)

      // Verify metadata
      expect(result.current.expectedTotalStages).toBe(9)
      expect(result.current.analysisMetadata?.title).toBe('Building Microservices')
      expect(result.current.skipReasons).toEqual({
        trends_analyst: 'Not applicable',
      })

      // Verify stage statuses
      expect(result.current.stageStatuses.get('extraction')?.status).toBe('complete')
      expect(result.current.stageStatuses.get('tech_comparison')?.status).toBe('complete')
      expect(result.current.stageStatuses.get('security_audit')?.status).toBe('failed')
      expect(result.current.stageStatuses.get('implementation_planning')?.status).toBe('complete')

      // Verify success metrics
      expect(result.current.stageSuccessMetrics?.size).toBe(2)
      expect(result.current.stageSuccessMetrics?.get('tech_comparison')?.findingsQuality).toBe(
        'high'
      )
      expect(result.current.stageSuccessMetrics?.get('implementation_planning')?.coverage).toBe(
        'partial'
      )
    })

    it('should handle workflow and agent completion stages together', () => {
      const events: SSEEvent[] = [
        {
          type: 'progress',
          analysis_id: TEST_ANALYSIS_ID,
          stage: 'tech_comparison', // Frontend stage name
          status: 'complete',
          timestamp: '2024-01-01T00:01:00Z',
        },
        {
          type: 'progress',
          analysis_id: TEST_ANALYSIS_ID,
          stage: 'security_audit', // Frontend stage name
          status: 'complete',
          timestamp: '2024-01-01T00:02:00Z',
        },
        {
          type: 'progress',
          analysis_id: TEST_ANALYSIS_ID,
          stage: 'aggregation',
          status: 'complete',
          timestamp: '2024-01-01T00:03:00Z',
        },
      ]

      const { result } = renderHook(() => useStageStatusProcessing(events))

      // Should process all stage names correctly
      expect(result.current.stageStatuses.get('tech_comparison')?.status).toBe('complete')
      expect(result.current.stageStatuses.get('security_audit')?.status).toBe('complete')
      expect(result.current.stageStatuses.get('aggregation')?.status).toBe('complete')
    })
  })

  describe('memoization', () => {
    it('should return same object reference when events array unchanged', () => {
      const events: SSEEvent[] = [
        {
          type: 'progress',
          analysis_id: TEST_ANALYSIS_ID,
          stage: 'extraction',
          status: 'complete',
          timestamp: '2024-01-01T00:00:00Z',
        },
      ]

      const { result, rerender } = renderHook(({ evts }) => useStageStatusProcessing(evts), {
        initialProps: { evts: events },
      })

      const firstResult = result.current

      // Rerender with same array reference
      rerender({ evts: events })

      // Should return same object reference (memoized)
      expect(result.current).toBe(firstResult)
    })

    it('should recompute when events array changes', () => {
      const events1: SSEEvent[] = [
        {
          type: 'progress',
          analysis_id: TEST_ANALYSIS_ID,
          stage: 'extraction',
          status: 'complete',
          timestamp: '2024-01-01T00:00:00Z',
        },
      ]

      const events2: SSEEvent[] = [
        ...events1,
        {
          type: 'progress',
          analysis_id: TEST_ANALYSIS_ID,
          stage: 'tech_comparison',
          status: 'complete',
          timestamp: '2024-01-01T00:01:00Z',
        },
      ]

      const { result, rerender } = renderHook(({ evts }) => useStageStatusProcessing(evts), {
        initialProps: { evts: events1 },
      })

      const firstResult = result.current
      expect(firstResult.stageStatuses.size).toBe(1)

      // Rerender with new array
      rerender({ evts: events2 })

      // Should recompute and return new object
      expect(result.current).not.toBe(firstResult)
      expect(result.current.stageStatuses.size).toBe(2)
    })
  })
})
