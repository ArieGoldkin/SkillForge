import type React from 'react'

import { BookOpen, Loader2 } from 'lucide-react'

import { cn } from '@lib/utils'

import { SkillCardSkeleton } from '../SkillCardSkeleton'

import type { SkillGridViewProps } from './types'
import { useInfiniteScroll } from './useInfiniteScroll'
import { VirtualizedGrid } from './VirtualizedGrid'

/** Stable IDs for loading skeleton placeholders */
const SKELETON_IDS = ['sk-1', 'sk-2', 'sk-3', 'sk-4', 'sk-5', 'sk-6'] as const

/**
 * Empty state component
 */
function EmptyState({ message }: { message: string }): React.ReactNode {
  return (
    <div className="col-span-full flex flex-col items-center justify-center py-16 text-center">
      <div className="rounded-full bg-muted p-6 mb-4">
        <BookOpen className="h-12 w-12 text-muted-foreground" />
      </div>
      <h3 className="text-lg font-semibold mb-2">No Skills Found</h3>
      <p className="text-sm text-muted-foreground max-w-md">{message}</p>
    </div>
  )
}

/**
 * SkillGridView - Virtualized grid layout for SkillCards
 *
 * Displays skills in a responsive virtualized grid with loading states,
 * empty state, and infinite scroll support.
 *
 * Grid breakpoints:
 * - Mobile: 1 column
 * - Tablet (md): 2 columns
 * - Desktop (lg): 3 columns
 *
 * @example
 * ```tsx
 * <SkillGridView
 *   skills={skillsData}
 *   onSelectSkill={(id) => router.push(`/skills/${id}`)}
 *   loading={isLoading}
 *   emptyMessage="Try adjusting your filters or search query"
 *   onLoadMore={loadNextPage}
 *   canLoadMore={hasNextPage}
 * />
 * ```
 */
export function SkillGridView({
  skills,
  onSelectSkill,
  loading = false,
  emptyMessage = 'No skills found. Try adjusting your filters or search query.',
  className,
  onLoadMore,
  canLoadMore = false,
  isLoadingMore = false,
}: SkillGridViewProps): React.ReactNode {
  const sentinelRef = useInfiniteScroll(onLoadMore, canLoadMore)

  return (
    <div className="space-y-4">
      {loading ? (
        <div
          className={cn('grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6', className)}
          role="list"
          aria-label="Skills grid loading"
        >
          {SKELETON_IDS.map((id) => (
            <SkillCardSkeleton key={id} />
          ))}
        </div>
      ) : skills.length === 0 ? (
        <div
          className={cn('grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6', className)}
          role="list"
          aria-label="Skills grid"
        >
          <EmptyState message={emptyMessage} />
        </div>
      ) : (
        <VirtualizedGrid skills={skills} onSelectSkill={onSelectSkill} className={className} />
      )}

      {/* Infinite scroll sentinel */}
      {onLoadMore && canLoadMore && (
        <div ref={sentinelRef} className="flex justify-center py-4">
          {isLoadingMore ? (
            <div className="flex items-center gap-2 text-sm text-muted-foreground">
              <Loader2 className="h-4 w-4 animate-spin" aria-hidden="true" />
              <span>Loading more…</span>
            </div>
          ) : (
            <div className="text-xs text-muted-foreground">Scroll to load more</div>
          )}
        </div>
      )}
    </div>
  )
}

SkillGridView.displayName = 'SkillGridView'
