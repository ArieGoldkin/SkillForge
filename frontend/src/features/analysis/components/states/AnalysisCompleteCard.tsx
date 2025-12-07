import { ArtifactPreviewModal, useArtifactPreview } from '@features/artifact'

import { cn } from '@lib/utils'

import { CompleteCardContent } from './internal'

interface AnalysisCompleteCardProps {
  artifactId: string | null | undefined
  analysisId?: string
  variant?: 'default' | 'column'
  sourceUrl?: string
}

export function AnalysisCompleteCard(props: AnalysisCompleteCardProps) {
  const { artifactId, analysisId, variant = 'default', sourceUrl } = props
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
          isColumn={isColumn}
          onPreview={preview.openPreview}
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
      />
    </div>
  )
}
