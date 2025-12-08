import React, { useEffect, useRef } from 'react'

import { BookOpen, Loader2 } from 'lucide-react'

import { Card } from '@shared/components/ui/card'

import { cn } from '@lib/utils'

import { SkillCard, type SkillCardProps } from './SkillCard'

/** Stable IDs for loading skeleton placeholders */
const SKELETON_IDS = ['sk-1', 'sk-2', 'sk-3', 'sk-4', 'sk-5', 'sk-6'] as const

/**
 * Props for SkillGridView component
 */
export interface SkillGridViewProps {
  skills: SkillCardProps[]
  onSelectSkill: (id: string) => void
  loading?: boolean
  emptyMessage?: string
  className?: string
  onLoadMore?: () => void
  canLoadMore?: boolean
  isLoadingMore?: boolean
}

/**
 * Loading skeleton for skill card
 */
const SkillCardSkeleton: React.FC = () => {
  return (
    <Card className="overflow-hidden">
      <div className="w-full h-48 bg-muted animate-pulse" />
      <div className="p-6 space-y-4">
        <div className="h-6 bg-muted rounded animate-pulse w-3/4" />
        <div className="space-y-2">
          <div className="h-4 bg-muted rounded animate-pulse" />
          <div className="h-4 bg-muted rounded animate-pulse w-5/6" />
        </div>
        <div className="flex gap-2">
          <div className="h-6 bg-muted rounded animate-pulse w-20" />
          <div className="h-6 bg-muted rounded animate-pulse w-16" />
        </div>
      </div>
    </Card>
  )
}

/**
 * Empty state component
 */
const EmptyState: React.FC<{ message: string }> = ({ message }) => {
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
 * SkillGridView - Grid layout for SkillCards
 *
 * Displays skills in a responsive grid layout with loading states and empty state.
 * Automatically adjusts columns based on screen size.
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
 * />
 * ```
 */
// eslint-disable-next-line max-lines-per-function
export const SkillGridView: React.FC<SkillGridViewProps> = ({
  skills,
  onSelectSkill,
  loading = false,
  emptyMessage = 'No skills found. Try adjusting your filters or search query.',
  className,
  onLoadMore,
  canLoadMore = false,
  isLoadingMore = false,
}) => {
  const sentinelRef = useRef<HTMLDivElement | null>(null)

  useEffect(() => {
    if (!onLoadMore || !canLoadMore) return

    const observer = new IntersectionObserver(
      (entries) => {
        const entry = entries[0]
        if (entry.isIntersecting) {
          onLoadMore()
        }
      },
      {
        root: null,
        rootMargin: '200px', // trigger slightly before reaching the end
        threshold: 0.1,
      }
    )

    const sentinel = sentinelRef.current
    if (sentinel) observer.observe(sentinel)

    return () => {
      if (sentinel) observer.unobserve(sentinel)
      observer.disconnect()
    }
  }, [onLoadMore, canLoadMore])

  return (
    <div className="space-y-4">
      <div
        className={cn('grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6', className)}
        role="list"
        aria-label="Skills grid"
      >
        {loading ? (
          // Loading skeletons
          SKELETON_IDS.map((id) => <SkillCardSkeleton key={id} />)
        ) : skills.length === 0 ? (
          // Empty state
          <EmptyState message={emptyMessage} />
        ) : (
          // Skill cards
          skills.map((skill) => <SkillCard key={skill.id} {...skill} onSelect={onSelectSkill} />)
        )}
      </div>

      {/* Infinite scroll sentinel + loading indicator */}
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
