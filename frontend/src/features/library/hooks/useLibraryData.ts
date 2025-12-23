import type { SearchMode } from '@app-types/api'

import type { SkillFilters as SkillFiltersType } from '../components/SkillFilters'
import { mapFiltersToQuery } from '../utils'

import { useFilteredSkills } from './useFilteredSkills'
import { useLibraryResultCount } from './useLibraryResultCount'
import { useLibrarySearchInfinite } from './useLibrarySearch'
import { useLibrarySkills } from './useLibrarySkills'

interface UseLibraryDataParams {
  searchQuery: string
  searchMode: SearchMode
  filters: SkillFiltersType
  showCompletedOnly: boolean
  limit: number
}

export function useLibraryData({
  searchQuery,
  searchMode,
  filters,
  showCompletedOnly,
  limit,
}: UseLibraryDataParams) {
  // Use server-side infinite search API
  const {
    data: searchResults,
    isLoading,
    isFetching,
    fetchNextPage,
    hasNextPage,
    isFetchingNextPage,
    error: searchError,
    isError,
    refetch,
  } = useLibrarySearchInfinite({
    query: searchQuery || undefined,
    search_mode: searchMode,
    ...mapFiltersToQuery(filters, showCompletedOnly),
    limit,
  })

  // Transform search results into skills format
  const { skills, availableTags, availableStatuses } = useLibrarySkills({ searchResults })

  // Apply client-side filters for difficulty/tags (server doesn't support these yet)
  const filteredSkills = useFilteredSkills(skills, '', filters)

  const { showingCount, totalCount } = useLibraryResultCount({
    filteredSkillsCount: filteredSkills.length,
    searchQuery,
    searchResults,
  })

  return {
    filteredSkills,
    availableTags,
    availableStatuses,
    showingCount,
    totalCount,
    isLoading,
    isFetching,
    fetchNextPage,
    hasNextPage,
    isFetchingNextPage,
    searchError,
    isError,
    refetch,
    searchResults,
  }
}
