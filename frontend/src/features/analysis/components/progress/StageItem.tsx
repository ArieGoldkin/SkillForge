import type * as React from 'react'

import type { StageStatus } from '@app-types/sse'
import { CheckCircle2, Circle, Loader2, XCircle } from 'lucide-react'

import { Badge } from '@shared/components/ui/badge'

import { cn } from '@lib/utils'

import { formatAgentName, formatStatus, getStatusBadgeVariant, type StageState } from './constants'

/**
 * Get status icon component for a stage
 */
const getStatusIcon = (status: StageStatus): React.ReactNode => {
  const iconClasses = 'h-5 w-5'

  switch (status) {
    case 'complete':
      return <CheckCircle2 className={cn(iconClasses, 'text-[oklch(0.6959_0.1491_162.4796)]')} />
    case 'running':
      return (
        <Loader2 className={cn(iconClasses, 'animate-spin text-[oklch(0.7686_0.1647_70.0804)]')} />
      )
    case 'failed':
      return <XCircle className={cn(iconClasses, 'text-destructive')} />
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
 */
export const StageItem: React.FC<StageItemProps> = ({ stage, isLast }) => (
  <div className="relative pl-8">
    <div className="absolute left-0 top-1">{getStatusIcon(stage.status)}</div>
    {!isLast && (
      <div
        className={cn(
          'absolute left-[9px] top-6 bottom-0 w-0.5',
          stage.status === 'complete' ? 'bg-[oklch(0.6959_0.1491_162.4796)]/30' : 'bg-border'
        )}
      />
    )}
    <div
      className={cn(
        'pb-6 transition-all duration-300',
        stage.status === 'running' && 'border-l-2 border-primary pl-2 -ml-2'
      )}
    >
      <div className="flex items-start justify-between gap-2 mb-1">
        <h4 className="font-medium text-sm">{stage.label}</h4>
        <Badge variant={getStatusBadgeVariant(stage.status)} className="text-xs">
          {formatStatus(stage.status)}
        </Badge>
      </div>
      {stage.agent && stage.status === 'running' && (
        <div className="flex items-center gap-2 text-xs text-muted-foreground mt-1 animate-in slide-in-from-left-2 duration-200">
          <Loader2 className="h-3 w-3 animate-spin text-primary" />
          <span className="font-medium">{formatAgentName(stage.agent)}</span>
        </div>
      )}
      {stage.error && (
        <div className="text-xs text-destructive mt-2 p-2 bg-destructive/10 rounded">
          <span className="font-medium">Error:</span> {stage.error}
        </div>
      )}
    </div>
  </div>
)

StageItem.displayName = 'StageItem'
