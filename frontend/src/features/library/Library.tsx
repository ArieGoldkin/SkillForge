import { useTransition } from 'react'

import { LibraryContent } from './components/LibraryContent'
import { LibraryHeader } from './components/LibraryHeader'
import { useLibraryContentProps, useLibraryData, useLibraryFilters, useLibraryState } from './hooks'

const LIMIT = 15

/* eslint-disable max-lines-per-function -- React 19 transition wrappers add lines for UX improvement */
export default function Library() {
  // React 19: Use transition for non-blocking filter/search updates
  const [isPending, startTransition] = useTransition()

  const {
    searchQuery,
    setSearchQuery,
    searchMode,
    setSearchMode,
    showCompletedOnly,
    setShowCompletedOnly,
    filters,
    setFilters,
  } = useLibraryState()

  const libraryData = useLibraryData({
    searchQuery,
    searchMode,
    filters,
    showCompletedOnly,
    limit: LIMIT,
  })

  const { handleFiltersChange } = useLibraryFilters({
    showCompletedOnly,
    setShowCompletedOnly,
    setFilters,
  })

  // Wrap handlers in transitions for smooth UI
  const handleSearchQueryChange = (query: string) => {
    startTransition(() => {
      setSearchQuery(query)
    })
  }

  const handleSearchModeChange = (mode: typeof searchMode) => {
    startTransition(() => {
      setSearchMode(mode)
    })
  }

  const handleFiltersChangeTransition = (newFilters: typeof filters) => {
    startTransition(() => {
      handleFiltersChange(newFilters)
    })
  }

  const contentProps = useLibraryContentProps({
    searchQuery,
    setSearchQuery: handleSearchQueryChange,
    searchMode,
    setSearchMode: handleSearchModeChange,
    showCompletedOnly,
    setShowCompletedOnly,
    filters,
    handleFiltersChange: handleFiltersChangeTransition,
    libraryData,
  })

  return (
    <div className="container mx-auto px-4 py-8 max-w-7xl">
      <LibraryHeader />
      <LibraryContent {...contentProps} isPending={isPending} />
    </div>
  )
}
