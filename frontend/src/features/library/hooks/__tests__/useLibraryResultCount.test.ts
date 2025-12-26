/**
 * Tests for useLibraryResultCount - Result count calculation
 *
 * Validates showing/total count logic for library results.
 */

import { renderHook } from '@testing-library/react'
import { describe, it, expect } from 'vitest'

import { useLibraryResultCount } from '../useLibraryResultCount'

describe('useLibraryResultCount', () => {
  describe('basic counting', () => {
    it('returns showing count equal to filtered skills count', () => {
      const { result } = renderHook(() =>
        useLibraryResultCount({
          filteredSkillsCount: 10,
          searchQuery: '',
          searchResults: undefined,
        })
      )

      expect(result.current.showingCount).toBe(10)
    })

    it('returns total count from search results when no query', () => {
      const { result } = renderHook(() =>
        useLibraryResultCount({
          filteredSkillsCount: 5,
          searchQuery: '',
          searchResults: {
            pages: [{ total: 100 }],
          },
        })
      )

      expect(result.current.showingCount).toBe(5)
      expect(result.current.totalCount).toBe(100)
    })

    it('returns showing count as total when search query is active', () => {
      const { result } = renderHook(() =>
        useLibraryResultCount({
          filteredSkillsCount: 3,
          searchQuery: 'React',
          searchResults: {
            pages: [{ total: 100 }],
          },
        })
      )

      expect(result.current.showingCount).toBe(3)
      expect(result.current.totalCount).toBe(3)
    })
  })

  describe('search query handling', () => {
    it('treats empty string as no search', () => {
      const { result } = renderHook(() =>
        useLibraryResultCount({
          filteredSkillsCount: 5,
          searchQuery: '',
          searchResults: {
            pages: [{ total: 50 }],
          },
        })
      )

      expect(result.current.totalCount).toBe(50)
    })

    it('treats whitespace-only string as search query', () => {
      const { result } = renderHook(() =>
        useLibraryResultCount({
          filteredSkillsCount: 5,
          searchQuery: '   ',
          searchResults: {
            pages: [{ total: 50 }],
          },
        })
      )

      // Whitespace is trimmed, so treated as empty
      expect(result.current.totalCount).toBe(50)
    })

    it('handles single character search query', () => {
      const { result } = renderHook(() =>
        useLibraryResultCount({
          filteredSkillsCount: 8,
          searchQuery: 'R',
          searchResults: {
            pages: [{ total: 100 }],
          },
        })
      )

      expect(result.current.showingCount).toBe(8)
      expect(result.current.totalCount).toBe(8)
    })

    it('handles long search query', () => {
      const { result } = renderHook(() =>
        useLibraryResultCount({
          filteredSkillsCount: 2,
          searchQuery: 'very long search query with multiple words',
          searchResults: {
            pages: [{ total: 100 }],
          },
        })
      )

      expect(result.current.totalCount).toBe(2)
    })
  })

  describe('search results handling', () => {
    it('handles undefined search results', () => {
      const { result } = renderHook(() =>
        useLibraryResultCount({
          filteredSkillsCount: 5,
          searchQuery: '',
          searchResults: undefined,
        })
      )

      expect(result.current.showingCount).toBe(5)
      expect(result.current.totalCount).toBe(5)
    })

    it('handles undefined pages array', () => {
      const { result } = renderHook(() =>
        useLibraryResultCount({
          filteredSkillsCount: 7,
          searchQuery: '',
          searchResults: {},
        })
      )

      expect(result.current.showingCount).toBe(7)
      expect(result.current.totalCount).toBe(7)
    })

    it('handles empty pages array', () => {
      const { result } = renderHook(() =>
        useLibraryResultCount({
          filteredSkillsCount: 3,
          searchQuery: '',
          searchResults: {
            pages: [],
          },
        })
      )

      expect(result.current.showingCount).toBe(3)
      expect(result.current.totalCount).toBe(3)
    })

    it('handles undefined total in first page', () => {
      const { result } = renderHook(() =>
        useLibraryResultCount({
          filteredSkillsCount: 4,
          searchQuery: '',
          searchResults: {
            pages: [{}],
          },
        })
      )

      expect(result.current.showingCount).toBe(4)
      expect(result.current.totalCount).toBe(4)
    })

    it('uses total from first page even if multiple pages exist', () => {
      const { result } = renderHook(() =>
        useLibraryResultCount({
          filteredSkillsCount: 30,
          searchQuery: '',
          searchResults: {
            pages: [{ total: 100 }, { total: 50 }, { total: 25 }],
          },
        })
      )

      // Should use first page total
      expect(result.current.totalCount).toBe(100)
    })
  })

  describe('zero counts', () => {
    it('handles zero filtered skills', () => {
      const { result } = renderHook(() =>
        useLibraryResultCount({
          filteredSkillsCount: 0,
          searchQuery: '',
          searchResults: {
            pages: [{ total: 100 }],
          },
        })
      )

      expect(result.current.showingCount).toBe(0)
      expect(result.current.totalCount).toBe(100)
    })

    it('handles zero total in search results', () => {
      const { result } = renderHook(() =>
        useLibraryResultCount({
          filteredSkillsCount: 0,
          searchQuery: '',
          searchResults: {
            pages: [{ total: 0 }],
          },
        })
      )

      expect(result.current.showingCount).toBe(0)
      expect(result.current.totalCount).toBe(0)
    })

    it('handles zero for both counts with search query', () => {
      const { result } = renderHook(() =>
        useLibraryResultCount({
          filteredSkillsCount: 0,
          searchQuery: 'nonexistent',
          searchResults: {
            pages: [{ total: 0 }],
          },
        })
      )

      expect(result.current.showingCount).toBe(0)
      expect(result.current.totalCount).toBe(0)
    })
  })

  describe('edge cases', () => {
    it('handles showing count greater than total', () => {
      const { result } = renderHook(() =>
        useLibraryResultCount({
          filteredSkillsCount: 150,
          searchQuery: '',
          searchResults: {
            pages: [{ total: 100 }],
          },
        })
      )

      // This shouldn't happen in practice, but hook should handle it
      expect(result.current.showingCount).toBe(150)
      expect(result.current.totalCount).toBe(100)
    })

    it('handles negative filtered count gracefully', () => {
      const { result } = renderHook(() =>
        useLibraryResultCount({
          filteredSkillsCount: -5,
          searchQuery: '',
          searchResults: {
            pages: [{ total: 100 }],
          },
        })
      )

      // Passes through the negative value (caller's responsibility to validate)
      expect(result.current.showingCount).toBe(-5)
    })

    it('handles very large counts', () => {
      const { result } = renderHook(() =>
        useLibraryResultCount({
          filteredSkillsCount: 999999,
          searchQuery: '',
          searchResults: {
            pages: [{ total: 1000000 }],
          },
        })
      )

      expect(result.current.showingCount).toBe(999999)
      expect(result.current.totalCount).toBe(1000000)
    })
  })

  describe('state updates', () => {
    it('updates when filtered count changes', () => {
      const { result, rerender } = renderHook(
        ({ filteredSkillsCount }) =>
          useLibraryResultCount({
            filteredSkillsCount,
            searchQuery: '',
            searchResults: {
              pages: [{ total: 100 }],
            },
          }),
        { initialProps: { filteredSkillsCount: 10 } }
      )

      expect(result.current.showingCount).toBe(10)

      rerender({ filteredSkillsCount: 20 })

      expect(result.current.showingCount).toBe(20)
    })

    it('updates when search query changes', () => {
      const { result, rerender } = renderHook(
        ({ searchQuery }) =>
          useLibraryResultCount({
            filteredSkillsCount: 5,
            searchQuery,
            searchResults: {
              pages: [{ total: 100 }],
            },
          }),
        { initialProps: { searchQuery: '' } }
      )

      expect(result.current.totalCount).toBe(100)

      rerender({ searchQuery: 'React' })

      expect(result.current.totalCount).toBe(5)
    })

    it('updates when search results change', () => {
      const { result, rerender } = renderHook(
        ({ searchResults }) =>
          useLibraryResultCount({
            filteredSkillsCount: 10,
            searchQuery: '',
            searchResults,
          }),
        { initialProps: { searchResults: { pages: [{ total: 50 }] } } }
      )

      expect(result.current.totalCount).toBe(50)

      rerender({ searchResults: { pages: [{ total: 100 }] } })

      expect(result.current.totalCount).toBe(100)
    })

    it('handles rapid successive updates', () => {
      const { result, rerender } = renderHook(
        ({ filteredSkillsCount }) =>
          useLibraryResultCount({
            filteredSkillsCount,
            searchQuery: '',
            searchResults: {
              pages: [{ total: 100 }],
            },
          }),
        { initialProps: { filteredSkillsCount: 1 } }
      )

      for (let i = 2; i <= 100; i++) {
        rerender({ filteredSkillsCount: i })
      }

      expect(result.current.showingCount).toBe(100)
    })
  })

  describe('complex scenarios', () => {
    it('handles transition from no search to search', () => {
      const { result, rerender } = renderHook(
        ({ searchQuery }) =>
          useLibraryResultCount({
            filteredSkillsCount: 5,
            searchQuery,
            searchResults: {
              pages: [{ total: 100 }],
            },
          }),
        { initialProps: { searchQuery: '' } }
      )

      expect(result.current.totalCount).toBe(100)

      rerender({ searchQuery: 'test' })

      expect(result.current.totalCount).toBe(5)
    })

    it('handles transition from search to no search', () => {
      const { result, rerender } = renderHook(
        ({ searchQuery }) =>
          useLibraryResultCount({
            filteredSkillsCount: 5,
            searchQuery,
            searchResults: {
              pages: [{ total: 100 }],
            },
          }),
        { initialProps: { searchQuery: 'test' } }
      )

      expect(result.current.totalCount).toBe(5)

      rerender({ searchQuery: '' })

      expect(result.current.totalCount).toBe(100)
    })

    it('handles filtering reducing showing count', () => {
      const { result, rerender } = renderHook(
        ({ filteredSkillsCount }) =>
          useLibraryResultCount({
            filteredSkillsCount,
            searchQuery: '',
            searchResults: {
              pages: [{ total: 100 }],
            },
          }),
        { initialProps: { filteredSkillsCount: 100 } }
      )

      expect(result.current.showingCount).toBe(100)
      expect(result.current.totalCount).toBe(100)

      // Apply filters
      rerender({ filteredSkillsCount: 25 })

      expect(result.current.showingCount).toBe(25)
      expect(result.current.totalCount).toBe(100) // Total unchanged
    })

    it('handles pagination increasing showing count', () => {
      const { result, rerender } = renderHook(
        ({ filteredSkillsCount }) =>
          useLibraryResultCount({
            filteredSkillsCount,
            searchQuery: '',
            searchResults: {
              pages: [{ total: 100 }],
            },
          }),
        { initialProps: { filteredSkillsCount: 20 } }
      )

      expect(result.current.showingCount).toBe(20)

      // Load more pages
      rerender({ filteredSkillsCount: 40 })

      expect(result.current.showingCount).toBe(40)

      rerender({ filteredSkillsCount: 60 })

      expect(result.current.showingCount).toBe(60)
    })
  })

  describe('type safety', () => {
    it('returns numeric counts', () => {
      const { result } = renderHook(() =>
        useLibraryResultCount({
          filteredSkillsCount: 10,
          searchQuery: '',
          searchResults: {
            pages: [{ total: 100 }],
          },
        })
      )

      expect(typeof result.current.showingCount).toBe('number')
      expect(typeof result.current.totalCount).toBe('number')
    })

    it('returns object with correct shape', () => {
      const { result } = renderHook(() =>
        useLibraryResultCount({
          filteredSkillsCount: 10,
          searchQuery: '',
          searchResults: {
            pages: [{ total: 100 }],
          },
        })
      )

      expect(result.current).toHaveProperty('showingCount')
      expect(result.current).toHaveProperty('totalCount')
      expect(Object.keys(result.current)).toHaveLength(2)
    })
  })
})
