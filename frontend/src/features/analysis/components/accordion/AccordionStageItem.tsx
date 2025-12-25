/* eslint-disable max-lines -- Stage item component requires comprehensive UI for all status states (pending, running, completed, failed, skipped) with error expansion, skip reasons, and accessibility attributes */
/**
 * AccordionStageItem - Compact stage row for accordion groups
 *
 * Matches the compact layout that StageItemSkeleton is designed for:
 * - Status icon (left edge)
 * - Stage name and metadata
 * - Status badge (right edge)
 * - Optional timestamp (responsive - hidden on mobile)
 *
 * This is the accordion-specific version, different from progress/StageItem.tsx
 * which has a vertical timeline layout.
 *
 * @module features/analysis/components/accordion/AccordionStageItem
 */

import { memo, useState } from 'react'
import type React from 'react'

import type { StageStatus } from '@app-types/sse'
import { AnimatePresence, motion } from 'framer-motion'
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

import { Badge } from '@shared/components/ui/badge'
import { Button } from '@shared/components/ui/button'

import { assertNever, cn } from '@lib/utils'

import { formatErrorCode } from '../../utils/errorCodeFormatter'

// ============================================================================
// Type Definitions
// ============================================================================

export interface AccordionStageItemProps {
  /** Stage name/id */
  stageName: string
  /** Display label */
  label: string
  /** Current status */
  status: StageStatus
  /** Optional agent executing this stage */
  agent?: string
  /** Optional error message */
  error?: string
  /** Optional error code */
  errorCode?: string
  /** Optional skip reason */
  skipReason?: string
  /** Whether to show timestamp (responsive - hidden on mobile) */
  showTimestamp?: boolean
  /** Optional timestamp */
  timestamp?: Date
  /** Optional additional CSS classes */
  className?: string
}

// ============================================================================
// Helper Functions
// ============================================================================

/**
 * Get status icon component for a stage
 */
const getStatusIcon = (status: StageStatus): React.ReactNode => {
  const iconClasses = 'h-4 w-4 flex-shrink-0'

  switch (status) {
    case 'complete':
      return <CheckCircle2 className={cn(iconClasses, 'text-status-success')} aria-hidden="true" />
    case 'running':
    case 'synthesizing':
    case 'detecting_conflicts':
      return (
        <Loader2
          className={cn(iconClasses, 'animate-spin text-status-warning')}
          aria-hidden="true"
        />
      )
    case 'failed':
    case 'static_fallback':
      return <XCircle className={cn(iconClasses, 'text-status-error')} aria-hidden="true" />
    case 'skipped':
      return <MinusCircle className={cn(iconClasses, 'text-muted-foreground')} aria-hidden="true" />
    case 'pending':
      return <Circle className={cn(iconClasses, 'text-muted-foreground')} aria-hidden="true" />
    default:
      return assertNever(status)
  }
}

/**
 * Get badge variant for stage status
 */
const getStatusBadgeVariant = (
  status: StageStatus
): 'default' | 'success' | 'warning' | 'info' | 'secondary' | 'destructive' => {
  switch (status) {
    case 'complete':
      return 'success'
    case 'running':
    case 'synthesizing':
    case 'detecting_conflicts':
      return 'warning'
    case 'failed':
    case 'static_fallback':
      return 'destructive'
    case 'skipped':
      return 'secondary'
    case 'pending':
      return 'default'
    default:
      return assertNever(status)
  }
}

/**
 * Format status for display
 */
const formatStatus = (status: StageStatus): string => {
  switch (status) {
    case 'complete':
      return 'Complete'
    case 'running':
      return 'Running'
    case 'synthesizing':
      return 'Synthesizing'
    case 'detecting_conflicts':
      return 'Detecting Conflicts'
    case 'static_fallback':
      return 'Static Fallback'
    case 'failed':
      return 'Failed'
    case 'skipped':
      return 'Skipped'
    case 'pending':
      return 'Pending'
    default:
      return assertNever(status)
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
 * Format agent name for display
 */
const formatAgentName = (agent: string): string => {
  return agent
    .split('_')
    .map((word) => word.charAt(0).toUpperCase() + word.slice(1).toLowerCase())
    .join(' ')
}

// ============================================================================
// Component
// ============================================================================

/**
 * AccordionStageItem - Compact stage row within accordion group
 *
 * WCAG 2.1 AA Compliance:
 * - 1.3.1 (Info and Relationships): Semantic HTML with role="listitem"
 * - 1.4.1 (Use of Color): Status conveyed via icons + text, not just color
 * - 2.1.1 (Keyboard): Error expansion accessible via keyboard
 * - 4.1.2 (Name, Role, Value): Proper ARIA labels for screen readers
 *
 * Layout matches StageItemSkeleton.tsx:
 * - Status icon (h-4 w-4)
 * - Stage name + status badge
 * - Optional timestamp (hidden on mobile via md:flex)
 * - Compact py-2 px-3 spacing
 */
/* eslint-disable max-lines-per-function, complexity -- Stage item component requires complete JSX layout for all status states with conditional rendering for error expansion, skip reasons, and timestamps */
export const AccordionStageItem: React.FC<AccordionStageItemProps> = memo(
  function AccordionStageItem({
    stageName,
    label,
    status,
    agent,
    error,
    errorCode,
    skipReason,
    showTimestamp = false,
    timestamp,
    className,
  }) {
    const [isErrorExpanded, setIsErrorExpanded] = useState(false)

    const hasError = (status === 'failed' || status === 'static_fallback') && error
    const isActive =
      status === 'running' || status === 'synthesizing' || status === 'detecting_conflicts'
    const isSkipped = status === 'skipped'

    return (
      <div
        className={cn(
          'py-2 px-3 rounded-md',
          'hover:bg-muted/50 transition-colors duration-200',
          // Active stage highlight
          isActive && 'bg-primary/5 border-l-2 border-primary shadow-sm',
          className
        )}
        role="listitem"
        aria-label={`${label}: ${formatStatus(status)}`}
        data-testid="accordion-stage-item"
        data-stage-id={stageName}
        data-stage-status={status}
      >
        <div className="flex items-start gap-3">
          {/* Status icon - matches h-4 w-4 from getStatusIcon */}
          <div className="mt-0.5">{getStatusIcon(status)}</div>

          {/* Stage info */}
          <div className="flex-1 min-w-0">
            {/* Stage name + status badge row */}
            <div className="flex items-center justify-between gap-2">
              {/* Stage name - matches text-sm font-medium */}
              <h5
                className={cn(
                  'text-sm font-medium truncate',
                  isActive ? 'text-foreground' : 'text-foreground/80'
                )}
                title={label}
              >
                {label}
              </h5>

              {/* Right side: timestamp + status badge */}
              <div className="flex items-center gap-2 flex-shrink-0">
                {/* Timestamp (responsive - hidden on mobile) */}
                {showTimestamp && timestamp && (
                  <div
                    className="hidden md:flex items-center gap-1 text-xs text-muted-foreground"
                    aria-label={`Completed at ${formatTimestamp(timestamp)}`}
                  >
                    <Clock className="h-3 w-3" aria-hidden="true" />
                    <span>{formatTimestamp(timestamp)}</span>
                  </div>
                )}

                {/* Status badge - matches Badge component */}
                <Badge
                  variant={getStatusBadgeVariant(status)}
                  className="text-xs"
                  role="status"
                  aria-live={isActive ? 'polite' : 'off'}
                >
                  {formatStatus(status)}
                </Badge>
              </div>
            </div>

            {/* Agent info (for active stages) */}
            {isActive && agent && (
              <div className="mt-1 flex items-center gap-1.5 text-xs text-muted-foreground">
                <Loader2 className="h-3 w-3 animate-spin text-primary" aria-hidden="true" />
                <span>{formatAgentName(agent)}</span>
              </div>
            )}

            {/* Skip Reason (for skipped stages) */}
            {isSkipped && skipReason && (
              <div
                className="mt-1 flex items-start gap-1.5 text-xs text-muted-foreground"
                role="note"
                aria-label={`Skip reason: ${skipReason}`}
                title={skipReason}
              >
                <AlertCircle className="h-3 w-3 mt-0.5 flex-shrink-0" aria-hidden="true" />
                <span className="line-clamp-2">{skipReason}</span>
              </div>
            )}

            {/* Error Details (expandable for failed stages) */}
            {hasError && (
              <div className="mt-2 space-y-2">
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => setIsErrorExpanded(!isErrorExpanded)}
                  className="h-auto p-0 text-xs text-destructive hover:text-destructive/80 hover:bg-transparent"
                  aria-expanded={isErrorExpanded}
                  aria-controls={`error-details-${stageName}`}
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
                      id={`error-details-${stageName}`}
                      initial={{ height: 0, opacity: 0 }}
                      animate={{ height: 'auto', opacity: 1 }}
                      exit={{ height: 0, opacity: 0 }}
                      transition={{ duration: 0.2, ease: 'easeInOut' }}
                      className="overflow-hidden"
                      role="region"
                      aria-label={`Error details for ${label}`}
                    >
                      <div className="p-3 rounded-md bg-destructive/10 border border-destructive/20 space-y-2">
                        <div className="text-xs text-destructive">
                          <span className="font-medium">Error:</span> {error}
                        </div>

                        {errorCode && (
                          <div className="flex items-center gap-2">
                            <span className="text-xs text-muted-foreground">Code:</span>
                            <Badge variant="destructive" className="text-xs">
                              {formatErrorCode(errorCode)}
                            </Badge>
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
  }
)

AccordionStageItem.displayName = 'AccordionStageItem'
