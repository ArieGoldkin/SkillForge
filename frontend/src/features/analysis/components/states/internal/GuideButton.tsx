/**
 * GuideButton - Navigate to artifact view
 *
 * Gets artifact/analysis IDs from Zustand store (Issue #396)
 * instead of props, eliminating 4-level prop drilling.
 *
 * Note: traceId is also available in the store and can be accessed
 * on the artifact page via useSSEStore(selectTraceId).
 */
import { selectAnalysisId, selectArtifactId, useSSEStore } from '@stores/sseStore'
import { Link } from '@tanstack/react-router'
import { ArrowRight, FileText } from 'lucide-react'

import { Button } from '@shared/components/ui/button'

import { cn } from '@lib/utils'

interface GuideButtonProps {
  /** UI-only prop - controls button size */
  isCompact?: boolean
}

export function GuideButton({ isCompact = false }: GuideButtonProps) {
  // Get IDs from store instead of props (Issue #396)
  const artifactId = useSSEStore(selectArtifactId)
  const analysisId = useSSEStore(selectAnalysisId)

  // Don't render if no artifact available
  if (!artifactId) return null

  return (
    <Link
      to="/artifact/$artifactId"
      params={{ artifactId }}
      search={{ analysisId: analysisId || undefined }}
    >
      <Button size={isCompact ? 'default' : 'lg'} className="gap-2">
        <FileText className={cn(isCompact ? 'h-4 w-4' : 'h-5 w-5')} />
        View Guide
        <ArrowRight className="h-4 w-4" />
      </Button>
    </Link>
  )
}
