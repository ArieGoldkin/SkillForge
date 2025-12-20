/* eslint-disable max-lines -- Component handles complex state management, error handling, SSE lifecycle, and multiple view states which require extensive logic */
import { useCallback, useEffect, useMemo, useRef, useState } from 'react'

import {
  useSSEStore,
  useLoadingState,
  useShowTimeoutWarning,
  useShouldShowProgress,
} from '@stores/sseStore'
import { getRouteApi } from '@tanstack/react-router'

import { AnalysisRenderRouter } from './components/render-router/AnalysisRenderRouter'
import { checkIsTrulyComplete } from './helpers/completionCheck'
import { useCompletionFocus } from './helpers/completionFocus'
import { useSSELifecycle } from './helpers/sseLifecycle'
import {
  selectEvents,
  selectConnectionState,
  selectAnalysisState,
} from './helpers/sseSelectors'
import { useAnalysisProgress } from './hooks/useAnalysisProgress'
import { useAnalysisStatus } from './hooks/useAnalysisStatus'

const routeApi = getRouteApi('/analyze/$id')

/**
 * Main analysis result component
 * Orchestrates SSE connection, status polling, and view state management
 * Delegates rendering to specialized view components
 */
// eslint-disable-next-line max-lines-per-function -- Component orchestrates SSE lifecycle, status polling, and view routing which requires extensive setup and state management. Rendering logic is extracted to separate components.
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
  const handleTimeoutWarningDismiss = useCallback(() => setTimeoutWarningDismissed(true), [])

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

  // 🎯 DECLARATIVE RENDER ROUTER - Replaces 100+ lines of complex conditionals
  // All routing logic is now handled by the AnalysisRenderRouter component

  const isFatalError = Boolean(
    (error || statusState.statusError || isFailed) && events.length === 0 && !isConnected
  )

  // Collect all props needed by any route
  const allProps = {
    // Route parameters
    id,
    completed,
    urlArtifactId,

    // Computed states
    isResolvedComplete,
    resolvedArtifactId,
    isFatalError,
    effectiveError,

    // Loading states
    loadingState,
    showTimeoutWarning,
    timeoutWarningDismissed,
    shouldShowProgress,
    handleTimeoutWarningDismiss,

    // Progress and metadata
    overallProgress,
    steps,
    activities,
    hasFailedStages,
    failedStagesCount,
    analysisMetadata,

    // Error states
    error,
    hasError,
    statusError: statusState.statusError,
    isFailed,

    // Connection state
    isConnected,
    isComplete,

    // Accessibility refs
    completionRef,
  }

  return <AnalysisRenderRouter {...allProps} />
}
