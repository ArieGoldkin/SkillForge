import * as React from 'react'

import { Loader2, Search, X } from 'lucide-react'

import { Input } from '@shared/components/ui/input'

import { cn } from '@lib/utils'
import { COMPONENT_CONSTANTS } from '@/lib/constants'

/**
 * Props for SkillSearch component
 */
export interface SkillSearchProps {
  placeholder?: string
  onSearch: (query: string) => void
  debounceMs?: number
  className?: string
}

/**
 * SkillSearch - Search input with debounced query
 *
 * Provides a search input field with debounced callbacks to avoid excessive API calls.
 * Includes clear button and loading indicator.
 *
 * @example
 * ```tsx
 * <SkillSearch
 *   placeholder="Search skills..."
 *   onSearch={(query) => fetchSkills(query)}
 *   debounceMs={300}
 * />
 * ```
 */
/* eslint-disable max-lines-per-function -- Component requires debounce logic with useEffect, event handlers, and complete JSX layout (search icon, input, loading/clear button). Further extraction would reduce cohesion. */
export const SkillSearch: React.FC<SkillSearchProps> = ({
  placeholder = 'Search...',
  onSearch,
  debounceMs = COMPONENT_CONSTANTS.SEARCH_DEBOUNCE_MS,
  className,
}) => {
  const [query, setQuery] = React.useState('')
  const [isSearching, setIsSearching] = React.useState(false)
  const timeoutRef = React.useRef<ReturnType<typeof setTimeout> | null>(null)

  // Debounced search
  React.useEffect(() => {
    // Clear existing timeout
    if (timeoutRef.current) {
      clearTimeout(timeoutRef.current)
    }

    // Set loading state for non-empty queries
    if (query.trim()) {
      setIsSearching(true)
    }

    // Create new timeout
    timeoutRef.current = setTimeout(() => {
      onSearch(query.trim())
      setIsSearching(false)
    }, debounceMs)

    // Cleanup on unmount
    return () => {
      if (timeoutRef.current) {
        clearTimeout(timeoutRef.current)
      }
    }
  }, [query, debounceMs, onSearch])

  const handleChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    setQuery(event.target.value)
  }

  const handleClear = () => {
    setQuery('')
    setIsSearching(false)
  }

  const handleKeyDown = (event: React.KeyboardEvent<HTMLInputElement>) => {
    // Trigger immediate search on Enter
    if (event.key === 'Enter') {
      event.preventDefault()
      if (timeoutRef.current) {
        clearTimeout(timeoutRef.current)
      }
      onSearch(query.trim())
      setIsSearching(false)
    }
  }

  return (
    <div className={cn('relative', className)}>
      {/* Search icon */}
      <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />

      {/* Input field */}
      <Input
        type="search"
        placeholder={placeholder}
        value={query}
        onChange={handleChange}
        onKeyDown={handleKeyDown}
        className="pl-9 pr-9"
        aria-label="Search"
      />

      {/* Loading indicator or clear button */}
      <div className="absolute right-3 top-1/2 -translate-y-1/2">
        {isSearching ? (
          <Loader2 className="h-4 w-4 animate-spin text-muted-foreground" aria-label="Searching" />
        ) : query ? (
          <button
            type="button"
            onClick={handleClear}
            className="text-muted-foreground hover:text-foreground transition-colors focus:outline-none focus-visible:ring-2 focus-visible:ring-ring rounded-sm"
            aria-label="Clear search"
          >
            <X className="h-4 w-4" />
          </button>
        ) : null}
      </div>
    </div>
  )
}

SkillSearch.displayName = 'SkillSearch'
