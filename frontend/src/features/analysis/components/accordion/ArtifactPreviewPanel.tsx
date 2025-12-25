/**
 * ArtifactPreviewPanel - Right panel for Two-Panel Master-Detail layout
 *
 * Displays the generated artifact markdown content inline on the completed
 * analysis page, eliminating the need to navigate away.
 *
 * Uses the existing MarkdownPreview component from the artifact feature.
 *
 * Issue #533: Full-width two-panel layout for completed analysis.
 *
 * @module features/analysis/components/accordion/ArtifactPreviewPanel
 */

import { memo } from 'react'

import { selectArtifactId, useSSEStore } from '@stores/sseStore'
import { AlertCircle, FileText, Loader2 } from 'lucide-react'

import { MarkdownPreview, useArtifact } from '@features/artifact'

import { cn } from '@lib/utils'

// ============================================================================
// Types
// ============================================================================

export interface ArtifactPreviewPanelProps {
  /** Optional additional className */
  className?: string
}

// ============================================================================
// Loading State
// ============================================================================

const LoadingState = () => (
  <div className="flex flex-col items-center justify-center py-16 text-muted-foreground">
    <Loader2 className="h-8 w-8 animate-spin mb-4" aria-hidden="true" />
    <p className="text-sm">Loading implementation guide...</p>
  </div>
)

// ============================================================================
// Error State
// ============================================================================

const ErrorState = ({ message }: { message: string }) => (
  <div className="flex flex-col items-center justify-center py-16 text-destructive">
    <AlertCircle className="h-8 w-8 mb-4" aria-hidden="true" />
    <p className="text-sm font-medium">Failed to load artifact</p>
    <p className="text-xs text-muted-foreground mt-1">{message}</p>
  </div>
)

// ============================================================================
// Empty State
// ============================================================================

const EmptyState = () => (
  <div className="flex flex-col items-center justify-center py-16 text-muted-foreground">
    <FileText className="h-8 w-8 mb-4" aria-hidden="true" />
    <p className="text-sm">No artifact available yet</p>
    <p className="text-xs mt-1">The implementation guide will appear here once generated</p>
  </div>
)

// ============================================================================
// Component
// ============================================================================

/**
 * ArtifactPreviewPanel - Inline markdown preview of analysis results
 *
 * States:
 * - Loading: Shows spinner while fetching artifact
 * - Error: Shows error message with retry hint
 * - Empty: Shows placeholder when no artifactId
 * - Content: Renders MarkdownPreview with full artifact
 *
 * WCAG Compliance:
 * - 1.3.1 (Info and Relationships): Semantic main content area
 * - 4.1.2 (Name, Role, Value): Proper aria-labels
 */
export const ArtifactPreviewPanel = memo(function ArtifactPreviewPanel({
  className,
}: ArtifactPreviewPanelProps) {
  const artifactId = useSSEStore(selectArtifactId)
  const { content, isLoading, error } = useArtifact(artifactId ?? undefined)

  return (
    <main
      className={cn(
        // Base styling
        'bg-card border border-border rounded-lg overflow-hidden',
        // Min height for visual consistency
        'min-h-[400px]',
        className
      )}
      aria-label="Implementation guide preview"
    >
      {/* Header */}
      <div className="px-4 py-3 border-b border-border bg-muted/30">
        <h2 className="text-sm font-semibold text-foreground flex items-center gap-2">
          <FileText className="h-4 w-4" aria-hidden="true" />
          Implementation Guide
        </h2>
      </div>

      {/* Content Area */}
      <div className="p-4">
        {!artifactId ? (
          <EmptyState />
        ) : isLoading ? (
          <LoadingState />
        ) : error ? (
          <ErrorState message={error.message} />
        ) : content ? (
          <MarkdownPreview content={content} showMetadata={false} />
        ) : (
          <EmptyState />
        )}
      </div>
    </main>
  )
})
