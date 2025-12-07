import { useMemo, useState } from 'react'

import type { AnalysisStatus, SearchMode } from '@app-types/api'
import { useQueryClient } from '@tanstack/react-query'
import { useNavigate } from '@tanstack/react-router'

import { Tabs, TabsList, TabsTrigger } from '@shared/components/ui/tabs'

import { analyzeAPI } from '@services/api.service'
import { ContentGrid } from './components/ContentGrid'
import { FiltersSidebar } from './components/FiltersSidebar'
import { LibraryHeader } from './components/LibraryHeader'
import type { SkillFilters as SkillFiltersType } from './components/SkillFilters'
import { SkillSearch } from './components/SkillSearch'
import { useFilteredSkills, useLibrarySearch } from './hooks'

const STATUS_MAP = {
  'not-started': 'pending',
  'in-progress': 'running',
  completed: 'complete',
  failed: 'failed',
} as const

const CONTENT_TYPE_TAGS = ['article', 'video', 'repo'] as const

export const mapFiltersToQuery = (
  filters: SkillFiltersType,
  showCompletedOnly: boolean
): {
  status?: string
  content_type?: string
} => {
  if (showCompletedOnly) {
    return { status: 'complete', content_type: pickContentType(filters) }
  }
  return {
    status: pickStatus(filters),
    content_type: pickContentType(filters),
  }
}

const pickStatus = (filters: SkillFiltersType): string | undefined => {
  if (!filters.status.length) return undefined
  const first = filters.status[0]
  return STATUS_MAP[first] ?? undefined
}

const pickContentType = (filters: SkillFiltersType): string | undefined => {
  const tag = filters.tags.find((t) => (CONTENT_TYPE_TAGS as readonly string[]).includes(t))
  return tag
}

/* eslint-disable max-lines-per-function -- Complex component with search, filters, and pagination logic. Further extraction would reduce cohesion. */
export const normalizeTitle = (rawTitle: string | null): string => {
  if (!rawTitle) return 'Untitled'
  return rawTitle.replace(/^title:\s*/i, '').trim() || 'Untitled'
}

export default function Library() {
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const [searchQuery, setSearchQuery] = useState('')
  const [searchMode, setSearchMode] = useState<SearchMode>('hybrid')
  const [showCompletedOnly, setShowCompletedOnly] = useState(true)
  const [filters, setFilters] = useState<SkillFiltersType>({
    difficulty: [],
    tags: [],
    status: [],
    durationRange: [0, 1000],
  })
  const [offset, setOffset] = useState(0)
  const limit = 20

  const mapStatusToSkillStatus = (status: AnalysisStatus) => {
    switch (status) {
      case 'complete':
        return 'completed'
      case 'failed':
        return 'failed'
      case 'extracting':
      case 'analyzing':
      case 'pending':
        return 'in-progress'
      default:
        return 'not-started'
    }
  }

  // Use server-side search API
  const { data: searchResults, isLoading } = useLibrarySearch({
    query: searchQuery || undefined,
    search_mode: searchMode,
    ...mapFiltersToQuery(filters, showCompletedOnly),
    limit,
    offset,
  })

  // Transform search results into skills format
  const skills = useMemo(() => {
    if (!searchResults?.items) return []

    return searchResults.items.map((item) => ({
      id: item.analysis_id,
      title: normalizeTitle(item.title),
      description: item.snippet
        ? // Strip HTML marks for description, keep snippet for display
          item.snippet.replace(/<\/?mark>/g, '')
        : `Analysis of ${item.content_type}`,
      snippet: item.snippet, // Preserved for potential future use
      thumbnail: `https://api.dicebear.com/7.x/shapes/svg?seed=${item.analysis_id}`,
      duration: 25,
      difficulty: 'intermediate' as const,
      tags: [item.content_type],
      progress: item.status === 'complete' ? 100 : undefined,
      status: mapStatusToSkillStatus(item.status),
      onSelect: (id: string) => {
        navigate({ to: '/analyze/$id', params: { id } })
      },
    }))
  }, [searchResults, navigate])

  // Apply client-side filters for difficulty/duration only (status/content_type handled by API)
  const filteredSkills = useFilteredSkills(skills, '', filters)

  const handleSelectSkill = (id: string) => {
    navigate({ to: '/analyze/$id', params: { id } })
  }

  const handleLoadMore = () => {
    if (searchResults && offset + limit < searchResults.total) {
      setOffset((prev) => prev + limit)
    }
  }

  const handleDeleteSkill = async (id: string) => {
    try {
      await analyzeAPI.deleteAnalysis(id)
      await queryClient.invalidateQueries({ queryKey: ['library'] })
      setOffset(0)
    } catch (error) {
      console.error('Failed to delete analysis', error)
      alert('Failed to delete analysis. Please try again.')
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
        <label className="flex items-center gap-2 text-sm text-muted-foreground">
          <input
            type="checkbox"
            checked={showCompletedOnly}
            onChange={(event) => {
              setShowCompletedOnly(event.target.checked)
              setOffset(0)
            }}
          />
          Show completed only
        </label>
        {searchResults && (
          <span className="text-sm text-muted-foreground ml-auto">
            Showing {Math.min(offset + limit, searchResults.total)} of {searchResults.total} results
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
            setOffset(0)
          }}
        />
        <div className="lg:col-span-3">
          <ContentGrid
            isLoading={isLoading}
            skills={filteredSkills}
            onSelectSkill={handleSelectSkill}
            onDeleteSkill={handleDeleteSkill}
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
