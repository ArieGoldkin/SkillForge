import { memo } from 'react'
import type * as React from 'react'

import type { StageStatus } from '@app-types/sse'
import { CheckCircle2, Circle, Loader2, XCircle } from 'lucide-react'

import { Badge } from '@shared/components/ui/badge'

import { cn } from '@lib/utils'

import { formatErrorCode } from '../../utils/errorCodeFormatter'

import { formatAgentName, formatStatus, getStatusBadgeVariant, type StageState } from './constants'

/**
 * Get status icon component for a stage
 */
const getStatusIcon = (status: StageStatus): React.ReactNode => {
  const iconClasses = 'h-5 w-5'

  switch (status) {
    case 'complete':
      return <CheckCircle2 className={cn(iconClasses, 'text-status-success')} />
    case 'running':
      return <Loader2 className={cn(iconClasses, 'animate-spin text-status-warning')} />
    case 'failed':
      return <XCircle className={cn(iconClasses, 'text-status-error')} />
    case 'pending':
      return <Circle className={cn(iconClasses, 'text-muted-foreground')} />
  }
}

interface StageItemProps {
  stage: StageState
  isLast: boolean
}

/**
 * Individual stage item in the progress timeline
 *
 * WCAG 1.3.1 (Info and Relationships):
 * - Uses role="listitem" for semantic structure
 * - aria-label describes stage and status
 * - Icon marked aria-hidden (decorative, status conveyed by badge)
 *
 * Wrapped with React.memo to prevent re-renders when stage/isLast unchanged.
 */
/* eslint-disable-next-line max-lines-per-function -- Accessibility attributes add necessary complexity */
export const StageItem = memo(function StageItem({ stage, isLast }: StageItemProps) {
  const stageId = `stage-${stage.name}`

  return (
    <div
      className="relative pl-8"
      data-testid="stage-indicator"
      data-stage-status={stage.status}
      role="listitem"
      aria-label={`${stage.label}: ${formatStatus(stage.status)}`}
    >
      {/* Status icon - decorative, hidden from screen readers */}
      <div className="absolute left-0 top-1" aria-hidden="true">
        {getStatusIcon(stage.status)}
      </div>
      {!isLast && (
        <div
          className={cn(
            'absolute left-[9px] top-6 bottom-0 w-0.5',
            stage.status === 'complete' ? 'bg-green-50' : 'bg-border'
          )}
          aria-hidden="true"
        />
      )}
      <div
        className={cn(
          'pb-6 transition-all duration-300',
          stage.status === 'running' && 'border-l-2 border-primary pl-2 -ml-2'
        )}
      >
        <div className="flex items-start justify-between gap-2 mb-1">
          <h4 id={stageId} className="font-medium text-sm">
            {stage.label}
          </h4>
          <Badge
            variant={getStatusBadgeVariant(stage.status)}
            className="text-xs"
            data-testid="status-text"
            role="status"
            aria-describedby={stageId}
          >
            {formatStatus(stage.status)}
          </Badge>
        </div>
        {stage.agent && stage.status === 'running' && (
          <div
            className="flex items-center gap-2 text-xs text-muted-foreground mt-1 animate-in slide-in-from-left-2 duration-200"
            aria-label={`Agent: ${formatAgentName(stage.agent)}`}
          >
            <Loader2 className="h-3 w-3 animate-spin text-primary" aria-hidden="true" />
            <span className="font-medium">{formatAgentName(stage.agent)}</span>
          </div>
        )}
        {stage.error && (
          <div
            className="text-xs text-destructive mt-2 p-2 bg-destructive/10 rounded space-y-1"
            role="alert"
            aria-label={`Error in ${stage.label}`}
          >
            <div>
              <span className="font-medium">Error:</span> {stage.error}
            </div>
            {stage.errorCode && (
              <div className="flex items-center gap-2">
                <span className="text-muted-foreground">Code:</span>
                <Badge variant="destructive" className="text-xs">
                  {formatErrorCode(stage.errorCode)}
                </Badge>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  )
})
