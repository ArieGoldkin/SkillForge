/**
 * Tests for useAnalysisMetadata - Extract analysis metadata from SSE events
 *
 * Tests metadata extraction including:
 * - Analysis metadata from extraction stage
 * - Skipped agents info from supervisor stage
 * - Skip reasons from supervisor stage
 * - Success metrics from agent completion events
 */

import type { SSEEvent } from '@app-types/sse'
import { renderHook } from '@testing-library/react'
import { describe, expect, it } from 'vitest'

import { useAnalysisMetadata } from '../useAnalysisMetadata'

// Valid UUIDs for testing
const TEST_ANALYSIS_ID = '123e4567-e89b-12d3-a456-426614174000'

describe('useAnalysisMetadata', () => {
  describe('empty events', () => {
    it('returns undefined metadata when no events provided', () => {
      const events: SSEEvent[] = []

      const { result } = renderHook(() => useAnalysisMetadata(events))

      expect(result.current.analysisMetadata).toBeUndefined()
      expect(result.current.skipReasons).toBeUndefined()
      expect(result.current.skippedAgentsInfo).toBeUndefined()
      expect(result.current.stageSuccessMetrics.size).toBe(0)
    })
  })

  describe('extraction stage metadata', () => {
    it('extracts analysisMetadata from extraction stage complete event', () => {
      const events: SSEEvent[] = [
        {
          type: 'progress',
          analysis_id: TEST_ANALYSIS_ID,
          stage: 'extraction',
          status: 'complete',
          timestamp: '2024-01-01T00:00:00Z',
          analysis_metadata: {
            title: 'Introduction to RAG',
            content_type: 'article',
            url: 'https://example.com/rag-intro',
            word_count: 1500,
          },
        },
      ]

      const { result } = renderHook(() => useAnalysisMetadata(events))

      expect(result.current.analysisMetadata).toEqual({
        title: 'Introduction to RAG',
        contentType: 'article',
        url: 'https://example.com/rag-intro',
        wordCount: 1500,
      })
    })

    it('converts snake_case to camelCase for content_type and word_count', () => {
      const events: SSEEvent[] = [
        {
          type: 'progress',
          analysis_id: TEST_ANALYSIS_ID,
          stage: 'extraction',
          status: 'complete',
          timestamp: '2024-01-01T00:00:00Z',
          analysis_metadata: {
            title: 'React 19 Features',
            content_type: 'video',
            url: 'https://youtube.com/react19',
            word_count: 2500,
          },
        },
      ]

      const { result } = renderHook(() => useAnalysisMetadata(events))

      // Verify snake_case backend fields are converted to camelCase
      expect(result.current.analysisMetadata).toEqual({
        title: 'React 19 Features',
        contentType: 'video', // content_type -> contentType
        url: 'https://youtube.com/react19',
        wordCount: 2500, // word_count -> wordCount
      })
    })

    it('extracts metadata from details.analysis_metadata if top-level is missing', () => {
      const events: SSEEvent[] = [
        {
          type: 'progress',
          analysis_id: TEST_ANALYSIS_ID,
          stage: 'extraction',
          status: 'complete',
          timestamp: '2024-01-01T00:00:00Z',
          details: {
            analysis_metadata: {
              title: 'LangGraph Guide',
              content_type: 'repo',
              url: 'https://github.com/langchain/langgraph',
              word_count: 5000,
            },
          },
        },
      ]

      const { result } = renderHook(() => useAnalysisMetadata(events))

      expect(result.current.analysisMetadata).toEqual({
        title: 'LangGraph Guide',
        contentType: 'repo',
        url: 'https://github.com/langchain/langgraph',
        wordCount: 5000,
      })
    })

    it('handles partial metadata (missing optional fields)', () => {
      const events: SSEEvent[] = [
        {
          type: 'progress',
          analysis_id: TEST_ANALYSIS_ID,
          stage: 'extraction',
          status: 'complete',
          timestamp: '2024-01-01T00:00:00Z',
          analysis_metadata: {
            title: 'Untitled Document',
            // content_type, url, word_count are optional
          },
        },
      ]

      const { result } = renderHook(() => useAnalysisMetadata(events))

      expect(result.current.analysisMetadata).toEqual({
        title: 'Untitled Document',
        contentType: undefined,
        url: undefined,
        wordCount: undefined,
      })
    })

    it('returns undefined when extraction stage has no metadata', () => {
      const events: SSEEvent[] = [
        {
          type: 'progress',
          analysis_id: TEST_ANALYSIS_ID,
          stage: 'extraction',
          status: 'complete',
          timestamp: '2024-01-01T00:00:00Z',
          // No analysis_metadata field
        },
      ]

      const { result } = renderHook(() => useAnalysisMetadata(events))

      expect(result.current.analysisMetadata).toBeUndefined()
    })
  })

  describe('supervisor routing - skipped agents', () => {
    it('extracts skippedAgentsInfo from supervisor routing event', () => {
      const events: SSEEvent[] = [
        {
          type: 'progress',
          analysis_id: TEST_ANALYSIS_ID,
          stage: 'supervisor_routing',
          status: 'complete',
          timestamp: '2024-01-01T00:00:00Z',
          details: {
            skipped_agents: ['code_quality_critic', 'performance_analyst'],
            selected_agents: ['tech_comparator', 'security_auditor'],
          },
        },
      ]

      const { result } = renderHook(() => useAnalysisMetadata(events))

      expect(result.current.skippedAgentsInfo).toEqual({
        agents: ['code_quality_critic', 'performance_analyst'],
        selectedAgents: ['tech_comparator', 'security_auditor'],
      })
    })

    it('extracts selectedAgents from supervisor routing event', () => {
      const events: SSEEvent[] = [
        {
          type: 'progress',
          analysis_id: TEST_ANALYSIS_ID,
          stage: 'supervisor_routing',
          status: 'complete',
          timestamp: '2024-01-01T00:00:00Z',
          details: {
            skipped_agents: [],
            selected_agents: ['tech_comparator', 'security_auditor', 'implementation_planner'],
          },
        },
      ]

      const { result } = renderHook(() => useAnalysisMetadata(events))

      expect(result.current.skippedAgentsInfo?.selectedAgents).toEqual([
        'tech_comparator',
        'security_auditor',
        'implementation_planner',
      ])
    })

    it('handles skipped_agents at top level (not nested in details)', () => {
      const events: SSEEvent[] = [
        {
          type: 'progress',
          analysis_id: TEST_ANALYSIS_ID,
          stage: 'supervisor_routing',
          status: 'complete',
          timestamp: '2024-01-01T00:00:00Z',
          // TypeScript doesn't allow this type-safely, but test runtime behavior
          ...({
            skipped_agents: ['trends_analyst'],
            selected_agents: ['tech_comparator'],
          } as unknown as object),
        },
      ]

      const { result } = renderHook(() => useAnalysisMetadata(events))

      // Should extract from top level if details is missing
      expect(result.current.skippedAgentsInfo?.agents).toEqual(['trends_analyst'])
      expect(result.current.skippedAgentsInfo?.selectedAgents).toEqual(['tech_comparator'])
    })

    it('returns undefined when supervisor has no skipped_agents', () => {
      const events: SSEEvent[] = [
        {
          type: 'progress',
          analysis_id: TEST_ANALYSIS_ID,
          stage: 'supervisor_routing',
          status: 'complete',
          timestamp: '2024-01-01T00:00:00Z',
          // No skipped_agents or selected_agents
        },
      ]

      const { result } = renderHook(() => useAnalysisMetadata(events))

      expect(result.current.skippedAgentsInfo).toBeUndefined()
    })
  })

  describe('supervisor routing - skip reasons', () => {
    it('extracts skipReasons from supervisor event', () => {
      const events: SSEEvent[] = [
        {
          type: 'progress',
          analysis_id: TEST_ANALYSIS_ID,
          stage: 'supervisor_routing',
          status: 'complete',
          timestamp: '2024-01-01T00:00:00Z',
          // TypeScript doesn't allow skip_reasons at top level, but test runtime
          ...({
            skip_reasons: {
              tech_comparator: 'No technology comparisons needed',
              performance_analyst: 'Content does not contain performance metrics',
            },
          } as unknown as object),
        },
      ]

      const { result } = renderHook(() => useAnalysisMetadata(events))

      expect(result.current.skipReasons).toEqual({
        tech_comparator: 'No technology comparisons needed',
        performance_analyst: 'Content does not contain performance metrics',
      })
    })

    it('extracts skip_reasons from details if top-level is missing', () => {
      const events: SSEEvent[] = [
        {
          type: 'progress',
          analysis_id: TEST_ANALYSIS_ID,
          stage: 'supervisor_routing',
          status: 'complete',
          timestamp: '2024-01-01T00:00:00Z',
          details: {
            skip_reasons: {
              security_auditor: 'No security concerns detected',
            },
          },
        },
      ]

      const { result } = renderHook(() => useAnalysisMetadata(events))

      expect(result.current.skipReasons).toEqual({
        security_auditor: 'No security concerns detected',
      })
    })

    it('returns undefined when supervisor has no skip_reasons', () => {
      const events: SSEEvent[] = [
        {
          type: 'progress',
          analysis_id: TEST_ANALYSIS_ID,
          stage: 'supervisor_routing',
          status: 'complete',
          timestamp: '2024-01-01T00:00:00Z',
        },
      ]

      const { result } = renderHook(() => useAnalysisMetadata(events))

      expect(result.current.skipReasons).toBeUndefined()
    })
  })

  describe('success metrics from agent completion', () => {
    it('extracts stageSuccessMetrics from agent completion events', () => {
      const events: SSEEvent[] = [
        {
          type: 'progress',
          analysis_id: TEST_ANALYSIS_ID,
          stage: 'tech_comparison',
          status: 'complete',
          timestamp: '2024-01-01T00:00:00Z',
          // TypeScript doesn't allow success_metrics at top level, test runtime
          ...({
            success_metrics: {
              findings_quality: 'high',
              coverage: 'comprehensive',
              key_insights: ['React has better performance', 'Vue has simpler learning curve'],
            },
          } as unknown as object),
        },
      ]

      const { result } = renderHook(() => useAnalysisMetadata(events))

      const metrics = result.current.stageSuccessMetrics.get('tech_comparison')
      expect(metrics).toEqual({
        findingsQuality: 'high',
        coverage: 'comprehensive',
        keyInsights: ['React has better performance', 'Vue has simpler learning curve'],
      })
    })

    it('extracts success_metrics from details if top-level is missing', () => {
      const events: SSEEvent[] = [
        {
          type: 'progress',
          analysis_id: TEST_ANALYSIS_ID,
          stage: 'security_audit',
          status: 'complete',
          timestamp: '2024-01-01T00:00:00Z',
          details: {
            success_metrics: {
              findings_quality: 'medium',
              coverage: 'partial',
              key_insights: ['XSS vulnerability detected', 'CSRF protection missing'],
            },
          },
        },
      ]

      const { result } = renderHook(() => useAnalysisMetadata(events))

      const metrics = result.current.stageSuccessMetrics.get('security_audit')
      expect(metrics).toEqual({
        findingsQuality: 'medium',
        coverage: 'partial',
        keyInsights: ['XSS vulnerability detected', 'CSRF protection missing'],
      })
    })

    it('handles partial success_metrics (missing optional fields)', () => {
      const events: SSEEvent[] = [
        {
          type: 'progress',
          analysis_id: TEST_ANALYSIS_ID,
          stage: 'implementation_planning',
          status: 'complete',
          timestamp: '2024-01-01T00:00:00Z',
          details: {
            success_metrics: {
              findings_quality: 'high',
              // coverage and key_insights are optional
            },
          },
        },
      ]

      const { result } = renderHook(() => useAnalysisMetadata(events))

      const metrics = result.current.stageSuccessMetrics.get('implementation_planning')
      expect(metrics).toEqual({
        findingsQuality: 'high',
        coverage: undefined,
        keyInsights: undefined,
      })
    })

    it('ignores infrastructure stages for success metrics (extraction)', () => {
      const events: SSEEvent[] = [
        {
          type: 'progress',
          analysis_id: TEST_ANALYSIS_ID,
          stage: 'extraction',
          status: 'complete',
          timestamp: '2024-01-01T00:00:00Z',
          details: {
            success_metrics: {
              findings_quality: 'high',
              coverage: 'comprehensive',
            },
          },
        },
      ]

      const { result } = renderHook(() => useAnalysisMetadata(events))

      // Infrastructure stages should not have success metrics recorded
      expect(result.current.stageSuccessMetrics.has('extraction')).toBe(false)
    })

    it('ignores infrastructure stages for success metrics (embedding)', () => {
      const events: SSEEvent[] = [
        {
          type: 'progress',
          analysis_id: TEST_ANALYSIS_ID,
          stage: 'embedding',
          status: 'complete',
          timestamp: '2024-01-01T00:00:00Z',
          details: {
            success_metrics: {
              findings_quality: 'high',
            },
          },
        },
      ]

      const { result } = renderHook(() => useAnalysisMetadata(events))

      expect(result.current.stageSuccessMetrics.has('embedding')).toBe(false)
    })

    it('ignores infrastructure stages for success metrics (supervisor_routing)', () => {
      const events: SSEEvent[] = [
        {
          type: 'progress',
          analysis_id: TEST_ANALYSIS_ID,
          stage: 'supervisor_routing',
          status: 'complete',
          timestamp: '2024-01-01T00:00:00Z',
          details: {
            success_metrics: {
              findings_quality: 'high',
            },
          },
        },
      ]

      const { result } = renderHook(() => useAnalysisMetadata(events))

      expect(result.current.stageSuccessMetrics.has('supervisor_routing')).toBe(false)
    })

    it('ignores infrastructure stages for success metrics (aggregation)', () => {
      const events: SSEEvent[] = [
        {
          type: 'progress',
          analysis_id: TEST_ANALYSIS_ID,
          stage: 'aggregation',
          status: 'complete',
          timestamp: '2024-01-01T00:00:00Z',
          details: {
            success_metrics: {
              findings_quality: 'high',
            },
          },
        },
      ]

      const { result } = renderHook(() => useAnalysisMetadata(events))

      expect(result.current.stageSuccessMetrics.has('aggregation')).toBe(false)
    })

    it('ignores infrastructure stages for success metrics (artifact_generation)', () => {
      const events: SSEEvent[] = [
        {
          type: 'progress',
          analysis_id: TEST_ANALYSIS_ID,
          stage: 'artifact_generation',
          status: 'complete',
          timestamp: '2024-01-01T00:00:00Z',
          details: {
            success_metrics: {
              findings_quality: 'high',
            },
          },
        },
      ]

      const { result } = renderHook(() => useAnalysisMetadata(events))

      expect(result.current.stageSuccessMetrics.has('artifact_generation')).toBe(false)
    })

    it('multiple agents with metrics are collected correctly', () => {
      const events: SSEEvent[] = [
        {
          type: 'progress',
          analysis_id: TEST_ANALYSIS_ID,
          stage: 'tech_comparison',
          status: 'complete',
          timestamp: '2024-01-01T00:00:00Z',
          details: {
            success_metrics: {
              findings_quality: 'high',
              coverage: 'comprehensive',
              key_insights: ['React vs Vue comparison'],
            },
          },
        },
        {
          type: 'progress',
          analysis_id: TEST_ANALYSIS_ID,
          stage: 'security_audit',
          status: 'complete',
          timestamp: '2024-01-01T00:01:00Z',
          details: {
            success_metrics: {
              findings_quality: 'medium',
              coverage: 'partial',
              key_insights: ['XSS vulnerability found'],
            },
          },
        },
        {
          type: 'progress',
          analysis_id: TEST_ANALYSIS_ID,
          stage: 'implementation_planning',
          status: 'complete',
          timestamp: '2024-01-01T00:02:00Z',
          details: {
            success_metrics: {
              findings_quality: 'high',
              coverage: 'comprehensive',
              key_insights: ['Step-by-step migration plan', 'Testing strategy'],
            },
          },
        },
      ]

      const { result } = renderHook(() => useAnalysisMetadata(events))

      expect(result.current.stageSuccessMetrics.size).toBe(3)

      const techMetrics = result.current.stageSuccessMetrics.get('tech_comparison')
      expect(techMetrics?.findingsQuality).toBe('high')
      expect(techMetrics?.coverage).toBe('comprehensive')
      expect(techMetrics?.keyInsights).toEqual(['React vs Vue comparison'])

      const securityMetrics = result.current.stageSuccessMetrics.get('security_audit')
      expect(securityMetrics?.findingsQuality).toBe('medium')
      expect(securityMetrics?.coverage).toBe('partial')
      expect(securityMetrics?.keyInsights).toEqual(['XSS vulnerability found'])

      const implMetrics = result.current.stageSuccessMetrics.get('implementation_planning')
      expect(implMetrics?.findingsQuality).toBe('high')
      expect(implMetrics?.coverage).toBe('comprehensive')
      expect(implMetrics?.keyInsights).toEqual(['Step-by-step migration plan', 'Testing strategy'])
    })

    it('handles backend agent names via normalizeStageNameFromBackend', () => {
      const events: SSEEvent[] = [
        {
          type: 'progress',
          analysis_id: TEST_ANALYSIS_ID,
          // Backend sends agent name 'tech_comparator' but it should map to 'tech_comparison'
          stage: 'tech_comparison',
          status: 'complete',
          timestamp: '2024-01-01T00:00:00Z',
          details: {
            success_metrics: {
              findings_quality: 'high',
              coverage: 'comprehensive',
            },
          },
        },
      ]

      const { result } = renderHook(() => useAnalysisMetadata(events))

      // Should be stored under normalized stage name
      expect(result.current.stageSuccessMetrics.has('tech_comparison')).toBe(true)
    })

    it('does not collect metrics from non-complete agent events', () => {
      const events: SSEEvent[] = [
        {
          type: 'progress',
          analysis_id: TEST_ANALYSIS_ID,
          stage: 'tech_comparison',
          status: 'running', // Not complete
          timestamp: '2024-01-01T00:00:00Z',
          details: {
            success_metrics: {
              findings_quality: 'high',
            },
          },
        },
      ]

      const { result } = renderHook(() => useAnalysisMetadata(events))

      // Should not collect metrics from running stages
      expect(result.current.stageSuccessMetrics.size).toBe(0)
    })

    it('does not collect metrics when success_metrics is missing', () => {
      const events: SSEEvent[] = [
        {
          type: 'progress',
          analysis_id: TEST_ANALYSIS_ID,
          stage: 'tech_comparison',
          status: 'complete',
          timestamp: '2024-01-01T00:00:00Z',
          // No success_metrics
        },
      ]

      const { result } = renderHook(() => useAnalysisMetadata(events))

      expect(result.current.stageSuccessMetrics.size).toBe(0)
    })

    it('ignores success_metrics from unknown stage names', () => {
      const events: SSEEvent[] = [
        {
          type: 'progress',
          analysis_id: TEST_ANALYSIS_ID,
          // Use a stage name that normalizeStageNameFromBackend will return null for
          stage: 'unknown_stage_name' as 'tech_comparison', // Cast to satisfy TypeScript
          status: 'complete',
          timestamp: '2024-01-01T00:00:00Z',
          details: {
            success_metrics: {
              findings_quality: 'high',
              coverage: 'comprehensive',
            },
          },
        },
      ]

      const { result } = renderHook(() => useAnalysisMetadata(events))

      // Should not store metrics for unknown stage names
      expect(result.current.stageSuccessMetrics.size).toBe(0)
    })
  })

  describe('memoization', () => {
    it('returns same object reference when events array does not change', () => {
      const events: SSEEvent[] = [
        {
          type: 'progress',
          analysis_id: TEST_ANALYSIS_ID,
          stage: 'extraction',
          status: 'complete',
          timestamp: '2024-01-01T00:00:00Z',
          analysis_metadata: {
            title: 'Test Article',
            content_type: 'article',
          },
        },
      ]

      const { result, rerender } = renderHook(() => useAnalysisMetadata(events))

      const firstResult = result.current

      // Re-render with same events array
      rerender()

      const secondResult = result.current

      // Should return same object reference due to useMemo
      expect(secondResult).toBe(firstResult)
    })

    it('returns new object reference when events array changes', () => {
      const events1: SSEEvent[] = [
        {
          type: 'progress',
          analysis_id: TEST_ANALYSIS_ID,
          stage: 'extraction',
          status: 'complete',
          timestamp: '2024-01-01T00:00:00Z',
          analysis_metadata: {
            title: 'Test Article',
            content_type: 'article',
          },
        },
      ]

      const { result, rerender } = renderHook(
        ({ events }: { events: SSEEvent[] }) => useAnalysisMetadata(events),
        { initialProps: { events: events1 } }
      )

      const firstResult = result.current

      // Re-render with different events
      const events2: SSEEvent[] = [
        ...events1,
        {
          type: 'progress',
          analysis_id: TEST_ANALYSIS_ID,
          stage: 'tech_comparison',
          status: 'complete',
          timestamp: '2024-01-01T00:01:00Z',
          details: {
            success_metrics: {
              findings_quality: 'high',
            },
          },
        },
      ]

      rerender({ events: events2 })

      const secondResult = result.current

      // Should return different object reference when events change
      expect(secondResult).not.toBe(firstResult)
      expect(secondResult.stageSuccessMetrics.size).toBe(1)
    })
  })

  describe('integration - full workflow', () => {
    it('extracts all metadata types from complete workflow', () => {
      const events: SSEEvent[] = [
        {
          type: 'progress',
          analysis_id: TEST_ANALYSIS_ID,
          stage: 'extraction',
          status: 'complete',
          timestamp: '2024-01-01T00:00:00Z',
          analysis_metadata: {
            title: 'RAG System Design',
            content_type: 'article',
            url: 'https://example.com/rag-design',
            word_count: 3000,
          },
        },
        {
          type: 'progress',
          analysis_id: TEST_ANALYSIS_ID,
          stage: 'supervisor_routing',
          status: 'complete',
          timestamp: '2024-01-01T00:01:00Z',
          details: {
            skipped_agents: ['code_quality_critic', 'performance_analyst'],
            selected_agents: ['tech_comparator', 'security_auditor', 'implementation_planner'],
            skip_reasons: {
              code_quality_critic: 'No code to review',
              performance_analyst: 'No performance metrics',
            },
          },
        },
        {
          type: 'progress',
          analysis_id: TEST_ANALYSIS_ID,
          stage: 'tech_comparison',
          status: 'complete',
          timestamp: '2024-01-01T00:02:00Z',
          details: {
            success_metrics: {
              findings_quality: 'high',
              coverage: 'comprehensive',
              key_insights: ['Compared embedding models', 'Vector DB comparison'],
            },
          },
        },
        {
          type: 'progress',
          analysis_id: TEST_ANALYSIS_ID,
          stage: 'security_audit',
          status: 'complete',
          timestamp: '2024-01-01T00:03:00Z',
          details: {
            success_metrics: {
              findings_quality: 'medium',
              coverage: 'partial',
              key_insights: ['API key exposure risk'],
            },
          },
        },
        {
          type: 'progress',
          analysis_id: TEST_ANALYSIS_ID,
          stage: 'implementation_planning',
          status: 'complete',
          timestamp: '2024-01-01T00:04:00Z',
          details: {
            success_metrics: {
              findings_quality: 'high',
              coverage: 'comprehensive',
              key_insights: ['Migration steps', 'Testing strategy', 'Deployment plan'],
            },
          },
        },
      ]

      const { result } = renderHook(() => useAnalysisMetadata(events))

      // Analysis metadata
      expect(result.current.analysisMetadata).toEqual({
        title: 'RAG System Design',
        contentType: 'article',
        url: 'https://example.com/rag-design',
        wordCount: 3000,
      })

      // Skipped agents info
      expect(result.current.skippedAgentsInfo).toEqual({
        agents: ['code_quality_critic', 'performance_analyst'],
        selectedAgents: ['tech_comparator', 'security_auditor', 'implementation_planner'],
      })

      // Skip reasons
      expect(result.current.skipReasons).toEqual({
        code_quality_critic: 'No code to review',
        performance_analyst: 'No performance metrics',
      })

      // Success metrics from all agent stages
      expect(result.current.stageSuccessMetrics.size).toBe(3)
      expect(result.current.stageSuccessMetrics.get('tech_comparison')).toEqual({
        findingsQuality: 'high',
        coverage: 'comprehensive',
        keyInsights: ['Compared embedding models', 'Vector DB comparison'],
      })
      expect(result.current.stageSuccessMetrics.get('security_audit')).toEqual({
        findingsQuality: 'medium',
        coverage: 'partial',
        keyInsights: ['API key exposure risk'],
      })
      expect(result.current.stageSuccessMetrics.get('implementation_planning')).toEqual({
        findingsQuality: 'high',
        coverage: 'comprehensive',
        keyInsights: ['Migration steps', 'Testing strategy', 'Deployment plan'],
      })
    })
  })
})
