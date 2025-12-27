/**
 * MiniGroupCard - Compact card for sidebar display
 *
 * Simplified version of CompactGroupCard designed for the two-panel
 * master-detail layout. Shows essential info at ~80px height:
 * - Group icon and label
 * - Status badge with count
 * - Progress bar
 *
 * @module features/analysis/components/accordion/MiniGroupCard
 */

import { memo } from 'react'

import type { LucideIcon } from 'lucide-react'

import { Badge } from '@shared/components/ui/badge'
import { Progress } from '@shared/components/ui/progress'

import { cn } from '@lib/utils'

import type { GroupStatus, GroupStatusMeta } from '../../types/accordion'

// ============================================================================
// Types
// ============================================================================

export interface MiniGroupCardProps {
  /** Group display label */
  label: string
  /** Icon component */
  icon: LucideIcon
  /** Computed status metadata */
  statusMeta: GroupStatusMeta
  /** Optional additional className */
  className?: string
}

// ============================================================================
// Helper Functions
// ============================================================================

/** Status configuration for badge variants and border colors */
const statusConfig = {
  pending: {
    badgeVariant: 'default' as const,
    borderColor: 'border-l-muted-foreground/30',
  },
  'in-progress': {
    badgeVariant: 'info' as const,
    borderColor: 'border-l-primary',
  },
  completed: {
    badgeVariant: 'success' as const,
    borderColor: 'border-l-[oklch(0.6959_0.1491_162.4796)]',
  },
  failed: {
    badgeVariant: 'destructive' as const,
    borderColor: 'border-l-destructive',
  },
  partial: {
    badgeVariant: 'warning' as const,
    borderColor: 'border-l-[oklch(0.7686_0.1647_70.0804)]',
  },
} satisfies Record<
  GroupStatus,
  {
    badgeVariant: 'default' | 'success' | 'warning' | 'info' | 'destructive'
    borderColor: string
  }
>

/** Get badge variant for each status */
const getBadgeVariant = (
  status: GroupStatus
): 'default' | 'success' | 'warning' | 'info' | 'destructive' => {
  return statusConfig[status].badgeVariant
}

/** Get status-based border color */
const getStatusBorderColor = (status: GroupStatus): string => {
  return statusConfig[status].borderColor
}

// ============================================================================
// Component
// ============================================================================

/**
 * MiniGroupCard - Compact card for sidebar stage summary
 *
 * WCAG Compliance:
 * - 1.4.1 (Use of Color): Status conveyed via badges + borders
 * - 4.1.2 (Name, Role, Value): Proper aria-label for screen readers
 */
export const MiniGroupCard = memo(function MiniGroupCard({
  label,
  icon: Icon,
  statusMeta,
  className,
}: MiniGroupCardProps) {
  return (
    <div
      className={cn(
        // Card styling
        'bg-card border border-border rounded-md',
        // Left border accent based on status
        'border-l-4',
        getStatusBorderColor(statusMeta.status),
        // Padding and layout
        'p-2.5 flex flex-col gap-1.5',
        // Compact height
        'min-h-[72px]',
        // Hover effect
        'hover:shadow-sm transition-shadow duration-200',
        className
      )}
      aria-label={`${label}: ${statusMeta.completed} of ${statusMeta.total} stages completed`}
    >
      {/* Header: Icon + Label + Badge */}
      <div className="flex items-center gap-2">
        <Icon
          className={cn(
            'h-3.5 w-3.5 flex-shrink-0',
            statusMeta.status === 'in-progress' && 'text-primary animate-pulse',
            statusMeta.status === 'completed' && 'text-[oklch(0.6959_0.1491_162.4796)]',
            statusMeta.status === 'failed' && 'text-destructive',
            statusMeta.status === 'partial' && 'text-[oklch(0.7686_0.1647_70.0804)]',
            statusMeta.status === 'pending' && 'text-muted-foreground'
          )}
          aria-hidden="true"
        />

        <span className="text-xs font-medium text-foreground truncate flex-1">{label}</span>

        <Badge
          variant={getBadgeVariant(statusMeta.status)}
          className="text-[9px] px-1 py-0 h-4 flex-shrink-0"
        >
          {statusMeta.completed}/{statusMeta.total}
        </Badge>
      </div>

      {/* Progress Bar */}
      <Progress
        value={statusMeta.progress}
        className="h-1"
        aria-label={`${label} progress`}
        aria-valuetext={`${statusMeta.progress}% complete`}
      />
    </div>
  )
})
