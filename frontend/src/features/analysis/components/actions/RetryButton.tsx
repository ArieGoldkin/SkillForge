/**
 * RetryButton - Retry failed analyses with max retry limit
 *
 * Displays a "Retry" button for failed analyses, with:
 * - Retry counter showing current/max retries
 * - Disabled state when max retries reached
 * - Loading state during retry
 * - Error display for failed retry attempts
 *
 * Used in: AnalysisActionsCard for failed analyses
 */

import { AlertCircle, RefreshCcw } from 'lucide-react'

import { Alert, AlertDescription } from '@shared/components/ui/alert'
import { Button } from '@shared/components/ui/button'

import { cn } from '@lib/utils'

const MAX_RETRIES = 3

export interface RetryButtonProps {
  /** Current analysis ID */
  analysisId: string
  /** Current retry count from backend */
  retryCount: number
  /** Maximum allowed retries (default: 3) */
  maxRetries?: number
  /** Callback when retry is triggered */
  onRetry: () => void
  /** Loading state during retry */
  isRetrying: boolean
  /** Error from retry attempt */
  retryError?: string
}

export function RetryButton({
  analysisId: _analysisId,
  retryCount,
  maxRetries = MAX_RETRIES,
  onRetry,
  isRetrying,
  retryError,
}: RetryButtonProps) {
  const hasRetriesLeft = retryCount < maxRetries
  const retriesRemaining = maxRetries - retryCount

  return (
    <div className="flex flex-col gap-3">
      <div className="flex items-center gap-3">
        <Button
          onClick={onRetry}
          disabled={!hasRetriesLeft || isRetrying}
          variant={hasRetriesLeft ? 'default' : 'outline'}
          size="lg"
          className={cn('gap-2', !hasRetriesLeft && 'cursor-not-allowed opacity-50')}
        >
          <RefreshCcw className={cn('h-5 w-5', isRetrying && 'animate-spin')} />
          {isRetrying ? 'Retrying...' : hasRetriesLeft ? 'Retry Analysis' : 'Max Retries Reached'}
        </Button>

        {/* Retry counter */}
        {hasRetriesLeft && (
          <span className="text-sm text-muted-foreground">
            {retriesRemaining} {retriesRemaining === 1 ? 'retry' : 'retries'} remaining
          </span>
        )}
      </div>

      {/* Max retries warning */}
      {!hasRetriesLeft && (
        <Alert variant="destructive" className="bg-destructive/10">
          <AlertCircle className="h-4 w-4" />
          <AlertDescription>
            Maximum retry limit reached ({maxRetries}/{maxRetries}). Please check the error details
            or contact support if the issue persists.
          </AlertDescription>
        </Alert>
      )}

      {/* Retry error */}
      {retryError && (
        <Alert variant="destructive">
          <AlertCircle className="h-4 w-4" />
          <AlertDescription>{retryError}</AlertDescription>
        </Alert>
      )}
    </div>
  )
}
