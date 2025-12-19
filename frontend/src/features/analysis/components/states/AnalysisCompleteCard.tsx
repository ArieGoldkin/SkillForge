import { memo } from 'react'

import { ArtifactPreviewModal, useArtifactPreview } from '@features/artifact'

import { cn } from '@lib/utils'

import { CompleteCardContent } from './internal'

interface AnalysisCompleteCardProps {
  artifactId: string | null | undefined
  analysisId?: string
  traceId?: string
  variant?: 'default' | 'column'
  sourceUrl?: string
  hasFailedStages?: boolean
  failedStagesCount?: number
}

/**
 * AnalysisCompleteCard - Displays completion state with preview modal
 *
 * Wrapped with React.memo - only re-renders when props change.
 */
export const AnalysisCompleteCard = memo(function AnalysisCompleteCard(
  props: AnalysisCompleteCardProps
) {
  const {
    artifactId,
    analysisId,
    traceId,
    variant = 'default',
    sourceUrl,
    hasFailedStages = false,
    failedStagesCount = 0,
  } = props
  const isColumn = variant === 'column'
  const preview = useArtifactPreview(artifactId)

  return (
    <div className={cn(isColumn ? 'h-full' : 'mt-8')}>
      <div
        className={cn('bg-card border border-border rounded-xl', isColumn ? 'p-6 h-full' : 'p-8')}
      >
        <CompleteCardContent
          artifactId={artifactId}
          analysisId={analysisId}
          traceId={traceId}
          isColumn={isColumn}
          onPreview={preview.openPreview}
          hasFailedStages={hasFailedStages}
          failedStagesCount={failedStagesCount}
        />
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
