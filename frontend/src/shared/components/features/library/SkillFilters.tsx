import type * as React from 'react'

import { Filter, X } from 'lucide-react'

import { cn } from '@/lib/utils'
import { Badge } from '@/shared/components/ui/badge'
import { Button } from '@/shared/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/shared/components/ui/card'

import type { SkillDifficulty, SkillStatus } from './SkillCard'
import { DifficultyFilter } from './SkillFilters/DifficultyFilter'
import { DurationFilter } from './SkillFilters/DurationFilter'
import { StatusFilter } from './SkillFilters/StatusFilter'
import { TagFilter } from './SkillFilters/TagFilter'
import { useSkillFilters } from './SkillFilters/useSkillFilters'

/**
 * Filter configuration
 */
export interface SkillFilters {
  difficulty: SkillDifficulty[]
  status: SkillStatus[]
  tags: string[]
  durationRange: [number, number]
}

/**
 * Props for SkillFilters component
 */
export interface SkillFiltersProps {
  filters: SkillFilters
  onChange: (filters: SkillFilters) => void
  availableTags: string[]
  className?: string
}

/**
 * SkillFilters - Filter sidebar for library
 *
 * Provides filtering controls for difficulty, status, tags, and duration range.
 * Displays active filter count and clear all functionality.
 *
 * @example
 * ```tsx
 * <SkillFilters
 *   filters={{
 *     difficulty: ['intermediate'],
 *     status: ['in-progress'],
 *     tags: ['React'],
 *     durationRange: [0, 120]
 *   }}
 *   onChange={(filters) => setFilters(filters)}
 *   availableTags={['React', 'TypeScript', 'Next.js']}
 * />
 * ```
 */
export const SkillFilters: React.FC<SkillFiltersProps> = ({
  filters,
  onChange,
  availableTags,
  className,
}) => {
  const { handlers, activeFilterCount } = useSkillFilters(filters, onChange)

  return (
    <Card className={cn('h-fit', className)}>
      <CardHeader>
        <div className="flex items-center justify-between">
          <CardTitle className="flex items-center gap-2 text-base">
            <Filter className="h-4 w-4" />
            Filters
            {activeFilterCount > 0 && (
              <Badge variant="default" className="ml-1">
                {activeFilterCount}
              </Badge>
            )}
          </CardTitle>
          {activeFilterCount > 0 && (
            <Button
              variant="ghost"
              size="sm"
              onClick={handlers.handleClearAll}
              className="h-8 text-xs"
              aria-label="Clear all filters"
            >
              <X className="h-3 w-3 mr-1" />
              Clear
            </Button>
          )}
        </div>
      </CardHeader>
      <CardContent className="space-y-6">
        <DifficultyFilter
          selectedDifficulties={filters.difficulty}
          onChange={handlers.handleDifficultyChange}
        />
        <StatusFilter selectedStatuses={filters.status} onChange={handlers.handleStatusChange} />
        <TagFilter
          availableTags={availableTags}
          selectedTags={filters.tags}
          onChange={handlers.handleTagChange}
        />
        <DurationFilter />
      </CardContent>
    </Card>
  )
}

SkillFilters.displayName = 'SkillFilters'
