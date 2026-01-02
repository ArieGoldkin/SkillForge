/**
 * FailedStageDetails - Expandable error details panel for failed analyses
 */

import { useState } from 'react'

import { AlertCircle, ChevronDown, ChevronUp, RefreshCw } from 'lucide-react'

import {
  getErrorExplanation,
  isErrorRetryable,
  type ErrorExplanation,
} from '@/features/analysis/utils/errorCodeFormatter'

import { Button } from '@shared/components/ui/button'
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from '@shared/components/ui/collapsible'

import { cn } from '@lib/utils'

interface FailedStageDetailsProps {
  errorCode?: string | null
  errorMessage?: string | null
  failedAtStage?: string | null
  analysisId: string
  onRetry?: (analysisId: string, stage?: string) => void
  defaultExpanded?: boolean
  className?: string
}

function formatStageName(stage: string | null | undefined): string {
  if (!stage) return 'Unknown Stage'
  return stage
    .split('_')
    .map((word) => word.charAt(0).toUpperCase() + word.slice(1).toLowerCase())
    .join(' ')
}

interface ErrorContentPanelProps {
  displayMessage: string
  explanation: ErrorExplanation
  retryable: boolean
  analysisId: string
  failedAtStage?: string | null
  onRetry?: (analysisId: string, stage?: string) => void
}

function ErrorContentPanel({
  displayMessage,
  explanation,
  retryable,
  analysisId,
  failedAtStage,
  onRetry,
}: ErrorContentPanelProps) {
  return (
    <div className="rounded-md bg-destructive/10 border border-destructive/20 p-4 space-y-3">
      <div>
        <div className="text-xs font-medium text-destructive mb-1">Why this failed:</div>
        <p className="text-sm text-foreground">{displayMessage}</p>
      </div>
      <div>
        <div className="text-xs font-medium text-destructive mb-1">How to fix:</div>
        <p className="text-sm text-foreground">{explanation.action}</p>
      </div>
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
  )
}

interface ErrorTriggerProps {
  title: string
  failedAtStage?: string | null
  isOpen: boolean
}

function ErrorTrigger({ title, failedAtStage, isOpen }: ErrorTriggerProps) {
  return (
    <Button variant="ghost" className="w-full justify-between p-3 h-auto hover:bg-destructive/10">
      <div className="flex items-center gap-2 flex-1 text-left">
        <AlertCircle className="h-4 w-4 text-destructive flex-shrink-0" />
        <div className="flex-1 min-w-0">
          <div className="font-medium text-sm text-destructive">{title}</div>
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
  )
}

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
  const explanation: ErrorExplanation = getErrorExplanation(errorCode)
  const retryable = isErrorRetryable(errorCode)
  const displayMessage = errorMessage || explanation.reason

  return (
    <Collapsible open={isOpen} onOpenChange={setIsOpen} className={cn('w-full', className)}>
      <CollapsibleTrigger asChild>
        <ErrorTrigger title={explanation.title} failedAtStage={failedAtStage} isOpen={isOpen} />
      </CollapsibleTrigger>
      <CollapsibleContent className="pt-2">
        <ErrorContentPanel
          displayMessage={displayMessage}
          explanation={explanation}
          retryable={retryable}
          analysisId={analysisId}
          failedAtStage={failedAtStage}
          onRetry={onRetry}
        />
      </CollapsibleContent>
    </Collapsible>
  )
}
