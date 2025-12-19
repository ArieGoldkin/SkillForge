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

import { ErrorBoundary } from '@shared/components'

import {
  ActivityColumn,
  AnalysisCompleteCard,
  AnalysisErrorFallback,
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

// Check if status indicates completion (both 'complete' from SSE and 'completed' from backend)
const isStatusComplete = (status?: string) => status === 'completed' || status === 'complete'

// Check if we're still waiting for SSE events to start
const checkWaitingForFirstEvent = (params: {
  isResolvedComplete: boolean
  isFailed: boolean
  eventsLength: number
  error: Error | null
  isComplete: boolean
  statusLoading: boolean
  resolvedStatus?: string
}) =>
  !params.isResolvedComplete &&
  !params.isFailed &&
  params.eventsLength === 0 &&
  !params.error &&
  !params.isComplete &&
  (params.statusLoading || !params.resolvedStatus)

// useDerivedState logic inlined into useMemo above for React Compiler compatibility

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

// eslint-disable-next-line complexity -- Component handles complex state management, error handling, SSE lifecycle, and multiple view states which require extensive logic
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
    // Inline the useDerivedState logic to avoid React Compiler memoization issues
    const resolvedArtifactId = artifactId || statusState.resolvedArtifactId || urlArtifactId
    const resolvedStatus = statusState.resolvedStatus || (isComplete ? 'completed' : undefined)

    // CRITICAL: Only consider analysis truly complete if:
    // 1. Artifact generation completed (isComplete = true)
    // 2. No failed stages (overallProgress.stage === 'complete', not just 'analyzing' or 'generating')
    // 3. Progress is 100% (not 99% which indicates failures or pending stages)
    // 4. No failed stages (hasFailedStages = false) - CRITICAL: Never show as truly complete if there are failed stages
    const isTrulyComplete =
      !hasFailedStages &&
      ((completed && Boolean(urlArtifactId)) ||
        isStatusComplete(resolvedStatus) ||
        (isComplete && overallProgress.stage === 'complete' && overallProgress.progress === 100))

    const isResolvedComplete = isTrulyComplete
    const isFailed = resolvedStatus === 'failed' || hasError
    const effectiveError =
      statusState.statusError ||
      errorMessage ||
      error?.message ||
      'An error occurred during analysis'
    const waitingForFirstEvent = checkWaitingForFirstEvent({
      isResolvedComplete,
      isFailed,
      eventsLength: events.length,
      error,
      isComplete,
      statusLoading: statusState.loading,
      resolvedStatus: statusState.resolvedStatus,
    })

    return {
      resolvedArtifactId,
      isResolvedComplete,
      isFailed,
      waitingForFirstEvent,
      effectiveError,
    }
  }, [
    artifactId,
    urlArtifactId,
    statusState,
    isComplete,
    events,
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
      <div className="container mx-auto px-4 py-8 max-w-7xl">
        <AnalysisHeader
          title={analysisMetadata?.title || 'Content Analysis'}
          url={analysisMetadata?.url || (id ? `Analysis ID: ${id}` : '')}
          contentType={analysisMetadata?.contentType}
          wordCount={analysisMetadata?.wordCount}
        />

        {/* Timeout warning banner (Issue #399) */}
        <TimeoutWarningBanner
          showTimeoutWarning={showTimeoutWarning && !timeoutWarningDismissed}
          onDismiss={handleTimeoutWarningDismiss}
        />

        <LoadingStateDisplay loadingState={loadingState} />

        {/* Show progress during analysis phases */}
        {shouldShowProgress && (
          <ErrorBoundary
            fallback={(props) => <AnalysisErrorFallback {...props} section="Progress" />}
            name="ProgressColumn"
          >
            <ProgressColumn
              overallProgress={overallProgress}
              steps={steps}
              hasFailedStages={hasFailedStages}
              failedStagesCount={failedStagesCount}
              analysisMetadata={analysisMetadata}
            />
          </ErrorBoundary>
        )}
      </div>
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

  // Determine if this is a fatal error (no events received and connection failed)
  const isFatalError =
    (error || statusState.statusError || isFailed) && events.length === 0 && !isConnected

  return (
    <div className="container mx-auto px-4 py-8 max-w-7xl">
      {/* Live region for screen reader announcements */}
      <div aria-live="polite" aria-atomic="true" className="sr-only">
        {isComplete &&
          (hasFailedStages
            ? 'Analysis complete with errors. Some stages failed. Review your results below.'
            : 'Analysis complete. Review your results below.')}
      </div>

      <AnalysisHeader
        title={analysisMetadata?.title || 'Content Analysis'}
        url={analysisMetadata?.url || (id ? `Analysis ID: ${id}` : '')}
        contentType={analysisMetadata?.contentType}
        wordCount={analysisMetadata?.wordCount}
      />

      {(error || hasError || statusState.statusError || isFailed) && (
        <ErrorAlert message={effectiveError} />
      )}

      {/* Only show progress UI if not a fatal error (i.e., we have some data or connection) */}
      {!isFatalError && (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          <ErrorBoundary
            fallback={(props) => <AnalysisErrorFallback {...props} section="Progress" />}
            name="ProgressColumn"
          >
            <ProgressColumn
              overallProgress={overallProgress}
              steps={steps}
              hasFailedStages={hasFailedStages}
              failedStagesCount={failedStagesCount}
              analysisMetadata={analysisMetadata}
            />
          </ErrorBoundary>
          {/* Show completion card only when artifact is ready (isComplete = true), regardless of failures */}
          {/* The card itself will show appropriate message based on hasFailedStages */}
          <ErrorBoundary
            fallback={(props) => <AnalysisErrorFallback {...props} section="Activity" />}
            name="ActivityColumn"
          >
            {/* Issue #396: AnalysisCompleteCard gets data from Zustand store */}
            {isComplete && (resolvedArtifactId || artifactId) ? (
              <div
                ref={completionRef}
                tabIndex={-1}
                aria-label={hasFailedStages ? 'Analysis complete with errors' : 'Analysis complete'}
                className="outline-none"
              >
                <AnalysisCompleteCard variant="column" />
              </div>
            ) : (
              <ActivityColumn activities={activities} isLive={isConnected} />
            )}
          </ErrorBoundary>
        </div>
      )}
    </div>
  )
}
