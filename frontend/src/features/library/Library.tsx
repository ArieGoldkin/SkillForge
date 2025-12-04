import { useState, useMemo } from 'react'

import type { SearchMode } from '@app-types/api'
import { useNavigate } from '@tanstack/react-router'

import { Tabs, TabsList, TabsTrigger } from '@shared/components/ui/tabs'

import { ContentGrid } from './components/ContentGrid'
import { FiltersSidebar } from './components/FiltersSidebar'
import { LibraryHeader } from './components/LibraryHeader'
import type { SkillFilters as SkillFiltersType } from './components/SkillFilters'
import { SkillSearch } from './components/SkillSearch'
import { useFilteredSkills, useLibrarySearch } from './hooks'

/* eslint-disable max-lines-per-function -- Complex component with search, filters, and pagination logic. Further extraction would reduce cohesion. */
export default function Library() {
  const navigate = useNavigate()
  const [searchQuery, setSearchQuery] = useState('')
  const [searchMode, setSearchMode] = useState<SearchMode>('hybrid')
  const [filters, setFilters] = useState<SkillFiltersType>({
    difficulty: [],
    tags: [],
    status: [],
    durationRange: [0, 1000],
  })
  const [offset, setOffset] = useState(0)
  const limit = 20

  // Use server-side search API
  const { data: searchResults, isLoading } = useLibrarySearch({
    query: searchQuery || undefined,
    search_mode: searchMode,
    limit,
    offset,
  })

  // Transform search results into skills format
  const skills = useMemo(() => {
    if (!searchResults?.items) return []

    return searchResults.items.map((item) => ({
      id: item.analysis_id,
      title: item.title || 'Untitled',
      description: item.snippet
        ? // Strip HTML marks for description, keep snippet for display
          item.snippet.replace(/<\/?mark>/g, '')
        : `Analysis of ${item.content_type}`,
      snippet: item.snippet, // Preserved for potential future use
      thumbnail: `https://api.dicebear.com/7.x/shapes/svg?seed=${item.analysis_id}`,
      duration: 25,
      difficulty: 'intermediate' as const,
      tags: [item.content_type],
      progress: 0,
      status: 'not-started' as const,
      onSelect: (id: string) => {
        navigate({ to: '/analyze/$id', params: { id } })
      },
    }))
  }, [searchResults, navigate])

  // Apply client-side filters for difficulty/tags (server doesn't support these yet)
  const filteredSkills = useFilteredSkills(skills, '', filters)

  const handleSelectSkill = (id: string) => {
    navigate({ to: '/analyze/$id', params: { id } })
  }

  const handleLoadMore = () => {
    if (searchResults && offset + limit < searchResults.total) {
      setOffset((prev) => prev + limit)
    }
  }

  const hasMore = searchResults ? offset + limit < searchResults.total : false

  return (
    <div className="container mx-auto px-4 py-8 max-w-7xl">
      <LibraryHeader />

      {/* Search input */}
      <div className="mb-4">
        <SkillSearch onSearch={setSearchQuery} placeholder="Search analyses..." />
      </div>

      {/* Search mode toggle */}
      <div className="mb-6 flex items-center gap-3">
        <span className="text-sm text-muted-foreground">Search mode:</span>
        <Tabs value={searchMode} onValueChange={(value) => setSearchMode(value as SearchMode)}>
          <TabsList>
            <TabsTrigger value="hybrid">Hybrid</TabsTrigger>
            <TabsTrigger value="fulltext">Full-Text</TabsTrigger>
            <TabsTrigger value="semantic">Semantic</TabsTrigger>
          </TabsList>
        </Tabs>
        {searchResults && (
          <span className="text-sm text-muted-foreground ml-auto">
            Showing {Math.min(offset + limit, searchResults.total)} of {searchResults.total} results
          </span>
        )}
      </div>

      {/* Main content grid with filters */}
      <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
        <FiltersSidebar filters={filters} onChange={setFilters} />
        <div className="lg:col-span-3">
          <ContentGrid
            isLoading={isLoading}
            skills={filteredSkills}
            onSelectSkill={handleSelectSkill}
          />

          {/* Load More button */}
          {hasMore && searchResults && (
            <div className="mt-6 flex justify-center">
              <button
                type="button"
                onClick={handleLoadMore}
                className="px-6 py-2 text-sm font-medium text-primary bg-primary/10 hover:bg-primary/20 rounded-md transition-colors"
              >
                Load More ({searchResults.total - (offset + limit)} remaining)
              </button>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
