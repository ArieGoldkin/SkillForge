import { Badge } from '@shared/components/ui/badge'

import { formatErrorCode } from '../../utils/errorCodeFormatter'

interface AnalysisProgressCardErrorSummaryProps {
  failedStagesCount: number
  failedStageErrorCodes: string[]
}

/**
 * Error summary section for completed analyses with failures
 */
export function AnalysisProgressCardErrorSummary({
  failedStagesCount,
  failedStageErrorCodes,
}: AnalysisProgressCardErrorSummaryProps) {
  return (
    <div className="rounded-md bg-destructive/10 border border-destructive/20 p-3 space-y-2">
      <div className="flex items-start gap-2">
        <div className="flex-1">
          <p className="text-sm font-medium text-destructive">
            {failedStagesCount} {failedStagesCount === 1 ? 'stage' : 'stages'} failed
          </p>
          <p className="text-xs text-muted-foreground mt-1">
            The analysis completed but encountered errors. Check the stages below for details.
          </p>
        </div>
      </div>
      {failedStageErrorCodes.length > 0 && (
        <div className="flex flex-wrap items-center gap-2 mt-2 pt-2 border-t border-destructive/20">
          <span className="text-xs text-muted-foreground">Error codes:</span>
          {failedStageErrorCodes.map((errorCode) => (
            <Badge key={errorCode} variant="destructive" className="text-xs">
              {formatErrorCode(errorCode)}
            </Badge>
          ))}
        </div>
      )}
    </div>
  )
}
