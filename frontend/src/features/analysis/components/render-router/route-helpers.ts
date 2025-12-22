import { BUSINESS_CONSTANTS } from '@/lib/constants'

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
  }
}

/**
 * Extracts props needed for progress views (ProgressColumn)
 */
export function extractProgressProps(props: {
  overallProgress: AnalysisProps['overallProgress']
  steps: AnalysisProps['steps']
  hasFailedStages: boolean
  failedStagesCount: number
  failedStageErrorCodes?: string[]
  analysisMetadata?: AnalysisProps['analysisMetadata']
}): ProgressProps {
  return {
    overallProgress: props.overallProgress,
    steps: props.steps,
    hasFailedStages: props.hasFailedStages,
    failedStagesCount: props.failedStagesCount,
    failedStageErrorCodes: props.failedStageErrorCodes,
    analysisMetadata: props.analysisMetadata,
  }
}

/**
 * Extracts props needed for the default analysis UI (ActiveAnalysisView)
 * NOTE: This function is currently unused as ActiveAnalysisView was inlined into the router
 * Keeping it for backwards compatibility in case it's needed in the future
 */
// eslint-disable-next-line max-lines-per-function -- Complex prop extraction and transformation logic for analysis UI
export function extractAnalysisProps(props: {
  id: string
  analysisMetadata?: AnalysisProps['analysisMetadata']
  isComplete: boolean
  hasFailedStages: boolean
  error: Error | null
  hasError: boolean
  statusError: string | null | undefined
  isFailed: boolean
  effectiveError: string
  isFatalError: boolean
  overallProgress: AnalysisProps['overallProgress']
  steps: AnalysisProps['steps']
  failedStagesCount: number
  resolvedArtifactId?: string
  artifactId?: string
  activities: AnalysisProps['activities']
  isConnected: boolean
  completionRef: AnalysisProps['completionRef']
}) {
  // Transform complex types to what ActiveAnalysisView expects
  const simplifiedOverallProgress = {
    stage: props.overallProgress.stage,
    progress: props.overallProgress.progress,
  }

  const simplifiedSteps = props.steps.map((step) => ({
    id: step.id,
    name: step.title || step.id, // Use title as name, fallback to id
    status: (step.status === 'in-progress'
      ? 'running'
      : step.status === 'skipped'
        ? 'pending'
        : step.status) as 'pending' | 'running' | 'completed' | 'failed', // Map and cast status
    progress: step.timestamp ? BUSINESS_CONSTANTS.PROGRESS_COMPLETE_PERCENTAGE : undefined, // Simple progress calculation
    error: step.errorDetails?.error,
  }))

  return {
    id: props.id,
    analysisMetadata: props.analysisMetadata,
    isComplete: props.isComplete,
    hasFailedStages: props.hasFailedStages,
    error: props.error,
    hasError: props.hasError,
    statusError: props.statusError,
    isFailed: props.isFailed,
    effectiveError: props.effectiveError,
    isFatalError: props.isFatalError,
    overallProgress: simplifiedOverallProgress,
    steps: simplifiedSteps,
    failedStagesCount: props.failedStagesCount,
    resolvedArtifactId: props.resolvedArtifactId,
    artifactId: props.artifactId,
    activities: props.activities,
    isConnected: props.isConnected,
    completionRef: props.completionRef,
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
