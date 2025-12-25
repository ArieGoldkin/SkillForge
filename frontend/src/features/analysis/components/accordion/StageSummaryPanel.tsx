/**
 * StageSummaryPanel - Left sidebar for Two-Panel Master-Detail layout
 *
 * Displays a compact 2x4 grid of stage groups with action buttons.
 * Designed for sticky positioning on desktop, collapsible on mobile.
 *
 * Issue #533: Full-width two-panel layout for completed analysis.
 *
 * @module features/analysis/components/accordion/StageSummaryPanel
 */

import { memo } from 'react'

import { selectArtifactId, useSSEStore } from '@stores/sseStore'
import { useNavigate } from '@tanstack/react-router'
import { Download, ExternalLink, Eye } from 'lucide-react'

import type { StageName } from '@/schemas/base'

import { useArtifactPreview } from '@features/artifact'

import { Button } from '@shared/components/ui/button'

import { cn } from '@lib/utils'

import type { StageStatusEntry } from '../../hooks/stageConfig'
import { useStageGroups } from '../../hooks/useStageGroups'

import { MiniGroupCard } from './MiniGroupCard'

// ============================================================================
// Types
// ============================================================================

export interface StageSummaryPanelProps {
  /** Stage statuses map for group computation */
  stageStatuses: Map<StageName, StageStatusEntry>
  /** Whether analysis has failed stages */
  hasErrors?: boolean
  /** Optional additional className */
  className?: string
}

// ============================================================================
// Component
// ============================================================================

/**
 * StageSummaryPanel - Sidebar with stage groups and actions
 *
 * Layout:
 * - 2x4 grid of MiniGroupCards (7 groups + 1 summary/action cell)
 * - Action buttons: View Results, Preview, Download
 * - Sticky positioning on large screens
 *
 * WCAG Compliance:
 * - 2.1.1 (Keyboard): All buttons keyboard accessible
 * - 4.1.2 (Name, Role, Value): Proper button labels
 */
/* eslint-disable max-lines-per-function -- Panel layout requires complete JSX structure */
export const StageSummaryPanel = memo(function StageSummaryPanel({
  stageStatuses,
  hasErrors = false,
  className,
}: StageSummaryPanelProps) {
  const navigate = useNavigate()
  const artifactId = useSSEStore(selectArtifactId)
  const preview = useArtifactPreview(artifactId)
  const stageGroups = useStageGroups(stageStatuses)

  const handleViewResults = () => {
    if (artifactId) {
      navigate({ to: '/artifact/$artifactId', params: { artifactId } })
    }
  }

  // Calculate overall progress
  const totalStages = stageGroups.reduce((sum, g) => sum + g.status.total, 0)
  const completedStages = stageGroups.reduce((sum, g) => sum + g.status.completed, 0)
  const overallProgress = totalStages > 0 ? Math.round((completedStages / totalStages) * 100) : 0

  return (
    <aside
      className={cn(
        // Base layout
        'flex flex-col gap-4',
        // Sticky on desktop
        'lg:sticky lg:top-6 lg:self-start',
        className
      )}
      aria-label="Analysis stage summary"
    >
      {/* Header with overall status */}
      <div
        className={cn(
          'p-3 rounded-lg border',
          hasErrors
            ? 'bg-[oklch(0.7686_0.1647_70.0804)]/10 border-[oklch(0.7686_0.1647_70.0804)]/30'
            : 'bg-[oklch(0.9_0.1_162.48)]/10 border-[oklch(0.6959_0.1491_162.4796)]/30'
        )}
      >
        <div className="flex items-center justify-between mb-2">
          <h2 className="text-sm font-semibold text-foreground">
            {hasErrors ? 'Complete with Errors' : 'Analysis Complete'}
          </h2>
          <span className="text-xs text-muted-foreground">
            {completedStages}/{totalStages} stages
          </span>
        </div>
        <div className="w-full bg-muted rounded-full h-1.5">
          <div
            className={cn(
              'h-1.5 rounded-full transition-all duration-300',
              hasErrors ? 'bg-[oklch(0.7686_0.1647_70.0804)]' : 'bg-[oklch(0.6959_0.1491_162.4796)]'
            )}
            style={{ width: `${overallProgress}%` }}
          />
        </div>
      </div>

      {/* Stage Groups Grid - 2 columns on mobile, 2 on desktop sidebar */}
      <div className="grid grid-cols-2 gap-2" role="list" aria-label="Stage groups">
        {stageGroups.map(({ group, status }) => (
          <MiniGroupCard key={group.id} label={group.label} icon={group.icon} statusMeta={status} />
        ))}
      </div>

      {/* Action Buttons */}
      <div className="flex flex-col gap-2 pt-2 border-t border-border">
        {/* Primary Action: View Results */}
        <Button
          onClick={handleViewResults}
          disabled={!artifactId}
          className="w-full h-9"
          aria-label="View analysis results"
        >
          <ExternalLink className="h-4 w-4 mr-2" aria-hidden="true" />
          View Results
        </Button>

        {/* Secondary Actions Row */}
        <div className="flex gap-2">
          <Button
            variant="outline"
            size="sm"
            onClick={preview.openPreview}
            disabled={!artifactId}
            className="flex-1 h-8 text-xs"
            aria-label="Preview artifact"
          >
            <Eye className="h-3 w-3 mr-1" aria-hidden="true" />
            Preview
          </Button>
          <Button
            variant="outline"
            size="sm"
            onClick={preview.download}
            disabled={!artifactId || preview.isLoading}
            className="flex-1 h-8 text-xs"
            aria-label="Download artifact"
          >
            <Download className="h-3 w-3 mr-1" aria-hidden="true" />
            Download
          </Button>
        </div>
      </div>
    </aside>
  )
})
