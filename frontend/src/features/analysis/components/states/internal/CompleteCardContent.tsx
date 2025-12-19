import { AlertTriangle, CheckCircle } from 'lucide-react'

import { cn } from '@lib/utils'

import { ActionButtons } from './ActionButtons'

interface CompleteCardContentProps {
  artifactId: string | null | undefined
  analysisId?: string
  traceId?: string
  isColumn: boolean
  onPreview: () => void
  hasFailedStages?: boolean
  failedStagesCount?: number
}

export function CompleteCardContent(props: CompleteCardContentProps) {
  const {
    artifactId,
    analysisId,
    traceId,
    isColumn,
    onPreview,
    hasFailedStages = false,
    failedStagesCount = 0,
  } = props
  const iconSize = isColumn ? 'h-6 w-6' : 'h-8 w-8'
  const iconWrapSize = isColumn ? 'h-12 w-12 mb-3' : 'h-16 w-16 mb-4'

  // Determine icon, title, and message based on whether there are failures
  const Icon = hasFailedStages ? AlertTriangle : CheckCircle
  const iconColor = hasFailedStages ? 'text-destructive' : 'text-primary'
  const iconBg = hasFailedStages ? 'bg-destructive/10' : 'bg-primary/10'
  const title = hasFailedStages ? 'Analysis Completed with Errors' : 'Analysis Complete'
  const message = hasFailedStages
    ? `Your implementation guide is ready, but ${failedStagesCount} ${failedStagesCount === 1 ? 'stage' : 'stages'} failed during analysis. Review the failed stages below and check the guide for any missing information.`
    : 'Your implementation guide is ready. View the detailed analysis with code examples.'

  return (
    <div
      className={cn('flex flex-col items-center text-center', isColumn && 'h-full justify-center')}
    >
      <div className={cn('rounded-full flex items-center justify-center', iconWrapSize, iconBg)}>
        <Icon className={cn(iconColor, iconSize)} />
      </div>
      <h2 className={cn('font-semibold', isColumn ? 'text-xl mb-2' : 'text-2xl mb-2')}>{title}</h2>
      <p className={cn('text-muted-foreground', isColumn ? 'text-sm mb-4' : 'mb-6 max-w-md')}>
        {message}
      </p>
      {artifactId ? (
        <ActionButtons
          artifactId={artifactId}
          analysisId={analysisId}
          traceId={traceId}
          isCompact={isColumn}
          onPreview={onPreview}
        />
      ) : (
        <p className="text-sm text-muted-foreground py-4">No guide available.</p>
      )}
    </div>
  )
}
