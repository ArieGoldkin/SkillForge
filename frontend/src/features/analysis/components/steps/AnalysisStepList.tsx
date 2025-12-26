/* eslint-disable max-lines -- Component includes rich expandable sections for success metrics, skip reasons, and error details which require additional lines */
import * as React from 'react'

import { AlertCircle, CheckCircle2, Circle, Info, Loader2, XCircle } from 'lucide-react'

import { BUSINESS_CONSTANTS, TIME_CONSTANTS, UI_CONSTANTS } from '@/lib/constants'

import { Badge } from '@shared/components/ui/badge'
import { Card, CardContent, CardHeader, CardTitle } from '@shared/components/ui/card'

import { cn } from '@lib/utils'

/**
 * Status type for each analysis step
 */
export type AnalysisStepStatus = 'pending' | 'in-progress' | 'completed' | 'failed' | 'skipped'

/**
 * Individual analysis step
 *
 * @property id - Unique identifier for the step
 * @property title - Step name/title
 * @property description - Detailed description of the step
 * @property status - Current status of the step
 * @property timestamp - Optional timestamp when step was updated
 * @property duration - Optional duration in milliseconds
 * @property successMetrics - Optional success metrics for completed stages
 * @property skipReason - Optional reason why stage was skipped
 * @property errorDetails - Optional error details for failed stages
 */
export interface AnalysisStep {
  id: string
  title: string
  description: string
  status: AnalysisStepStatus
  timestamp?: Date
  duration?: number
  successMetrics?: {
    findingsQuality?: 'high' | 'medium' | 'low'
    coverage?: 'comprehensive' | 'partial' | 'minimal'
    keyInsights?: string[]
  }
  skipReason?: string
  errorDetails?: {
    error: string
    errorCode?: string
    processingTime?: number
  }
}

/**
 * Props for AnalysisStepList component
 */
export interface AnalysisStepListProps {
  steps: AnalysisStep[]
  className?: string
}

/**
 * Format timestamp relative to now
 */
const formatRelativeTime = (timestamp: Date): string => {
  const now = Date.now()
  const diff = now - timestamp.getTime()

  const seconds = Math.floor(diff / BUSINESS_CONSTANTS.MILLISECONDS_PER_SECOND)
  const minutes = Math.floor(seconds / TIME_CONSTANTS.SECONDS_PER_MINUTE)
  const hours = Math.floor(minutes / TIME_CONSTANTS.MINUTES_PER_HOUR)

  if (seconds < TIME_CONSTANTS.SECONDS_PER_MINUTE) return `${seconds} seconds ago`
  if (minutes < TIME_CONSTANTS.MINUTES_PER_HOUR)
    return `${minutes} ${minutes === 1 ? 'minute' : 'minutes'} ago`
  return `${hours} ${hours === 1 ? 'hour' : 'hours'} ago`
}

/**
 * Format duration in milliseconds to human-readable string
 */
const formatDuration = (ms: number): string => {
  const seconds = Math.floor(ms / BUSINESS_CONSTANTS.MILLISECONDS_PER_SECOND)
  const minutes = Math.floor(seconds / TIME_CONSTANTS.SECONDS_PER_MINUTE)

  if (seconds < TIME_CONSTANTS.SECONDS_PER_MINUTE) return `${seconds}s`
  return `${minutes}m ${seconds % TIME_CONSTANTS.SECONDS_PER_MINUTE}s`
}

/**
 * Get icon component for step status
 */
const getStatusIcon = (status: AnalysisStepStatus): React.ReactNode => {
  const iconClasses = 'h-5 w-5'

  switch (status) {
    case 'completed':
      return <CheckCircle2 className={cn(iconClasses, 'text-status-success')} />
    case 'in-progress':
      return <Loader2 className={cn(iconClasses, 'animate-spin text-status-warning')} />
    case 'failed':
      return <XCircle className={cn(iconClasses, 'text-destructive')} />
    case 'skipped':
      return <Circle className={cn(iconClasses, 'text-muted-foreground opacity-50')} />
    case 'pending':
      return <Circle className={cn(iconClasses, 'text-muted-foreground')} />
  }
}

/**
 * Get badge variant for step status
 */
const getStatusBadgeVariant = (
  status: AnalysisStepStatus
): 'default' | 'success' | 'warning' | 'destructive' | 'secondary' => {
  switch (status) {
    case 'completed':
      return 'success'
    case 'in-progress':
      return 'warning'
    case 'failed':
      return 'destructive'
    case 'skipped':
      return 'secondary'
    case 'pending':
      return 'default'
  }
}

/**
 * Individual step item component
 */
/* eslint-disable max-lines-per-function, complexity -- StepItem requires complete timeline step layout (dot, connecting line, expandable content with button, timestamp/duration, description). Interactive expandable state and conditional rendering with success metrics, skip reasons, and error details necessitate current structure. */
function StepItem({ step, isLast }: { step: AnalysisStep; isLast: boolean }): React.ReactNode {
  const [isExpanded, setIsExpanded] = React.useState(false)

  return (
    <div className="relative pl-8">
      {/* Timeline dot */}
      <div className="absolute left-0 top-1">{getStatusIcon(step.status)}</div>

      {/* Connecting line */}
      {!isLast && (
        <div
          className={cn(
            'absolute left-[9px] top-6 bottom-0 w-0.5',
            step.status === 'completed' ? 'bg-status-success/30' : 'bg-border'
          )}
        />
      )}

      {/* Step content */}
      <div
        className={cn(
          'pb-6 transition-all',
          step.status === 'in-progress' && 'border-l-2 border-primary pl-2 -ml-2'
        )}
      >
        <button
          type="button"
          onClick={() => setIsExpanded(!isExpanded)}
          className="w-full text-left focus:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 rounded-md"
        >
          <div
            className={`${UI_CONSTANTS.FLEX_START} ${UI_CONSTANTS.FLEX_BETWEEN} ${UI_CONSTANTS.FLEX_GAP_SM} ${UI_CONSTANTS.MARGIN_BOTTOM_SM}`}
          >
            <h4 className="font-medium text-sm">{step.title}</h4>
            <Badge variant={getStatusBadgeVariant(step.status)} className="text-xs">
              {step.status === 'in-progress' ? 'Running' : step.status}
            </Badge>
          </div>

          {/* Timestamp and duration */}
          <div
            className={`${UI_CONSTANTS.FLEX_ITEMS_CENTER} ${UI_CONSTANTS.FLEX_GAP_SM} ${UI_CONSTANTS.FONT_SIZE_XS} ${UI_CONSTANTS.TEXT_COLOR_MUTED}`}
          >
            {step.timestamp && <span>{formatRelativeTime(step.timestamp)}</span>}
            {step.duration && step.status === 'completed' && (
              <>
                <span>•</span>
                <span>{formatDuration(step.duration)}</span>
              </>
            )}
          </div>

          {/* Error preview (collapsed) - Show brief error message */}
          {step.status === 'failed' && step.errorDetails && !isExpanded && (
            <div className="mt-1 text-xs text-destructive truncate">{step.errorDetails.error}</div>
          )}

          {/* Skip reason preview (collapsed) */}
          {step.status === 'skipped' && step.skipReason && !isExpanded && (
            <div className="mt-1 text-xs text-muted-foreground italic truncate">
              {step.skipReason}
            </div>
          )}
        </button>

        {/* Expandable description with rich details */}
        {isExpanded && (
          <div className="mt-2 space-y-3 text-sm animate-in slide-in-from-top-2 duration-200">
            {/* Main description */}
            <p className="text-muted-foreground">{step.description}</p>

            {/* Success metrics for completed stages */}
            {step.status === 'completed' && step.successMetrics && (
              <div className="rounded-md bg-green-500/10 border border-green-500/20 p-3 space-y-2">
                <div className="flex items-center gap-2 text-green-600 dark:text-green-400">
                  <CheckCircle2 className={`${UI_CONSTANTS.HEIGHT_SM} ${UI_CONSTANTS.WIDTH_SM}`} />
                  <span className="font-medium">Success Metrics</span>
                </div>
                <div className="space-y-1.5 text-xs">
                  {step.successMetrics.findingsQuality && (
                    <div className="flex items-center gap-2">
                      <span className="text-muted-foreground">Quality:</span>
                      <Badge
                        variant={
                          step.successMetrics.findingsQuality === 'high'
                            ? 'success'
                            : step.successMetrics.findingsQuality === 'medium'
                              ? 'default'
                              : 'secondary'
                        }
                        className="text-xs"
                      >
                        {step.successMetrics.findingsQuality}
                      </Badge>
                    </div>
                  )}
                  {step.successMetrics.coverage && (
                    <div className="flex items-center gap-2">
                      <span className="text-muted-foreground">Coverage:</span>
                      <Badge variant="outline" className="text-xs">
                        {step.successMetrics.coverage}
                      </Badge>
                    </div>
                  )}
                  {step.successMetrics.keyInsights &&
                    step.successMetrics.keyInsights.length > 0 && (
                      <div>
                        <span className="text-muted-foreground">Key Insights:</span>
                        <ul className="mt-1 ml-4 list-disc space-y-0.5">
                          {step.successMetrics.keyInsights.slice(0, 3).map((insight, idx) => (
                            // eslint-disable-next-line react/no-array-index-key -- Limited to 3 items, stable order
                            <li key={idx} className="text-muted-foreground">
                              {insight}
                            </li>
                          ))}
                        </ul>
                      </div>
                    )}
                </div>
              </div>
            )}

            {/* Skip reason for skipped stages */}
            {step.status === 'skipped' && step.skipReason && (
              <div className="rounded-md bg-muted border border-border p-3">
                <div className="flex items-center gap-2 text-muted-foreground mb-1">
                  <Info className={`${UI_CONSTANTS.HEIGHT_SM} ${UI_CONSTANTS.WIDTH_SM}`} />
                  <span className="font-medium">Skip Reason</span>
                </div>
                <p className="text-xs text-muted-foreground">{step.skipReason}</p>
              </div>
            )}

            {/* Error details for failed stages */}
            {step.status === 'failed' && step.errorDetails && (
              <div className="rounded-md bg-destructive/10 border border-destructive/20 p-3 space-y-2">
                <div className="flex items-center gap-2 text-destructive">
                  <AlertCircle className={`${UI_CONSTANTS.HEIGHT_SM} ${UI_CONSTANTS.WIDTH_SM}`} />
                  <span className="font-medium">Error Details</span>
                </div>
                <div className="space-y-1.5 text-xs">
                  <div>
                    <span className="text-muted-foreground">Error:</span>
                    <p className="mt-0.5 text-destructive break-words">{step.errorDetails.error}</p>
                  </div>
                  {step.errorDetails.errorCode && (
                    <div className="flex items-center gap-2">
                      <span className="text-muted-foreground">Code:</span>
                      <Badge variant="destructive" className="text-xs">
                        {step.errorDetails.errorCode}
                      </Badge>
                    </div>
                  )}
                  {step.errorDetails.processingTime !== undefined && (
                    <div className="flex items-center gap-2">
                      <span className="text-muted-foreground">Duration:</span>
                      <span className="text-muted-foreground">
                        {formatDuration(step.errorDetails.processingTime)}
                      </span>
                    </div>
                  )}
                </div>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  )
}

/**
 * AnalysisStepList - Vertical timeline of analysis steps
 *
 * Displays a timeline view of all analysis steps with status indicators,
 * timestamps, and expandable descriptions. Active step is highlighted with
 * teal accent.
 *
 * @example
 * ```tsx
 * <AnalysisStepList
 *   steps={[
 *     {
 *       id: '1',
 *       title: 'Extracting Content',
 *       description: 'Fetching and parsing content from URL',
 *       status: 'completed',
 *       timestamp: new Date(Date.now() - 120000),
 *       duration: 5000
 *     },
 *     {
 *       id: '2',
 *       title: 'Multi-Agent Analysis',
 *       description: 'Running specialized analysis agents',
 *       status: 'in-progress',
 *       timestamp: new Date()
 *     }
 *   ]}
 * />
 * ```
 */
export function AnalysisStepList({ steps, className }: AnalysisStepListProps): React.ReactNode {
  return (
    <Card className={cn('animate-in fade-in-50 duration-300', className)}>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">Analysis Stages</CardTitle>
      </CardHeader>
      <CardContent>
        {steps.length === 0 ? (
          <p className="text-sm text-muted-foreground text-center py-4">No steps available</p>
        ) : (
          <div className="space-y-0">
            {steps.map((step, index) => (
              <StepItem key={step.id} step={step} isLast={index === steps.length - 1} />
            ))}
          </div>
        )}
      </CardContent>
    </Card>
  )
}

AnalysisStepList.displayName = 'AnalysisStepList'
