/**
 * ArtifactSkeleton - Loading skeleton for artifact page content
 *
 * Matches the layout structure from ArtifactPage:
 * - Header with title and metadata bar
 * - Two-column layout: TOC sidebar + main content
 * - Content blocks representing markdown sections
 * - Quality banner placeholder
 *
 * @module features/artifact/components/ArtifactSkeleton
 */

import type React from 'react'

import { Card } from '@shared/components/ui/card'
import { Skeleton, SkeletonText } from '@shared/components/ui/skeleton'

// Stable IDs for skeleton TOC items
const TOC_SKELETON_IDS = [
  'toc-sk-1',
  'toc-sk-2',
  'toc-sk-3',
  'toc-sk-4',
  'toc-sk-5',
  'toc-sk-6',
] as const

// Stable IDs for skeleton content sections
const CONTENT_SKELETON_IDS = [
  'content-sk-1',
  'content-sk-2',
  'content-sk-3',
  'content-sk-4',
] as const

// Stable IDs for skeleton list items
const LIST_ITEM_SKELETON_IDS = ['list-sk-1', 'list-sk-2', 'list-sk-3'] as const

/**
 * TOC Sidebar Skeleton Component
 */
function TOCSidebarSkeleton(): React.ReactNode {
  return (
    <aside className="mb-6 lg:mb-0 lg:sticky lg:top-8 lg:self-start">
      <Card className="p-4">
        <SkeletonText width="1/2" className="h-5 mb-4" />
        <div className="space-y-3">
          {TOC_SKELETON_IDS.map((id) => (
            <div key={id} className="space-y-2">
              <SkeletonText width="3/4" className="h-4" />
              <div className="pl-4 space-y-2">
                <SkeletonText width="2/3" className="h-3" />
                <SkeletonText width="1/2" className="h-3" />
              </div>
            </div>
          ))}
        </div>
      </Card>
    </aside>
  )
}

/**
 * Content Section Skeleton Component
 */
function ContentSectionSkeleton({
  sectionId,
  isFirst,
}: {
  sectionId: string
  isFirst: boolean
}): React.ReactNode {
  const showCodeBlock = sectionId === 'content-sk-1' || sectionId === 'content-sk-3'
  const showListItems = sectionId === 'content-sk-1' || sectionId === 'content-sk-4'

  return (
    <div className="space-y-4">
      {/* Section heading */}
      <SkeletonText width={isFirst ? 'full' : '2/3'} className="h-7" />

      {/* Paragraph blocks (3-4 lines each) */}
      <div className="space-y-2">
        <SkeletonText width="full" className="h-4" />
        <SkeletonText width="full" className="h-4" />
        <SkeletonText width="full" className="h-4" />
        <SkeletonText width="3/4" className="h-4" />
      </div>

      {/* Code block skeleton (sections 1 and 3) */}
      {showCodeBlock && (
        <Card className="p-4 bg-muted/50">
          <div className="space-y-2">
            <SkeletonText width="1/2" className="h-3" />
            <SkeletonText width="3/4" className="h-3" />
            <SkeletonText width="2/3" className="h-3" />
            <SkeletonText width="full" className="h-3" />
          </div>
        </Card>
      )}

      {/* List items skeleton (sections 1 and 4) */}
      {showListItems && (
        <div className="pl-4 space-y-2">
          {LIST_ITEM_SKELETON_IDS.map((listId) => (
            <div key={listId} className="flex items-start gap-2">
              <Skeleton className="h-1.5 w-1.5 rounded-full mt-2 flex-shrink-0" />
              <SkeletonText width="full" className="h-4" />
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

/**
 * Loading skeleton for artifact page
 *
 * WCAG 2.1 AA Compliance:
 * - aria-busy="true" on container during loading
 * - aria-hidden on skeleton elements (decorative)
 * - Maintains responsive grid layout matching loaded state
 *
 * Layout matches ArtifactPage.tsx:
 * - lg:grid-cols-[250px_1fr] - TOC sidebar + content
 * - xl:grid-cols-[280px_1fr] - Wider sidebar on XL screens
 */
/* eslint-disable max-lines-per-function -- Skeleton component requires complete JSX layout structure for all sections */
export function ArtifactSkeleton(): React.ReactNode {
  return (
    <div
      className="space-y-8"
      data-testid="artifact-skeleton"
      aria-busy="true"
      aria-label="Loading artifact content"
    >
      {/* Header skeleton - matches ArtifactHeader.tsx */}
      <div className="flex items-start justify-between mb-8">
        <div className="space-y-2">
          <SkeletonText width="1/2" className="h-8" />
          <SkeletonText width="3/4" className="h-4" />
        </div>
        <div className="flex items-center gap-2">
          <Skeleton className="h-9 w-32" />
          <Skeleton className="h-9 w-28" />
        </div>
      </div>

      {/* Quality banner skeleton (optional, appears when warnings exist) */}
      <Card className="p-4 border-amber-500/50 bg-amber-500/10">
        <div className="space-y-2">
          <SkeletonText width="1/3" className="h-5" />
          <SkeletonText width="full" className="h-4" />
          <SkeletonText width="2/3" className="h-4" />
        </div>
      </Card>

      {/* Two-column layout: TOC + Content (matches ArtifactPage grid) */}
      <div className="lg:grid lg:grid-cols-[250px_1fr] lg:gap-8 xl:grid-cols-[280px_1fr] xl:gap-12">
        <TOCSidebarSkeleton />

        {/* Main content skeleton */}
        <main className="min-w-0 space-y-6">
          {/* Markdown content blocks (4 sections) */}
          {CONTENT_SKELETON_IDS.map((sectionId, index) => (
            <ContentSectionSkeleton key={sectionId} sectionId={sectionId} isFirst={index === 0} />
          ))}

          {/* Feedback buttons skeleton */}
          <div className="mt-8 pt-6 border-t border-border">
            <div className="flex items-center gap-3">
              <SkeletonText width="1/4" className="h-5 mb-3" />
            </div>
            <div className="flex gap-2">
              <Skeleton className="h-10 w-32" />
              <Skeleton className="h-10 w-32" />
            </div>
          </div>
        </main>
      </div>
    </div>
  )
}
/* eslint-enable max-lines-per-function */

ArtifactSkeleton.displayName = 'ArtifactSkeleton'
