/**
 * CompactGroupCard - Card-based group display with inline stage chips
 *
 * Designed for the full-width grid layout where all groups are visible
 * at once without scrolling. Each card shows:
 * - Group icon and label with status badge
 * - Group description (truncated)
 * - Inline stage chips showing individual stage status
 * - Progress bar at bottom
 *
 * @module features/analysis/components/accordion/CompactGroupCard
 */
/* eslint-disable max-lines -- Component requires detailed state logic and JSX structure */

import { memo } from 'react'

import { CheckCircle2, Loader2, XCircle } from 'lucide-react'

import type { StageName } from '@/schemas/base'

import { Badge } from '@shared/components/ui/badge'
import { Progress, type ProgressVariant } from '@shared/components/ui/progress'

import { cn } from '@lib/utils'

import type { StageStatusEntry } from '../../hooks/stageConfig'
import type { GroupStatusMeta, StageGroup } from '../../types/accordion'

import { StageChip } from './StageChip'

// ============================================================================
// Types
// ============================================================================

export interface CompactGroupCardProps {
  /** Group configuration */
  group: StageGroup
  /** Computed status metadata */
  statusMeta: GroupStatusMeta
  /** Stage statuses map for individual stage display */
  stageStatuses: Map<StageName, StageStatusEntry>
  /** Optional additional className */
  className?: string
}

// ============================================================================
// Helper Functions
// ============================================================================

/** Get badge variant based on completion state */
const getBadgeVariant = (
  statusMeta: GroupStatusMeta
): 'default' | 'success' | 'warning' | 'info' | 'destructive' | 'secondary' => {
  // 0% completion = gray/muted badge
  if (statusMeta.completed === 0) {
    return 'secondary'
  }
  // 100% completion with no failures = green/success
  if (statusMeta.completed === statusMeta.total && statusMeta.failed === 0) {
    return 'success'
  }
  // Has failures = amber/warning
  if (statusMeta.failed > 0) {
    return 'warning'
  }
  // In progress = blue/info
  if (statusMeta.running > 0) {
    return 'info'
  }
  // Default for partial progress without failures
  return 'default'
}

/** Get status-based border color */
const getStatusBorderColor = (statusMeta: GroupStatusMeta): string => {
  // 0% completion = gray
  if (statusMeta.completed === 0 && statusMeta.running === 0) {
    return 'border-l-muted-foreground/30'
  }
  // 100% completion with no failures = green
  if (statusMeta.completed === statusMeta.total && statusMeta.failed === 0) {
    return 'border-l-[oklch(0.6959_0.1491_162.4796)]'
  }
  // Has failures = amber
  if (statusMeta.failed > 0) {
    return 'border-l-[oklch(0.7686_0.1647_70.0804)]'
  }
  // In progress = blue
  if (statusMeta.running > 0) {
    return 'border-l-primary'
  }
  // Default
  return 'border-l-muted-foreground/30'
}

/** Get progress bar variant based on state */
const getProgressVariant = (statusMeta: GroupStatusMeta): ProgressVariant => {
  // 0% progress = muted (gray, no fill)
  if (statusMeta.progress === 0) {
    return 'muted'
  }
  // 100% with no failures = success (green)
  if (statusMeta.progress === 100 && statusMeta.failed === 0) {
    return 'success'
  }
  // Has failures = warning (amber)
  if (statusMeta.failed > 0) {
    return 'warning'
  }
  // In progress = default (blue)
  if (statusMeta.running > 0) {
    return 'default'
  }
  // Default for partial progress
  return 'default'
}

/** Get status label for accessibility */
const getStatusLabel = (statusMeta: GroupStatusMeta): string => {
  if (statusMeta.completed === 0) {
    return 'Pending'
  }
  if (statusMeta.completed === statusMeta.total && statusMeta.failed === 0) {
    return 'Complete'
  }
  if (statusMeta.failed > 0) {
    return 'Has Failures'
  }
  if (statusMeta.running > 0) {
    return 'In Progress'
  }
  return 'Partial'
}

// ============================================================================
// Component
// ============================================================================

/**
 * CompactGroupCard - Grid-friendly card for stage group display
 *
 * WCAG Compliance:
 * - 1.3.1 (Info and Relationships): Semantic structure with heading
 * - 1.4.1 (Use of Color): Status conveyed via icons + badges, not just color
 * - 4.1.2 (Name, Role, Value): Proper aria-labels for screen readers
 */
/* eslint-disable max-lines-per-function -- Card layout requires complete JSX structure */
export const CompactGroupCard = memo(function CompactGroupCard({
  group,
  statusMeta,
  stageStatuses,
  className,
}: CompactGroupCardProps) {
  const Icon = group.icon
  const badgeVariant = getBadgeVariant(statusMeta)
  const progressVariant = getProgressVariant(statusMeta)
  const statusLabel = getStatusLabel(statusMeta)

  // Determine icon color based on actual state
  const getIconColor = () => {
    if (statusMeta.completed === 0 && statusMeta.running === 0) {
      return 'text-muted-foreground'
    }
    if (statusMeta.completed === statusMeta.total && statusMeta.failed === 0) {
      return 'text-[oklch(0.6959_0.1491_162.4796)]'
    }
    if (statusMeta.failed > 0) {
      return 'text-[oklch(0.7686_0.1647_70.0804)]'
    }
    if (statusMeta.running > 0) {
      return 'text-primary animate-pulse'
    }
    return 'text-muted-foreground'
  }

  return (
    <article
      className={cn(
        // Card styling
        'bg-card border border-border rounded-lg',
        // Left border accent based on status
        'border-l-4',
        getStatusBorderColor(statusMeta),
        // Padding and layout - increased for better breathing room
        'p-4 flex flex-col gap-3',
        // Hover effect
        'hover:shadow-sm transition-shadow duration-200',
        // Min height for visual consistency - increased from 140px
        'min-h-[180px]',
        className
      )}
      aria-label={`${group.label}: ${statusLabel}, ${statusMeta.completed} of ${statusMeta.total} stages completed`}
    >
      {/* Header: Icon + Label + Count + Badge */}
      <div className="flex items-start justify-between gap-2">
        <div className="flex items-center gap-2 min-w-0 flex-1">
          {/* Group Icon */}
          <Icon className={cn('h-4 w-4 flex-shrink-0', getIconColor())} aria-hidden="true" />

          {/* Label + Count */}
          <div className="min-w-0 flex-1">
            <h3 className="text-sm font-semibold text-foreground truncate">{group.label}</h3>
          </div>
        </div>

        {/* Status Badge */}
        <Badge variant={badgeVariant} className="text-[10px] px-1.5 py-0 flex-shrink-0">
          {statusMeta.completed}/{statusMeta.total}
        </Badge>
      </div>

      {/* Description (if present) - allow 2 lines before truncating */}
      {group.description && (
        <p className="text-xs text-muted-foreground/80 line-clamp-2">{group.description}</p>
      )}

      {/* Stage Chips - Inline horizontal layout with better spacing */}
      <div className="flex flex-wrap gap-1.5" role="list" aria-label="Stage statuses">
        {group.stages.map((stageName) => (
          <StageChip
            key={stageName}
            stageName={stageName}
            status={stageStatuses.get(stageName)}
            size="md"
          />
        ))}
      </div>

      {/* Status Summary (for non-pending groups with issues) */}
      {(statusMeta.running > 0 || statusMeta.failed > 0) && (
        <div className="flex items-center gap-2 text-[10px]">
          {statusMeta.running > 0 && (
            <span className="flex items-center gap-1 text-primary">
              <Loader2 className="h-2.5 w-2.5 animate-spin" />
              {statusMeta.running} running
            </span>
          )}
          {statusMeta.failed > 0 && (
            <span className="flex items-center gap-1 text-destructive">
              <XCircle className="h-2.5 w-2.5" />
              {statusMeta.failed} failed
            </span>
          )}
          {statusMeta.completed > 0 && statusMeta.status !== 'completed' && (
            <span className="flex items-center gap-1 text-[oklch(0.6959_0.1491_162.4796)]">
              <CheckCircle2 className="h-2.5 w-2.5" />
              {statusMeta.completed} done
            </span>
          )}
        </div>
      )}

      {/* Progress Bar - Always at bottom, more visible */}
      <div className="mt-auto pt-1">
        <Progress
          value={statusMeta.progress}
          variant={progressVariant}
          className="h-2"
          aria-label={`${group.label} progress`}
          aria-valuetext={`${statusMeta.progress}% complete`}
        />
      </div>
    </article>
  )
})
