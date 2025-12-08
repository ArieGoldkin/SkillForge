import { useMemo, useState } from 'react'

import type { AnalysisStatus, SearchMode } from '@app-types/api'
import { useNavigate } from '@tanstack/react-router'

import { Tabs, TabsList, TabsTrigger } from '@shared/components/ui/tabs'

import { ContentGrid } from './components/ContentGrid'
import { FiltersSidebar } from './components/FiltersSidebar'
import { LibraryHeader } from './components/LibraryHeader'
import type { SkillStatus } from './components/SkillCard'
import type { SkillFilters as SkillFiltersType } from './components/SkillFilters'
import { SkillSearch } from './components/SkillSearch'
import { useFilteredSkills, useLibrarySearchInfinite } from './hooks'
import { mapFiltersToQuery, normalizeTitle } from './utils'
import { dedupeByAnalysisId } from './utils/libraryTransform'

/* eslint-disable max-lines-per-function -- Complex component with search, filters, and pagination logic. Further extraction would reduce cohesion. */
export default function Library() {
  const navigate = useNavigate()
  const [searchQuery, setSearchQuery] = useState('')
  const [searchMode, setSearchMode] = useState<SearchMode>('hybrid')
  const [showCompletedOnly, setShowCompletedOnly] = useState(true)
  const [filters, setFilters] = useState<SkillFiltersType>({
    difficulty: [],
    tags: [],
    status: [],
    durationRange: [0, 1000],
  })
  const limit = 15

  const mapAnalysisStatusToSkillStatus = (status: AnalysisStatus): SkillStatus => {
    if (status === 'complete') return 'completed'
    if (status === 'failed') return 'failed'
    return 'in-progress'
  }

  // Use server-side infinite search API
  const {
    data: searchResults,
    isLoading,
    isFetching,
    fetchNextPage,
    hasNextPage,
    isFetchingNextPage,
  } = useLibrarySearchInfinite({
    query: searchQuery || undefined,
    search_mode: searchMode,
    ...mapFiltersToQuery(filters, showCompletedOnly),
    limit,
  })

  // Transform search results into skills format
  const skills = useMemo(() => {
    const pages = searchResults?.pages ?? []
    const items = dedupeByAnalysisId(pages.flatMap((page) => page.items))
    if (!items.length) {
      return []
    }

    return items.map((item) => {
      const tags = item.tags?.length ? item.tags : [item.content_type]
      const isFailed = item.status === 'failed'
      return {
        id: item.analysis_id,
        title: normalizeTitle(item.title),
        description: item.snippet
          ? item.snippet.replace(/<\/?mark>/g, '')
          : `Analysis of ${item.content_type}`,
        snippet: item.snippet,
        thumbnail: `https://api.dicebear.com/7.x/shapes/svg?seed=${item.analysis_id}`,
        duration: 25,
        difficulty: 'intermediate' as const,
        tags,
        progress: isFailed ? undefined : 0,
        status: mapAnalysisStatusToSkillStatus(item.status),
        analysisStatus: item.status,
        onSelect: (id: string) => {
          navigate({ to: '/analyze/$id', params: { id } })
        },
      }
    })
  }, [searchResults, navigate])

  const availableTags = useMemo(() => {
    const tagSet = new Set<string>()
    const pages = searchResults?.pages ?? []
    const items = dedupeByAnalysisId(pages.flatMap((page) => page.items))
    items.forEach((item) => {
      const tags = item.tags?.length ? item.tags : [item.content_type]
      tags.forEach((tag) => tagSet.add(tag))
    })
    return Array.from(tagSet)
  }, [searchResults])

  const availableStatuses = useMemo<AnalysisStatus[]>(() => {
    const statusSet = new Set<AnalysisStatus>()
    const pages = searchResults?.pages ?? []
    const items = dedupeByAnalysisId(pages.flatMap((page) => page.items))
    items.forEach((item) => {
      if (item.status) {
        statusSet.add(item.status)
      }
    })
    return Array.from(statusSet)
  }, [searchResults])

  // Apply client-side filters for difficulty/tags (server doesn't support these yet)
  const filteredSkills = useFilteredSkills(skills, '', filters)

  const handleSelectSkill = (id: string) => {
    navigate({ to: '/analyze/$id', params: { id } })
  }

  const showingCount = filteredSkills.length
  const totalCount = searchQuery.trim()
    ? showingCount
    : (searchResults?.pages?.[0]?.total ?? filteredSkills.length)

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
        <label className="flex items-center gap-2 text-sm text-muted-foreground">
          <input
            type="checkbox"
            checked={showCompletedOnly}
            onChange={(event) => setShowCompletedOnly(event.target.checked)}
          />
          Show finished only
        </label>
        {searchResults && (
          <span className="text-sm text-muted-foreground ml-auto">
            {searchQuery.trim()
              ? `Showing ${showingCount} result${showingCount === 1 ? '' : 's'}`
              : `Showing ${showingCount} of ${totalCount} result${totalCount === 1 ? '' : 's'}`}
          </span>
        )}
      </div>

      {/* Main content grid with filters */}
      <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
        <FiltersSidebar
          filters={filters}
          onChange={(next) => {
            setFilters(next)
            if (next.status.length > 0 && showCompletedOnly) {
              setShowCompletedOnly(false)
            }
          }}
          availableTags={availableTags}
          availableStatuses={availableStatuses}
        />
        <div className="lg:col-span-3">
          <ContentGrid
            isLoading={isLoading}
            skills={filteredSkills}
            onSelectSkill={handleSelectSkill}
            onLoadMore={hasNextPage ? fetchNextPage : undefined}
            canLoadMore={Boolean(hasNextPage)}
            isLoadingMore={isFetchingNextPage || isFetching || isLoading}
          />
        </div>
      </div>
    </div>
  )
}
