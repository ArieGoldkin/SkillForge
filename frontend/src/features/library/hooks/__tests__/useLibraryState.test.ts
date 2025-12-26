/**
 * Tests for useLibraryState - Library state management
 *
 * Validates state initialization, updates, and type safety.
 */

import { renderHook, act } from '@testing-library/react'
import { describe, it, expect } from 'vitest'

import { COMPONENT_CONSTANTS } from '@/lib/constants'

import { useLibraryState } from '../useLibraryState'

describe('useLibraryState', () => {
  describe('initialization', () => {
    it('starts with empty search query', () => {
      const { result } = renderHook(() => useLibraryState())

      expect(result.current.searchQuery).toBe('')
    })

    it('starts with hybrid search mode', () => {
      const { result } = renderHook(() => useLibraryState())

      expect(result.current.searchMode).toBe('hybrid')
    })

    it('starts with showCompletedOnly enabled', () => {
      const { result } = renderHook(() => useLibraryState())

      expect(result.current.showCompletedOnly).toBe(true)
    })

    it('initializes filters with empty arrays', () => {
      const { result } = renderHook(() => useLibraryState())

      expect(result.current.filters.difficulty).toEqual([])
      expect(result.current.filters.tags).toEqual([])
      expect(result.current.filters.status).toEqual([])
    })

    it('initializes duration range correctly', () => {
      const { result } = renderHook(() => useLibraryState())

      expect(result.current.filters.durationRange).toEqual([
        0,
        COMPONENT_CONSTANTS.SKILL_DURATION_FILTER_MAX,
      ])
    })
  })

  describe('search query state', () => {
    it('updates search query', () => {
      const { result } = renderHook(() => useLibraryState())

      act(() => {
        result.current.setSearchQuery('React hooks')
      })

      expect(result.current.searchQuery).toBe('React hooks')
    })

    it('clears search query', () => {
      const { result } = renderHook(() => useLibraryState())

      act(() => {
        result.current.setSearchQuery('test')
      })

      expect(result.current.searchQuery).toBe('test')

      act(() => {
        result.current.setSearchQuery('')
      })

      expect(result.current.searchQuery).toBe('')
    })

    it('handles multiple consecutive updates', () => {
      const { result } = renderHook(() => useLibraryState())

      act(() => {
        result.current.setSearchQuery('first')
        result.current.setSearchQuery('second')
        result.current.setSearchQuery('third')
      })

      expect(result.current.searchQuery).toBe('third')
    })
  })

  describe('search mode state', () => {
    it('updates search mode to semantic', () => {
      const { result } = renderHook(() => useLibraryState())

      act(() => {
        result.current.setSearchMode('semantic')
      })

      expect(result.current.searchMode).toBe('semantic')
    })

    it('updates search mode to fulltext', () => {
      const { result } = renderHook(() => useLibraryState())

      act(() => {
        result.current.setSearchMode('fulltext')
      })

      expect(result.current.searchMode).toBe('fulltext')
    })

    it('toggles between search modes', () => {
      const { result } = renderHook(() => useLibraryState())

      act(() => {
        result.current.setSearchMode('semantic')
      })

      expect(result.current.searchMode).toBe('semantic')

      act(() => {
        result.current.setSearchMode('hybrid')
      })

      expect(result.current.searchMode).toBe('hybrid')
    })
  })

  describe('showCompletedOnly state', () => {
    it('toggles showCompletedOnly to false', () => {
      const { result } = renderHook(() => useLibraryState())

      act(() => {
        result.current.setShowCompletedOnly(false)
      })

      expect(result.current.showCompletedOnly).toBe(false)
    })

    it('toggles showCompletedOnly to true', () => {
      const { result } = renderHook(() => useLibraryState())

      act(() => {
        result.current.setShowCompletedOnly(false)
      })

      expect(result.current.showCompletedOnly).toBe(false)

      act(() => {
        result.current.setShowCompletedOnly(true)
      })

      expect(result.current.showCompletedOnly).toBe(true)
    })
  })

  describe('filters state', () => {
    it('updates difficulty filters', () => {
      const { result } = renderHook(() => useLibraryState())

      act(() => {
        result.current.setFilters({
          ...result.current.filters,
          difficulty: ['beginner', 'intermediate'],
        })
      })

      expect(result.current.filters.difficulty).toEqual(['beginner', 'intermediate'])
    })

    it('updates tags filters', () => {
      const { result } = renderHook(() => useLibraryState())

      act(() => {
        result.current.setFilters({
          ...result.current.filters,
          tags: ['react', 'typescript'],
        })
      })

      expect(result.current.filters.tags).toEqual(['react', 'typescript'])
    })

    it('updates status filters', () => {
      const { result } = renderHook(() => useLibraryState())

      act(() => {
        result.current.setFilters({
          ...result.current.filters,
          status: ['complete', 'failed'],
        })
      })

      expect(result.current.filters.status).toEqual(['complete', 'failed'])
    })

    it('updates duration range', () => {
      const { result } = renderHook(() => useLibraryState())

      act(() => {
        result.current.setFilters({
          ...result.current.filters,
          durationRange: [30, 120],
        })
      })

      expect(result.current.filters.durationRange).toEqual([30, 120])
    })

    it('replaces entire filters object', () => {
      const { result } = renderHook(() => useLibraryState())

      const newFilters = {
        difficulty: ['advanced'],
        tags: ['testing'],
        status: ['in_progress'],
        durationRange: [60, 180],
      }

      act(() => {
        result.current.setFilters(newFilters)
      })

      expect(result.current.filters).toEqual(newFilters)
    })
  })

  describe('combined state updates', () => {
    it('updates search query and mode together', () => {
      const { result } = renderHook(() => useLibraryState())

      act(() => {
        result.current.setSearchQuery('React')
        result.current.setSearchMode('semantic')
      })

      expect(result.current.searchQuery).toBe('React')
      expect(result.current.searchMode).toBe('semantic')
    })

    it('updates filters and showCompletedOnly together', () => {
      const { result } = renderHook(() => useLibraryState())

      act(() => {
        result.current.setShowCompletedOnly(false)
        result.current.setFilters({
          ...result.current.filters,
          tags: ['api'],
        })
      })

      expect(result.current.showCompletedOnly).toBe(false)
      expect(result.current.filters.tags).toEqual(['api'])
    })

    it('handles complex state update scenario', () => {
      const { result } = renderHook(() => useLibraryState())

      act(() => {
        result.current.setSearchQuery('TypeScript')
        result.current.setSearchMode('fulltext')
        result.current.setShowCompletedOnly(false)
        result.current.setFilters({
          difficulty: ['intermediate'],
          tags: ['typescript', 'advanced'],
          status: ['complete'],
          durationRange: [45, 90],
        })
      })

      expect(result.current.searchQuery).toBe('TypeScript')
      expect(result.current.searchMode).toBe('fulltext')
      expect(result.current.showCompletedOnly).toBe(false)
      expect(result.current.filters).toEqual({
        difficulty: ['intermediate'],
        tags: ['typescript', 'advanced'],
        status: ['complete'],
        durationRange: [45, 90],
      })
    })
  })

  describe('edge cases', () => {
    it('handles empty filter arrays', () => {
      const { result } = renderHook(() => useLibraryState())

      act(() => {
        result.current.setFilters({
          difficulty: [],
          tags: [],
          status: [],
          durationRange: [0, 100],
        })
      })

      expect(result.current.filters.difficulty).toEqual([])
      expect(result.current.filters.tags).toEqual([])
      expect(result.current.filters.status).toEqual([])
    })

    it('handles extreme duration ranges', () => {
      const { result } = renderHook(() => useLibraryState())

      act(() => {
        result.current.setFilters({
          ...result.current.filters,
          durationRange: [0, 999999],
        })
      })

      expect(result.current.filters.durationRange).toEqual([0, 999999])
    })

    it('handles whitespace in search query', () => {
      const { result } = renderHook(() => useLibraryState())

      act(() => {
        result.current.setSearchQuery('  test query  ')
      })

      expect(result.current.searchQuery).toBe('  test query  ')
    })

    it('handles rapid state changes', () => {
      const { result } = renderHook(() => useLibraryState())

      act(() => {
        for (let i = 0; i < 100; i++) {
          result.current.setSearchQuery(`query-${i}`)
        }
      })

      expect(result.current.searchQuery).toBe('query-99')
    })
  })

  describe('state isolation', () => {
    it('maintains independent state across multiple hook instances', () => {
      const { result: result1 } = renderHook(() => useLibraryState())
      const { result: result2 } = renderHook(() => useLibraryState())

      act(() => {
        result1.current.setSearchQuery('first instance')
        result2.current.setSearchQuery('second instance')
      })

      expect(result1.current.searchQuery).toBe('first instance')
      expect(result2.current.searchQuery).toBe('second instance')
    })

    it('does not share filter state between instances', () => {
      const { result: result1 } = renderHook(() => useLibraryState())
      const { result: result2 } = renderHook(() => useLibraryState())

      act(() => {
        result1.current.setFilters({
          ...result1.current.filters,
          tags: ['instance1'],
        })
        result2.current.setFilters({
          ...result2.current.filters,
          tags: ['instance2'],
        })
      })

      expect(result1.current.filters.tags).toEqual(['instance1'])
      expect(result2.current.filters.tags).toEqual(['instance2'])
    })
  })

  describe('type safety', () => {
    it('provides correctly typed setters', () => {
      const { result } = renderHook(() => useLibraryState())

      // Type checks - these should compile without errors
      expect(typeof result.current.setSearchQuery).toBe('function')
      expect(typeof result.current.setSearchMode).toBe('function')
      expect(typeof result.current.setShowCompletedOnly).toBe('function')
      expect(typeof result.current.setFilters).toBe('function')
    })

    it('returns valid filter structure', () => {
      const { result } = renderHook(() => useLibraryState())

      // Runtime validation of filter structure
      expect(Array.isArray(result.current.filters.difficulty)).toBe(true)
      expect(Array.isArray(result.current.filters.tags)).toBe(true)
      expect(Array.isArray(result.current.filters.status)).toBe(true)
      expect(Array.isArray(result.current.filters.durationRange)).toBe(true)
      expect(result.current.filters.durationRange).toHaveLength(2)
    })
  })
})
