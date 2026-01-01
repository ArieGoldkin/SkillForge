import * as React from 'react'

import { AlertCircle, ChevronDown, ExternalLink } from 'lucide-react'

import { Badge } from '@shared/components/ui/badge'
import { Button } from '@shared/components/ui/button'
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from '@shared/components/ui/collapsible'

import {
  formatErrorCode,
  getErrorExplanation,
  isErrorCritical,
} from '../../utils/errorCodeFormatter'

import { cn } from '@lib/utils'

interface AnalysisProgressCardErrorSummaryProps {
  failedStagesCount: number
  failedStageErrorCodes: string[]
  /** Optional callback to view detailed error information */
  onViewDetails?: () => void
}

/**
 * Error summary section for completed analyses with failures
 *
 * Enhanced with:
 * - User-friendly error explanations
 * - Critical vs non-critical failure grouping
 * - Actionable guidance
 * - Expandable details
 */
export function AnalysisProgressCardErrorSummary({
  failedStagesCount,
  failedStageErrorCodes,
  onViewDetails,
}: AnalysisProgressCardErrorSummaryProps) {
  const [isExpanded, setIsExpanded] = React.useState(false)

  // Group errors by severity
  const criticalErrors = failedStageErrorCodes.filter((code) => isErrorCritical(code))
  const nonCriticalErrors = failedStageErrorCodes.filter((code) => !isErrorCritical(code))

  // Get primary error explanation (first critical, or first error)
  const primaryErrorCode = criticalErrors[0] || failedStageErrorCodes[0]
  const primaryExplanation = primaryErrorCode ? getErrorExplanation(primaryErrorCode) : null

  return (
    <div className="rounded-md bg-destructive/10 border border-destructive/20 p-4 space-y-3">
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
          {criticalErrors.length > 0 && (
            <p className="text-xs font-medium text-destructive mt-2">
              {criticalErrors.length} critical {criticalErrors.length === 1 ? 'error' : 'errors'}{' '}
              may affect results
            </p>
          )}
        </div>
      </div>

      {/* Actionable guidance */}
      {primaryExplanation && (
        <div className="bg-background/50 rounded-md p-3 border border-destructive/10">
          <p className="text-xs font-medium text-foreground mb-1.5">What you can do:</p>
          <p className="text-xs text-muted-foreground">{primaryExplanation.action}</p>
        </div>
      )}

      {/* Expandable error details */}
      {failedStageErrorCodes.length > 0 && (
        <Collapsible open={isExpanded} onOpenChange={setIsExpanded}>
          <CollapsibleTrigger asChild>
            <Button variant="ghost" size="sm" className="w-full justify-between text-xs h-8">
              <span>
                {isExpanded ? 'Hide' : 'Show'} error details ({failedStageErrorCodes.length}{' '}
                {failedStageErrorCodes.length === 1 ? 'error' : 'errors'})
              </span>
              <ChevronDown
                className={cn('h-3 w-3 transition-transform', isExpanded && 'rotate-180')}
              />
            </Button>
          </CollapsibleTrigger>
          <CollapsibleContent className="pt-2 space-y-2">
            {criticalErrors.length > 0 && (
              <div>
                <p className="text-xs font-medium text-destructive mb-1.5">Critical Errors:</p>
                <div className="flex flex-wrap gap-1.5">
                  {criticalErrors.map((errorCode) => (
                    <Badge key={errorCode} variant="destructive" className="text-xs">
                      {formatErrorCode(errorCode)}
                    </Badge>
                  ))}
                </div>
              </div>
            )}
            {nonCriticalErrors.length > 0 && (
              <div>
                <p className="text-xs font-medium text-muted-foreground mb-1.5">
                  Non-Critical Errors:
                </p>
                <div className="flex flex-wrap gap-1.5">
                  {nonCriticalErrors.map((errorCode) => (
                    <Badge key={errorCode} variant="secondary" className="text-xs">
                      {formatErrorCode(errorCode)}
                    </Badge>
                  ))}
                </div>
              </div>
            )}
          </CollapsibleContent>
        </Collapsible>
      )}

      {/* View details button */}
      {onViewDetails && (
        <Button variant="outline" size="sm" onClick={onViewDetails} className="w-full text-xs">
          <ExternalLink className="h-3 w-3 mr-2" />
          View detailed error information
        </Button>
      )}
    </div>
  )
}
