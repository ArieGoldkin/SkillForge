/**
 * MiniMap Component - Compact Overview Sidebar for Desktop+ Layouts
 *
 * Provides a bird's-eye view of all stage groups with:
 * - Visual progress indicators per group
 * - Quick jump navigation to any group
 * - Overall analysis progress summary
 * - Status filtering and quick stage access
 * - Highlights currently active group
 *
 * @module features/analysis/components/accordion/MiniMap
 */

/* eslint-disable max-lines -- Complex component with multiple sub-components (GroupIndicator, ProgressHeader, ControlsBar, MiniMap main) */

import { memo, useMemo, useState } from 'react'

import {
  AlertCircle,
  CheckCircle2,
  ChevronDown,
  Circle,
  Clock,
  Filter,
  Loader2,
  Map as MapIcon,
} from 'lucide-react'
import { motion } from 'motion/react'

import { Badge } from '@shared/components/ui/badge'
import { Button } from '@shared/components/ui/button'
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from '@shared/components/ui/dropdown-menu'
import { Progress } from '@shared/components/ui/progress'
import { ScrollArea } from '@shared/components/ui/scroll-area'

import { cn } from '@lib/utils'

import type { GroupStatus } from '../../types/accordion'

// ============================================================================
// Type Definitions
// ============================================================================

/**
 * Stage group data for MiniMap
 */
export interface MiniMapGroup {
  /** Unique group identifier */
  id: string
  /** Display label for the group */
  label: string
  /** Group status (pending, in-progress, completed, failed, partial) */
  status: GroupStatus
  /** Progress percentage (0-100) */
  progress: number
  /** Number of stages in this group */
  stagesCount: number
  /** Optional short description */
  description?: string
}

/**
 * Overall analysis status
 */
export type AnalysisStatus = 'pending' | 'in-progress' | 'completed' | 'failed'

/**
 * Status filter option
 */
export type StatusFilter = 'all' | 'active' | 'completed' | 'failed' | 'pending'

/**
 * Props for MiniMap component
 */
export interface MiniMapProps {
  /** Array of stage groups to display */
  groups: MiniMapGroup[]
  /** Currently active group ID (if any) */
  activeGroupId: string | null
  /** Handler for jumping to a group */
  onJumpToGroup: (groupId: string) => void
  /** Overall analysis progress (0-100) */
  overallProgress: number
  /** Overall analysis status */
  overallStatus: AnalysisStatus
  /** Optional className for wrapper */
  className?: string
}

// ============================================================================
// Status Configuration
// ============================================================================

/**
 * Status color and icon mapping
 */
const STATUS_CONFIG = {
  pending: {
    color: 'text-muted-foreground',
    bgColor: 'bg-muted/50',
    borderColor: 'border-muted',
    icon: Circle,
    label: 'Pending',
  },
  'in-progress': {
    color: 'text-blue-500',
    bgColor: 'bg-blue-500/10',
    borderColor: 'border-blue-500/30',
    icon: Loader2,
    label: 'In Progress',
  },
  completed: {
    color: 'text-green-500',
    bgColor: 'bg-green-500/10',
    borderColor: 'border-green-500/30',
    icon: CheckCircle2,
    label: 'Completed',
  },
  failed: {
    color: 'text-red-500',
    bgColor: 'bg-red-500/10',
    borderColor: 'border-red-500/30',
    icon: AlertCircle,
    label: 'Failed',
  },
  partial: {
    color: 'text-yellow-500',
    bgColor: 'bg-yellow-500/10',
    borderColor: 'border-yellow-500/30',
    icon: AlertCircle,
    label: 'Partial',
  },
} as const

/**
 * Overall status badge variant mapping
 */
const OVERALL_STATUS_VARIANT = {
  pending: 'default' as const,
  'in-progress': 'info' as const,
  completed: 'success' as const,
  failed: 'destructive' as const,
}

// ============================================================================
// Sub-Components
// ============================================================================

/**
 * Group progress indicator - visual dots representing stages
 */
interface GroupIndicatorProps {
  group: MiniMapGroup
  isActive: boolean
  onClick: () => void
}

/* eslint-disable max-lines-per-function -- Complex visual component requires full JSX layout (header, progress bar, stage dots, status) */
const GroupIndicator = memo(function GroupIndicator({
  group,
  isActive,
  onClick,
}: GroupIndicatorProps) {
  const config = STATUS_CONFIG[group.status]
  const Icon = config.icon

  // Generate stage dots (max 10 visible)
  const maxDots = 10
  const dots = Math.min(group.stagesCount, maxDots)
  const hasMore = group.stagesCount > maxDots

  return (
    <motion.button
      onClick={onClick}
      className={cn(
        'w-full p-3 rounded-lg border transition-all duration-200',
        'hover:bg-muted/50 hover:border-primary/50 cursor-pointer',
        'text-left group',
        isActive && 'bg-primary/5 border-primary ring-2 ring-primary/20',
        !isActive && config.borderColor
      )}
      whileHover={{ scale: 1.02 }}
      whileTap={{ scale: 0.98 }}
    >
      {/* Group Header */}
      <div className="flex items-start justify-between gap-2 mb-2">
        <div className="flex items-center gap-2 flex-1 min-w-0">
          <Icon
            className={cn(
              'h-4 w-4 shrink-0',
              config.color,
              group.status === 'in-progress' && 'animate-spin'
            )}
          />
          <span className="text-sm font-medium truncate" title={group.label}>
            {group.label}
          </span>
        </div>
        {isActive && (
          <Badge variant="default" className="text-xs shrink-0">
            Active
          </Badge>
        )}
      </div>

      {/* Progress Bar */}
      <div className="mb-2">
        <Progress value={group.progress} className="h-1.5" />
      </div>

      {/* Stage Dots */}
      <div className="flex items-center gap-1 flex-wrap">
        {Array.from({ length: dots }).map((_, index) => {
          const isCompleted = (index / dots) * 100 < group.progress
          return (
            <div
              /* eslint-disable-next-line react/no-array-index-key -- Index is safe here as dots are static visual elements scoped by group.id */
              key={`${group.id}-dot-${index}`}
              className={cn(
                'w-1.5 h-1.5 rounded-full transition-colors',
                isCompleted ? config.color.replace('text-', 'bg-') : 'bg-muted-foreground/20'
              )}
            />
          )
        })}
        {hasMore && (
          <span className="text-xs text-muted-foreground ml-1">+{group.stagesCount - maxDots}</span>
        )}
      </div>

      {/* Progress Text */}
      <div className="flex items-center justify-between mt-2 text-xs text-muted-foreground">
        <span>{group.progress}%</span>
        <span>
          {group.stagesCount} {group.stagesCount === 1 ? 'stage' : 'stages'}
        </span>
      </div>
    </motion.button>
  )
})
/* eslint-enable max-lines-per-function */

/**
 * Overall progress summary header
 */
interface ProgressHeaderProps {
  overallProgress: number
  overallStatus: AnalysisStatus
}

const ProgressHeader = memo(function ProgressHeader({
  overallProgress,
  overallStatus,
}: ProgressHeaderProps) {
  const statusLabel = STATUS_CONFIG[overallStatus]?.label || 'Unknown'

  return (
    <div className="p-4 border-b border-border bg-muted/30">
      <div className="flex items-center gap-2 mb-3">
        <MapIcon className="h-5 w-5 text-primary" />
        <h3 className="font-semibold text-sm">Progress Overview</h3>
      </div>

      {/* Overall Progress Bar */}
      <div className="mb-2">
        <Progress value={overallProgress} className="h-2" />
      </div>

      {/* Status and Percentage */}
      <div className="flex items-center justify-between">
        <Badge variant={OVERALL_STATUS_VARIANT[overallStatus]}>{statusLabel}</Badge>
        <span className="text-lg font-bold text-primary">{overallProgress}%</span>
      </div>
    </div>
  )
})

/**
 * Filter and quick jump controls
 */
interface ControlsBarProps {
  statusFilter: StatusFilter
  onStatusFilterChange: (filter: StatusFilter) => void
  groups: MiniMapGroup[]
  onJumpToGroup: (groupId: string) => void
}

/* eslint-disable max-lines-per-function -- Complex controls component with two dropdown menus (filter and quick jump) */
const ControlsBar = memo(function ControlsBar({
  statusFilter,
  onStatusFilterChange,
  groups,
  onJumpToGroup,
}: ControlsBarProps) {
  const filterOptions: { value: StatusFilter; label: string; icon: typeof Filter }[] = [
    { value: 'all', label: 'All Groups', icon: Filter },
    { value: 'active', label: 'Active Only', icon: Loader2 },
    { value: 'completed', label: 'Completed', icon: CheckCircle2 },
    { value: 'failed', label: 'Failed', icon: AlertCircle },
    { value: 'pending', label: 'Pending', icon: Clock },
  ]

  return (
    <div className="p-3 border-b border-border space-y-2">
      {/* Status Filter Dropdown */}
      <DropdownMenu>
        <DropdownMenuTrigger asChild>
          <Button variant="outline" size="sm" className="w-full justify-between">
            <div className="flex items-center gap-2">
              <Filter className="h-3.5 w-3.5" />
              <span className="text-xs">
                {filterOptions.find((opt) => opt.value === statusFilter)?.label}
              </span>
            </div>
            <ChevronDown className="h-3.5 w-3.5 text-muted-foreground" />
          </Button>
        </DropdownMenuTrigger>
        <DropdownMenuContent align="start" className="w-[220px]">
          {filterOptions.map((option) => {
            const OptionIcon = option.icon
            return (
              <DropdownMenuItem
                key={option.value}
                onClick={() => onStatusFilterChange(option.value)}
                className="cursor-pointer"
              >
                <OptionIcon className="h-4 w-4 mr-2" />
                {option.label}
                {statusFilter === option.value && (
                  <CheckCircle2 className="h-4 w-4 ml-auto text-primary" />
                )}
              </DropdownMenuItem>
            )
          })}
        </DropdownMenuContent>
      </DropdownMenu>

      {/* Quick Jump Dropdown */}
      <DropdownMenu>
        <DropdownMenuTrigger asChild>
          <Button variant="outline" size="sm" className="w-full justify-between">
            <div className="flex items-center gap-2">
              <MapIcon className="h-3.5 w-3.5" />
              <span className="text-xs">Jump to Group</span>
            </div>
            <ChevronDown className="h-3.5 w-3.5 text-muted-foreground" />
          </Button>
        </DropdownMenuTrigger>
        <DropdownMenuContent align="start" className="w-[220px] max-h-[300px] overflow-y-auto">
          {groups.map((group) => {
            const Icon = STATUS_CONFIG[group.status].icon
            return (
              <DropdownMenuItem
                key={group.id}
                onClick={() => onJumpToGroup(group.id)}
                className="cursor-pointer"
              >
                <Icon
                  className={cn(
                    'h-4 w-4 mr-2',
                    STATUS_CONFIG[group.status].color,
                    group.status === 'in-progress' && 'animate-spin'
                  )}
                />
                <span className="truncate">{group.label}</span>
              </DropdownMenuItem>
            )
          })}
        </DropdownMenuContent>
      </DropdownMenu>
    </div>
  )
})
/* eslint-enable max-lines-per-function */

// ============================================================================
// Main Component
// ============================================================================

/**
 * MiniMap - Compact overview sidebar for desktop+ layouts
 *
 * @example
 * ```tsx
 * <MiniMap
 *   groups={stageGroups}
 *   activeGroupId={activeGroup?.id || null}
 *   onJumpToGroup={handleJumpToGroup}
 *   overallProgress={75}
 *   overallStatus="in-progress"
 * />
 * ```
 */
/* eslint-disable max-lines-per-function -- Main component requires complete layout (header, controls, scrollable list with filtering) */
export const MiniMap = memo(function MiniMap({
  groups,
  activeGroupId,
  onJumpToGroup,
  overallProgress,
  overallStatus,
  className,
}: MiniMapProps) {
  const [statusFilter, setStatusFilter] = useState<StatusFilter>('all')

  // Filter groups based on selected status
  const filteredGroups = useMemo(() => {
    if (statusFilter === 'all') {
      return groups
    }

    return groups.filter((group) => {
      switch (statusFilter) {
        case 'active':
          return group.status === 'in-progress'
        case 'completed':
          return group.status === 'completed'
        case 'failed':
          return group.status === 'failed' || group.status === 'partial'
        case 'pending':
          return group.status === 'pending'
        default:
          return true
      }
    })
  }, [groups, statusFilter])

  return (
    <div
      className={cn(
        'w-[250px] shrink-0 border-l border-border bg-background',
        'sticky top-0 h-screen flex flex-col',
        className
      )}
    >
      {/* Overall Progress Header */}
      <ProgressHeader overallProgress={overallProgress} overallStatus={overallStatus} />

      {/* Controls */}
      <ControlsBar
        statusFilter={statusFilter}
        onStatusFilterChange={setStatusFilter}
        groups={groups}
        onJumpToGroup={onJumpToGroup}
      />

      {/* Groups List */}
      <ScrollArea className="flex-1">
        <div className="p-3 space-y-2">
          {filteredGroups.length === 0 ? (
            <div className="text-center py-8 px-4">
              <Filter className="h-8 w-8 text-muted-foreground mx-auto mb-2" />
              <p className="text-sm text-muted-foreground">No groups match this filter</p>
            </div>
          ) : (
            filteredGroups.map((group) => (
              <GroupIndicator
                key={group.id}
                group={group}
                isActive={group.id === activeGroupId}
                onClick={() => onJumpToGroup(group.id)}
              />
            ))
          )}
        </div>
      </ScrollArea>
    </div>
  )
})
/* eslint-enable max-lines-per-function */
