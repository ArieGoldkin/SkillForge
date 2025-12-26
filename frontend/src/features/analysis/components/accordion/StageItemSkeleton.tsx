/**
 * StageItemSkeleton - Loading skeleton for stage item row
 *
 * Matches the compact layout of StageItem:
 * - Status icon area (left edge)
 * - Stage name and metadata
 * - Status badge (right edge)
 * - Optional timestamp (responsive - hidden on mobile)
 *
 * @module features/analysis/components/accordion/StageItemSkeleton
 */

import type React from 'react'

import { Skeleton, SkeletonText, SkeletonCircle } from '@shared/components/ui/skeleton'

import { cn } from '@lib/utils'

/**
 * Props for StageItemSkeleton
 */
export interface StageItemSkeletonProps {
  /** Whether to show timestamp (responsive - hidden on mobile) */
  showTimestamp?: boolean
  /** Optional additional CSS classes */
  className?: string
}

/**
 * Loading skeleton for stage item row within accordion
 *
 * WCAG 2.1 AA Compliance:
 * - aria-hidden on skeleton elements (decorative)
 * - Parent accordion group should have aria-busy="true" during loading
 * - Maintains same visual structure as loaded stage for layout stability
 *
 * Layout matches StageItem.tsx:
 * - Status icon (h-4 w-4)
 * - Stage name + status badge
 * - Optional timestamp (hidden on mobile via md:flex)
 * - Compact py-2 px-3 spacing
 */
export function StageItemSkeleton({
  showTimestamp = false,
  className,
}: StageItemSkeletonProps): React.ReactNode {
  return (
    <div
      className={cn(
        'py-2 px-3 rounded-md',
        'hover:bg-muted/50 transition-colors duration-200',
        className
      )}
      role="listitem"
      data-testid="stage-item-skeleton"
      aria-hidden="true"
    >
      <div className="flex items-start gap-3">
        {/* Status icon skeleton - matches h-4 w-4 from getStatusIcon */}
        <div className="mt-0.5">
          <SkeletonCircle size="xs" className="h-4 w-4" />
        </div>

        {/* Stage info skeleton */}
        <div className="flex-1 min-w-0">
          {/* Stage name + status badge row */}
          <div className="flex items-center justify-between gap-2">
            {/* Stage name skeleton - matches text-sm font-medium */}
            <SkeletonText width="1/2" className="h-5" />

            {/* Right side: timestamp + status badge */}
            <div className="flex items-center gap-2 flex-shrink-0">
              {/* Timestamp skeleton (responsive - hidden on mobile) */}
              {showTimestamp && (
                <div className="hidden md:flex items-center gap-1">
                  <SkeletonCircle size="xs" className="h-3 w-3" />
                  <Skeleton className="h-3 w-16" />
                </div>
              )}

              {/* Status badge skeleton - matches Badge component */}
              <Skeleton className="h-6 w-20" rounded="md" />
            </div>
          </div>

          {/* Description skeleton (for active/running stages) */}
          <div className="mt-1">
            <SkeletonText width="3/4" className="h-3" />
          </div>
        </div>
      </div>
    </div>
  )
}

StageItemSkeleton.displayName = 'StageItemSkeleton'
