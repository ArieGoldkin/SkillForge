/**
 * CompletedAnalysisView - Full page view for completed analysis
 *
 * Issue #396: Simplified props - AnalysisCompleteCard now gets data
 * from Zustand store instead of prop drilling.
 *
 * Wrapped with React.memo - only re-renders when props change.
 */
import { memo } from 'react'

import type { OverallProgress, ProgressStep } from '../../hooks/useAnalysisProgress'
import { ProgressColumn } from '../progress/ProgressColumn'
import { AnalysisHeader } from '../steps/AnalysisHeader'

import { AnalysisCompleteCard } from './AnalysisCompleteCard'

interface CompletedAnalysisViewProps {
  /** Used for header URL display only */
  analysisId?: string
  overallProgress: OverallProgress
  steps: ProgressStep[]
  hasFailedStages: boolean
  failedStagesCount: number
  analysisMetadata?: {
    title?: string
    contentType?: 'article' | 'video' | 'repo'
    url?: string
    wordCount?: number
  }
}

export const CompletedAnalysisView = memo(function CompletedAnalysisView({
  analysisId,
  overallProgress,
  steps,
  hasFailedStages,
  failedStagesCount,
  analysisMetadata,
}: CompletedAnalysisViewProps) {
  return (
    <div className="container mx-auto px-4 py-8 max-w-7xl">
      <AnalysisHeader
        title={analysisMetadata?.title || 'Content Analysis'}
        url={analysisMetadata?.url || (analysisId ? `Analysis ID: ${analysisId}` : '')}
        contentType={analysisMetadata?.contentType}
        wordCount={analysisMetadata?.wordCount}
      />

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <ProgressColumn
          overallProgress={overallProgress}
          steps={steps}
          hasFailedStages={hasFailedStages}
          failedStagesCount={failedStagesCount}
          analysisMetadata={analysisMetadata}
        />
        {/* Issue #396: AnalysisCompleteCard gets data from store */}
        <AnalysisCompleteCard variant="column" />
      </div>
    </div>
  )
})
