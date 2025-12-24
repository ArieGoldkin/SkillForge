import { BUSINESS_CONSTANTS, ROUTING_PRIORITIES } from '@/lib/constants'

import { ErrorBoundary } from '@shared/components'

import { ActivityColumn } from '../activity/ActivityColumn'
import { LoadingStateDisplay } from '../LoadingStateDisplay'
import { ErrorAlert } from '../progress/ErrorAlert'
import { ProgressColumn } from '../progress/ProgressColumn'
import { AnalysisCompleteCard } from '../states/AnalysisCompleteCard'
import { CompletedAnalysisView } from '../states/CompletedAnalysisView'
import { AnalysisHeader } from '../steps/AnalysisHeader'

import { CommonAnalysisLayout } from './CommonAnalysisLayout'
import { extractCompletionProps, extractProgressProps } from './route-helpers'
import type { RenderRoute, AnalysisProps } from './types'

/**
 * Priority-based render routes for analysis states
 *
 * Routes are evaluated in order of priority (highest first).
 * The first route whose condition returns true will be used.
 *
 * Issue #439: Artifact-based completion model
 * ============================================
 * Completion is determined by artifact existence (single source of truth).
 * - isResolvedComplete = Boolean(resolvedArtifactId) from AnalyzeResult.tsx
 * - This eliminates state desync between SSE, progress calc, and router
 * - hasFailedStages is for UI display (error badge), not completion gating
 */
const RENDER_ROUTES: RenderRoute[] = [
  // Priority 100: Legacy completion (highest priority - backwards compatibility)
  // Used when navigating directly to a completed analysis via URL params
  {
    priority: BUSINESS_CONSTANTS.PRIORITY_LEGACY_COMPLETION,
    condition: ({ completed, urlArtifactId }) => Boolean(completed && urlArtifactId),
    render: (props) => <CompletedAnalysisView {...extractCompletionProps(props)} />,
  },

  // Priority 90: Modern completion (artifact-based - Issue #439)
  // Artifact existence is the single source of truth for completion
  {
    priority: ROUTING_PRIORITIES.MODERN_COMPLETION,
    condition: ({ isResolvedComplete, resolvedArtifactId }) =>
      Boolean(isResolvedComplete && resolvedArtifactId),
    render: (props) => <CompletedAnalysisView {...extractCompletionProps(props)} />,
  },

  // Priority 80: Loading states (active analysis phases)
  {
    priority: ROUTING_PRIORITIES.LOADING_STATES,
    condition: ({ loadingState }) =>
      ['waiting_for_events', 'extracting', 'analyzing', 'generating'].includes(loadingState.type),
    render: (props) => (
      <CommonAnalysisLayout
        analysisMetadata={props.analysisMetadata}
        analysisId={props.id}
        showTimeoutWarning={props.showTimeoutWarning && !props.timeoutWarningDismissed}
        onTimeoutWarningDismiss={props.handleTimeoutWarningDismiss}
        progressContent={
          props.shouldShowProgress ? (
            <ErrorBoundary fallback={<div>Error loading progress</div>} name="ProgressColumn">
              <ProgressColumn
                {...extractProgressProps({
                  overallProgress: props.overallProgress,
                  steps: props.steps,
                  hasFailedStages: props.hasFailedStages,
                  failedStagesCount: props.failedStagesCount,
                  failedStageErrorCodes: props.failedStageErrorCodes,
                  analysisMetadata: props.analysisMetadata,
                  stageStatuses: props.stageStatuses,
                  analysisMode: props.analysisMode,
                  activities: props.activities,
                  isConnected: props.isConnected,
                  skipReasons: props.skipReasons,
                  stageSuccessMetrics: props.stageSuccessMetrics,
                })}
              />
            </ErrorBoundary>
          ) : undefined
        }
      >
        <LoadingStateDisplay loadingState={props.loadingState} />
      </CommonAnalysisLayout>
    ),
  },

  // Priority 70: Error states (analysis failed)
  {
    priority: ROUTING_PRIORITIES.ERROR_STATES,
    condition: ({ loadingState }) => loadingState.type === 'error',
    render: (props) => (
      <CommonAnalysisLayout analysisMetadata={props.analysisMetadata} analysisId={props.id}>
        <LoadingStateDisplay loadingState={props.loadingState} />
      </CommonAnalysisLayout>
    ),
  },

  // Priority 60: Loading completion (analysis finished via loading state)
  {
    priority: ROUTING_PRIORITIES.LOADING_COMPLETION,
    condition: ({ loadingState }) => loadingState.type === 'complete',
    render: (props) => <CompletedAnalysisView {...extractCompletionProps(props)} />,
  },

  // Priority 10: Default analysis UI (fallback - active analysis view)
  {
    priority: ROUTING_PRIORITIES.DEFAULT_ANALYSIS_UI,
    condition: () => true, // Always matches as fallback
    // eslint-disable-next-line complexity, max-lines-per-function -- Complex conditional rendering logic for multiple analysis states
    render: (props) => {
      const {
        id,
        analysisMetadata,
        isComplete,
        hasFailedStages,
        error,
        hasError,
        statusError,
        isFailed,
        effectiveError,
        isFatalError,
        overallProgress,
        steps,
        failedStagesCount,
        failedStageErrorCodes,
        resolvedArtifactId,
        artifactId,
        activities,
        isConnected,
        completionRef,
      } = props

      const hasErrors = error || hasError || statusError || isFailed
      const ariaMessage = hasFailedStages
        ? 'Analysis complete with errors. Some stages failed. Review your results below.'
        : 'Analysis complete. Review your results below.'

      // Inline the ActiveAnalysisView logic to avoid type conflicts
      return (
        <div className="container mx-auto px-4 py-8 max-w-7xl" data-testid="active-analysis-view">
          <div aria-live="polite" aria-atomic="true" className="sr-only">
            {isComplete && ariaMessage}
          </div>
          {/* Test helper text */}
          <div style={{ display: 'none' }}>Active: {id}</div>
          <AnalysisHeader
            title={analysisMetadata?.title || 'Content Analysis'}
            url={analysisMetadata?.url || (id ? `Analysis ID: ${id}` : '')}
            contentType={analysisMetadata?.contentType}
            wordCount={analysisMetadata?.wordCount}
          />
          {hasErrors && <ErrorAlert message={effectiveError} />}
          {!isFatalError && (
            <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
              <ProgressColumn
                {...extractProgressProps({
                  overallProgress,
                  steps,
                  hasFailedStages,
                  failedStagesCount,
                  failedStageErrorCodes,
                  analysisMetadata,
                  stageStatuses: props.stageStatuses,
                  analysisMode: props.analysisMode,
                  activities,
                  isConnected,
                  skipReasons: props.skipReasons,
                  stageSuccessMetrics: props.stageSuccessMetrics,
                })}
              />
              {/* Activity or Completion Column */}
              {isComplete && (resolvedArtifactId || artifactId) ? (
                <div
                  ref={completionRef}
                  tabIndex={-1}
                  aria-label={
                    hasFailedStages ? 'Analysis complete with errors' : 'Analysis complete'
                  }
                  className="outline-none"
                >
                  <AnalysisCompleteCard variant="column" />
                </div>
              ) : (
                <ActivityColumn activities={activities} isLive={isConnected} />
              )}
            </div>
          )}
        </div>
      )
    },
  },
]

/**
 * Declarative render router for analysis states
 *
 * Replaces complex nested conditionals with a clean, priority-based routing system.
 * Each route defines a condition and render function. Routes are evaluated in
 * priority order (highest first), and the first matching route is used.
 *
 * @param props - Complete analysis props
 * @returns The rendered React element for the current analysis state
 */
export function AnalysisRenderRouter(props: AnalysisProps) {
  // Sort routes by priority (highest first) and find the first match
  const route = [...RENDER_ROUTES]
    .sort((a, b) => b.priority - a.priority)
    .find((route) => route.condition(props))

  // This should never happen if routes are properly configured
  if (!route) {
    throw new Error('No render route matched - this indicates a configuration error')
  }

  return route.render(props)
}
