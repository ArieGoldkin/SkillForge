import type { OverallProgress, ProgressStep } from '../../hooks/useAnalysisProgress'
import { ProgressColumn } from '../progress/ProgressColumn'
import { AnalysisHeader } from '../steps/AnalysisHeader'

import { AnalysisCompleteCard } from './AnalysisCompleteCard'

interface CompletedAnalysisViewProps {
  analysisId?: string
  artifactId: string
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

export function CompletedAnalysisView({
  analysisId,
  artifactId,
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
        <AnalysisCompleteCard
          artifactId={artifactId}
          analysisId={analysisId}
          variant="column"
          hasFailedStages={hasFailedStages}
          failedStagesCount={failedStagesCount}
        />
      </div>
    </div>
  )
}
