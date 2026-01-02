import * as React from 'react'

import { AlertCircle, ChevronDown, ExternalLink } from 'lucide-react'

import { Badge } from '@shared/components/ui/badge'
import { Button } from '@shared/components/ui/button'
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from '@shared/components/ui/collapsible'

import { cn } from '@lib/utils'

import {
  formatErrorCode,
  getErrorExplanation,
  isErrorCritical,
} from '../../utils/errorCodeFormatter'

interface ErrorBadgeListProps {
  title: string
  errors: string[]
  variant: 'destructive' | 'secondary'
  titleClassName?: string
}

function ErrorBadgeList({ title, errors, variant, titleClassName }: ErrorBadgeListProps) {
  if (errors.length === 0) return null
  return (
    <div>
      <p className={cn('text-xs font-medium mb-1.5', titleClassName)}>{title}</p>
      <div className="flex flex-wrap gap-1.5">
        {errors.map((errorCode) => (
          <Badge key={errorCode} variant={variant} className="text-xs">
            {formatErrorCode(errorCode)}
          </Badge>
        ))}
      </div>
    </div>
  )
}

interface ErrorHeaderProps {
  failedStagesCount: number
  primaryExplanation: ReturnType<typeof getErrorExplanation> | null
  criticalErrorCount: number
}

function ErrorHeader({
  failedStagesCount,
  primaryExplanation,
  criticalErrorCount,
}: ErrorHeaderProps) {
  return (
    <div className="flex items-start gap-3">
      <AlertCircle className="h-5 w-5 text-destructive flex-shrink-0 mt-0.5" />
      <div className="flex-1 min-w-0">
        <p className="text-sm font-medium text-destructive">
          Analysis completed with {failedStagesCount}{' '}
          {failedStagesCount === 1 ? 'failure' : 'failures'}
        </p>
        {primaryExplanation && (
          <p className="text-xs text-muted-foreground mt-1.5">{primaryExplanation.reason}</p>
        )}
        {criticalErrorCount > 0 && (
          <p className="text-xs font-medium text-destructive mt-2">
            {criticalErrorCount} critical {criticalErrorCount === 1 ? 'error' : 'errors'} may affect
            results
          </p>
        )}
      </div>
    </div>
  )
}

interface ActionableGuidanceProps {
  action: string
}

function ActionableGuidance({ action }: ActionableGuidanceProps) {
  return (
    <div className="bg-background/50 rounded-md p-3 border border-destructive/10">
      <p className="text-xs font-medium text-foreground mb-1.5">What you can do:</p>
      <p className="text-xs text-muted-foreground">{action}</p>
    </div>
  )
}

interface ExpandableErrorDetailsProps {
  isExpanded: boolean
  onExpandedChange: (expanded: boolean) => void
  errorCodes: string[]
  criticalErrors: string[]
  nonCriticalErrors: string[]
}

function ExpandableErrorDetails({
  isExpanded,
  onExpandedChange,
  errorCodes,
  criticalErrors,
  nonCriticalErrors,
}: ExpandableErrorDetailsProps) {
  return (
    <Collapsible open={isExpanded} onOpenChange={onExpandedChange}>
      <CollapsibleTrigger asChild>
        <Button variant="ghost" size="sm" className="w-full justify-between text-xs h-8">
          <span>
            {isExpanded ? 'Hide' : 'Show'} error details ({errorCodes.length}{' '}
            {errorCodes.length === 1 ? 'error' : 'errors'})
          </span>
          <ChevronDown className={cn('h-3 w-3 transition-transform', isExpanded && 'rotate-180')} />
        </Button>
      </CollapsibleTrigger>
      <CollapsibleContent className="pt-2 space-y-2">
        <ErrorBadgeList
          title="Critical Errors:"
          errors={criticalErrors}
          variant="destructive"
          titleClassName="text-destructive"
        />
        <ErrorBadgeList
          title="Non-Critical Errors:"
          errors={nonCriticalErrors}
          variant="secondary"
          titleClassName="text-muted-foreground"
        />
      </CollapsibleContent>
    </Collapsible>
  )
}

interface ViewDetailsButtonProps {
  onClick: () => void
}

function ViewDetailsButton({ onClick }: ViewDetailsButtonProps) {
  return (
    <Button variant="outline" size="sm" onClick={onClick} className="w-full text-xs">
      <ExternalLink className="h-3 w-3 mr-2" />
      View detailed error information
    </Button>
  )
}

interface AnalysisProgressCardErrorSummaryProps {
  failedStagesCount: number
  failedStageErrorCodes: string[]
  onViewDetails?: () => void
}

/**
 * Error summary section for completed analyses with failures
 */
export function AnalysisProgressCardErrorSummary({
  failedStagesCount,
  failedStageErrorCodes,
  onViewDetails,
}: AnalysisProgressCardErrorSummaryProps) {
  const [isExpanded, setIsExpanded] = React.useState(false)
  const criticalErrors = failedStageErrorCodes.filter((code) => isErrorCritical(code))
  const nonCriticalErrors = failedStageErrorCodes.filter((code) => !isErrorCritical(code))
  const primaryErrorCode = criticalErrors[0] || failedStageErrorCodes[0]
  const primaryExplanation = primaryErrorCode ? getErrorExplanation(primaryErrorCode) : null

  return (
    <div className="rounded-md bg-destructive/10 border border-destructive/20 p-4 space-y-3">
      <ErrorHeader
        failedStagesCount={failedStagesCount}
        primaryExplanation={primaryExplanation}
        criticalErrorCount={criticalErrors.length}
      />
      {primaryExplanation && <ActionableGuidance action={primaryExplanation.action} />}
      {failedStageErrorCodes.length > 0 && (
        <ExpandableErrorDetails
          isExpanded={isExpanded}
          onExpandedChange={setIsExpanded}
          errorCodes={failedStageErrorCodes}
          criticalErrors={criticalErrors}
          nonCriticalErrors={nonCriticalErrors}
        />
      )}
      {onViewDetails && <ViewDetailsButton onClick={onViewDetails} />}
    </div>
  )
}
