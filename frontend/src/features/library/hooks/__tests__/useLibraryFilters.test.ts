/**
 * Tests for useLibraryFilters - Library filter state management
 *
 * Validates filter change handling, showCompletedOnly coordination,
 * and initial filter state generation.
 */

import { renderHook, act } from '@testing-library/react'
import { describe, it, expect, vi } from 'vitest'

import type { SkillFilters } from '@/features/library/components/SkillFilters'
import { COMPONENT_CONSTANTS } from '@/lib/constants'

import { useLibraryFilters, useInitialFilters } from '../useLibraryFilters'

describe('useLibraryFilters', () => {
  describe('handleFiltersChange', () => {
    it('calls setFilters with new filter values', () => {
      const setFilters = vi.fn()
      const setShowCompletedOnly = vi.fn()

      const { result } = renderHook(() =>
        useLibraryFilters({
          showCompletedOnly: false,
          setShowCompletedOnly,
          setFilters,
        })
      )

      const newFilters: SkillFilters = {
        difficulty: ['beginner'],
        tags: ['react'],
        status: [],
        durationRange: [0, 100],
      }

      act(() => {
        result.current.handleFiltersChange(newFilters)
      })

      expect(setFilters).toHaveBeenCalledWith(newFilters)
      expect(setFilters).toHaveBeenCalledTimes(1)
    })

    it('disables showCompletedOnly when status filters are applied', () => {
      const setFilters = vi.fn()
      const setShowCompletedOnly = vi.fn()

      const { result } = renderHook(() =>
        useLibraryFilters({
          showCompletedOnly: true,
          setShowCompletedOnly,
          setFilters,
        })
      )

      const newFilters: SkillFilters = {
        difficulty: [],
        tags: [],
        status: ['in_progress'],
        durationRange: [0, 100],
      }

      act(() => {
        result.current.handleFiltersChange(newFilters)
      })

      expect(setShowCompletedOnly).toHaveBeenCalledWith(false)
    })

    it('does not disable showCompletedOnly if it was already false', () => {
      const setFilters = vi.fn()
      const setShowCompletedOnly = vi.fn()

      const { result } = renderHook(() =>
        useLibraryFilters({
          showCompletedOnly: false,
          setShowCompletedOnly,
          setFilters,
        })
      )

      const newFilters: SkillFilters = {
        difficulty: [],
        tags: [],
        status: ['in_progress'],
        durationRange: [0, 100],
      }

      act(() => {
        result.current.handleFiltersChange(newFilters)
      })

      // Should not call setShowCompletedOnly if already false
      expect(setShowCompletedOnly).not.toHaveBeenCalled()
    })

    it('does not disable showCompletedOnly when status is empty', () => {
      const setFilters = vi.fn()
      const setShowCompletedOnly = vi.fn()

      const { result } = renderHook(() =>
        useLibraryFilters({
          showCompletedOnly: true,
          setShowCompletedOnly,
          setFilters,
        })
      )

      const newFilters: SkillFilters = {
        difficulty: ['intermediate'],
        tags: ['typescript'],
        status: [],
        durationRange: [0, 100],
      }

      act(() => {
        result.current.handleFiltersChange(newFilters)
      })

      expect(setShowCompletedOnly).not.toHaveBeenCalled()
    })

    it('handles multiple status values', () => {
      const setFilters = vi.fn()
      const setShowCompletedOnly = vi.fn()

      const { result } = renderHook(() =>
        useLibraryFilters({
          showCompletedOnly: true,
          setShowCompletedOnly,
          setFilters,
        })
      )

      const newFilters: SkillFilters = {
        difficulty: [],
        tags: [],
        status: ['in_progress', 'completed'],
        durationRange: [0, 100],
      }

      act(() => {
        result.current.handleFiltersChange(newFilters)
      })

      expect(setShowCompletedOnly).toHaveBeenCalledWith(false)
    })

    it('memoizes callback correctly', () => {
      const setFilters = vi.fn()
      const setShowCompletedOnly = vi.fn()

      const { result, rerender } = renderHook(
        ({ showCompletedOnly }) =>
          useLibraryFilters({
            showCompletedOnly,
            setShowCompletedOnly,
            setFilters,
          }),
        { initialProps: { showCompletedOnly: false } }
      )

      const firstCallback = result.current.handleFiltersChange

      // Rerender with same props
      rerender({ showCompletedOnly: false })

      // Should be same reference
      expect(result.current.handleFiltersChange).toBe(firstCallback)
    })

    it('updates callback when dependencies change', () => {
      const setFilters = vi.fn()
      const setShowCompletedOnly = vi.fn()

      const { result, rerender } = renderHook(
        ({ showCompletedOnly }) =>
          useLibraryFilters({
            showCompletedOnly,
            setShowCompletedOnly,
            setFilters,
          }),
        { initialProps: { showCompletedOnly: false } }
      )

      const firstCallback = result.current.handleFiltersChange

      // Rerender with different showCompletedOnly
      rerender({ showCompletedOnly: true })

      // Should be different reference
      expect(result.current.handleFiltersChange).not.toBe(firstCallback)
    })
  })

  describe('complex filter scenarios', () => {
    it('handles all filters applied together', () => {
      const setFilters = vi.fn()
      const setShowCompletedOnly = vi.fn()

      const { result } = renderHook(() =>
        useLibraryFilters({
          showCompletedOnly: true,
          setShowCompletedOnly,
          setFilters,
        })
      )

      const complexFilters: SkillFilters = {
        difficulty: ['beginner', 'intermediate'],
        tags: ['react', 'typescript', 'testing'],
        status: ['in_progress'],
        durationRange: [30, 120],
      }

      act(() => {
        result.current.handleFiltersChange(complexFilters)
      })

      expect(setFilters).toHaveBeenCalledWith(complexFilters)
      expect(setShowCompletedOnly).toHaveBeenCalledWith(false)
    })

    it('handles clearing all filters', () => {
      const setFilters = vi.fn()
      const setShowCompletedOnly = vi.fn()

      const { result } = renderHook(() =>
        useLibraryFilters({
          showCompletedOnly: false,
          setShowCompletedOnly,
          setFilters,
        })
      )

      const emptyFilters: SkillFilters = {
        difficulty: [],
        tags: [],
        status: [],
        durationRange: [0, COMPONENT_CONSTANTS.SKILL_DURATION_FILTER_MAX],
      }

      act(() => {
        result.current.handleFiltersChange(emptyFilters)
      })

      expect(setFilters).toHaveBeenCalledWith(emptyFilters)
      expect(setShowCompletedOnly).not.toHaveBeenCalled()
    })

    it('handles partial filter updates', () => {
      const setFilters = vi.fn()
      const setShowCompletedOnly = vi.fn()

      const { result } = renderHook(() =>
        useLibraryFilters({
          showCompletedOnly: false,
          setShowCompletedOnly,
          setFilters,
        })
      )

      // Only difficulty filter applied
      const partialFilters: SkillFilters = {
        difficulty: ['advanced'],
        tags: [],
        status: [],
        durationRange: [0, 100],
      }

      act(() => {
        result.current.handleFiltersChange(partialFilters)
      })

      expect(setFilters).toHaveBeenCalledWith(partialFilters)
    })
  })

  describe('edge cases', () => {
    it('handles undefined filter arrays gracefully', () => {
      const setFilters = vi.fn()
      const setShowCompletedOnly = vi.fn()

      const { result } = renderHook(() =>
        useLibraryFilters({
          showCompletedOnly: true,
          setShowCompletedOnly,
          setFilters,
        })
      )

      const filtersWithEmptyArrays: SkillFilters = {
        difficulty: [],
        tags: [],
        status: [],
        durationRange: [0, 100],
      }

      act(() => {
        result.current.handleFiltersChange(filtersWithEmptyArrays)
      })

      expect(setFilters).toHaveBeenCalledWith(filtersWithEmptyArrays)
      expect(setShowCompletedOnly).not.toHaveBeenCalled()
    })

    it('handles extreme duration ranges', () => {
      const setFilters = vi.fn()
      const setShowCompletedOnly = vi.fn()

      const { result } = renderHook(() =>
        useLibraryFilters({
          showCompletedOnly: false,
          setShowCompletedOnly,
          setFilters,
        })
      )

      const extremeDurationFilters: SkillFilters = {
        difficulty: [],
        tags: [],
        status: [],
        durationRange: [0, 999999],
      }

      act(() => {
        result.current.handleFiltersChange(extremeDurationFilters)
      })

      expect(setFilters).toHaveBeenCalledWith(extremeDurationFilters)
    })

    it('handles rapid filter changes', () => {
      const setFilters = vi.fn()
      const setShowCompletedOnly = vi.fn()

      const { result } = renderHook(() =>
        useLibraryFilters({
          showCompletedOnly: false,
          setShowCompletedOnly,
          setFilters,
        })
      )

      const filters1: SkillFilters = {
        difficulty: ['beginner'],
        tags: [],
        status: [],
        durationRange: [0, 100],
      }

      const filters2: SkillFilters = {
        difficulty: ['beginner', 'intermediate'],
        tags: ['react'],
        status: [],
        durationRange: [0, 100],
      }

      const filters3: SkillFilters = {
        difficulty: [],
        tags: [],
        status: ['completed'],
        durationRange: [0, 100],
      }

      act(() => {
        result.current.handleFiltersChange(filters1)
        result.current.handleFiltersChange(filters2)
        result.current.handleFiltersChange(filters3)
      })

      expect(setFilters).toHaveBeenCalledTimes(3)
      expect(setFilters).toHaveBeenNthCalledWith(1, filters1)
      expect(setFilters).toHaveBeenNthCalledWith(2, filters2)
      expect(setFilters).toHaveBeenNthCalledWith(3, filters3)
    })
  })
})

describe('useInitialFilters', () => {
  it('returns initial filter state with empty arrays', () => {
    const { result } = renderHook(() => useInitialFilters())

    expect(result.current.difficulty).toEqual([])
    expect(result.current.tags).toEqual([])
    expect(result.current.status).toEqual([])
  })

  it('returns correct default duration range', () => {
    const { result } = renderHook(() => useInitialFilters())

    expect(result.current.durationRange).toEqual([0, COMPONENT_CONSTANTS.SKILL_DURATION_FILTER_MAX])
  })

  it('returns same structure on multiple calls', () => {
    const { result: result1 } = renderHook(() => useInitialFilters())
    const { result: result2 } = renderHook(() => useInitialFilters())

    expect(result1.current).toEqual(result2.current)
  })

  it('returns a new object reference each time', () => {
    const { result, rerender } = renderHook(() => useInitialFilters())

    const firstResult = result.current

    rerender()

    const secondResult = result.current

    // Should be equal in value but different references
    expect(firstResult).toEqual(secondResult)
    expect(firstResult).not.toBe(secondResult)
  })

  it('uses correct constant for max duration', () => {
    const { result } = renderHook(() => useInitialFilters())

    const maxDuration = result.current.durationRange[1]
    expect(maxDuration).toBe(COMPONENT_CONSTANTS.SKILL_DURATION_FILTER_MAX)
    expect(typeof maxDuration).toBe('number')
  })

  it('returns valid SkillFilters type', () => {
    const { result } = renderHook(() => useInitialFilters())

    // Type checking (runtime validation)
    expect(Array.isArray(result.current.difficulty)).toBe(true)
    expect(Array.isArray(result.current.tags)).toBe(true)
    expect(Array.isArray(result.current.status)).toBe(true)
    expect(Array.isArray(result.current.durationRange)).toBe(true)
    expect(result.current.durationRange).toHaveLength(2)
  })
})
