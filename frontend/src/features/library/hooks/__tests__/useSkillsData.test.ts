/**
 * Tests for useSkillsData - Transform analyses to skills format
 *
 * Validates analysis-to-skill transformation and status mapping.
 */

import { renderHook } from '@testing-library/react'
import { describe, it, expect, vi } from 'vitest'

import { useSkillsData } from '../useSkillsData'

vi.mock('@tanstack/react-router', () => ({
  useNavigate: () => vi.fn(),
}))

describe('useSkillsData', () => {
  describe('initialization', () => {
    it('returns empty array when analyses is undefined', () => {
      const { result } = renderHook(() => useSkillsData(undefined))

      expect(result.current).toEqual([])
    })

    it('returns empty array when analyses is empty', () => {
      const { result } = renderHook(() => useSkillsData([]))

      expect(result.current).toEqual([])
    })
  })

  describe('transformation', () => {
    it('transforms single analysis to skill format', () => {
      const analyses = [
        {
          id: 'analysis-1',
          title: 'React Hooks Guide',
          content_type: 'article',
          status: 'complete',
        },
      ]

      const { result } = renderHook(() => useSkillsData(analyses))

      expect(result.current).toHaveLength(1)
      expect(result.current[0]).toEqual(
        expect.objectContaining({
          id: 'analysis-1',
          title: 'React Hooks Guide',
          description: 'Analysis of article',
          duration: 25,
          difficulty: 'intermediate',
        })
      )
    })

    it('transforms multiple analyses', () => {
      const analyses = [
        {
          id: 'analysis-1',
          title: 'React Hooks',
          content_type: 'article',
          status: 'complete',
        },
        {
          id: 'analysis-2',
          title: 'TypeScript Basics',
          content_type: 'tutorial',
          status: 'complete',
        },
      ]

      const { result } = renderHook(() => useSkillsData(analyses))

      expect(result.current).toHaveLength(2)
      expect(result.current[0].title).toBe('React Hooks')
      expect(result.current[1].title).toBe('TypeScript Basics')
    })

    it('uses "Untitled" for null titles', () => {
      const analyses = [
        {
          id: 'analysis-1',
          title: null,
          content_type: 'article',
          status: 'complete',
        },
      ]

      const { result } = renderHook(() => useSkillsData(analyses))

      expect(result.current[0].title).toBe('Untitled')
    })

    it('generates thumbnail URL from analysis ID', () => {
      const analyses = [
        {
          id: 'analysis-123',
          title: 'Test',
          content_type: 'article',
          status: 'complete',
        },
      ]

      const { result } = renderHook(() => useSkillsData(analyses))

      expect(result.current[0].thumbnail).toBe(
        'https://api.dicebear.com/7.x/shapes/svg?seed=analysis-123'
      )
    })
  })

  describe('status mapping', () => {
    it('maps complete status correctly', () => {
      const analyses = [
        {
          id: 'analysis-1',
          title: 'Test',
          content_type: 'article',
          status: 'complete',
        },
      ]

      const { result } = renderHook(() => useSkillsData(analyses))

      expect(result.current[0].status).toBe('completed')
      expect(result.current[0].progress).toBe(100)
    })

    it('maps failed status correctly', () => {
      const analyses = [
        {
          id: 'analysis-1',
          title: 'Test',
          content_type: 'article',
          status: 'failed',
        },
      ]

      const { result } = renderHook(() => useSkillsData(analyses))

      expect(result.current[0].status).toBe('failed')
      expect(result.current[0].progress).toBe(65)
    })

    it('maps extraction_failed status to failed', () => {
      const analyses = [
        {
          id: 'analysis-1',
          title: 'Test',
          content_type: 'article',
          status: 'extraction_failed',
        },
      ]

      const { result } = renderHook(() => useSkillsData(analyses))

      expect(result.current[0].status).toBe('failed')
    })

    it('maps analysis_failed status to failed', () => {
      const analyses = [
        {
          id: 'analysis-1',
          title: 'Test',
          content_type: 'article',
          status: 'analysis_failed',
        },
      ]

      const { result } = renderHook(() => useSkillsData(analyses))

      expect(result.current[0].status).toBe('failed')
    })

    it('maps artifact_failed status to failed', () => {
      const analyses = [
        {
          id: 'analysis-1',
          title: 'Test',
          content_type: 'article',
          status: 'artifact_failed',
        },
      ]

      const { result } = renderHook(() => useSkillsData(analyses))

      expect(result.current[0].status).toBe('failed')
    })

    it('maps quality_gate_failed status to failed', () => {
      const analyses = [
        {
          id: 'analysis-1',
          title: 'Test',
          content_type: 'article',
          status: 'quality_gate_failed',
        },
      ]

      const { result } = renderHook(() => useSkillsData(analyses))

      expect(result.current[0].status).toBe('failed')
    })

    it('maps other statuses to in-progress', () => {
      const statuses = ['pending', 'extracting', 'analyzing']

      statuses.forEach((status) => {
        const analyses = [
          {
            id: 'analysis-1',
            title: 'Test',
            content_type: 'article',
            status,
          },
        ]

        const { result } = renderHook(() => useSkillsData(analyses))

        expect(result.current[0].status).toBe('in-progress')
        expect(result.current[0].progress).toBe(65)
      })
    })
  })

  describe('tags', () => {
    it('includes content_type in tags', () => {
      const analyses = [
        {
          id: 'analysis-1',
          title: 'Test',
          content_type: 'article',
          status: 'complete',
        },
      ]

      const { result } = renderHook(() => useSkillsData(analyses))

      expect(result.current[0].tags).toContain('article')
    })

    it('includes status in tags', () => {
      const analyses = [
        {
          id: 'analysis-1',
          title: 'Test',
          content_type: 'article',
          status: 'complete',
        },
      ]

      const { result } = renderHook(() => useSkillsData(analyses))

      expect(result.current[0].tags).toContain('complete')
    })

    it('creates tags array with content_type and status', () => {
      const analyses = [
        {
          id: 'analysis-1',
          title: 'Test',
          content_type: 'tutorial',
          status: 'failed',
        },
      ]

      const { result } = renderHook(() => useSkillsData(analyses))

      expect(result.current[0].tags).toEqual(['tutorial', 'failed'])
    })
  })

  describe('navigation', () => {
    it('provides onSelect function', () => {
      const analyses = [
        {
          id: 'analysis-1',
          title: 'Test',
          content_type: 'article',
          status: 'complete',
        },
      ]

      const { result } = renderHook(() => useSkillsData(analyses))

      expect(typeof result.current[0].onSelect).toBe('function')
    })

    it('onSelect function accepts analysis ID', () => {
      const analyses = [
        {
          id: 'analysis-1',
          title: 'Test',
          content_type: 'article',
          status: 'complete',
        },
      ]

      const { result } = renderHook(() => useSkillsData(analyses))

      // Should not throw
      expect(() => result.current[0].onSelect('analysis-1')).not.toThrow()
    })
  })

  describe('edge cases', () => {
    it('handles analysis with all null/undefined fields', () => {
      const analyses = [
        {
          id: 'analysis-1',
          title: null,
          content_type: 'unknown',
          status: 'unknown',
        },
      ]

      const { result } = renderHook(() => useSkillsData(analyses))

      expect(result.current).toHaveLength(1)
      expect(result.current[0].title).toBe('Untitled')
    })

    it('handles large number of analyses', () => {
      const analyses = Array.from({ length: 1000 }, (_, i) => ({
        id: `analysis-${i}`,
        title: `Analysis ${i}`,
        content_type: 'article',
        status: 'complete',
      }))

      const { result } = renderHook(() => useSkillsData(analyses))

      expect(result.current).toHaveLength(1000)
    })

    it('handles different content types', () => {
      const contentTypes = ['article', 'tutorial', 'video', 'documentation']

      contentTypes.forEach((contentType) => {
        const analyses = [
          {
            id: 'analysis-1',
            title: 'Test',
            content_type: contentType,
            status: 'complete',
          },
        ]

        const { result } = renderHook(() => useSkillsData(analyses))

        expect(result.current[0].description).toBe(`Analysis of ${contentType}`)
        expect(result.current[0].tags).toContain(contentType)
      })
    })

    it('maintains consistent difficulty level', () => {
      const analyses = [
        {
          id: 'analysis-1',
          title: 'Test 1',
          content_type: 'article',
          status: 'complete',
        },
        {
          id: 'analysis-2',
          title: 'Test 2',
          content_type: 'tutorial',
          status: 'failed',
        },
      ]

      const { result } = renderHook(() => useSkillsData(analyses))

      // All should have same difficulty
      expect(result.current.every((skill) => skill.difficulty === 'intermediate')).toBe(true)
    })

    it('maintains consistent duration', () => {
      const analyses = [
        {
          id: 'analysis-1',
          title: 'Test 1',
          content_type: 'article',
          status: 'complete',
        },
        {
          id: 'analysis-2',
          title: 'Test 2',
          content_type: 'tutorial',
          status: 'failed',
        },
      ]

      const { result } = renderHook(() => useSkillsData(analyses))

      // All should have same duration
      expect(result.current.every((skill) => skill.duration === 25)).toBe(true)
    })
  })

  describe('memoization', () => {
    it('returns new array when analyses change', () => {
      const analyses1 = [
        {
          id: 'analysis-1',
          title: 'Test 1',
          content_type: 'article',
          status: 'complete',
        },
      ]

      const analyses2 = [
        {
          id: 'analysis-2',
          title: 'Test 2',
          content_type: 'tutorial',
          status: 'complete',
        },
      ]

      const { result, rerender } = renderHook(({ analyses }) => useSkillsData(analyses), {
        initialProps: { analyses: analyses1 },
      })

      const firstResult = result.current

      rerender({ analyses: analyses2 })

      const secondResult = result.current

      expect(firstResult).not.toBe(secondResult)
      expect(firstResult[0].id).toBe('analysis-1')
      expect(secondResult[0].id).toBe('analysis-2')
    })
  })
})
