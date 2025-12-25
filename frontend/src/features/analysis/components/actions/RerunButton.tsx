/**
 * RerunButton - Rerun completed analyses with latest AI
 *
 * Displays a "Rerun with Latest AI" button for completed analyses:
 * - Skips content extraction (uses existing content)
 * - Runs analysis with current AI models/prompts
 * - Archives previous artifact, creates new one
 * - Shows loading state during rerun
 * - Displays errors if rerun fails
 *
 * Used in: AnalysisActionsCard for completed analyses
 */

import { AlertCircle, Sparkles } from 'lucide-react'

import { Alert, AlertDescription } from '@shared/components/ui/alert'
import { Button } from '@shared/components/ui/button'
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from '@shared/components/ui/tooltip'

import { cn } from '@lib/utils'

export interface RerunButtonProps {
  /** Current analysis ID */
  analysisId: string
  /** Current rerun count from backend */
  rerunCount?: number
  /** Callback when rerun is triggered */
  onRerun: () => void
  /** Loading state during rerun */
  isRerunning: boolean
  /** Error from rerun attempt */
  rerunError?: string
}

// eslint-disable-next-line max-lines-per-function -- UI component with tooltip JSX
export function RerunButton({
  analysisId: _analysisId,
  rerunCount = 0,
  onRerun,
  isRerunning,
  rerunError,
}: RerunButtonProps) {
  const tooltipContent = (
    <div className="space-y-2">
      <p className="font-semibold">Rerun with Latest AI</p>
      <ul className="space-y-1 text-xs">
        <li>✓ Uses existing content (no re-extraction)</li>
        <li>✓ Runs with current AI models & prompts</li>
        <li>✓ Archives previous artifact</li>
        <li>✓ Generates fresh analysis</li>
      </ul>
      {rerunCount > 0 && (
        <p className="text-xs text-muted-foreground pt-1 border-t">
          Previously rerun {rerunCount} {rerunCount === 1 ? 'time' : 'times'}
        </p>
      )}
    </div>
  )

  return (
    <div className="flex flex-col gap-3">
      <TooltipProvider>
        <Tooltip>
          <TooltipTrigger asChild>
            <Button
              onClick={onRerun}
              disabled={isRerunning}
              variant="secondary"
              size="lg"
              className={cn('gap-2', isRerunning && 'cursor-wait')}
            >
              <Sparkles className={cn('h-5 w-5', isRerunning && 'animate-pulse')} />
              {isRerunning ? 'Rerunning...' : 'Rerun with Latest AI'}
            </Button>
          </TooltipTrigger>
          <TooltipContent side="bottom" className="max-w-xs">
            {tooltipContent}
          </TooltipContent>
        </Tooltip>
      </TooltipProvider>

      {/* Rerun count badge */}
      {rerunCount > 0 && !isRerunning && (
        <span className="text-xs text-muted-foreground">
          Analysis has been rerun {rerunCount} {rerunCount === 1 ? 'time' : 'times'}
        </span>
      )}

      {/* Rerun error */}
      {rerunError && (
        <Alert variant="destructive">
          <AlertCircle className="h-4 w-4" />
          <AlertDescription>{rerunError}</AlertDescription>
        </Alert>
      )}
    </div>
  )
}
