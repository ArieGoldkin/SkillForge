import { useCallback } from 'react'

import { COMPONENT_CONSTANTS } from '@/lib/constants'

import type { SkillFilters as SkillFiltersType } from '../components/SkillFilters'

interface UseLibraryFiltersParams {
  showCompletedOnly: boolean
  setShowCompletedOnly: (value: boolean) => void
  setFilters: (filters: SkillFiltersType | ((prev: SkillFiltersType) => SkillFiltersType)) => void
}

export function useLibraryFilters({
  showCompletedOnly,
  setShowCompletedOnly,
  setFilters,
}: UseLibraryFiltersParams) {
  const handleFiltersChange = useCallback(
    (next: SkillFiltersType) => {
      setFilters(next)
      if (next.status.length > 0 && showCompletedOnly) {
        setShowCompletedOnly(false)
      }
    },
    [setFilters, showCompletedOnly, setShowCompletedOnly]
  )

  return {
    handleFiltersChange,
  }
}

export function useInitialFilters(): SkillFiltersType {
  return {
    difficulty: [],
    tags: [],
    status: [],
    durationRange: [0, COMPONENT_CONSTANTS.SKILL_DURATION_FILTER_MAX],
  }
}
