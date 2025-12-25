/**
 * CompactActionCard - Grid-integrated action card for completed analysis
 *
 * Designed to fit in the grid layout alongside CompactGroupCards.
 * Shows completion status and primary action button.
 *
 * Gets artifactId from Zustand store (Issue #396).
 *
 * @module features/analysis/components/accordion/CompactActionCard
 */

import { memo } from 'react'

import { selectArtifactId, useSSEStore } from '@stores/sseStore'
import { useNavigate } from '@tanstack/react-router'
import { CheckCircle2, Download, ExternalLink, Eye, Sparkles } from 'lucide-react'

import { useArtifactPreview } from '@features/artifact'

import { Button } from '@shared/components/ui/button'

import { cn } from '@lib/utils'

// ============================================================================
// Types
// ============================================================================

export interface CompactActionCardProps {
  /** Whether analysis has failed stages */
  hasErrors?: boolean
  /** Optional additional className */
  className?: string
}

// ============================================================================
// Component
// ============================================================================

/**
 * CompactActionCard - Completion action card for grid layout
 *
 * WCAG Compliance:
 * - 2.1.1 (Keyboard): All buttons keyboard accessible
 * - 4.1.2 (Name, Role, Value): Proper button labels
 */
/* eslint-disable max-lines-per-function -- Action card layout requires complete JSX structure */
export const CompactActionCard = memo(function CompactActionCard({
  hasErrors = false,
  className,
}: CompactActionCardProps) {
  const navigate = useNavigate()
  const artifactId = useSSEStore(selectArtifactId)
  const preview = useArtifactPreview(artifactId)

  const handleViewResults = () => {
    if (artifactId) {
      navigate({ to: '/artifact/$artifactId', params: { artifactId } })
    }
  }

  return (
    <article
      className={cn(
        // Card styling - match CompactGroupCard
        'bg-card border border-border rounded-lg',
        // Left border accent - green for success, amber for partial
        'border-l-4',
        hasErrors
          ? 'border-l-[oklch(0.7686_0.1647_70.0804)]'
          : 'border-l-[oklch(0.6959_0.1491_162.4796)]',
        // Padding and layout
        'p-3 flex flex-col gap-3',
        // Min height for visual consistency with group cards
        'min-h-[140px]',
        // Hover effect
        'hover:shadow-sm transition-shadow duration-200',
        className
      )}
      aria-label={hasErrors ? 'Analysis complete with errors' : 'Analysis complete'}
    >
      {/* Header with completion icon */}
      <div className="flex items-center gap-2">
        <div
          className={cn(
            'flex items-center justify-center w-8 h-8 rounded-full',
            hasErrors ? 'bg-[oklch(0.7686_0.1647_70.0804)]/15' : 'bg-[oklch(0.9_0.1_162.48)]/20'
          )}
        >
          {hasErrors ? (
            <Sparkles className="h-4 w-4 text-[oklch(0.7686_0.1647_70.0804)]" aria-hidden="true" />
          ) : (
            <CheckCircle2
              className="h-4 w-4 text-[oklch(0.6959_0.1491_162.4796)]"
              aria-hidden="true"
            />
          )}
        </div>
        <div>
          <h3 className="text-sm font-semibold text-foreground">
            {hasErrors ? 'Complete with Errors' : 'Analysis Complete'}
          </h3>
          <p className="text-[11px] text-muted-foreground">Your results are ready</p>
        </div>
      </div>

      {/* Action Buttons - Stack vertically in card */}
      <div className="flex flex-col gap-2 mt-auto">
        {/* Primary Action: View Results */}
        <Button
          onClick={handleViewResults}
          disabled={!artifactId}
          className="w-full h-9 text-sm"
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
    </article>
  )
})
