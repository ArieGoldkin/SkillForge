import { memo, type KeyboardEvent } from 'react'

import { motion } from 'framer-motion'
import { CheckCircle2, ChevronRight, Clock, Loader2, XCircle } from 'lucide-react'

import type { GroupStatus, GroupStatusMeta, StageGroup } from '@/features/analysis/types/accordion'

import { Badge } from '@shared/components/ui/badge'
import { Progress } from '@shared/components/ui/progress'

import { cn } from '@lib/utils'

/** Props for GroupHeader component */
export interface GroupHeaderProps {
  group: StageGroup
  status: GroupStatus
  progress: number
  isExpanded: boolean
  onToggle: () => void
  stagesCompleted: number
  stagesTotal: number
  statusMeta?: GroupStatusMeta
  className?: string
}

/** Get estimated time for a group based on stage count */
function getEstimatedTime(stageCount: number): string {
  if (stageCount <= 3) return '1-2 min'
  if (stageCount <= 7) return '3-5 min'
  return '5-10 min'
}

/** Get badge variant and styling for each group status */
const getStatusConfig = (
  status: GroupStatus
): { variant: 'default' | 'success' | 'warning' | 'info' | 'destructive'; label: string } => {
  const configs: Record<
    GroupStatus,
    { variant: 'default' | 'success' | 'warning' | 'info' | 'destructive'; label: string }
  > = {
    pending: { variant: 'default', label: 'Pending' },
    'in-progress': { variant: 'info', label: 'In Progress' },
    completed: { variant: 'success', label: 'Completed' },
    failed: { variant: 'destructive', label: 'Failed' },
    partial: { variant: 'warning', label: 'Partial' },
  }

  return configs[status]
}

/**
 * GroupHeader - Collapsible header for stage groups with keyboard support,
 * status-based coloring, and rich preview content when collapsed.
 */
/* eslint-disable max-lines-per-function, complexity -- Layout-heavy component with multiple conditional rows */
export const GroupHeader = memo(function GroupHeader({
  group,
  status,
  progress,
  isExpanded,
  onToggle,
  stagesCompleted,
  stagesTotal,
  statusMeta,
  className,
}: GroupHeaderProps) {
  const statusConfig = getStatusConfig(status)
  const Icon = group.icon

  // WCAG 2.1.1: Keyboard navigation (Enter/Space to toggle)
  const handleKeyDown = (event: KeyboardEvent<HTMLButtonElement>) => {
    if (event.key === 'Enter' || event.key === ' ') {
      event.preventDefault()
      onToggle()
    }
  }

  return (
    <button
      type="button"
      onClick={onToggle}
      onKeyDown={handleKeyDown}
      aria-expanded={isExpanded}
      aria-controls={`group-content-${group.id}`}
      className={cn(
        // Base layout - flex-col for stacking rows
        'w-full flex flex-col gap-1.5 text-left',
        // Touch targets (WCAG 2.5.5) - TALLER headers for more info
        // Mobile: 72px minimum (min-h-[72px])
        'min-h-[72px] py-3',
        // Tablet: 80px (md:min-h-20)
        'md:min-h-20 md:py-4',
        // Desktop: 72px (lg:min-h-[72px]) - taller than before for description
        'lg:min-h-[72px] lg:py-3',
        // Padding
        'px-4 md:px-5 lg:px-4',
        // Background and border
        'bg-muted/30 hover:bg-muted/50 border-b border-border',
        // Transitions
        'transition-colors duration-200',
        // Focus styles (WCAG 2.4.7 Focus Visible)
        'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2',
        // Rounded corners (top corners rounded)
        'rounded-t-md',
        className
      )}
      aria-label={`${group.label} group: ${statusConfig.label}, ${stagesCompleted} of ${stagesTotal} stages completed`}
    >
      {/* Row 1: Main header content */}
      <div className="flex items-center gap-3 w-full">
        {/* Chevron with rotation animation */}
        <motion.div
          animate={{ rotate: isExpanded ? 90 : 0 }}
          transition={{ duration: 0.2, ease: 'easeInOut' }}
          className="shrink-0"
        >
          <ChevronRight className="h-5 w-5 text-muted-foreground" aria-hidden="true" />
        </motion.div>

        {/* Group Icon with status-based coloring */}
        <div className="shrink-0">
          <Icon
            className={cn(
              'h-5 w-5',
              status === 'in-progress' && 'text-primary animate-pulse',
              status === 'completed' && 'text-[oklch(0.6959_0.1491_162.4796)]',
              status === 'failed' && 'text-destructive',
              status === 'partial' && 'text-[oklch(0.7686_0.1647_70.0804)]',
              status === 'pending' && 'text-muted-foreground'
            )}
            aria-hidden="true"
          />
        </div>

        {/* Group Label and Stage Count */}
        <div className="flex-1 min-w-0 flex items-center gap-2">
          <h3 className="text-sm font-semibold text-foreground truncate">{group.label}</h3>
          <span className="text-xs text-muted-foreground whitespace-nowrap">
            {stagesCompleted}/{stagesTotal}
          </span>
        </div>

        {/* Status Badge */}
        <div className="shrink-0">
          <Badge variant={statusConfig.variant} className="text-xs">
            {statusConfig.label}
          </Badge>
        </div>
      </div>

      {/* Row 2: Description + Progress Bar (when collapsed) */}
      {!isExpanded && (
        <div className="flex items-center gap-3 pl-8 w-full">
          {group.description && (
            <p className="text-xs text-muted-foreground/80 truncate flex-1 min-w-0">
              {group.description}
            </p>
          )}

          {status !== 'pending' && (
            <div className="w-24 shrink-0">
              <Progress
                value={progress}
                className="h-1.5"
                aria-label={`${group.label} progress`}
                aria-valuetext={`${progress}% complete`}
              />
            </div>
          )}
        </div>
      )}

      {/* Row 3: Stage Preview (collapsed, has activity) */}
      {!isExpanded && statusMeta && (statusMeta.running > 0 || statusMeta.failed > 0) && (
        <div className="flex items-center gap-3 pl-8 text-xs">
          {statusMeta.running > 0 && (
            <span className="flex items-center gap-1 text-blue-500">
              <Loader2 className="h-3 w-3 animate-spin" />
              {statusMeta.running} running
            </span>
          )}
          {statusMeta.failed > 0 && (
            <span className="flex items-center gap-1 text-destructive">
              <XCircle className="h-3 w-3" />
              {statusMeta.failed} failed
            </span>
          )}
          {statusMeta.completed > 0 && status !== 'completed' && (
            <span className="flex items-center gap-1 text-green-500">
              <CheckCircle2 className="h-3 w-3" />
              {statusMeta.completed} done
            </span>
          )}
        </div>
      )}

      {/* Row 4: Estimated Time (collapsed, pending or in-progress) */}
      {!isExpanded && (status === 'pending' || status === 'in-progress') && (
        <div className="flex items-center gap-1.5 pl-8 text-xs text-muted-foreground">
          <Clock className="h-3 w-3" />
          <span>Est. {getEstimatedTime(stagesTotal)}</span>
        </div>
      )}

      {/* Progress Bar for expanded state */}
      {isExpanded && status !== 'pending' && (
        <div className="pl-8 pr-2 w-full">
          <Progress
            value={progress}
            className="h-1.5"
            aria-label={`${group.label} progress`}
            aria-valuetext={`${progress}% complete`}
          />
        </div>
      )}
    </button>
  )
})
