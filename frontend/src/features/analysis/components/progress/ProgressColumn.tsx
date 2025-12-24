import { memo } from 'react'

import type { StageName } from '@app-types/sse'

import type { StageStatusEntry } from '../../hooks/stageConfig'
import type { AgentActivity } from '../../hooks/useActivityFeed'
import type { OverallProgress } from '../../hooks/useAnalysisProgress'
import type { AnalysisMode } from '../../types/accordion'
import { AccordionProgressTracker } from '../accordion/AccordionProgressTracker'
import type { SuccessMetrics } from '../accordion/AccordionProgressTracker'
import { AnalysisProgressCard } from '../steps/AnalysisProgressCard'

interface ProgressColumnProps {
  overallProgress: OverallProgress
  hasFailedStages?: boolean
  failedStagesCount?: number
  failedStageErrorCodes?: string[]
  analysisMetadata?: {
    title?: string
    contentType?: 'article' | 'video' | 'repo'
    url?: string
    wordCount?: number
  }
  /** Stage statuses for accordion groups */
  stageStatuses: Map<StageName, StageStatusEntry>
  analysisMode?: AnalysisMode
  activities?: AgentActivity[]
  isLive?: boolean
  skipReasons?: Record<string, string>
  stageSuccessMetrics?: Map<string, SuccessMetrics>
}

/**
 * ProgressColumn - Displays analysis progress with hierarchical accordion groups
 *
 * Renders stage progress using AccordionProgressTracker with:
 * - 7 collapsible stage groups (Core Workflow, Content Analysis, Tier 1-3, etc.)
 * - MiniMap sidebar for quick navigation
 * - Activity feed integration
 *
 * Wrapped with React.memo to prevent re-renders when parent re-renders
 * but props haven't changed. Critical for SSE streaming performance.
 */
export const ProgressColumn = memo(function ProgressColumn({
  overallProgress,
  hasFailedStages = false,
  failedStagesCount = 0,
  failedStageErrorCodes = [],
  analysisMetadata,
  stageStatuses,
  analysisMode = 'standard',
  activities = [],
  isLive = false,
  skipReasons,
  stageSuccessMetrics,
}: ProgressColumnProps) {
  return (
    <div className="lg:col-span-2 space-y-6">
      {/* Overall progress summary */}
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
        failedStageErrorCodes={failedStageErrorCodes}
      />

      {/* Hierarchical accordion progress tracker */}
      <AccordionProgressTracker
        stageStatuses={stageStatuses}
        skipReasons={skipReasons}
        stageSuccessMetrics={stageSuccessMetrics}
        analysisMode={analysisMode}
        activities={activities}
        isLive={isLive}
      />
    </div>
  )
})
