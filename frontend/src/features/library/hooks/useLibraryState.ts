import { useState } from 'react'

import type { SearchMode } from '@app-types/api'

import type { SkillFilters as SkillFiltersType } from '../components/SkillFilters'

import { useInitialFilters } from './useLibraryFilters'

export function useLibraryState() {
  const [searchQuery, setSearchQuery] = useState('')
  const [searchMode, setSearchMode] = useState<SearchMode>('hybrid')
  const [showCompletedOnly, setShowCompletedOnly] = useState(true)
  const [filters, setFilters] = useState<SkillFiltersType>(useInitialFilters)

  return {
    searchQuery,
    setSearchQuery,
    searchMode,
    setSearchMode,
    showCompletedOnly,
    setShowCompletedOnly,
    filters,
    setFilters,
  }
}
