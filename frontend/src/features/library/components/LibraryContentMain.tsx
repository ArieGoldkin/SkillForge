import type { AnalysisStatus } from '@/types/api'

import { ContentGrid } from './ContentGrid'
import { FiltersSidebar } from './FiltersSidebar'
import type { SkillStatus } from './SkillCard'
import type { SkillFilters as SkillFiltersType } from './SkillFilters'

interface Skill {
  id: string
  title: string
  description: string
  thumbnail: string
  duration: number
  difficulty: 'beginner' | 'intermediate' | 'advanced'
  tags: string[]
  progress?: number
  status: SkillStatus
  onSelect: (id: string) => void
}

interface LibraryContentMainProps {
  filters: SkillFiltersType
  onFiltersChange: (filters: SkillFiltersType) => void
  availableTags: string[]
  availableStatuses: AnalysisStatus[]
  filteredSkills: Skill[]
  isLoading: boolean
  isFetching: boolean
  hasNextPage: boolean
  isFetchingNextPage: boolean
  onSelectSkill: (id: string) => void
  onLoadMore?: () => void
  isPending?: boolean
}

export function LibraryContentMain({
  filters,
  onFiltersChange,
  availableTags,
  availableStatuses,
  filteredSkills,
  isLoading,
  isFetching,
  hasNextPage,
  isFetchingNextPage,
  onSelectSkill,
  onLoadMore,
  isPending,
}: LibraryContentMainProps) {
  return (
    <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
      <FiltersSidebar
        filters={filters}
        onChange={onFiltersChange}
        availableTags={availableTags}
        availableStatuses={availableStatuses}
      />
      <div
        className="lg:col-span-3"
        style={{ opacity: isPending ? 0.6 : 1, transition: 'opacity 0.2s' }}
      >
        <ContentGrid
          isLoading={isLoading}
          skills={filteredSkills}
          onSelectSkill={onSelectSkill}
          onLoadMore={onLoadMore}
          canLoadMore={Boolean(hasNextPage)}
          isLoadingMore={isFetchingNextPage || isFetching || isLoading}
        />
      </div>
    </div>
  )
}
