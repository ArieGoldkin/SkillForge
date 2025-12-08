import { act, renderHook } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'

import { useSkillFilters, type SkillFilters } from '../useSkillFilters'

const createEmptyFilters = (): SkillFilters => ({
  difficulty: [],
  status: [],
  tags: [],
  durationRange: [0, 1000],
})

describe('useSkillFilters', () => {
  it('calculates active filter count correctly', () => {
    const filters: SkillFilters = {
      difficulty: ['beginner', 'intermediate'],
      status: ['complete'],
      tags: ['React'],
      durationRange: [0, 1000],
    }
    const { result } = renderHook(() => useSkillFilters(filters, vi.fn()))

    expect(result.current.activeFilterCount).toBe(4)
  })

  it('handles difficulty change', () => {
    const onChange = vi.fn()
    const { result } = renderHook(() => useSkillFilters(createEmptyFilters(), onChange))

    act(() => {
      result.current.handlers.handleDifficultyChange('beginner', true)
    })

    expect(onChange).toHaveBeenCalledWith(expect.objectContaining({ difficulty: ['beginner'] }))
  })

  it('clears all filters', () => {
    const filters: SkillFilters = {
      difficulty: ['beginner'],
      status: ['completed'],
      tags: ['React'],
      durationRange: [10, 100],
    }
    const onChange = vi.fn()
    const { result } = renderHook(() => useSkillFilters(filters, onChange))

    act(() => {
      result.current.handlers.handleClearAll()
    })

    expect(onChange).toHaveBeenCalledWith(createEmptyFilters())
  })
})
