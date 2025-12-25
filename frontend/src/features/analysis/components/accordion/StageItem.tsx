/* eslint-disable max-lines -- Stage item component requires comprehensive UI for all status states (pending, running, completed, failed, skipped) with error expansion, success metrics, and accessibility attributes */
/**
 * StageItem - Individual stage row within a hierarchical accordion group
 *
 * Displays a compact stage status row showing:
 * - Status icon (pending, running, completed, failed, skipped)
 * - Stage name
 * - Status badge
 * - Timestamp (responsive - hidden on mobile)
 * - Error details (expandable for failed stages)
 * - Success metrics (shown for completed stages)
 * - Skip reason (tooltip/hover for skipped stages)
 *
 * Design:
 * - Compact layout optimized for accordion use
 * - Active stages highlighted with subtle pulsing animation
 * - Error states show expandable error details
 * - Accessible with ARIA labels and semantic HTML
 *
 * @module features/analysis/components/accordion/StageItem
 */

import { memo, useState } from 'react'

import { motion, AnimatePresence } from 'framer-motion'
import {
  AlertCircle,
  CheckCircle2,
  ChevronDown,
  ChevronRight,
  Circle,
  Clock,
  Loader2,
  MinusCircle,
  XCircle,
} from 'lucide-react'

import type { SuccessMetrics } from '@/schemas/sse'

import { Badge } from '@shared/components/ui/badge'
import { Button } from '@shared/components/ui/button'

import { cn } from '@lib/utils'

import type { ProgressStep } from '../../hooks/useProgressSteps'
import { formatErrorCode } from '../../utils/errorCodeFormatter'

// ============================================================================
// Type Definitions
// ============================================================================

interface StageItemProps {
  /** Stage data from useProgressSteps */
  stage: ProgressStep
  /** Whether this stage is currently running */
  isActive: boolean
  /** Whether to show timestamps (responsive - hidden on mobile) */
  showTimestamp: boolean
}

// ============================================================================
// Helper Functions
// ============================================================================

/**
 * Get status icon component for a stage
 */
const getStatusIcon = (status: ProgressStep['status']): React.ReactNode => {
  const iconClasses = 'h-4 w-4 flex-shrink-0'

  switch (status) {
    case 'completed':
      return <CheckCircle2 className={cn(iconClasses, 'text-status-success')} aria-hidden="true" />
    case 'in-progress':
      return (
        <Loader2
          className={cn(iconClasses, 'animate-spin text-status-warning')}
          aria-hidden="true"
        />
      )
    case 'failed':
      return <XCircle className={cn(iconClasses, 'text-status-error')} aria-hidden="true" />
    case 'skipped':
      return <MinusCircle className={cn(iconClasses, 'text-muted-foreground')} aria-hidden="true" />
    case 'pending':
      return <Circle className={cn(iconClasses, 'text-muted-foreground')} aria-hidden="true" />
  }
}

/**
 * Get badge variant for stage status
 */
const getStatusBadgeVariant = (
  status: ProgressStep['status']
): 'default' | 'success' | 'warning' | 'info' | 'secondary' | 'destructive' => {
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
 * Format status for display
 */
const formatStatus = (status: ProgressStep['status']): string => {
  switch (status) {
    case 'completed':
      return 'Complete'
    case 'in-progress':
      return 'Running'
    case 'failed':
      return 'Failed'
    case 'skipped':
      return 'Skipped'
    case 'pending':
      return 'Pending'
  }
}

/**
 * Format timestamp for display
 */
const formatTimestamp = (timestamp: Date): string => {
  return timestamp.toLocaleTimeString('en-US', {
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
  })
}

/**
 * Format success metrics for display
 * Returns array of { key, label } objects for proper React keys
 */
const formatSuccessMetrics = (metrics: SuccessMetrics): Array<{ key: string; label: string }> => {
  const formatted: Array<{ key: string; label: string }> = []

  if (metrics.findings_quality) {
    formatted.push({ key: 'quality', label: `Quality: ${metrics.findings_quality}` })
  }

  if (metrics.coverage) {
    formatted.push({ key: 'coverage', label: `Coverage: ${metrics.coverage}` })
  }

  if (metrics.key_insights && metrics.key_insights.length > 0) {
    formatted.push({ key: 'insights', label: `${metrics.key_insights.length} insights` })
  }

  return formatted
}

// ============================================================================
// Component
// ============================================================================

/**
 * StageItem - Individual stage row within an expanded accordion group
 *
 * WCAG Compliance:
 * - 1.3.1 (Info and Relationships): Semantic HTML with role="listitem"
 * - 1.4.1 (Use of Color): Status conveyed via icons + text
 * - 2.1.1 (Keyboard): Error expansion accessible via keyboard
 * - 4.1.2 (Name, Role, Value): Proper ARIA labels for screen readers
 *
 * Wrapped with React.memo to prevent unnecessary re-renders when props unchanged.
 */
/* eslint-disable max-lines-per-function, complexity -- Stage item component requires complete JSX layout for all status states (pending, running, completed, failed, skipped) with conditional rendering for error expansion, success metrics, skip reasons, and timestamps. Multiple conditional branches for different status types are necessary for comprehensive UI. */
export const StageItem = memo(function StageItem({
  stage,
  isActive,
  showTimestamp,
}: StageItemProps) {
  const [isErrorExpanded, setIsErrorExpanded] = useState(false)

  const hasError = stage.status === 'failed' && stage.errorDetails
  const hasSuccessMetrics = stage.status === 'completed' && stage.successMetrics
  const isSkipped = stage.status === 'skipped'

  return (
    <div
      className={cn(
        'group relative py-2 px-3 rounded-md transition-all duration-300',
        // Active stage highlight
        isActive && 'bg-primary/5 border-l-2 border-primary shadow-sm animate-pulse-subtle',
        // Hover effect
        'hover:bg-muted/50'
      )}
      role="listitem"
      aria-label={`${stage.title}: ${formatStatus(stage.status)}`}
      data-testid="accordion-stage-item"
      data-stage-id={stage.id}
      data-stage-status={stage.status}
    >
      <div className="flex items-start gap-3">
        {/* Status Icon */}
        <div className="mt-0.5">{getStatusIcon(stage.status)}</div>

        {/* Stage Info */}
        <div className="flex-1 min-w-0 space-y-1">
          {/* Stage Name + Status Badge */}
          <div className="flex items-center justify-between gap-2">
            <h5
              className={cn(
                'text-sm font-medium truncate',
                isActive ? 'text-foreground' : 'text-foreground/80'
              )}
              title={stage.title}
            >
              {stage.title}
            </h5>

            <div className="flex items-center gap-2 flex-shrink-0">
              {/* Timestamp (responsive) */}
              {showTimestamp && stage.timestamp && (
                <div
                  className="hidden md:flex items-center gap-1 text-xs text-muted-foreground"
                  aria-label={`Completed at ${formatTimestamp(stage.timestamp)}`}
                >
                  <Clock className="h-3 w-3" aria-hidden="true" />
                  <span>{formatTimestamp(stage.timestamp)}</span>
                </div>
              )}

              {/* Status Badge */}
              <Badge
                variant={getStatusBadgeVariant(stage.status)}
                className="text-xs"
                role="status"
                aria-live={isActive ? 'polite' : 'off'}
              >
                {formatStatus(stage.status)}
              </Badge>
            </div>
          </div>

          {/* Description (for running stages) */}
          {isActive && stage.description && (
            <p className="text-xs text-muted-foreground">{stage.description}</p>
          )}

          {/* Success Metrics (for completed stages) */}
          {hasSuccessMetrics && stage.successMetrics && (
            <div
              className="flex flex-wrap items-center gap-2 text-xs text-muted-foreground"
              aria-label="Success metrics"
            >
              {formatSuccessMetrics(stage.successMetrics).map((metric) => (
                <span
                  key={metric.key}
                  className="inline-flex items-center gap-1 px-2 py-0.5 rounded-md bg-success/10 text-success-foreground"
                >
                  {metric.label}
                </span>
              ))}
            </div>
          )}

          {/* Skip Reason (for skipped stages) */}
          {isSkipped && stage.skipReason && (
            <div
              className="flex items-start gap-1.5 text-xs text-muted-foreground"
              role="note"
              aria-label={`Skip reason: ${stage.skipReason}`}
              title={stage.skipReason}
            >
              <AlertCircle className="h-3 w-3 mt-0.5 flex-shrink-0" aria-hidden="true" />
              <span className="line-clamp-2">{stage.skipReason}</span>
            </div>
          )}

          {/* Error Details (expandable for failed stages) */}
          {hasError && (
            <div className="space-y-2">
              <Button
                variant="ghost"
                size="sm"
                onClick={() => setIsErrorExpanded(!isErrorExpanded)}
                className="h-auto p-0 text-xs text-destructive hover:text-destructive/80 hover:bg-transparent"
                aria-expanded={isErrorExpanded}
                aria-controls={`error-details-${stage.id}`}
              >
                <span className="flex items-center gap-1.5">
                  {isErrorExpanded ? (
                    <ChevronDown className="h-3 w-3" aria-hidden="true" />
                  ) : (
                    <ChevronRight className="h-3 w-3" aria-hidden="true" />
                  )}
                  <span className="font-medium">Error Details</span>
                </span>
              </Button>

              <AnimatePresence>
                {isErrorExpanded && (
                  <motion.div
                    id={`error-details-${stage.id}`}
                    initial={{ height: 0, opacity: 0 }}
                    animate={{ height: 'auto', opacity: 1 }}
                    exit={{ height: 0, opacity: 0 }}
                    transition={{ duration: 0.2, ease: 'easeInOut' }}
                    className="overflow-hidden"
                    role="region"
                    aria-label={`Error details for ${stage.title}`}
                  >
                    <div className="p-3 rounded-md bg-destructive/10 border border-destructive/20 space-y-2">
                      <div className="text-xs text-destructive">
                        <span className="font-medium">Error:</span>{' '}
                        {stage.errorDetails?.error || 'Unknown error'}
                      </div>

                      {stage.errorDetails?.errorCode && (
                        <div className="flex items-center gap-2">
                          <span className="text-xs text-muted-foreground">Code:</span>
                          <Badge variant="destructive" className="text-xs">
                            {formatErrorCode(stage.errorDetails.errorCode)}
                          </Badge>
                        </div>
                      )}

                      {stage.errorDetails?.processingTime && (
                        <div className="text-xs text-muted-foreground">
                          Processing time: {stage.errorDetails.processingTime}ms
                        </div>
                      )}
                    </div>
                  </motion.div>
                )}
              </AnimatePresence>
            </div>
          )}
        </div>
      </div>
    </div>
  )
})
