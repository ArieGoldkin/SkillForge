/* eslint-disable max-lines -- Component handles complex state management, error handling, SSE lifecycle, and multiple view states which require extensive logic */
import { useCallback, useEffect, useMemo, useRef, useState } from 'react'

import type { SSEStore } from '@stores/sseStore'
import {
  useSSEStore,
  useLoadingState,
  useShowTimeoutWarning,
  useShouldShowProgress,
} from '@stores/sseStore'
import { getRouteApi } from '@tanstack/react-router'

import {
  ActivityColumn,
  AnalysisCompleteCard,
  AnalysisHeader,
  ErrorAlert,
  LoadingStateDisplay,
  ProgressColumn,
  TimeoutWarningBanner,
} from './components'
import { CompletedAnalysisView } from './components/states/CompletedAnalysisView'
import { useAnalysisProgress } from './hooks/useAnalysisProgress'
import { useAnalysisStatus } from './hooks/useAnalysisStatus'

// New computed loading state hooks (Issue #399)

const routeApi = getRouteApi('/analyze/$id')

/**
 * Zustand Selectors - Optimized consolidated subscriptions
 * Reduces from 7 individual subscriptions to 3 consolidated ones
 */

/**
 * High-frequency events selector (keep separate to avoid unnecessary re-renders)
 */
const selectEvents = (state: SSEStore) => state.events

/**
 * Connection state selector - consolidates connection-related state and actions
 */
const selectConnectionState = (state: SSEStore) => ({
  isConnected: state.isConnected,
  connect: state.connect,
  disconnect: state.disconnect,
})

/**
 * Analysis state selector - consolidates analysis completion, errors, and reset
 */
const selectAnalysisState = (state: SSEStore) => ({
  isComplete: state.isComplete,
  error: state.error,
  reset: state.reset,
})

// Legacy selectors removed - now using consolidated selectors

const useSSELifecycle = ({
  analysisId,
  shouldConnect,
  connect,
  disconnect,
  reset,
}: {
  analysisId?: string
  shouldConnect: boolean
  connect: (id: string) => void
  disconnect: () => void
  reset: () => void
}) => {
  useEffect(() => {
    if (shouldConnect && analysisId) {
      reset()
      connect(analysisId)
    } else {
      disconnect()
    }
    return () => disconnect()
  }, [analysisId, shouldConnect, connect, disconnect, reset])
}

// Check if status indicates completion
const isStatusComplete = (status?: string) => status === 'completed' || status === 'complete'

// Check if truly complete (all stages passed, 100% progress)
const checkIsTrulyComplete = (params: {
  hasFailedStages: boolean
  completed?: boolean
  urlArtifactId?: string
  resolvedStatus?: string
  isComplete: boolean
  overallProgress: { stage: string; progress: number }
}) =>
  !params.hasFailedStages &&
  ((params.completed && Boolean(params.urlArtifactId)) ||
    isStatusComplete(params.resolvedStatus) ||
    (params.isComplete &&
      params.overallProgress.stage === 'complete' &&
      params.overallProgress.progress === 100))

/**
 * Custom hook for managing focus when analysis completes
 * WCAG 2.4.3: Focus Order - Moves focus to completion card for screen readers
 */
const useCompletionFocus = (isComplete: boolean) => {
  const completionRef = useRef<HTMLDivElement>(null)
  const hasAnnouncedRef = useRef(false)

  useEffect(() => {
    if (isComplete && completionRef.current && !hasAnnouncedRef.current) {
      // Focus the completion card for screen reader users
      completionRef.current.focus()
      hasAnnouncedRef.current = true
    }
  }, [isComplete])

  // Reset announcement flag when not complete
  useEffect(() => {
    if (!isComplete) {
      hasAnnouncedRef.current = false
    }
  }, [isComplete])

  return completionRef
}

// Component for rendering analysis in progress state
// eslint-disable-next-line max-lines-per-function -- Component renders progress header, timeout warning, loading state, and progress columns which require JSX structure
function AnalysisInProgress({
  analysisMetadata,
  showTimeoutWarning,
  timeoutWarningDismissed,
  onDismissTimeout,
  loadingState,
  shouldShowProgress,
  overallProgress,
  steps,
  hasFailedStages,
  failedStagesCount,
}: {
  analysisMetadata?: {
    title?: string
    url?: string
    contentType?: 'article' | 'video' | 'repo'
    wordCount?: number
  }
  showTimeoutWarning: boolean
  timeoutWarningDismissed: boolean
  onDismissTimeout: () => void
  loadingState: ReturnType<typeof useLoadingState>
  shouldShowProgress: boolean
  overallProgress: ReturnType<typeof useAnalysisProgress>['overallProgress']
  steps: ReturnType<typeof useAnalysisProgress>['steps']
  hasFailedStages: boolean
  failedStagesCount: number
}) {
  return (
    <div className="container mx-auto px-4 py-8 max-w-7xl">
      <AnalysisHeader
        title={analysisMetadata?.title || 'Content Analysis'}
        url={analysisMetadata?.url || ''}
        contentType={analysisMetadata?.contentType}
        wordCount={analysisMetadata?.wordCount}
      />
      <TimeoutWarningBanner
        showTimeoutWarning={showTimeoutWarning && !timeoutWarningDismissed}
        onDismiss={onDismissTimeout}
      />
      <LoadingStateDisplay loadingState={loadingState} />
      {shouldShowProgress && (
        <ProgressColumn
          overallProgress={overallProgress}
          steps={steps}
          hasFailedStages={hasFailedStages}
          failedStagesCount={failedStagesCount}
          analysisMetadata={analysisMetadata}
        />
      )}
    </div>
  )
}

// Right column - shows completion card or activity feed
function ActivityOrCompletionColumn({
  isComplete,
  resolvedArtifactId,
  artifactId,
  hasFailedStages,
  completionRef,
  activities,
  isConnected,
}: {
  isComplete: boolean
  resolvedArtifactId: string | undefined
  artifactId: string | undefined
  hasFailedStages: boolean
  completionRef: React.RefObject<HTMLDivElement | null>
  activities: ReturnType<typeof useAnalysisProgress>['activities']
  isConnected: boolean
}) {
  if (isComplete && (resolvedArtifactId || artifactId)) {
    return (
      <div
        ref={completionRef}
        tabIndex={-1}
        aria-label={hasFailedStages ? 'Analysis complete with errors' : 'Analysis complete'}
        className="outline-none"
      >
        <AnalysisCompleteCard variant="column" />
      </div>
    )
  }
  return <ActivityColumn activities={activities} isLive={isConnected} />
}

/**
 * Active analysis view - shows progress, activity feed, and optional completion card
 * Includes error handling, accessibility announcements, and responsive layout
 */
// eslint-disable-next-line max-lines-per-function -- Component includes accessibility features, error states, and responsive layout which require multiple JSX elements
function ActiveAnalysisView({
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
  resolvedArtifactId,
  artifactId,
  activities,
  isConnected,
  completionRef,
}: {
  id: string
  analysisMetadata?: {
    title?: string
    url?: string
    contentType?: 'article' | 'video' | 'repo'
    wordCount?: number
  }
  isComplete: boolean
  hasFailedStages: boolean
  error: Error | null
  hasError: boolean
  statusError: string | null | undefined
  isFailed: boolean
  effectiveError: string
  isFatalError: boolean
  overallProgress: ReturnType<typeof useAnalysisProgress>['overallProgress']
  steps: ReturnType<typeof useAnalysisProgress>['steps']
  failedStagesCount: number
  resolvedArtifactId: string | undefined
  artifactId: string | undefined
  activities: ReturnType<typeof useAnalysisProgress>['activities']
  isConnected: boolean
  completionRef: React.RefObject<HTMLDivElement | null>
}) {
  const hasErrors = error || hasError || statusError || isFailed
  const ariaMessage = hasFailedStages
    ? 'Analysis complete with errors. Some stages failed. Review your results below.'
    : 'Analysis complete. Review your results below.'

  return (
    <div className="container mx-auto px-4 py-8 max-w-7xl">
      <div aria-live="polite" aria-atomic="true" className="sr-only">
        {isComplete && ariaMessage}
      </div>
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
            overallProgress={overallProgress}
            steps={steps}
            hasFailedStages={hasFailedStages}
            failedStagesCount={failedStagesCount}
            analysisMetadata={analysisMetadata}
          />
          <ActivityOrCompletionColumn
            isComplete={isComplete}
            resolvedArtifactId={resolvedArtifactId}
            artifactId={artifactId}
            hasFailedStages={hasFailedStages}
            completionRef={completionRef}
            activities={activities}
            isConnected={isConnected}
          />
        </div>
      )}
    </div>
  )
}

/**
 * Main analysis result component
 * Orchestrates SSE connection, status polling, and view state management
 * Delegates rendering to specialized view components
 */
// eslint-disable-next-line complexity, max-lines-per-function -- Component orchestrates SSE lifecycle, status polling, and view routing which requires extensive setup and state management. Rendering logic is extracted to separate components.
export default function AnalyzeResult() {
  const { id } = routeApi.useParams()
  const { completed, artifactId: urlArtifactId } = routeApi.useSearch()

  // Consolidated selectors for optimal performance (3 instead of 7 subscriptions)
  const events = useSSEStore(selectEvents)
  const { isConnected, connect, disconnect } = useSSEStore(selectConnectionState)
  const { isComplete, error, reset } = useSSEStore(selectAnalysisState)

  // New computed loading states (Issue #399)
  const loadingState = useLoadingState()
  const showTimeoutWarning = useShowTimeoutWarning()
  const shouldShowProgress = useShouldShowProgress()

  // Timeout warning dismissal state (Issue #399)
  const [timeoutWarningDismissed, setTimeoutWarningDismissed] = useState(false)

  // Memoized event handler to prevent unnecessary re-renders
  const handleTimeoutWarningDismiss = useCallback(() => {
    setTimeoutWarningDismissed(true)
  }, [])

  // Focus management for accessibility
  const completionRef = useCompletionFocus(isComplete)
  // Issue #396: traceId no longer needed here - leaf components get it from store
  const {
    overallProgress,
    steps,
    activities,
    hasError,
    errorMessage,
    artifactId,
    hasFailedStages,
    failedStagesCount,
    analysisMetadata,
  } = useAnalysisProgress(events)
  const statusState = useAnalysisStatus({
    analysisId: id,
    completedParam: Boolean(completed),
    sseState: { eventsLength: events.length, isComplete, artifactId },
  })

  useSSELifecycle({
    analysisId: id,
    shouldConnect: statusState.shouldConnect,
    connect,
    disconnect,
    reset,
  })

  const { resolvedArtifactId, isResolvedComplete, isFailed, effectiveError } = useMemo(() => {
    const resolvedArtifactId = artifactId || statusState.resolvedArtifactId || urlArtifactId
    const resolvedStatus = statusState.resolvedStatus || (isComplete ? 'completed' : undefined)

    const isTrulyComplete = checkIsTrulyComplete({
      hasFailedStages,
      completed,
      urlArtifactId,
      resolvedStatus,
      isComplete,
      overallProgress,
    })

    const isResolvedComplete = isTrulyComplete
    const isFailed = resolvedStatus === 'failed' || hasError
    const effectiveError =
      statusState.statusError ||
      errorMessage ||
      error?.message ||
      'An error occurred during analysis'

    return {
      resolvedArtifactId,
      isResolvedComplete,
      isFailed,
      effectiveError,
    }
  }, [
    artifactId,
    urlArtifactId,
    statusState,
    isComplete,
    hasError,
    error,
    errorMessage,
    completed,
    overallProgress,
    hasFailedStages,
  ])

  // Issue #396: CompletedAnalysisView no longer needs artifactId/traceId props
  // - those are now accessed from Zustand store by AnalysisCompleteCard
  if (completed && urlArtifactId) {
    return (
      <CompletedAnalysisView
        analysisId={id}
        overallProgress={overallProgress}
        steps={steps}
        hasFailedStages={hasFailedStages}
        failedStagesCount={failedStagesCount}
        analysisMetadata={analysisMetadata}
      />
    )
  }

  if (isResolvedComplete && resolvedArtifactId) {
    return (
      <CompletedAnalysisView
        analysisId={id}
        overallProgress={overallProgress}
        steps={steps}
        hasFailedStages={hasFailedStages}
        failedStagesCount={failedStagesCount}
        analysisMetadata={analysisMetadata}
      />
    )
  }

  // Use computed loading states for simplified rendering (Issue #399)
  const shouldShowLoadingState =
    loadingState.type === 'waiting_for_events' ||
    loadingState.type === 'extracting' ||
    loadingState.type === 'analyzing' ||
    loadingState.type === 'generating'

  // Show loading state during analysis phases
  if (shouldShowLoadingState) {
    return (
      <AnalysisInProgress
        analysisMetadata={{
          title: analysisMetadata?.title,
          url: analysisMetadata?.url || (id ? `Analysis ID: ${id}` : ''),
          contentType: analysisMetadata?.contentType,
          wordCount: analysisMetadata?.wordCount,
        }}
        showTimeoutWarning={showTimeoutWarning}
        timeoutWarningDismissed={timeoutWarningDismissed}
        onDismissTimeout={handleTimeoutWarningDismiss}
        loadingState={loadingState}
        shouldShowProgress={shouldShowProgress}
        overallProgress={overallProgress}
        steps={steps}
        hasFailedStages={hasFailedStages}
        failedStagesCount={failedStagesCount}
      />
    )
  }

  // Handle error states
  if (loadingState.type === 'error') {
    return (
      <div className="container mx-auto px-4 py-8 max-w-7xl">
        <AnalysisHeader
          title={analysisMetadata?.title || 'Content Analysis'}
          url={analysisMetadata?.url || (id ? `Analysis ID: ${id}` : '')}
          contentType={analysisMetadata?.contentType}
          wordCount={analysisMetadata?.wordCount}
        />
        <LoadingStateDisplay loadingState={loadingState} />
      </div>
    )
  }

  // Handle completion states
  if (loadingState.type === 'complete') {
    return (
      <CompletedAnalysisView
        analysisId={id}
        overallProgress={overallProgress}
        steps={steps}
        hasFailedStages={hasFailedStages}
        failedStagesCount={failedStagesCount}
        analysisMetadata={analysisMetadata}
      />
    )
  }

  const isFatalError = Boolean(
    (error || statusState.statusError || isFailed) && events.length === 0 && !isConnected
  )

  return (
    <ActiveAnalysisView
      id={id}
      analysisMetadata={analysisMetadata}
      isComplete={isComplete}
      hasFailedStages={hasFailedStages}
      error={error}
      hasError={hasError}
      statusError={statusState.statusError}
      isFailed={isFailed}
      effectiveError={effectiveError}
      isFatalError={isFatalError}
      overallProgress={overallProgress}
      steps={steps}
      failedStagesCount={failedStagesCount}
      resolvedArtifactId={resolvedArtifactId}
      artifactId={artifactId}
      activities={activities}
      isConnected={isConnected}
      completionRef={completionRef}
    />
  )
}
