/**
 * QualityWarningBanner - Display quality warnings for artifacts
 *
 * Shows when an artifact has quality issues (warnings, low scores, or failed quality gate).
 * Uses amber/yellow styling to indicate warning (not error - artifact was still generated).
 */

import { useState } from 'react'

import { AlertTriangle, ChevronDown, ChevronUp } from 'lucide-react'

import { Alert, AlertDescription, AlertTitle } from '@shared/components/ui/alert'

import { cn } from '@lib/utils'

export interface QualityWarningBannerProps {
  warnings: string[]
  avgScore?: number
  passed?: boolean
}

function WarningsList({ warnings, isExpanded }: { warnings: string[]; isExpanded: boolean }) {
  if (warnings.length === 1) {
    return <p className="text-sm">{warnings[0]}</p>
  }

  return (
    <div className={cn('text-sm', !isExpanded && 'line-clamp-2')}>
      <ul className="ml-4 list-disc space-y-1">
        {warnings.map((warning) => (
          <li key={warning}>{warning}</li>
        ))}
      </ul>
    </div>
  )
}

function ExpandButton({
  isExpanded,
  warningsCount,
  onClick,
}: {
  isExpanded: boolean
  warningsCount: number
  onClick: () => void
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      className="flex items-center gap-1 text-sm font-normal hover:underline"
      aria-expanded={isExpanded}
      aria-label={isExpanded ? 'Collapse warnings' : 'Expand warnings'}
    >
      {isExpanded ? (
        <>
          Hide details <ChevronUp className="h-4 w-4" />
        </>
      ) : (
        <>
          Show {warningsCount} warnings <ChevronDown className="h-4 w-4" />
        </>
      )}
    </button>
  )
}

export function QualityWarningBanner({ warnings, avgScore, passed }: QualityWarningBannerProps) {
  const [isExpanded, setIsExpanded] = useState(false)

  if (warnings.length === 0 && passed !== false) {
    return null
  }

  const hasWarnings = warnings.length > 0
  const showScore = avgScore !== undefined && avgScore !== null

  return (
    <Alert
      className={cn(
        'border-amber-200 bg-amber-50 text-amber-800',
        'dark:border-amber-800 dark:bg-amber-950 dark:text-amber-200'
      )}
    >
      <AlertTriangle className="h-4 w-4 text-amber-600 dark:text-amber-400" />
      <AlertTitle className="flex items-center justify-between">
        <span>Quality Notice</span>
        {hasWarnings && warnings.length > 1 && (
          <ExpandButton
            isExpanded={isExpanded}
            warningsCount={warnings.length}
            onClick={() => setIsExpanded(!isExpanded)}
          />
        )}
      </AlertTitle>
      <AlertDescription className="mt-2">
        {passed === false && (
          <p className="mb-2 font-medium">
            This artifact did not meet all quality thresholds but was generated to provide useful
            content.
          </p>
        )}
        {showScore && (
          <p className="mb-2">
            Quality score: <span className="font-medium">{avgScore.toFixed(2)}</span> / 1.0
          </p>
        )}
        {hasWarnings && <WarningsList warnings={warnings} isExpanded={isExpanded} />}
      </AlertDescription>
    </Alert>
  )
}
