/* eslint-disable max-lines -- Hero card component requires complete layout structure with multiple responsive variants and action buttons */
/**
 * HeroSummaryCard - Hero section with summary stats and primary CTA
 *
 * Designed for completed analysis view to show:
 * - Overall completion status with visual hierarchy
 * - Summary statistics (total/completed/failed/skipped stages)
 * - Primary action buttons (View Results, Preview, Download)
 * - Completion status indicator
 *
 * @module features/analysis/components/accordion/HeroSummaryCard
 */

import { memo } from 'react'

import { selectArtifactId, useSSEStore } from '@stores/sseStore'
import { useNavigate } from '@tanstack/react-router'
import {
  AlertCircle,
  CheckCircle2,
  Download,
  ExternalLink,
  Eye,
  Loader2,
  Sparkles,
} from 'lucide-react'

import { useArtifactPreview } from '@features/artifact'

import { Button } from '@shared/components/ui/button'

import { cn } from '@lib/utils'

// ============================================================================
// Types
// ============================================================================

export interface HeroSummaryCardProps {
  /** Total number of stages */
  totalStages: number
  /** Number of completed stages */
  completedStages: number
  /** Number of failed stages */
  failedStages: number
  /** Number of skipped stages */
  skippedStages: number
  /** Whether analysis has errors */
  hasErrors: boolean
  /** Whether analysis is still in progress */
  isInProgress?: boolean
  /** Optional artifact ID (overrides store value) */
  artifactId?: string
  /** Optional additional className */
  className?: string
}

// ============================================================================
// Component
// ============================================================================

/**
 * HeroSummaryCard - Hero summary with stats and primary CTA
 *
 * Visual hierarchy:
 * - Large completion status badge (Success/Partial/Failed)
 * - Grid of summary statistics
 * - Primary action buttons
 *
 * WCAG Compliance:
 * - 2.1.1 (Keyboard): All buttons keyboard accessible
 * - 1.4.1 (Use of Color): Status conveyed via icons + text, not just color
 * - 4.1.2 (Name, Role, Value): Proper aria-labels
 */
/* eslint-disable max-lines-per-function, complexity -- Hero card requires complete layout structure with multiple action buttons, responsive variants, and conditional rendering for in-progress state */
export const HeroSummaryCard = memo(function HeroSummaryCard({
  totalStages,
  completedStages,
  failedStages,
  skippedStages,
  hasErrors,
  isInProgress = false,
  artifactId: propsArtifactId,
  className,
}: HeroSummaryCardProps) {
  const navigate = useNavigate()
  const storeArtifactId = useSSEStore(selectArtifactId)
  const artifactId = propsArtifactId ?? storeArtifactId
  const preview = useArtifactPreview(artifactId)

  const completionPercent = totalStages > 0 ? Math.round((completedStages / totalStages) * 100) : 0

  const handleViewResults = () => {
    if (artifactId) {
      navigate({ to: '/artifact/$artifactId', params: { artifactId } })
    }
  }

  return (
    <article
      className={cn(
        // Card styling
        'bg-gradient-to-br from-card to-muted/20',
        'border-2 rounded-xl',
        // Border color based on status
        isInProgress
          ? 'border-[oklch(0.6232_0.2118_259.1492)]' // Blue for in-progress
          : hasErrors
            ? 'border-[oklch(0.7686_0.1647_70.0804)]'
            : 'border-[oklch(0.6959_0.1491_162.4796)]',
        // Layout
        'p-6 md:p-8',
        // Shadow
        'shadow-lg',
        className
      )}
      aria-label={
        isInProgress
          ? `Analysis in progress - ${completionPercent}% complete`
          : hasErrors
            ? `Analysis complete with ${failedStages} errors`
            : 'Analysis completed successfully'
      }
    >
      {/* Header Section */}
      <div className="flex flex-col md:flex-row items-start md:items-center justify-between gap-6 mb-6">
        {/* Status Badge & Title */}
        <div className="flex items-center gap-4">
          <div
            className={cn(
              'flex items-center justify-center w-16 h-16 rounded-full',
              isInProgress
                ? 'bg-[oklch(0.6232_0.2118_259.1492)]/15' // Blue for in-progress
                : hasErrors
                  ? 'bg-[oklch(0.7686_0.1647_70.0804)]/15'
                  : 'bg-[oklch(0.9_0.1_162.48)]/30'
            )}
          >
            {isInProgress ? (
              <Loader2
                className="h-8 w-8 text-[oklch(0.6232_0.2118_259.1492)] animate-spin"
                aria-hidden="true"
              />
            ) : hasErrors ? (
              <Sparkles
                className="h-8 w-8 text-[oklch(0.7686_0.1647_70.0804)]"
                aria-hidden="true"
              />
            ) : (
              <CheckCircle2
                className="h-8 w-8 text-[oklch(0.6959_0.1491_162.4796)]"
                aria-hidden="true"
              />
            )}
          </div>

          <div>
            <h2 className="text-2xl font-bold text-foreground">
              {isInProgress
                ? 'Analysis In Progress'
                : hasErrors
                  ? 'Complete with Errors'
                  : 'Analysis Complete'}
            </h2>
            <p className="text-sm text-muted-foreground mt-1">
              {completionPercent}% of stages completed{isInProgress ? '' : ' successfully'}
            </p>
          </div>
        </div>

        {/* Primary Action Buttons (Desktop) - Only show when complete */}
        {!isInProgress && (
          <div className="hidden md:flex gap-3">
            <Button
              onClick={handleViewResults}
              disabled={!artifactId}
              size="lg"
              className="h-11"
              aria-label="View analysis results"
            >
              <ExternalLink className="h-4 w-4 mr-2" aria-hidden="true" />
              View Results
            </Button>

            <Button
              variant="outline"
              size="lg"
              onClick={preview.openPreview}
              disabled={!artifactId}
              className="h-11"
              aria-label="Preview artifact"
            >
              <Eye className="h-4 w-4 mr-2" aria-hidden="true" />
              Preview
            </Button>

            <Button
              variant="outline"
              size="lg"
              onClick={preview.download}
              disabled={!artifactId || preview.isLoading}
              className="h-11"
              aria-label="Download artifact"
            >
              <Download className="h-4 w-4 mr-2" aria-hidden="true" />
              Download
            </Button>
          </div>
        )}
      </div>

      {/* Statistics Grid */}
      <div className={cn('grid grid-cols-2 md:grid-cols-4 gap-4', !isInProgress && 'mb-6')}>
        {/* Total Stages */}
        <div className="bg-background/60 rounded-lg p-4 border border-border/50">
          <div className="text-2xl font-bold text-foreground">{totalStages}</div>
          <div className="text-xs text-muted-foreground mt-1">Total Stages</div>
        </div>

        {/* Completed */}
        <div className="bg-[oklch(0.9_0.1_162.48)]/10 rounded-lg p-4 border border-[oklch(0.6959_0.1491_162.4796)]/30">
          <div className="text-2xl font-bold text-[oklch(0.6959_0.1491_162.4796)] flex items-center gap-2">
            <CheckCircle2 className="h-5 w-5" aria-hidden="true" />
            {completedStages}
          </div>
          <div className="text-xs text-muted-foreground mt-1">Completed</div>
        </div>

        {/* Failed */}
        {failedStages > 0 && (
          <div className="bg-destructive/10 rounded-lg p-4 border border-destructive/30">
            <div className="text-2xl font-bold text-destructive flex items-center gap-2">
              <AlertCircle className="h-5 w-5" aria-hidden="true" />
              {failedStages}
            </div>
            <div className="text-xs text-muted-foreground mt-1">Failed</div>
          </div>
        )}

        {/* Skipped */}
        {skippedStages > 0 && (
          <div className="bg-muted/50 rounded-lg p-4 border border-border/50">
            <div className="text-2xl font-bold text-muted-foreground">{skippedStages}</div>
            <div className="text-xs text-muted-foreground mt-1">Skipped</div>
          </div>
        )}
      </div>

      {/* Primary Action Buttons (Mobile) - Stack vertically - Only show when complete */}
      {!isInProgress && (
        <div className="md:hidden flex flex-col gap-3">
          <Button
            onClick={handleViewResults}
            disabled={!artifactId}
            size="lg"
            className="w-full h-11"
            aria-label="View analysis results"
          >
            <ExternalLink className="h-4 w-4 mr-2" aria-hidden="true" />
            View Results
          </Button>

          <div className="flex gap-3">
            <Button
              variant="outline"
              size="lg"
              onClick={preview.openPreview}
              disabled={!artifactId}
              className="flex-1 h-11"
              aria-label="Preview artifact"
            >
              <Eye className="h-4 w-4 mr-2" aria-hidden="true" />
              Preview
            </Button>

            <Button
              variant="outline"
              size="lg"
              onClick={preview.download}
              disabled={!artifactId || preview.isLoading}
              className="flex-1 h-11"
              aria-label="Download artifact"
            >
              <Download className="h-4 w-4 mr-2" aria-hidden="true" />
              Download
            </Button>
          </div>
        </div>
      )}
    </article>
  )
})
