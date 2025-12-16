import type { OverallProgress, ProgressStep } from '../../hooks/useAnalysisProgress'
import { AnalysisProgressCard } from '../steps/AnalysisProgressCard'
import { AnalysisStepList } from '../steps/AnalysisStepList'

interface ProgressColumnProps {
  overallProgress: OverallProgress
  steps: ProgressStep[]
  analysisMetadata?: {
    title?: string
    contentType?: 'article' | 'video' | 'repo'
    url?: string
    wordCount?: number
  }
}

export function ProgressColumn({ overallProgress, steps, analysisMetadata }: ProgressColumnProps) {
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
      />
      <AnalysisStepList steps={steps} />
    </div>
  )
}
