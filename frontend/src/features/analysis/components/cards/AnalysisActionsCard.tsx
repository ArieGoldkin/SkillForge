/**
 * AnalysisActionsCard - Context-aware action buttons for analyses
 *
 * Displays appropriate actions based on analysis status:
 * - Failed analyses: RetryButton (up to 3 retries)
 * - Completed analyses: RerunButton (unlimited reruns)
 * - Shows error details for failed analyses
 *
 * Used in: AnalyzeResult for failed/completed analyses
 */

import type { AnalysisStatus } from '@app-types/api'

import { Card, CardContent } from '@shared/components/ui/card'

import { RerunButton } from '../actions/RerunButton'
import { RetryButton } from '../actions/RetryButton'

import { ActionCardHeader, ErrorDetails } from './internal'
import { isFailureStatus } from './internal/helpers'

export interface AnalysisActionsCardProps {
  /** Analysis ID */
  analysisId: string
  /** Current analysis status */
  status: AnalysisStatus
  /** Current retry count (for failed analyses) */
  retryCount?: number
  /** Current rerun count (for completed analyses) */
  rerunCount?: number
  /** Error code (for failed analyses) */
  errorCode?: string | null
  /** Error message (for failed analyses) */
  errorMessage?: string | null
  /** Stage where failure occurred */
  failedAtStage?: string | null
  /** Retry callback */
  onRetry: () => void
  /** Rerun callback */
  onRerun: () => void
  /** Loading state during retry */
  isRetrying?: boolean
  /** Loading state during rerun */
  isRerunning?: boolean
  /** Error from retry/rerun attempt */
  actionError?: string
}

// eslint-disable-next-line max-lines-per-function -- Well-structured card component
export function AnalysisActionsCard({
  analysisId,
  status,
  retryCount = 0,
  rerunCount = 0,
  errorCode,
  errorMessage,
  failedAtStage,
  onRetry,
  onRerun,
  isRetrying = false,
  isRerunning = false,
  actionError,
}: AnalysisActionsCardProps) {
  const isFailed = isFailureStatus(status)
  const isComplete = status === 'complete'

  // Don't render if status doesn't support actions
  if (!isFailed && !isComplete) {
    return null
  }

  return (
    <Card className="border-border">
      <ActionCardHeader status={status} isFailed={isFailed} />

      <CardContent className="space-y-4">
        {/* Error details for failed analyses */}
        {isFailed && (
          <ErrorDetails
            errorCode={errorCode}
            errorMessage={errorMessage}
            failedAtStage={failedAtStage}
          />
        )}

        {/* Action buttons */}
        {isFailed ? (
          <RetryButton
            analysisId={analysisId}
            retryCount={retryCount}
            onRetry={onRetry}
            isRetrying={isRetrying}
            retryError={actionError}
          />
        ) : (
          <RerunButton
            analysisId={analysisId}
            rerunCount={rerunCount}
            onRerun={onRerun}
            isRerunning={isRerunning}
            rerunError={actionError}
          />
        )}
      </CardContent>
    </Card>
  )
}
