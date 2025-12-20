/**
 * Tests for useActivityFeed - Activity feed extraction from SSE events
 *
 * These tests validate that the hook correctly transforms SSE events
 * into agent activity entries for display in the activity feed.
 */

import { renderHook } from '@testing-library/react'
import { describe, expect, it } from 'vitest'

import type { SSEEvent } from '@/schemas/sse'

import { useActivityFeed } from '../useActivityFeed'

const TEST_ANALYSIS_ID = '123e4567-e89b-12d3-a456-426614174000'

describe('useActivityFeed', () => {
  describe('empty events', () => {
    it('returns empty array when no events provided', () => {
      const { result } = renderHook(() => useActivityFeed([]))

      expect(result.current).toEqual([])
    })
  })

  describe('event filtering', () => {
    it('includes only progress and complete events', () => {
      const events: SSEEvent[] = [
        {
          type: 'progress',
          analysis_id: TEST_ANALYSIS_ID,
          stage: 'extraction',
          status: 'running',
          timestamp: '2025-01-01T00:00:00Z',
        },
        {
          type: 'error',
          analysis_id: TEST_ANALYSIS_ID,
          stage: 'tech_comparison',
          status: 'failed',
          timestamp: '2025-01-01T00:01:00Z',
          error: 'Agent failed',
        },
        {
          type: 'progress',
          analysis_id: TEST_ANALYSIS_ID,
          stage: 'security_audit',
          status: 'complete',
          timestamp: '2025-01-01T00:02:00Z',
        },
        {
          type: 'complete',
          analysis_id: TEST_ANALYSIS_ID,
          stage: 'artifact_generation',
          status: 'complete',
          timestamp: '2025-01-01T00:03:00Z',
        },
      ]

      const { result } = renderHook(() => useActivityFeed(events))

      // Error event should be filtered out
      expect(result.current).toHaveLength(3)
      // IDs are based on index AFTER filtering, so indices are 0, 1, 2
      expect(result.current.map((a) => a.id)).toEqual([
        'artifact_generation-2',
        'security_audit-1',
        'extraction-0',
      ])
    })

    it('excludes error events completely', () => {
      const events: SSEEvent[] = [
        {
          type: 'error',
          analysis_id: TEST_ANALYSIS_ID,
          stage: 'tech_comparison',
          status: 'failed',
          timestamp: '2025-01-01T00:00:00Z',
          error: 'Agent crashed',
        },
        {
          type: 'error',
          analysis_id: TEST_ANALYSIS_ID,
          stage: 'security_audit',
          status: 'failed',
          timestamp: '2025-01-01T00:01:00Z',
          error: 'Timeout',
        },
      ]

      const { result } = renderHook(() => useActivityFeed(events))

      expect(result.current).toEqual([])
    })
  })

  describe('chronological ordering', () => {
    it('returns activities in reverse chronological order (newest first)', () => {
      const events: SSEEvent[] = [
        {
          type: 'progress',
          analysis_id: TEST_ANALYSIS_ID,
          stage: 'extraction',
          status: 'running',
          timestamp: '2025-01-01T00:00:00Z',
        },
        {
          type: 'progress',
          analysis_id: TEST_ANALYSIS_ID,
          stage: 'supervisor_routing',
          status: 'running',
          timestamp: '2025-01-01T00:01:00Z',
        },
        {
          type: 'progress',
          analysis_id: TEST_ANALYSIS_ID,
          stage: 'tech_comparison',
          status: 'running',
          timestamp: '2025-01-01T00:02:00Z',
        },
      ]

      const { result } = renderHook(() => useActivityFeed(events))

      // Newest event should be first
      expect(result.current[0].id).toBe('tech_comparison-2')
      expect(result.current[1].id).toBe('supervisor_routing-1')
      expect(result.current[2].id).toBe('extraction-0')
    })
  })

  describe('agent name extraction', () => {
    it('extracts agent name from stage name for agent stages', () => {
      const events: SSEEvent[] = [
        {
          type: 'progress',
          analysis_id: TEST_ANALYSIS_ID,
          stage: 'extraction',
          status: 'running',
          timestamp: '2025-01-01T00:00:00Z',
        },
        {
          type: 'progress',
          analysis_id: TEST_ANALYSIS_ID,
          stage: 'tech_comparison',
          status: 'running',
          timestamp: '2025-01-01T00:01:00Z',
        },
        {
          type: 'progress',
          analysis_id: TEST_ANALYSIS_ID,
          stage: 'security_audit',
          status: 'running',
          timestamp: '2025-01-01T00:02:00Z',
        },
      ]

      const { result } = renderHook(() => useActivityFeed(events))

      expect(result.current[0].agentName).toBe('Security Auditor')
      expect(result.current[1].agentName).toBe('Tech Comparator')
      expect(result.current[2].agentName).toBe('Content Extractor')
    })

    it('extracts agent name from details.agent when available', () => {
      const events: SSEEvent[] = [
        {
          type: 'progress',
          analysis_id: TEST_ANALYSIS_ID,
          stage: 'extraction',
          status: 'running',
          timestamp: '2025-01-01T00:00:00Z',
          details: {
            agent: 'content_extractor',
          },
        },
        {
          type: 'progress',
          analysis_id: TEST_ANALYSIS_ID,
          stage: 'tech_comparison',
          status: 'running',
          timestamp: '2025-01-01T00:01:00Z',
          details: {
            agent: 'tech_comparator',
          },
        },
      ]

      const { result } = renderHook(() => useActivityFeed(events))

      expect(result.current[0].agentName).toBe('Tech Comparator')
      expect(result.current[1].agentName).toBe('Content Extractor')
    })

    it('uses formatted name for workflow stages', () => {
      const events: SSEEvent[] = [
        {
          type: 'progress',
          analysis_id: TEST_ANALYSIS_ID,
          stage: 'workflow',
          status: 'running',
          timestamp: '2025-01-01T00:00:00Z',
        },
      ]

      const { result } = renderHook(() => useActivityFeed(events))

      // Workflow is in STAGE_CONFIG, so it gets formatted
      expect(result.current[0].agentName).toBe('Workflow')
    })
  })

  describe('action description extraction', () => {
    it('generates correct action for running status', () => {
      const events: SSEEvent[] = [
        {
          type: 'progress',
          analysis_id: TEST_ANALYSIS_ID,
          stage: 'extraction',
          status: 'running',
          timestamp: '2025-01-01T00:00:00Z',
        },
        {
          type: 'progress',
          analysis_id: TEST_ANALYSIS_ID,
          stage: 'tech_comparison',
          status: 'running',
          timestamp: '2025-01-01T00:01:00Z',
        },
      ]

      const { result } = renderHook(() => useActivityFeed(events))

      expect(result.current[0].action).toBe('Comparing technology patterns...')
      expect(result.current[1].action).toBe('Extracting content from URL...')
    })

    it('generates correct action for complete status with word count', () => {
      const events: SSEEvent[] = [
        {
          type: 'progress',
          analysis_id: TEST_ANALYSIS_ID,
          stage: 'extraction',
          status: 'complete',
          timestamp: '2025-01-01T00:00:00Z',
          details: {
            word_count: 1500,
          },
        },
      ]

      const { result } = renderHook(() => useActivityFeed(events))

      expect(result.current[0].action).toBe('Extracted 1500 words from content')
    })

    it('generates correct action for complete status with findings_summary', () => {
      const events: SSEEvent[] = [
        {
          type: 'progress',
          analysis_id: TEST_ANALYSIS_ID,
          stage: 'tech_comparison',
          status: 'complete',
          timestamp: '2025-01-01T00:00:00Z',
          details: {
            findings_summary: 'Compared React vs Vue, Angular',
          },
        },
      ]

      const { result } = renderHook(() => useActivityFeed(events))

      expect(result.current[0].action).toBe('Compared React vs Vue, Angular')
    })

    it('generates correct action for complete status with insights_count', () => {
      const events: SSEEvent[] = [
        {
          type: 'progress',
          analysis_id: TEST_ANALYSIS_ID,
          stage: 'security_audit',
          status: 'complete',
          timestamp: '2025-01-01T00:00:00Z',
          details: {
            insights_count: 5,
          },
        },
        {
          type: 'progress',
          analysis_id: TEST_ANALYSIS_ID,
          stage: 'implementation_planning',
          status: 'complete',
          timestamp: '2025-01-01T00:01:00Z',
          details: {
            insights_count: 1,
          },
        },
      ]

      const { result } = renderHook(() => useActivityFeed(events))

      expect(result.current[0].action).toBe('Found 1 insight')
      expect(result.current[1].action).toBe('Found 5 insights')
    })

    it('uses action description for workflow stages', () => {
      const events: SSEEvent[] = [
        {
          type: 'progress',
          analysis_id: TEST_ANALYSIS_ID,
          stage: 'workflow',
          status: 'running',
          timestamp: '2025-01-01T00:00:00Z',
        },
      ]

      const { result } = renderHook(() => useActivityFeed(events))

      // Workflow is in STAGE_CONFIG with a running action defined
      expect(result.current[0].action).toBe('Managing workflow...')
    })
  })

  describe('id generation', () => {
    it('generates correct id format with stage and index', () => {
      const events: SSEEvent[] = [
        {
          type: 'progress',
          analysis_id: TEST_ANALYSIS_ID,
          stage: 'extraction',
          status: 'running',
          timestamp: '2025-01-01T00:00:00Z',
        },
        {
          type: 'progress',
          analysis_id: TEST_ANALYSIS_ID,
          stage: 'tech_comparison',
          status: 'running',
          timestamp: '2025-01-01T00:01:00Z',
        },
        {
          type: 'complete',
          analysis_id: TEST_ANALYSIS_ID,
          stage: 'artifact_generation',
          status: 'complete',
          timestamp: '2025-01-01T00:02:00Z',
        },
      ]

      const { result } = renderHook(() => useActivityFeed(events))

      // IDs should be in format: ${stage}-${index}
      // But reversed due to .reverse() call
      expect(result.current[0].id).toBe('artifact_generation-2')
      expect(result.current[1].id).toBe('tech_comparison-1')
      expect(result.current[2].id).toBe('extraction-0')
    })

    it('maintains unique ids even for duplicate stages', () => {
      const events: SSEEvent[] = [
        {
          type: 'progress',
          analysis_id: TEST_ANALYSIS_ID,
          stage: 'extraction',
          status: 'running',
          timestamp: '2025-01-01T00:00:00Z',
        },
        {
          type: 'progress',
          analysis_id: TEST_ANALYSIS_ID,
          stage: 'extraction',
          status: 'complete',
          timestamp: '2025-01-01T00:01:00Z',
        },
      ]

      const { result } = renderHook(() => useActivityFeed(events))

      // Even though both are extraction, they have different indices
      expect(result.current[0].id).toBe('extraction-1')
      expect(result.current[1].id).toBe('extraction-0')
      expect(result.current[0].id).not.toBe(result.current[1].id)
    })
  })

  describe('timestamp conversion', () => {
    it('converts ISO timestamp strings to Date objects', () => {
      const events: SSEEvent[] = [
        {
          type: 'progress',
          analysis_id: TEST_ANALYSIS_ID,
          stage: 'extraction',
          status: 'running',
          timestamp: '2025-01-01T12:30:45.123Z',
        },
      ]

      const { result } = renderHook(() => useActivityFeed(events))

      expect(result.current[0].timestamp).toBeInstanceOf(Date)
      expect(result.current[0].timestamp.toISOString()).toBe('2025-01-01T12:30:45.123Z')
    })

    it('handles different ISO timestamp formats', () => {
      const events: SSEEvent[] = [
        {
          type: 'progress',
          analysis_id: TEST_ANALYSIS_ID,
          stage: 'extraction',
          status: 'running',
          timestamp: '2025-01-01T00:00:00Z',
        },
        {
          type: 'progress',
          analysis_id: TEST_ANALYSIS_ID,
          stage: 'tech_comparison',
          status: 'running',
          timestamp: '2025-01-01T00:00:00.000Z',
        },
        {
          type: 'progress',
          analysis_id: TEST_ANALYSIS_ID,
          stage: 'security_audit',
          status: 'running',
          timestamp: '2025-01-01T00:00:00+00:00',
        },
      ]

      const { result } = renderHook(() => useActivityFeed(events))

      expect(result.current[0].timestamp).toBeInstanceOf(Date)
      expect(result.current[1].timestamp).toBeInstanceOf(Date)
      expect(result.current[2].timestamp).toBeInstanceOf(Date)
    })
  })

  describe('complete event handling', () => {
    it('processes complete events correctly', () => {
      const events: SSEEvent[] = [
        {
          type: 'complete',
          analysis_id: TEST_ANALYSIS_ID,
          stage: 'artifact_generation',
          status: 'complete',
          timestamp: '2025-01-01T00:00:00Z',
          artifact_id: '456e4567-e89b-12d3-a456-426614174001',
        },
      ]

      const { result } = renderHook(() => useActivityFeed(events))

      expect(result.current).toHaveLength(1)
      expect(result.current[0].agentName).toBe('Report Generator')
      // Without artifact_id in details, it falls back to generic action
      expect(result.current[0].action).toBe('Completed Generating Report')
      expect(result.current[0].id).toBe('artifact_generation-0')
    })
  })

  describe('memoization', () => {
    it('returns same reference when events array has not changed', () => {
      const events: SSEEvent[] = [
        {
          type: 'progress',
          analysis_id: TEST_ANALYSIS_ID,
          stage: 'extraction',
          status: 'running',
          timestamp: '2025-01-01T00:00:00Z',
        },
      ]

      const { result, rerender } = renderHook(() => useActivityFeed(events))
      const firstResult = result.current

      rerender()
      const secondResult = result.current

      expect(firstResult).toBe(secondResult)
    })

    it('returns new reference when events array changes', () => {
      const events1: SSEEvent[] = [
        {
          type: 'progress',
          analysis_id: TEST_ANALYSIS_ID,
          stage: 'extraction',
          status: 'running',
          timestamp: '2025-01-01T00:00:00Z',
        },
      ]

      const events2: SSEEvent[] = [
        {
          type: 'progress',
          analysis_id: TEST_ANALYSIS_ID,
          stage: 'extraction',
          status: 'running',
          timestamp: '2025-01-01T00:00:00Z',
        },
        {
          type: 'progress',
          analysis_id: TEST_ANALYSIS_ID,
          stage: 'tech_comparison',
          status: 'running',
          timestamp: '2025-01-01T00:01:00Z',
        },
      ]

      const { result, rerender } = renderHook(({ events }) => useActivityFeed(events), {
        initialProps: { events: events1 },
      })
      const firstResult = result.current

      rerender({ events: events2 })
      const secondResult = result.current

      expect(firstResult).not.toBe(secondResult)
      expect(firstResult).toHaveLength(1)
      expect(secondResult).toHaveLength(2)
    })
  })

  describe('integration with complex scenarios', () => {
    it('handles full workflow with multiple agents', () => {
      const events: SSEEvent[] = [
        {
          type: 'progress',
          analysis_id: TEST_ANALYSIS_ID,
          stage: 'extraction',
          status: 'running',
          timestamp: '2025-01-01T00:00:00Z',
        },
        {
          type: 'progress',
          analysis_id: TEST_ANALYSIS_ID,
          stage: 'extraction',
          status: 'complete',
          timestamp: '2025-01-01T00:01:00Z',
          details: { word_count: 2500 },
        },
        {
          type: 'progress',
          analysis_id: TEST_ANALYSIS_ID,
          stage: 'supervisor_routing',
          status: 'running',
          timestamp: '2025-01-01T00:02:00Z',
        },
        {
          type: 'progress',
          analysis_id: TEST_ANALYSIS_ID,
          stage: 'supervisor_routing',
          status: 'complete',
          timestamp: '2025-01-01T00:03:00Z',
        },
        {
          type: 'progress',
          analysis_id: TEST_ANALYSIS_ID,
          stage: 'tech_comparison',
          status: 'running',
          timestamp: '2025-01-01T00:04:00Z',
        },
        {
          type: 'error',
          analysis_id: TEST_ANALYSIS_ID,
          stage: 'security_audit',
          status: 'failed',
          timestamp: '2025-01-01T00:05:00Z',
          error: 'Agent crashed',
        },
        {
          type: 'progress',
          analysis_id: TEST_ANALYSIS_ID,
          stage: 'tech_comparison',
          status: 'complete',
          timestamp: '2025-01-01T00:06:00Z',
          details: { findings_summary: 'Compared 3 frameworks' },
        },
        {
          type: 'complete',
          analysis_id: TEST_ANALYSIS_ID,
          stage: 'artifact_generation',
          status: 'complete',
          timestamp: '2025-01-01T00:07:00Z',
          artifact_id: '789e4567-e89b-12d3-a456-426614174002',
        },
      ]

      const { result } = renderHook(() => useActivityFeed(events))

      // Error event should be filtered out, so 7 events expected
      expect(result.current).toHaveLength(7)

      // Check that activities are in reverse chronological order
      // Index is based on position AFTER filtering (error event removed)
      expect(result.current[0].id).toBe('artifact_generation-6')
      expect(result.current[0].agentName).toBe('Report Generator')
      // Without artifact_id in details, falls back to generic action
      expect(result.current[0].action).toBe('Completed Generating Report')

      expect(result.current[1].id).toBe('tech_comparison-5')
      expect(result.current[1].action).toBe('Compared 3 frameworks')

      expect(result.current[6].id).toBe('extraction-0')
      expect(result.current[6].action).toBe('Extracting content from URL...')
    })

    it('handles mixed event types with different details', () => {
      const events: SSEEvent[] = [
        {
          type: 'progress',
          analysis_id: TEST_ANALYSIS_ID,
          stage: 'extraction',
          status: 'complete',
          timestamp: '2025-01-01T00:00:00Z',
          details: {
            word_count: 1200,
            agent: 'content_extractor',
          },
        },
        {
          type: 'progress',
          analysis_id: TEST_ANALYSIS_ID,
          stage: 'tech_comparison',
          status: 'complete',
          timestamp: '2025-01-01T00:01:00Z',
          details: {
            findings_summary: 'React dominates',
            insights_count: 8,
          },
        },
        {
          type: 'progress',
          analysis_id: TEST_ANALYSIS_ID,
          stage: 'security_audit',
          status: 'complete',
          timestamp: '2025-01-01T00:02:00Z',
          details: {
            insights_count: 3,
          },
        },
        {
          type: 'complete',
          analysis_id: TEST_ANALYSIS_ID,
          stage: 'artifact_generation',
          status: 'complete',
          timestamp: '2025-01-01T00:03:00Z',
          artifact_id: '456e4567-e89b-12d3-a456-426614174001',
        },
      ]

      const { result } = renderHook(() => useActivityFeed(events))

      expect(result.current).toHaveLength(4)

      // Check that findings_summary takes precedence over insights_count
      expect(result.current[2].action).toBe('React dominates')

      // Check that insights_count is used when findings_summary not available
      expect(result.current[1].action).toBe('Found 3 insights')

      // Check that word_count is extracted correctly
      expect(result.current[3].action).toBe('Extracted 1200 words from content')
    })
  })
})
