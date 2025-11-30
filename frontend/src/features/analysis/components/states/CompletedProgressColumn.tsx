import { AnalysisProgressCard } from '../steps/AnalysisProgressCard'
import { AnalysisStepList } from '../steps/AnalysisStepList'
import { STAGE_CONFIG, TOTAL_STAGES } from '../../hooks/stageConfig'
import type { StageName } from '@app-types/sse'
import type { AnalysisStep } from '../steps/AnalysisStepList'

const completedSteps: AnalysisStep[] = Object.entries(STAGE_CONFIG)
  .sort(([, a], [, b]) => a.order - b.order)
  .map(([stageName, config]) => ({
    id: stageName as StageName,
    title: config.title,
    status: 'completed' as const,
    description: 'Completed',
  }))

export function CompletedProgressColumn() {
  return (
    <div className="lg:col-span-2 space-y-6">
      <AnalysisProgressCard
        stage="complete"
        progress={100}
        currentStep="Analysis Complete"
        totalSteps={TOTAL_STAGES}
        completedSteps={TOTAL_STAGES}
      />
      <AnalysisStepList steps={completedSteps} />
    </div>
  )
}
