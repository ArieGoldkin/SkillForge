import { memo } from 'react'

import type { OverallProgress, ProgressStep } from '../../hooks/useAnalysisProgress'
import { AnalysisProgressCard } from '../steps/AnalysisProgressCard'
import { AnalysisStepList } from '../steps/AnalysisStepList'

interface ProgressColumnProps {
  overallProgress: OverallProgress
  steps: ProgressStep[]
  hasFailedStages?: boolean
  failedStagesCount?: number
  analysisMetadata?: {
    title?: string
    contentType?: 'article' | 'video' | 'repo'
    url?: string
    wordCount?: number
  }
}

/**
 * ProgressColumn - Displays analysis progress card and step list
 *
 * Wrapped with React.memo to prevent re-renders when parent re-renders
 * but props haven't changed. Critical for SSE streaming performance.
 */
export const ProgressColumn = memo(function ProgressColumn({
  overallProgress,
  steps,
  hasFailedStages = false,
  failedStagesCount = 0,
  analysisMetadata,
}: ProgressColumnProps) {
  return (
    <div className="lg:col-span-2 space-y-6">
      <AnalysisProgressCard
        stage={overallProgress.stage}
        progress={overallProgress.progress}
        currentStep={overallProgress.currentStep}
        totalSteps={overallProgress.totalSteps}
        completedSteps={overallProgress.completedSteps}
        estimatedTimeRemaining={overallProgress.estimatedTimeRemaining}
        contentType={analysisMetadata?.contentType}
        wordCount={analysisMetadata?.wordCount}
        hasFailedStages={hasFailedStages}
        failedStagesCount={failedStagesCount}
      />
      <AnalysisStepList steps={steps} />
    </div>
  )
})
