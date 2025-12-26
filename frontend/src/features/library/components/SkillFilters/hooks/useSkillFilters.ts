/**
 * useSkillFilters - Custom hook for skill filter state management
 *
 * Manages filter state and provides handlers for updating filters.
 * Abstracts filter logic from UI components.
 */

import { useMemo, useOptimistic } from 'react'

import type { AnalysisStatus } from '@app-types/api'

import { COMPONENT_CONSTANTS } from '@/lib/constants'

import type { SkillDifficulty } from '../../SkillCard'

/**
 * Filter configuration
 */
export interface SkillFilters {
  difficulty: SkillDifficulty[]
  status: AnalysisStatus[]
  tags: string[]
  durationRange: [number, number]
}

/**
 * Filter change handlers
 */
export interface SkillFiltersHandlers {
  handleDifficultyChange: (difficulty: SkillDifficulty, checked: boolean) => void
  handleStatusChange: (status: AnalysisStatus, checked: boolean) => void
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
/* eslint-disable max-lines-per-function -- React 19 optimistic updates add handlers for UX improvement */
export const useSkillFilters = (
  filters: SkillFilters,
  onChange: (filters: SkillFilters) => void
): UseSkillFiltersReturn => {
  // React 19: Use optimistic updates for immediate UI feedback on filter changes
  const [optimisticFilters, setOptimisticFilters] = useOptimistic(
    filters,
    (_currentFilters, newFilters: SkillFilters) => newFilters
  )

  // Calculate active filter count
  const activeFilterCount = useMemo(
    () =>
      optimisticFilters.difficulty.length +
      optimisticFilters.status.length +
      optimisticFilters.tags.length +
      (optimisticFilters.durationRange[0] > 0 ||
      optimisticFilters.durationRange[1] < COMPONENT_CONSTANTS.SKILL_DURATION_FILTER_MAX
        ? 1
        : 0),
    [optimisticFilters]
  )

  // Difficulty change handler with optimistic update
  const handleDifficultyChange = (difficulty: SkillDifficulty, checked: boolean) => {
    const newDifficulties = checked
      ? [...optimisticFilters.difficulty, difficulty]
      : optimisticFilters.difficulty.filter((d) => d !== difficulty)

    const newFilters = { ...optimisticFilters, difficulty: newDifficulties }
    setOptimisticFilters(newFilters)
    onChange(newFilters)
  }

  // Status change handler with optimistic update
  const handleStatusChange = (status: AnalysisStatus, checked: boolean) => {
    // Treat status as radio: only one status at a time
    const newStatuses = checked ? [status] : []
    const newFilters = { ...optimisticFilters, status: newStatuses }
    setOptimisticFilters(newFilters)
    onChange(newFilters)
  }

  // Tag change handler with optimistic update
  const handleTagChange = (tag: string, checked: boolean) => {
    const newTags = checked
      ? [...optimisticFilters.tags, tag]
      : optimisticFilters.tags.filter((t) => t !== tag)

    const newFilters = { ...optimisticFilters, tags: newTags }
    setOptimisticFilters(newFilters)
    onChange(newFilters)
  }

  // Clear all filters with optimistic update
  const handleClearAll = () => {
    const newFilters: SkillFilters = {
      difficulty: [],
      status: [],
      tags: [],
      durationRange: [0, COMPONENT_CONSTANTS.SKILL_DURATION_FILTER_MAX],
    }

    setOptimisticFilters(newFilters)
    onChange(newFilters)
  }

  return {
    filters: optimisticFilters,
    handlers: {
      handleDifficultyChange,
      handleStatusChange,
      handleTagChange,
      handleClearAll,
    },
    activeFilterCount,
  }
}
