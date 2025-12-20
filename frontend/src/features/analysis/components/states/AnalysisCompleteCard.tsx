/**
 * AnalysisCompleteCard - Displays completion state with preview modal
 *
 * Issue #396: Gets artifactId from Zustand store instead of props,
 * eliminating prop drilling from parent components.
 *
 * Wrapped with React.memo - only re-renders when props change.
 */
import { memo } from 'react'

import { selectArtifactId, useSSEStore } from '@stores/sseStore'

import { ArtifactPreviewModal, useArtifactPreview } from '@features/artifact'

import { cn } from '@lib/utils'

import { CompleteCardContent } from './internal'

interface AnalysisCompleteCardProps {
  /** UI-only props */
  variant?: 'default' | 'column'
  sourceUrl?: string
}

export const AnalysisCompleteCard = memo(function AnalysisCompleteCard({
  variant = 'default',
  sourceUrl,
}: AnalysisCompleteCardProps) {
  // Get artifactId from store instead of props (Issue #396)
  const artifactId = useSSEStore(selectArtifactId)

  const isColumn = variant === 'column'
  const preview = useArtifactPreview(artifactId)

  return (
    <div className={cn(isColumn ? 'h-full' : 'mt-8')}>
      <div
        className={cn('bg-card border border-border rounded-xl', isColumn ? 'p-6 h-full' : 'p-8')}
      >
        {/* CompleteCardContent gets its data from store (Issue #396) */}
        <CompleteCardContent isColumn={isColumn} onPreview={preview.openPreview} />
      </div>
      <ArtifactPreviewModal
        isOpen={preview.isOpen}
        onClose={preview.closePreview}
        content={preview.content}
        isLoading={preview.isLoading}
        error={preview.error}
        onDownload={preview.download}
        sourceUrl={sourceUrl}
        artifactId={artifactId}
      />
    </div>
  )
})
