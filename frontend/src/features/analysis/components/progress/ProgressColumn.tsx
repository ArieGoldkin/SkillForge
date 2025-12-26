/**
 * ProgressColumn - Grid-based live progress display
 *
 * Issue #533: Replaces old vertical accordion with new grid layout
 * - Uses same layout as CompletedAnalysisView for consistency
 * - HeroSummaryCard shows live progress stats
 * - CompactGroupCard grid shows all active groups
 * - Skipped groups shown as collapsed text list
 *
 * NO BACKWARDS COMPATIBILITY with old AccordionProgressTracker layout
 */
import { memo, useMemo } from 'react'

import type { StageName } from '@/schemas/sse'

import type { StageStatusEntry } from '../../hooks/stageConfig'
import type { OverallProgress } from '../../hooks/useAnalysisProgress'
import { useStageGroups } from '../../hooks/useStageGroups'
import type { AnalysisMode } from '../../types/accordion'
import { CompactGroupCard } from '../accordion/CompactGroupCard'
import { HeroSummaryCard } from '../accordion/HeroSummaryCard'

interface ProgressColumnProps {
  overallProgress: OverallProgress
  hasFailedStages?: boolean
  failedStagesCount?: number
  /** Stage statuses for accordion groups */
  stageStatuses: Map<StageName, StageStatusEntry>
  analysisMode?: AnalysisMode
}

/**
 * ProgressColumn - Grid-based live progress display
 *
 * Layout matches CompletedAnalysisView for visual consistency:
 * ┌─────────────────────────────────────────────────────────────┐
 * │ HeroSummaryCard - Live progress stats                       │
 * ├─────────────────────────────────────────────────────────────┤
 * │ ┌──────────────┐ ┌──────────────┐ ┌──────────────┐          │
 * │ │Core Workflow │ │Content Analys│ │Tier 1: Univ. │          │
 * │ │   1/3 ⟳     │ │   0/7        │ │   0/4        │          │
 * │ └──────────────┘ └──────────────┘ └──────────────┘          │
 * │ ┌──────────────┐ ┌──────────────┐ ┌──────────────┐          │
 * │ │Tier 2: Valid.│ │Tier 3: Rsrch │ │Quality Pipeln│          │
 * │ │   0/4        │ │   0/4        │ │   0/4        │          │
 * │ └──────────────┘ └──────────────┘ └──────────────┘          │
 * │                                                             │
 * │ Skipped Groups: Optional Stages (1 group skipped)           │
 * └─────────────────────────────────────────────────────────────┘
 *
 * Wrapped with React.memo for SSE streaming performance.
 */
/* eslint-disable max-lines-per-function -- Grid layout component requires complete JSX structure with multiple responsive grid sections */
export const ProgressColumn = memo(function ProgressColumn({
  hasFailedStages = false,
  stageStatuses,
}: ProgressColumnProps) {
  // Compute hierarchical group statuses from flat stage status map
  const groupsWithStatus = useStageGroups(stageStatuses)

  // Split into active groups (any activity) vs pending groups (no activity yet)
  const { activeGroups, pendingGroups } = useMemo(() => {
    const active = groupsWithStatus.filter(
      (g) => g.status.completed > 0 || g.status.failed > 0 || g.status.running > 0
    )
    const pending = groupsWithStatus.filter(
      (g) => g.status.completed === 0 && g.status.failed === 0 && g.status.running === 0
    )
    return { activeGroups: active, pendingGroups: pending }
  }, [groupsWithStatus])

  // Calculate live summary statistics for HeroSummaryCard
  const summaryStats = useMemo(() => {
    const totalStages = groupsWithStatus.reduce((sum, g) => sum + g.status.total, 0)
    const completedStages = groupsWithStatus.reduce((sum, g) => sum + g.status.completed, 0)
    const failedStages = groupsWithStatus.reduce((sum, g) => sum + g.status.failed, 0)
    const skippedStages = groupsWithStatus.reduce((sum, g) => sum + g.status.skipped, 0)
    const runningStages = groupsWithStatus.reduce((sum, g) => sum + g.status.running, 0)

    return {
      totalStages,
      completedStages,
      failedStages,
      skippedStages,
      runningStages,
    }
  }, [groupsWithStatus])

  // Determine if analysis is still in progress
  const isInProgress = summaryStats.runningStages > 0

  return (
    <div className="space-y-6">
      {/* Hero Summary Card - Live progress stats */}
      <HeroSummaryCard
        totalStages={summaryStats.totalStages}
        completedStages={summaryStats.completedStages}
        failedStages={summaryStats.failedStages}
        skippedStages={summaryStats.skippedStages}
        hasErrors={hasFailedStages}
        isInProgress={isInProgress}
      />

      {/* Active Groups Grid - Groups with any activity */}
      {activeGroups.length > 0 && (
        <div>
          <h3 className="text-lg font-semibold text-foreground mb-4">Active Stages</h3>
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-5">
            {activeGroups.map((groupWithStatus) => (
              <CompactGroupCard
                key={groupWithStatus.group.id}
                group={groupWithStatus.group}
                statusMeta={groupWithStatus.status}
                stageStatuses={stageStatuses}
              />
            ))}
          </div>
        </div>
      )}

      {/* Pending Groups Grid - Groups waiting to start */}
      {pendingGroups.length > 0 && (
        <div>
          <h3 className="text-lg font-semibold text-muted-foreground mb-4">Pending Stages</h3>
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-5">
            {pendingGroups.map((groupWithStatus) => (
              <CompactGroupCard
                key={groupWithStatus.group.id}
                group={groupWithStatus.group}
                statusMeta={groupWithStatus.status}
                stageStatuses={stageStatuses}
              />
            ))}
          </div>
        </div>
      )}

      {/* Empty State - Analysis starting */}
      {activeGroups.length === 0 && pendingGroups.length === 0 && (
        <div className="p-8 text-center text-muted-foreground bg-muted/30 rounded-lg border border-border/50">
          <p>Initializing analysis pipeline...</p>
        </div>
      )}
    </div>
  )
})
