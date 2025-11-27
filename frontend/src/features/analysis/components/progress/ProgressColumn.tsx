import type { OverallProgress, ProgressStep } from '../../hooks/useAnalysisProgress'
import { AnalysisProgressCard } from '../steps/AnalysisProgressCard'
import { AnalysisStepList } from '../steps/AnalysisStepList'

interface ProgressColumnProps {
  overallProgress: OverallProgress
  steps: ProgressStep[]
}

export function ProgressColumn({ overallProgress, steps }: ProgressColumnProps) {
  return (
    <div className="lg:col-span-2 space-y-6">
      <AnalysisProgressCard
        stage={overallProgress.stage}
        progress={overallProgress.progress}
        currentStep={overallProgress.currentStep}
        totalSteps={overallProgress.totalSteps}
        completedSteps={overallProgress.completedSteps}
        estimatedTimeRemaining={overallProgress.estimatedTimeRemaining}
      />
      <AnalysisStepList steps={steps} />
    </div>
  )
}
