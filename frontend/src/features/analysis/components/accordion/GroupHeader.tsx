import { memo, type KeyboardEvent } from 'react'

import { ChevronDown, ChevronRight } from 'lucide-react'
import { motion } from 'motion/react'

import type { GroupStatus, StageGroup } from '@/features/analysis/types/accordion'

import { Badge } from '@shared/components/ui/badge'
import { Progress } from '@shared/components/ui/progress'

import { cn } from '@lib/utils'

/**
 * Props for GroupHeader component
 */
export interface GroupHeaderProps {
  /** Stage group configuration (id, label, icon, stages) */
  group: StageGroup
  /** Current group status */
  status: GroupStatus
  /** Progress percentage (0-100) */
  progress: number
  /** Whether the group is currently expanded */
  isExpanded: boolean
  /** Callback when user toggles expand/collapse */
  onToggle: () => void
  /** Number of completed stages */
  stagesCompleted: number
  /** Total number of stages in group */
  stagesTotal: number
  /** Optional className for customization */
  className?: string
}

/**
 * Get badge variant and styling for each group status
 */
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
 * GroupHeader - Collapsible header for stage groups in accordion
 *
 * Features:
 * - Click/tap to expand/collapse
 * - Keyboard accessible (Enter/Space to toggle)
 * - Shows group icon, title, status badge, and progress
 * - Smooth expand/collapse animation via Framer Motion
 * - Touch targets: 56px mobile, 64px tablet, 48px desktop
 * - Status-based visual feedback
 *
 * @example
 * ```tsx
 * <GroupHeader
 *   group={coreWorkflowGroup}
 *   status="in-progress"
 *   progress={67}
 *   isExpanded={true}
 *   onToggle={() => setExpanded(!expanded)}
 *   stagesCompleted={2}
 *   stagesTotal={3}
 * />
 * ```
 */
/* eslint-disable max-lines-per-function -- Complete JSX layout for accordion group header requires full structure (chevron, icon, label, progress bar, status badge) with responsive touch targets and accessibility attributes */
export const GroupHeader = memo(function GroupHeader({
  group,
  status,
  progress,
  isExpanded,
  onToggle,
  stagesCompleted,
  stagesTotal,
  className,
}: GroupHeaderProps) {
  const statusConfig = getStatusConfig(status)
  const Icon = group.icon
  const ChevronIcon = isExpanded ? ChevronDown : ChevronRight

  /**
   * Handle keyboard navigation (Enter/Space to toggle)
   * WCAG 2.1.1 Keyboard: All functionality available via keyboard
   */
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
        // Base layout
        'w-full flex items-center gap-3 text-left',
        // Touch targets (WCAG 2.5.5)
        // Mobile: 56px (h-14)
        'h-14',
        // Tablet: 64px (md:h-16)
        'md:h-16',
        // Desktop: 48px (lg:h-12)
        'lg:h-12',
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
      {/* Chevron Icon - Expand/Collapse indicator */}
      <motion.div
        animate={{ rotate: isExpanded ? 90 : 0 }}
        transition={{ duration: 0.2, ease: 'easeInOut' }}
        className="shrink-0"
      >
        <ChevronIcon className="h-5 w-5 text-muted-foreground" aria-hidden="true" />
      </motion.div>

      {/* Group Icon */}
      <div className="shrink-0">
        <Icon
          className={cn(
            'h-5 w-5',
            // Status-based coloring
            status === 'in-progress' && 'text-primary animate-pulse',
            status === 'completed' && 'text-[oklch(0.6959_0.1491_162.4796)]',
            status === 'failed' && 'text-destructive',
            status === 'partial' && 'text-[oklch(0.7686_0.1647_70.0804)]',
            status === 'pending' && 'text-muted-foreground'
          )}
          aria-hidden="true"
        />
      </div>

      {/* Group Label and Progress Info */}
      <div className="flex-1 min-w-0 space-y-1">
        {/* Title and Stage Count */}
        <div className="flex items-center gap-2">
          <h3 className="text-sm font-semibold text-foreground truncate">{group.label}</h3>
          <span className="text-xs text-muted-foreground whitespace-nowrap">
            {stagesCompleted}/{stagesTotal}
          </span>
        </div>

        {/* Progress Bar (only show if not pending) */}
        {status !== 'pending' && (
          <Progress
            value={progress}
            className="h-1.5 w-full"
            aria-label={`${group.label} progress`}
            aria-valuetext={`${progress}% complete`}
          />
        )}
      </div>

      {/* Status Badge */}
      <div className="shrink-0">
        <Badge variant={statusConfig.variant} className="text-xs">
          {statusConfig.label}
        </Badge>
      </div>
    </button>
  )
})
