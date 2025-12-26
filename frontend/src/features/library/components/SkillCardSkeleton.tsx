/**
 * SkillCardSkeleton - Loading skeleton for SkillCard component
 *
 * Matches the exact layout of SkillCard:
 * - Thumbnail area (h-48)
 * - Title line
 * - Description (2 lines)
 * - Metadata row (difficulty, duration, status)
 * - Tags (3 badge placeholders)
 *
 * @module features/library/components/SkillCardSkeleton
 */

import type React from 'react'

import { Card } from '@shared/components/ui/card'
import { Skeleton, SkeletonText, SkeletonBlock } from '@shared/components/ui/skeleton'

/**
 * Loading skeleton for SkillCard
 *
 * WCAG 2.1 AA Compliance:
 * - aria-hidden on skeleton elements (decorative)
 * - Parent should have aria-busy="true" during loading
 * - Maintains same visual structure as loaded card for layout stability
 */
export function SkillCardSkeleton(): React.ReactNode {
  return (
    <Card className="overflow-hidden" data-testid="skill-card-skeleton">
      {/* Thumbnail skeleton - matches h-48 from SkillCardThumbnail */}
      <SkeletonBlock height="lg" rounded="none" className="h-48" />

      <div className="p-6 space-y-4">
        {/* Title skeleton - matches h-6 for text-lg font-semibold */}
        <SkeletonText width="3/4" className="h-6" />

        {/* Description skeleton - 2 lines matching text-sm */}
        <div className="space-y-2">
          <SkeletonText width="full" className="h-4" />
          <SkeletonText width="5/6" className="h-4" />
        </div>

        {/* Metadata row skeleton - difficulty, duration, status badges */}
        <div className="flex items-center gap-2">
          <Skeleton className="h-6 w-20" />
          <Skeleton className="h-6 w-16" />
          <Skeleton className="h-6 w-24" />
        </div>

        {/* Progress bar skeleton (optional, appears on in-progress cards) */}
        <div className="space-y-2">
          <SkeletonText width="1/4" className="h-3" />
          <Skeleton className="h-2 w-full" rounded="full" />
        </div>

        {/* Tags skeleton - 3 badge placeholders */}
        <div className="flex gap-2 flex-wrap">
          <Skeleton className="h-6 w-20" rounded="full" />
          <Skeleton className="h-6 w-16" rounded="full" />
          <Skeleton className="h-6 w-24" rounded="full" />
        </div>
      </div>
    </Card>
  )
}

SkillCardSkeleton.displayName = 'SkillCardSkeleton'
