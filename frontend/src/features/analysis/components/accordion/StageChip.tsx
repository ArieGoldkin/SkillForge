/**
 * StageChip - Compact inline chip for stage status display
 *
 * Designed for the CompactGroupCard grid layout where stages are shown
 * as horizontal chips instead of vertical list items.
 *
 * States:
 * - Complete: Green bg, checkmark icon
 * - Running: Blue bg, spinner icon
 * - Failed: Red bg, x icon
 * - Pending: Gray bg, circle icon
 * - Skipped: Muted bg, minus icon
 *
 * @module features/analysis/components/accordion/StageChip
 */

import { memo } from 'react'

import { CheckCircle2, Circle, Loader2, MinusCircle, XCircle } from 'lucide-react'

import { assertNever, cn } from '@lib/utils'

import type { StageStatusEntry } from '../../hooks/stageConfig'

// ============================================================================
// Types
// ============================================================================

export interface StageChipProps {
  /** Stage name for display */
  stageName: string
  /** Stage status entry from stageStatuses map */
  status?: StageStatusEntry
  /** Chip size variant */
  size?: 'sm' | 'md'
}

// ============================================================================
// Helper Functions
// ============================================================================

type StageStatus = 'pending' | 'running' | 'complete' | 'failed' | 'skipped'

/** Map StageStatusEntry to simplified status */
function getStageStatus(status?: StageStatusEntry): StageStatus {
  if (!status) return 'pending'

  const s = status.status
  if (s === 'complete') return 'complete'
  if (s === 'running' || s === 'synthesizing' || s === 'detecting_conflicts') return 'running'
  if (s === 'failed' || s === 'static_fallback') return 'failed'
  if (s === 'skipped') return 'skipped'
  return 'pending'
}

/** Get display label from stage name */
function formatStageName(stageName: string): string {
  // Convert snake_case to Title Case
  const formatted = stageName
    .split('_')
    .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
    .join(' ')

  // Smarter abbreviation for long names (16-18 char limit)
  if (formatted.length > 18) {
    // Try to abbreviate at word boundary
    const words = formatted.split(' ')
    if (words.length > 2) {
      // Keep first word full, abbreviate middle words, keep last word
      const first = words[0]
      const last = words[words.length - 1]
      const middle = words
        .slice(1, -1)
        .map((w) => w[0])
        .join('')
      const abbreviated = `${first} ${middle}${last}`
      if (abbreviated.length <= 18) {
        return abbreviated
      }
    }
    // Fall back to simple truncation
    return `${formatted.slice(0, 16)}...`
  }
  return formatted
}

/** Status-specific styling with strong contrast and borders */
const statusStyles: Record<
  StageStatus,
  { bg: string; text: string; icon: string; border: string }
> = {
  complete: {
    bg: 'bg-[oklch(0.6959_0.1491_162.4796)]',
    text: 'text-white',
    icon: 'text-white',
    border: 'border border-[oklch(0.5959_0.1691_162.4796)]',
  },
  running: {
    bg: 'bg-[oklch(0.6232_0.2118_259.1492)]',
    text: 'text-white',
    icon: 'text-white',
    border: 'border border-[oklch(0.5232_0.2318_259.1492)]',
  },
  failed: {
    bg: 'bg-[oklch(0.6369_0.2077_25.3313)]',
    text: 'text-white',
    icon: 'text-white',
    border: 'border border-[oklch(0.5369_0.2277_25.3313)]',
  },
  skipped: {
    bg: 'bg-[oklch(0.5556_0.0001_286.3746)]/50',
    text: 'text-muted-foreground',
    icon: 'text-muted-foreground',
    border: 'border border-[oklch(0.5556_0.0001_286.3746)]/30',
  },
  pending: {
    bg: 'bg-[oklch(0.5556_0.0001_286.3746)]/20',
    text: 'text-muted-foreground',
    icon: 'text-muted-foreground/70',
    border: 'border border-[oklch(0.5556_0.0001_286.3746)]/20',
  },
}

/** Status icons */
const StatusIcon = ({ status, className }: { status: StageStatus; className?: string }) => {
  const iconClass = cn('flex-shrink-0', className)

  switch (status) {
    case 'complete':
      return <CheckCircle2 className={iconClass} aria-hidden="true" />
    case 'running':
      return <Loader2 className={cn(iconClass, 'animate-spin')} aria-hidden="true" />
    case 'failed':
      return <XCircle className={iconClass} aria-hidden="true" />
    case 'skipped':
      return <MinusCircle className={iconClass} aria-hidden="true" />
    case 'pending':
      return <Circle className={iconClass} aria-hidden="true" />
    default:
      return assertNever(status)
  }
}

// ============================================================================
// Component
// ============================================================================

/**
 * StageChip - Inline status chip for compact stage display
 *
 * WCAG Compliance:
 * - 1.4.1 (Use of Color): Status conveyed via icons + text, not just color
 * - 4.1.2 (Name, Role, Value): Proper aria-label for screen readers
 */
export const StageChip = memo(function StageChip({
  stageName,
  status,
  size = 'sm',
}: StageChipProps) {
  const stageStatus = getStageStatus(status)
  const styles = statusStyles[stageStatus]
  const label = formatStageName(stageName)
  const fullStageName = stageName
    .split('_')
    .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
    .join(' ')

  // Improved size classes for better readability and touch targets
  const sizeClasses =
    size === 'sm'
      ? 'px-2 py-1 text-xs min-h-[24px]' // Increased from 10px text, added min-height
      : 'px-3 py-1.5 text-sm min-h-[32px]' // Better touch target for md

  const iconSize = size === 'sm' ? 'h-3 w-3' : 'h-3.5 w-3.5'

  return (
    <span
      className={cn(
        'inline-flex items-center gap-1.5 rounded-md font-medium',
        'transition-colors duration-200',
        styles.bg,
        styles.text,
        styles.border,
        sizeClasses
      )}
      title={`${fullStageName}: ${stageStatus}`}
      aria-label={`${fullStageName}: ${stageStatus}`}
    >
      <StatusIcon status={stageStatus} className={cn(iconSize, styles.icon)} />
      <span className="truncate max-w-[120px]">{label}</span>
    </span>
  )
})
