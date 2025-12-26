import type { FilterStatus, SearchMode } from '@app-types/api'

import { LibraryContentMain } from './LibraryContentMain'
import { LibraryErrorAlert } from './LibraryErrorAlert'
import { LibrarySearchHeader } from './LibrarySearchHeader'
import type { SkillFilters as SkillFiltersType } from './SkillFilters'

interface LibraryContentProps {
  searchQuery: string
  onSearchQueryChange: (query: string) => void
  searchMode: SearchMode
  onSearchModeChange: (mode: SearchMode) => void
  showCompletedOnly: boolean
  onShowCompletedOnlyChange: (value: boolean) => void
  filters: SkillFiltersType
  onFiltersChange: (filters: SkillFiltersType) => void
  availableTags: string[]
  availableStatuses: FilterStatus[]
  filteredSkills: Parameters<typeof LibraryContentMain>[0]['filteredSkills']
  showingCount: number
  totalCount: number
  searchResults?: { pages?: Array<{ total?: number }> }
  isLoading: boolean
  isFetching: boolean
  hasNextPage: boolean
  isFetchingNextPage: boolean
  isError: boolean
  searchError: Error | null
  onRetry: () => void
  onSelectSkill: (id: string) => void
  onLoadMore?: () => void
  isPending?: boolean
}

export function LibraryContent(props: LibraryContentProps) {
  const resultCount = props.searchResults
    ? {
        showing: props.showingCount,
        total: props.totalCount,
        hasQuery: Boolean(props.searchQuery.trim()),
      }
    : undefined

  return (
    <>
      <LibrarySearchHeader
        searchQuery={props.searchQuery}
        onSearchQueryChange={props.onSearchQueryChange}
        searchMode={props.searchMode}
        onSearchModeChange={props.onSearchModeChange}
        showCompletedOnly={props.showCompletedOnly}
        onShowCompletedOnlyChange={props.onShowCompletedOnlyChange}
        resultCount={resultCount}
      />

      {props.isError && (
        <LibraryErrorAlert
          error={props.searchError}
          onRetry={props.onRetry}
          isRetrying={props.isFetching}
        />
      )}

      <LibraryContentMain
        filters={props.filters}
        onFiltersChange={props.onFiltersChange}
        availableTags={props.availableTags}
        availableStatuses={props.availableStatuses}
        filteredSkills={props.filteredSkills}
        isLoading={props.isLoading}
        isFetching={props.isFetching}
        hasNextPage={props.hasNextPage}
        isFetchingNextPage={props.isFetchingNextPage}
        onSelectSkill={props.onSelectSkill}
        onLoadMore={props.onLoadMore}
        isPending={props.isPending}
      />
    </>
  )
}
