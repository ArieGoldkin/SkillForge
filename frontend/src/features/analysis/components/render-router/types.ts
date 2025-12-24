import type { ReactElement } from 'react'

import type { StageName } from '@app-types/sse'

import type { OverallProgress, AnalysisMetadata } from '../../../../stores/sseStore'
import type { LoadingState } from '../../../../types/loading'
import type { StageStatusEntry } from '../../hooks/stageConfig'
import type { AgentActivity } from '../../hooks/useActivityFeed'
import type { AnalysisMode } from '../../types/accordion'
import type { SuccessMetrics } from '../accordion/AccordionProgressTracker'
import type { AnalysisStep } from '../steps/AnalysisStepList'

/**
 * Interface for a render route with priority-based matching
 */
export interface RenderRoute {
  /** Priority determines order (higher = evaluated first) */
  priority: number
  /** Condition function that returns true if this route should be used */
  condition: (props: AnalysisProps) => boolean
  /** Render function that returns the React element for this route */
  render: (props: AnalysisProps) => ReactElement
}

/**
 * Complete props interface for the analysis render router
 * This includes all props that any route might need
 */
export interface AnalysisProps {
  // Route parameters
  id?: string
  completed?: boolean
  urlArtifactId?: string

  // Computed states
  isResolvedComplete: boolean
  resolvedArtifactId?: string
  artifactId?: string
  isFatalError: boolean
  effectiveError: string

  // Loading states
  loadingState: LoadingState
  showTimeoutWarning: boolean
  timeoutWarningDismissed: boolean
  shouldShowProgress: boolean
  handleTimeoutWarningDismiss: () => void

  // Progress and metadata
  overallProgress: OverallProgress
  steps: AnalysisStep[]
  activities: AgentActivity[]
  hasFailedStages: boolean
  failedStagesCount: number
  failedStageErrorCodes?: string[]
  analysisMetadata?: AnalysisMetadata
  // New props for accordion view
  stageStatuses?: Map<StageName, StageStatusEntry>
  analysisMode?: AnalysisMode
  skipReasons?: Record<string, string>
  stageSuccessMetrics?: Map<string, SuccessMetrics>

  // Error states
  error: Error | null
  hasError: boolean
  statusError: string | null | undefined
  isFailed: boolean

  // Connection state
  isConnected: boolean
  isComplete: boolean

  // Accessibility refs
  completionRef: React.RefObject<HTMLDivElement | null>
}

/**
 * Props for completion-related routes
 */
export interface CompletionProps {
  analysisId: string
  overallProgress: OverallProgress
  steps: AnalysisStep[]
  hasFailedStages: boolean
  failedStagesCount: number
  analysisMetadata?: AnalysisMetadata
}

/**
 * Props for progress-related routes
 */
export interface ProgressProps {
  overallProgress: OverallProgress
  steps: AnalysisStep[]
  hasFailedStages: boolean
  failedStagesCount: number
  failedStageErrorCodes?: string[]
  analysisMetadata?: AnalysisMetadata
  // New props for accordion view
  stageStatuses?: Map<StageName, StageStatusEntry>
  analysisMode?: AnalysisMode
  activities?: AgentActivity[]
  isLive?: boolean
  skipReasons?: Record<string, string>
  stageSuccessMetrics?: Map<string, SuccessMetrics>
  useAccordion?: boolean
}
