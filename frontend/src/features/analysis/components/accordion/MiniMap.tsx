/**
 * MiniMap Component - Compact Overview Sidebar for Desktop+ Layouts
 *
 * Provides a bird's-eye view of all stage groups with:
 * - Visual progress indicators per group
 * - Quick jump navigation to any group
 * - Overall analysis progress summary
 * - Highlights currently active group
 *
 * @module features/analysis/components/accordion/MiniMap
 */

import { memo } from 'react'

import { motion } from 'framer-motion'
import { AlertCircle, CheckCircle2, Circle, Loader2, Map as MapIcon } from 'lucide-react'

import { Badge } from '@shared/components/ui/badge'
import { Progress } from '@shared/components/ui/progress'

import { cn } from '@lib/utils'

import type { GroupStatus } from '../../types/accordion'

// ============================================================================
// Type Definitions
// ============================================================================

/**
 * Stage group data for MiniMap
 */
export interface MiniMapGroup {
  id: string
  label: string
  status: GroupStatus
  progress: number
  stagesCount: number
  description?: string
}

export type AnalysisStatus = 'pending' | 'in-progress' | 'completed' | 'failed'

export interface MiniMapProps {
  groups: MiniMapGroup[]
  activeGroupId: string | null
  onJumpToGroup: (groupId: string) => void
  overallProgress: number
  overallStatus: AnalysisStatus
  className?: string
}

// ============================================================================
// Status Configuration
// ============================================================================

const STATUS_CONFIG = {
  pending: {
    color: 'text-muted-foreground',
    bgColor: 'bg-muted/50',
    icon: Circle,
    label: 'Pending',
  },
  'in-progress': {
    color: 'text-blue-500',
    bgColor: 'bg-blue-500/10',
    icon: Loader2,
    label: 'In Progress',
  },
  completed: {
    color: 'text-green-500',
    bgColor: 'bg-green-500/10',
    icon: CheckCircle2,
    label: 'Completed',
  },
  failed: {
    color: 'text-red-500',
    bgColor: 'bg-red-500/10',
    icon: AlertCircle,
    label: 'Failed',
  },
  partial: {
    color: 'text-yellow-500',
    bgColor: 'bg-yellow-500/10',
    icon: AlertCircle,
    label: 'Partial',
  },
} as const

// ============================================================================
// Sub-Components
// ============================================================================

interface GroupIndicatorProps {
  group: MiniMapGroup
  isActive: boolean
  onClick: () => void
}

const GroupIndicator = memo(function GroupIndicator({
  group,
  isActive,
  onClick,
}: GroupIndicatorProps) {
  const config = STATUS_CONFIG[group.status]
  const Icon = config.icon

  return (
    <motion.button
      type="button"
      onClick={onClick}
      className={cn(
        'w-full p-3 rounded-lg border transition-all duration-200',
        'hover:bg-muted/50 hover:border-primary/50 cursor-pointer',
        'text-left',
        isActive && 'bg-primary/5 border-primary ring-2 ring-primary/20',
        !isActive && 'border-border'
      )}
      whileHover={{ scale: 1.02 }}
      whileTap={{ scale: 0.98 }}
    >
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

      <Progress value={group.progress} className="h-1.5 mb-2" />

      <div className="flex items-center justify-between text-xs text-muted-foreground">
        <span>{group.progress}%</span>
        <span>
          {group.stagesCount} {group.stagesCount === 1 ? 'stage' : 'stages'}
        </span>
      </div>
    </motion.button>
  )
})

// ============================================================================
// Main Component
// ============================================================================

/* eslint-disable max-lines-per-function -- Complete JSX layout for MiniMap navigation sidebar requires full structure (header with progress, scrollable groups list) with status indicators, progress bars, and empty state handling */
export const MiniMap = memo(function MiniMap({
  groups,
  activeGroupId,
  onJumpToGroup,
  overallProgress,
  overallStatus,
  className,
}: MiniMapProps) {
  const statusLabel = STATUS_CONFIG[overallStatus]?.label || 'Unknown'

  return (
    <div
      className={cn(
        'w-[250px] shrink-0 border-l border-border bg-background',
        'sticky top-0 h-screen flex flex-col',
        className
      )}
    >
      {/* Header */}
      <div className="p-4 border-b border-border bg-muted/30">
        <div className="flex items-center gap-2 mb-3">
          <MapIcon className="h-5 w-5 text-primary" />
          <h3 className="font-semibold text-sm">Progress Overview</h3>
        </div>
        <Progress value={overallProgress} className="h-2 mb-2" />
        <div className="flex items-center justify-between">
          <Badge variant={overallStatus === 'failed' ? 'destructive' : 'default'}>
            {statusLabel}
          </Badge>
          <span className="text-lg font-bold text-primary">{overallProgress}%</span>
        </div>
      </div>

      {/* Groups List */}
      <div className="flex-1 overflow-y-auto p-3 space-y-2">
        {groups.length === 0 ? (
          <div className="text-center py-8 px-4">
            <MapIcon className="h-8 w-8 text-muted-foreground mx-auto mb-2" />
            <p className="text-sm text-muted-foreground">No groups available</p>
          </div>
        ) : (
          groups.map((group) => (
            <GroupIndicator
              key={group.id}
              group={group}
              isActive={group.id === activeGroupId}
              onClick={() => onJumpToGroup(group.id)}
            />
          ))
        )}
      </div>
    </div>
  )
})
