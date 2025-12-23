import { LibraryContent } from './components/LibraryContent'
import { LibraryHeader } from './components/LibraryHeader'
import { useLibraryContentProps, useLibraryData, useLibraryFilters, useLibraryState } from './hooks'

const LIMIT = 15

export default function Library() {
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

  const contentProps = useLibraryContentProps({
    searchQuery,
    setSearchQuery,
    searchMode,
    setSearchMode,
    showCompletedOnly,
    setShowCompletedOnly,
    filters,
    handleFiltersChange,
    libraryData,
  })

  return (
    <div className="container mx-auto px-4 py-8 max-w-7xl">
      <LibraryHeader />
      <LibraryContent {...contentProps} />
    </div>
  )
}
