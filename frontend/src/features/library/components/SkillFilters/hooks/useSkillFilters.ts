/**
 * useSkillFilters - Custom hook for skill filter state management
 *
 * Manages filter state and provides handlers for updating filters.
 * Abstracts filter logic from UI components.
 */

import { useMemo } from 'react'

import type { SkillDifficulty, SkillStatus } from '../../SkillCard'

/**
 * Filter configuration
 */
export interface SkillFilters {
  difficulty: SkillDifficulty[]
  status: SkillStatus[]
  tags: string[]
  durationRange: [number, number]
}

/**
 * Filter change handlers
 */
export interface SkillFiltersHandlers {
  handleDifficultyChange: (difficulty: SkillDifficulty, checked: boolean) => void
  handleStatusChange: (status: SkillStatus, checked: boolean) => void
  handleTagChange: (tag: string, checked: boolean) => void
  handleClearAll: () => void
}

/**
 * Hook return value
 */
export interface UseSkillFiltersReturn {
  filters: SkillFilters
  handlers: SkillFiltersHandlers
  activeFilterCount: number
}

/**
 * Custom hook for managing skill filters
 *
 * @param filters - Current filter state
 * @param onChange - Callback when filters change
 * @returns Filter state, handlers, and active count
 */
export const useSkillFilters = (
  filters: SkillFilters,
  onChange: (filters: SkillFilters) => void
): UseSkillFiltersReturn => {
  // Calculate active filter count
  const activeFilterCount = useMemo(
    () =>
      filters.difficulty.length +
      filters.status.length +
      filters.tags.length +
      (filters.durationRange[0] > 0 || filters.durationRange[1] < 1000 ? 1 : 0),
    [filters]
  )

  // Difficulty change handler
  const handleDifficultyChange = (difficulty: SkillDifficulty, checked: boolean) => {
    const newDifficulties = checked
      ? [...filters.difficulty, difficulty]
      : filters.difficulty.filter((d) => d !== difficulty)

    onChange({ ...filters, difficulty: newDifficulties })
  }

  // Status change handler
  const handleStatusChange = (status: SkillStatus, checked: boolean) => {
    // Backend supports a single status; treat as radio (one selection)
    const newStatuses = checked ? [status] : []
    onChange({ ...filters, status: newStatuses })
  }

  // Tag change handler
  const handleTagChange = (tag: string, checked: boolean) => {
    const newTags = checked ? [...filters.tags, tag] : filters.tags.filter((t) => t !== tag)

    onChange({ ...filters, tags: newTags })
  }

  // Clear all filters
  const handleClearAll = () => {
    onChange({
      difficulty: [],
      status: [],
      tags: [],
      durationRange: [0, 1000],
    })
  }

  return {
    filters,
    handlers: {
      handleDifficultyChange,
      handleStatusChange,
      handleTagChange,
      handleClearAll,
    },
    activeFilterCount,
  }
}
