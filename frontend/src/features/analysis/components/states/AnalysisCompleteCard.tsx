import { CheckCircle } from 'lucide-react'

import { ArtifactPreviewModal, useArtifactPreview } from '@features/artifact'

import { cn } from '@lib/utils'

import { ActionButtons } from './internal'

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

  const iconSize = isColumn ? 'h-6 w-6' : 'h-8 w-8'
  const iconWrapSize = isColumn ? 'h-12 w-12 mb-3' : 'h-16 w-16 mb-4'

  return (
    <div className={cn(isColumn ? 'h-full' : 'mt-8')}>
      <div
        className={cn('bg-card border border-border rounded-xl', isColumn ? 'p-6 h-full' : 'p-8')}
      >
        <div
          className={cn(
            'flex flex-col items-center text-center',
            isColumn && 'h-full justify-center'
          )}
        >
          <div
            className={cn(
              'rounded-full bg-primary/10 flex items-center justify-center',
              iconWrapSize
            )}
          >
            <CheckCircle className={cn('text-primary', iconSize)} />
          </div>
          <h2 className={cn('font-semibold', isColumn ? 'text-xl mb-2' : 'text-2xl mb-2')}>
            Analysis Complete
          </h2>
          <p className={cn('text-muted-foreground', isColumn ? 'text-sm mb-4' : 'mb-6 max-w-md')}>
            Your implementation guide is ready. View the detailed analysis with code examples.
          </p>
          {artifactId ? (
            <ActionButtons
              artifactId={artifactId}
              analysisId={analysisId}
              isCompact={isColumn}
              onPreview={preview.openPreview}
            />
          ) : (
            <p className="text-sm text-muted-foreground py-4">No guide available.</p>
          )}
        </div>
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
