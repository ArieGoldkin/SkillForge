import type { SearchMode } from '@app-types/api'
import { useNavigate } from '@tanstack/react-router'

import type { SkillFilters as SkillFiltersType } from '../components/SkillFilters'

import type { useLibraryData } from './useLibraryData'

interface UseLibraryContentPropsParams {
  searchQuery: string
  setSearchQuery: (query: string) => void
  searchMode: SearchMode
  setSearchMode: (mode: SearchMode) => void
  showCompletedOnly: boolean
  setShowCompletedOnly: (value: boolean) => void
  filters: SkillFiltersType
  handleFiltersChange: (filters: SkillFiltersType) => void
  libraryData: ReturnType<typeof useLibraryData>
}

export function useLibraryContentProps({
  searchQuery,
  setSearchQuery,
  searchMode,
  setSearchMode,
  showCompletedOnly,
  setShowCompletedOnly,
  filters,
  handleFiltersChange,
  libraryData,
}: UseLibraryContentPropsParams) {
  const navigate = useNavigate()

  const handleSelectSkill = (id: string) => {
    navigate({ to: '/analyze/$id', params: { id } })
  }

  return {
    searchQuery,
    onSearchQueryChange: setSearchQuery,
    searchMode,
    onSearchModeChange: setSearchMode,
    showCompletedOnly,
    onShowCompletedOnlyChange: setShowCompletedOnly,
    filters,
    onFiltersChange: handleFiltersChange,
    availableTags: libraryData.availableTags,
    availableStatuses: libraryData.availableStatuses,
    filteredSkills: libraryData.filteredSkills,
    showingCount: libraryData.showingCount,
    totalCount: libraryData.totalCount,
    searchResults: libraryData.searchResults,
    isLoading: libraryData.isLoading,
    isFetching: libraryData.isFetching,
    hasNextPage: libraryData.hasNextPage ?? false,
    isFetchingNextPage: libraryData.isFetchingNextPage,
    isError: libraryData.isError,
    searchError: libraryData.searchError,
    onRetry: libraryData.refetch,
    onSelectSkill: handleSelectSkill,
    onLoadMore: libraryData.hasNextPage ? libraryData.fetchNextPage : undefined,
  }
}
