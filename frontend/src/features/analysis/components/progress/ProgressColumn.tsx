import { AnalysisProgressCard } from '../steps/AnalysisProgressCard'
import { AnalysisStepList } from '../steps/AnalysisStepList'
import { AnalysisSteps } from '../steps/AnalysisSteps'

interface MockTimestamps {
  twoMinAgo: string
  ninetySecAgo: string
  oneMinAgo: string
  fortyFiveSecAgo: string
  now: string
}

interface ProgressColumnProps {
  status: string
  mockTimestamps: MockTimestamps
}

export function ProgressColumn({ status, mockTimestamps }: ProgressColumnProps) {
  const isComplete = status === 'complete'

  return (
    <div className="lg:col-span-2 space-y-6">
      <AnalysisProgressCard
        stage={isComplete ? 'complete' : 'analyzing'}
        progress={isComplete ? 100 : 65}
        currentStep={isComplete ? 'Analysis complete' : 'Analyzing content'}
        totalSteps={4}
        completedSteps={isComplete ? 4 : 2}
        estimatedTimeRemaining={isComplete ? undefined : '~45 sec'}
      />
      <AnalysisStepList steps={AnalysisSteps({ isComplete, mockTimestamps })} />
    </div>
  )
}
