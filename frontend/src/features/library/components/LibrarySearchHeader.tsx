import type { SearchMode } from '@app-types/api'

import { SearchModeToggle } from './SearchModeToggle'
import { SkillSearch } from './SkillSearch'

interface LibrarySearchHeaderProps {
  searchQuery: string
  onSearchQueryChange: (query: string) => void
  searchMode: SearchMode
  onSearchModeChange: (mode: SearchMode) => void
  showCompletedOnly: boolean
  onShowCompletedOnlyChange: (value: boolean) => void
  resultCount?: {
    showing: number
    total?: number
    hasQuery: boolean
  }
}

export function LibrarySearchHeader({
  onSearchQueryChange,
  searchMode,
  onSearchModeChange,
  showCompletedOnly,
  onShowCompletedOnlyChange,
  resultCount,
}: LibrarySearchHeaderProps) {
  return (
    <>
      {/* Search input */}
      <div className="mb-4">
        <SkillSearch onSearch={onSearchQueryChange} placeholder="Search analyses..." />
      </div>

      {/* Search mode toggle */}
      <SearchModeToggle
        searchMode={searchMode}
        onSearchModeChange={onSearchModeChange}
        showCompletedOnly={showCompletedOnly}
        onShowCompletedOnlyChange={onShowCompletedOnlyChange}
        resultCount={resultCount}
      />
    </>
  )
}
