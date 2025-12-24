import { memo } from 'react'

import type { StageName } from '@app-types/sse'

import type { StageStatusEntry } from '../../hooks/stageConfig'
import type { AgentActivity } from '../../hooks/useActivityFeed'
import type { OverallProgress, ProgressStep } from '../../hooks/useAnalysisProgress'
import type { AnalysisMode } from '../../types/accordion'
import { AccordionProgressTracker } from '../accordion/AccordionProgressTracker'
import type { SuccessMetrics } from '../accordion/AccordionProgressTracker'
import { AnalysisProgressCard } from '../steps/AnalysisProgressCard'
import { AnalysisStepList } from '../steps/AnalysisStepList'

interface ProgressColumnProps {
  overallProgress: OverallProgress
  steps: ProgressStep[]
  hasFailedStages?: boolean
  failedStagesCount?: number
  failedStageErrorCodes?: string[]
  analysisMetadata?: {
    title?: string
    contentType?: 'article' | 'video' | 'repo'
    url?: string
    wordCount?: number
  }
  // New props for accordion view
  stageStatuses?: Map<StageName, StageStatusEntry>
  analysisMode?: AnalysisMode
  activities?: AgentActivity[]
  isLive?: boolean
  skipReasons?: Record<string, string>
  stageSuccessMetrics?: Map<string, SuccessMetrics>
  /**
   * Feature flag to enable accordion view
   * @default true - Accordion is the new default
   */
  useAccordion?: boolean
}

/**
 * ProgressColumn - Displays analysis progress card and step list/accordion
 *
 * Supports two display modes:
 * 1. Accordion view (default) - Hierarchical collapsible groups with stage organization
 * 2. Legacy flat list - Simple step-by-step list view
 *
 * Wrapped with React.memo to prevent re-renders when parent re-renders
 * but props haven't changed. Critical for SSE streaming performance.
 */
export const ProgressColumn = memo(function ProgressColumn({
  overallProgress,
  steps,
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
  useAccordion = true,
}: ProgressColumnProps) {
  // Convert 'deep_dive' to 'deep' for AccordionProgressTracker
  const normalizedAnalysisMode: AnalysisMode =
    analysisMode === 'deep_dive' ? 'deep' : (analysisMode as AnalysisMode)

  return (
    <div className="lg:col-span-2 space-y-6">
      {/* Overall progress summary - always shown */}
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

      {/* Conditional rendering: Accordion view or legacy flat list */}
      {useAccordion && stageStatuses ? (
        <AccordionProgressTracker
          stageStatuses={stageStatuses}
          skipReasons={skipReasons}
          stageSuccessMetrics={stageSuccessMetrics}
          analysisMode={normalizedAnalysisMode}
          activities={activities}
          isLive={isLive}
        />
      ) : (
        <AnalysisStepList steps={steps} />
      )}
    </div>
  )
})
