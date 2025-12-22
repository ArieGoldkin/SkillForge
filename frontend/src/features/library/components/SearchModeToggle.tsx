import type { SearchMode } from '@app-types/api'

import { Tabs, TabsList, TabsTrigger } from '@shared/components/ui/tabs'

interface SearchModeToggleProps {
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

export function SearchModeToggle({
  searchMode,
  onSearchModeChange,
  showCompletedOnly,
  onShowCompletedOnlyChange,
  resultCount,
}: SearchModeToggleProps) {
  return (
    <div className="mb-6 flex items-center gap-3">
      <span className="text-sm text-muted-foreground">Search mode:</span>
      <Tabs value={searchMode} onValueChange={(value) => onSearchModeChange(value as SearchMode)}>
        <TabsList>
          <TabsTrigger value="hybrid">Hybrid</TabsTrigger>
          <TabsTrigger value="fulltext">Full-Text</TabsTrigger>
          <TabsTrigger value="semantic">Semantic</TabsTrigger>
        </TabsList>
      </Tabs>
      <label className="flex items-center gap-2 text-sm text-muted-foreground">
        <input
          type="checkbox"
          checked={showCompletedOnly}
          onChange={(event) => onShowCompletedOnlyChange(event.target.checked)}
        />
        Show finished only
      </label>
      {resultCount && (
        <span className="text-sm text-muted-foreground ml-auto">
          {resultCount.hasQuery
            ? `Showing ${resultCount.showing} result${resultCount.showing === 1 ? '' : 's'}`
            : `Showing ${resultCount.showing} of ${resultCount.total ?? resultCount.showing} result${(resultCount.total ?? resultCount.showing) === 1 ? '' : 's'}`}
        </span>
      )}
    </div>
  )
}
