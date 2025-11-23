import * as React from 'react'

import { CheckCircle2, Circle, Loader2, XCircle } from 'lucide-react'

import { Badge } from '@/components/ui/badge'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { cn } from '@/lib/utils'

/**
 * Status type for each analysis step
 */
export type AnalysisStepStatus = 'pending' | 'in-progress' | 'completed' | 'failed'

/**
 * Individual analysis step
 *
 * @property id - Unique identifier for the step
 * @property title - Step name/title
 * @property description - Detailed description of the step
 * @property status - Current status of the step
 * @property timestamp - Optional timestamp when step was updated
 * @property duration - Optional duration in milliseconds
 */
export interface AnalysisStep {
  id: string
  title: string
  description: string
  status: AnalysisStepStatus
  timestamp?: Date
  duration?: number
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

  const seconds = Math.floor(diff / 1000)
  const minutes = Math.floor(seconds / 60)
  const hours = Math.floor(minutes / 60)

  if (seconds < 60) return `${seconds} seconds ago`
  if (minutes < 60) return `${minutes} ${minutes === 1 ? 'minute' : 'minutes'} ago`
  return `${hours} ${hours === 1 ? 'hour' : 'hours'} ago`
}

/**
 * Format duration in milliseconds to human-readable string
 */
const formatDuration = (ms: number): string => {
  const seconds = Math.floor(ms / 1000)
  const minutes = Math.floor(seconds / 60)

  if (seconds < 60) return `${seconds}s`
  return `${minutes}m ${seconds % 60}s`
}

/**
 * Get icon component for step status
 */
const getStatusIcon = (status: AnalysisStepStatus): React.ReactNode => {
  const iconClasses = 'h-5 w-5'

  switch (status) {
    case 'completed':
      return <CheckCircle2 className={cn(iconClasses, 'text-[oklch(0.6959_0.1491_162.4796)]')} />
    case 'in-progress':
      return (
        <Loader2 className={cn(iconClasses, 'animate-spin text-[oklch(0.7686_0.1647_70.0804)]')} />
      )
    case 'failed':
      return <XCircle className={cn(iconClasses, 'text-destructive')} />
    case 'pending':
      return <Circle className={cn(iconClasses, 'text-muted-foreground')} />
  }
}

/**
 * Get badge variant for step status
 */
const getStatusBadgeVariant = (
  status: AnalysisStepStatus
): 'default' | 'success' | 'warning' | 'destructive' => {
  switch (status) {
    case 'completed':
      return 'success'
    case 'in-progress':
      return 'warning'
    case 'failed':
      return 'destructive'
    case 'pending':
      return 'default'
  }
}

/**
 * Individual step item component
 */
/* eslint-disable max-lines-per-function -- StepItem requires complete timeline step layout (dot, connecting line, expandable content with button, timestamp/duration, description). Interactive expandable state and conditional rendering necessitate current structure. */
const StepItem: React.FC<{ step: AnalysisStep; isLast: boolean }> = ({ step, isLast }) => {
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
            step.status === 'completed' ? 'bg-[oklch(0.6959_0.1491_162.4796)]/30' : 'bg-border'
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
          <div className="flex items-start justify-between gap-2 mb-1">
            <h4 className="font-medium text-sm">{step.title}</h4>
            <Badge variant={getStatusBadgeVariant(step.status)} className="text-xs">
              {step.status === 'in-progress' ? 'Running' : step.status}
            </Badge>
          </div>

          {/* Timestamp and duration */}
          <div className="flex items-center gap-2 text-xs text-muted-foreground">
            {step.timestamp && <span>{formatRelativeTime(step.timestamp)}</span>}
            {step.duration && step.status === 'completed' && (
              <>
                <span>•</span>
                <span>{formatDuration(step.duration)}</span>
              </>
            )}
          </div>
        </button>

        {/* Expandable description */}
        {isExpanded && (
          <div className="mt-2 text-sm text-muted-foreground animate-in slide-in-from-top-2 duration-200">
            {step.description}
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

export const AnalysisStepList: React.FC<AnalysisStepListProps> = ({ steps, className }) => {
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
