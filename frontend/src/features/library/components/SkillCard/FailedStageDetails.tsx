/**
 * FailedStageDetails - Expandable error details panel for failed analyses
 *
 * Displays user-friendly error information with:
 * - Error title and explanation
 * - Why it failed (reason)
 * - How to fix (actionable steps)
 * - Retry button (if retryable)
 */

import { useState } from 'react'

import { AlertCircle, ChevronDown, ChevronUp, RefreshCw } from 'lucide-react'

import { Button } from '@shared/components/ui/button'
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from '@shared/components/ui/collapsible'

import {
  getErrorExplanation,
  isErrorRetryable,
  type ErrorExplanation,
} from '@/features/analysis/utils/errorCodeFormatter'

import { cn } from '@lib/utils'

interface FailedStageDetailsProps {
  /** Error code from backend */
  errorCode?: string | null
  /** Error message from backend (if available) */
  errorMessage?: string | null
  /** Stage where error occurred */
  failedAtStage?: string | null
  /** Analysis ID for retry functionality */
  analysisId: string
  /** Callback when retry is clicked */
  onRetry?: (analysisId: string, stage?: string) => void
  /** Whether to show expanded by default */
  defaultExpanded?: boolean
  /** Optional className */
  className?: string
}

/**
 * Format stage name for display
 */
function formatStageName(stage: string | null | undefined): string {
  if (!stage) return 'Unknown Stage'

  return stage
    .split('_')
    .map((word) => word.charAt(0).toUpperCase() + word.slice(1).toLowerCase())
    .join(' ')
}

/**
 * FailedStageDetails component
 *
 * Displays expandable error information with user-friendly explanations
 */
export function FailedStageDetails({
  errorCode,
  errorMessage,
  failedAtStage,
  analysisId,
  onRetry,
  defaultExpanded = false,
  className,
}: FailedStageDetailsProps) {
  const [isOpen, setIsOpen] = useState(defaultExpanded)

  // Get error explanation
  const explanation: ErrorExplanation = getErrorExplanation(errorCode)
  const retryable = isErrorRetryable(errorCode)

  // Use backend error message if available, otherwise use explanation
  const displayMessage = errorMessage || explanation.reason

  return (
    <Collapsible open={isOpen} onOpenChange={setIsOpen} className={cn('w-full', className)}>
      <CollapsibleTrigger asChild>
        <Button
          variant="ghost"
          className="w-full justify-between p-3 h-auto hover:bg-destructive/10"
        >
          <div className="flex items-center gap-2 flex-1 text-left">
            <AlertCircle className="h-4 w-4 text-destructive flex-shrink-0" />
            <div className="flex-1 min-w-0">
              <div className="font-medium text-sm text-destructive">{explanation.title}</div>
              {failedAtStage && (
                <div className="text-xs text-muted-foreground mt-0.5">
                  Failed at: {formatStageName(failedAtStage)}
                </div>
              )}
            </div>
          </div>
          {isOpen ? (
            <ChevronUp className="h-4 w-4 text-muted-foreground flex-shrink-0" />
          ) : (
            <ChevronDown className="h-4 w-4 text-muted-foreground flex-shrink-0" />
          )}
        </Button>
      </CollapsibleTrigger>

      <CollapsibleContent className="pt-2">
        <div className="rounded-md bg-destructive/10 border border-destructive/20 p-4 space-y-3">
          {/* Why it failed */}
          <div>
            <div className="text-xs font-medium text-destructive mb-1">Why this failed:</div>
            <p className="text-sm text-foreground">{displayMessage}</p>
          </div>

          {/* How to fix */}
          <div>
            <div className="text-xs font-medium text-destructive mb-1">How to fix:</div>
            <p className="text-sm text-foreground">{explanation.action}</p>
          </div>

          {/* Retry button */}
          {retryable && onRetry && (
            <div className="pt-2 border-t border-destructive/20">
              <Button
                variant="outline"
                size="sm"
                onClick={() => onRetry(analysisId, failedAtStage || undefined)}
                className="w-full"
              >
                <RefreshCw className="h-4 w-4 mr-2" />
                Retry {failedAtStage ? formatStageName(failedAtStage) : 'Analysis'}
              </Button>
            </div>
          )}
        </div>
      </CollapsibleContent>
    </Collapsible>
  )
}
