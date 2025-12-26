import type { CompletionProps, ProgressProps, AnalysisProps } from './types'

/**
 * Extracts props needed for completion views (CompletedAnalysisView)
 */
export function extractCompletionProps(props: {
  id?: string
  overallProgress: AnalysisProps['overallProgress']
  steps: AnalysisProps['steps']
  hasFailedStages: boolean
  failedStagesCount: number
  analysisMetadata?: AnalysisProps['analysisMetadata']
  stageStatuses?: AnalysisProps['stageStatuses']
  analysisMode?: AnalysisProps['analysisMode']
  skipReasons?: AnalysisProps['skipReasons']
  stageSuccessMetrics?: AnalysisProps['stageSuccessMetrics']
}): CompletionProps {
  if (!props.id) {
    throw new Error('Analysis ID is required for completion props')
  }

  return {
    analysisId: props.id,
    overallProgress: props.overallProgress,
    steps: props.steps,
    hasFailedStages: props.hasFailedStages,
    failedStagesCount: props.failedStagesCount,
    analysisMetadata: props.analysisMetadata,
    stageStatuses: props.stageStatuses ?? new Map(),
    analysisMode: props.analysisMode,
    skipReasons: props.skipReasons,
    stageSuccessMetrics: props.stageSuccessMetrics,
  }
}

/**
 * Extracts props needed for progress views (ProgressColumn with accordion)
 */
export function extractProgressProps(props: {
  overallProgress: AnalysisProps['overallProgress']
  hasFailedStages: boolean
  failedStagesCount: number
  failedStageErrorCodes?: string[]
  analysisMetadata?: AnalysisProps['analysisMetadata']
  stageStatuses: NonNullable<AnalysisProps['stageStatuses']>
  analysisMode?: AnalysisProps['analysisMode']
  activities?: AnalysisProps['activities']
  isConnected?: boolean
  skipReasons?: AnalysisProps['skipReasons']
  stageSuccessMetrics?: AnalysisProps['stageSuccessMetrics']
}): ProgressProps {
  return {
    overallProgress: props.overallProgress,
    hasFailedStages: props.hasFailedStages,
    failedStagesCount: props.failedStagesCount,
    failedStageErrorCodes: props.failedStageErrorCodes,
    analysisMetadata: props.analysisMetadata,
    stageStatuses: props.stageStatuses,
    analysisMode: props.analysisMode,
    activities: props.activities,
    isLive: props.isConnected,
    skipReasons: props.skipReasons,
    stageSuccessMetrics: props.stageSuccessMetrics,
  }
}

/**
 * Creates header props for consistent header rendering
 */
export function createHeaderProps(props: {
  analysisMetadata?: AnalysisProps['analysisMetadata']
  id?: string
}) {
  return {
    title: props.analysisMetadata?.title || 'Content Analysis',
    url: props.analysisMetadata?.url || (props.id ? `Analysis ID: ${props.id}` : ''),
    contentType: props.analysisMetadata?.contentType,
    wordCount: props.analysisMetadata?.wordCount,
  }
}
