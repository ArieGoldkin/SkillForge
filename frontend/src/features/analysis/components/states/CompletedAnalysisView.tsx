/**
 * CompletedAnalysisView - Full page view for completed analysis
 *
 * Issue #533: Hierarchical Progress with Hero Summary
 * - Hero summary card at top with stats and primary CTA
 * - Active groups only (filters out 0/N skipped groups)
 * - Skipped groups shown as collapsed list
 * - Responsive grid: 1 → 2 → 3 columns (not 4, fewer cards now)
 *
 * UX Improvements:
 * - No wasted space on skipped groups (0/4 shown as text, not cards)
 * - Clear visual hierarchy (hero → active groups → skipped list)
 * - Primary action prominent in hero (not buried in 8th card)
 * - Summary statistics immediately visible
 *
 * Issue #396: Simplified props - components get data from Zustand store.
 *
 * Wrapped with React.memo - only re-renders when props change.
 */
import { memo, useMemo } from 'react'

import type { StageName } from '@/schemas/sse'

import type { StageStatusEntry } from '../../hooks/stageConfig'
import type { OverallProgress, ProgressStep } from '../../hooks/useAnalysisProgress'
import { useStageGroups } from '../../hooks/useStageGroups'
import type { AnalysisMode } from '../../types/accordion'
import { CompactGroupCard } from '../accordion/CompactGroupCard'
import { HeroSummaryCard } from '../accordion/HeroSummaryCard'
import { AnalysisHeader } from '../steps/AnalysisHeader'
import { AnalysisProgressCardErrorSummary } from '../steps/AnalysisProgressCardErrorSummary'

interface CompletedAnalysisViewProps {
  /** Used for header URL display only */
  analysisId?: string
  overallProgress: OverallProgress
  steps: ProgressStep[]
  hasFailedStages: boolean
  failedStagesCount: number
  failedStageErrorCodes?: string[]
  analysisMetadata?: {
    title?: string
    contentType?: 'article' | 'video' | 'repo'
    url?: string
    wordCount?: number
  }
  /** Stage statuses for accordion groups */
  stageStatuses: Map<StageName, StageStatusEntry>
  analysisMode?: AnalysisMode
  skipReasons?: Record<string, string>
}

/**
 * CompletedAnalysisView - Hierarchical Progress with Hero Summary
 *
 * Layout:
 * ┌─────────────────────────────────────────────────────────────────────────┐
 * │ Header: Title + URL + Metadata                                          │
 * ├─────────────────────────────────────────────────────────────────────────┤
 * │                                                                         │
 * │ ┌─────────────────────────────────────────────────────────────────────┐ │
 * │ │ HeroSummaryCard - Stats + Primary CTA                               │ │
 * │ └─────────────────────────────────────────────────────────────────────┘ │
 * │                                                                         │
 * │ ── Active Groups (only those with progress > 0) ──────────────────────  │
 * │                                                                         │
 * │ ┌──────────────┐ ┌──────────────┐ ┌──────────────┐                     │
 * │ │ Core Workflow│ │Content Analys│ │Quality Pipeln│  ← ONLY 3 cards    │
 * │ │     3/3 ✓    │ │   1/7 ⚠️     │ │   3/4 ⚠️     │    (groups that    │
 * │ └──────────────┘ └──────────────┘ └──────────────┘    actually ran)   │
 * │                                                                         │
 * │ ── Skipped Groups (collapsed) ────────────────────────────────────────  │
 * │ Tier 1 Universal • Tier 2 Validation • Tier 3 Research • Optional       │
 * │ (4 groups skipped - Quick analysis mode)                                │
 * │                                                                         │
 * └─────────────────────────────────────────────────────────────────────────┘
 *
 * Responsive Breakpoints:
 * - Mobile (<640px): 1 column
 * - Tablet (640-1024px): 2 columns
 * - Desktop (≥1024px): 3 columns (not 4 - fewer cards now)
 */
/* eslint-disable max-lines-per-function -- Layout component requires complete JSX structure */
export const CompletedAnalysisView = memo(function CompletedAnalysisView({
  analysisId,
  hasFailedStages,
  failedStagesCount,
  failedStageErrorCodes = [],
  analysisMetadata,
  stageStatuses,
}: CompletedAnalysisViewProps) {
  // Compute hierarchical group statuses from flat stage status map
  const groupsWithStatus = useStageGroups(stageStatuses)

  // Filter groups into active (has progress) vs skipped (no progress)
  const { activeGroups, skippedGroups } = useMemo(() => {
    const active = groupsWithStatus.filter(
      (g) => g.status.completed > 0 || g.status.failed > 0 || g.status.running > 0
    )
    const skipped = groupsWithStatus.filter(
      (g) => g.status.completed === 0 && g.status.failed === 0 && g.status.running === 0
    )
    return { activeGroups: active, skippedGroups: skipped }
  }, [groupsWithStatus])

  // Calculate summary statistics for HeroSummaryCard
  const summaryStats = useMemo(() => {
    const totalStages = groupsWithStatus.reduce((sum, g) => sum + g.status.total, 0)
    const completedStages = groupsWithStatus.reduce((sum, g) => sum + g.status.completed, 0)
    const failedStages = groupsWithStatus.reduce((sum, g) => sum + g.status.failed, 0)
    const skippedStages = groupsWithStatus.reduce((sum, g) => sum + g.status.skipped, 0)

    return {
      totalStages,
      completedStages,
      failedStages,
      skippedStages,
    }
  }, [groupsWithStatus])

  return (
    <div className="container mx-auto px-4 py-6 max-w-[1800px] 2xl:px-8">
      {/* Hero Section - Title + Metadata */}
      <AnalysisHeader
        title={analysisMetadata?.title || 'Content Analysis'}
        url={analysisMetadata?.url || (analysisId ? `Analysis ID: ${analysisId}` : '')}
        contentType={analysisMetadata?.contentType}
        wordCount={analysisMetadata?.wordCount}
      />

      {/* Hero Summary Card - Stats + Primary CTA */}
      <HeroSummaryCard
        totalStages={summaryStats.totalStages}
        completedStages={summaryStats.completedStages}
        failedStages={summaryStats.failedStages}
        skippedStages={summaryStats.skippedStages}
        hasErrors={hasFailedStages}
        className="mt-6"
      />

      {/* Error Summary - Show when analysis completed with errors */}
      {hasFailedStages && failedStageErrorCodes.length > 0 && (
        <div className="mt-6">
          <AnalysisProgressCardErrorSummary
            failedStagesCount={failedStagesCount}
            failedStageErrorCodes={failedStageErrorCodes}
          />
        </div>
      )}

      {/* Active Groups Grid - Only groups with progress > 0 */}
      {activeGroups.length > 0 && (
        <div className="mt-8">
          <h3 className="text-lg font-semibold text-foreground mb-4">Stage Groups</h3>
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

      {/* Skipped Groups - Collapsed Text List */}
      {skippedGroups.length > 0 && (
        <div className="mt-6 p-4 bg-muted/30 rounded-lg border border-border/50">
          <div className="text-sm text-muted-foreground">
            <span className="font-medium">Skipped Groups:</span>{' '}
            {skippedGroups.map((g) => g.group.label).join(' • ')}
            <span className="ml-2 text-xs">
              ({skippedGroups.length} {skippedGroups.length === 1 ? 'group' : 'groups'} skipped)
            </span>
          </div>
        </div>
      )}
    </div>
  )
})
