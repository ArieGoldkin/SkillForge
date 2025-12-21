import { useCallback, useEffect, useMemo, useRef, useState } from 'react'

import type { SSEStore } from '@stores/sseStore'
import {
  useSSEStore,
  useLoadingState,
  useShowTimeoutWarning,
  useShouldShowProgress,
  selectSetAnalysisMetadata,
} from '@stores/sseStore'
import { getRouteApi } from '@tanstack/react-router'
import { useShallow } from 'zustand/react/shallow'

import { AnalysisRenderRouter } from './components/render-router/AnalysisRenderRouter'
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

/**
 * Single Source of Truth: Artifact-based completion check (Issue #439)
 *
 * BEFORE: Triple-check pattern requiring isComplete + progressStage + progressPercent
 *         This caused desync when supervisor routed to fewer stages than expected.
 *
 * AFTER: Artifact existence is the definitive completion signal.
 *        - Artifact is ONLY created after successful workflow completion
 *        - Backend validates artifact before setting status="complete"
 *        - hasFailedStages is for UI display (error badge), not completion gate
 *
 * @param artifactId - The artifact ID from SSE complete event or URL params
 * @returns true if analysis has completed (artifact exists)
 */
const checkIsTrulyComplete = (params: { artifactId: string | null | undefined }): boolean => {
  // Single source of truth: artifact exists = analysis complete
  return Boolean(params.artifactId)
}

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

// Local component definitions moved to separate files:
// - AnalysisInProgress → render-router/CommonAnalysisLayout
// - ActivityOrCompletionColumn → ActiveAnalysisView.tsx
// - ActiveAnalysisView → ActiveAnalysisView.tsx

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
  // Using useShallow for object-returning selectors to prevent infinite re-renders
  const events = useSSEStore(selectEvents)
  const { isConnected, connect, disconnect } = useSSEStore(useShallow(selectConnectionState))
  const { isComplete, error, reset } = useSSEStore(useShallow(selectAnalysisState))
  // Issue #452: Get setAnalysisMetadata to sync API data to store for completed analyses
  const setAnalysisMetadata = useSSEStore(selectSetAnalysisMetadata)

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

  // First, get artifact ID from SSE events (for active analyses)
  // This is needed before calling useAnalysisStatus to avoid circular dependency
  const sseArtifactId = useMemo(() => {
    // Extract artifact ID from SSE events if available
    const completeEvent = events.find(
      (e) => e.type === 'complete' || (e.type === 'progress' && e.artifact_id)
    )
    return completeEvent?.artifact_id
  }, [events])

  const statusState = useAnalysisStatus({
    analysisId: id,
    completedParam: Boolean(completed),
    sseState: { eventsLength: events.length, isComplete, artifactId: sseArtifactId },
  })

  // Merge SSE events with fetched progress events for completed analyses
  // If no SSE events exist (page loaded for completed analysis), use fetched progress events
  const mergedEvents = useMemo(() => {
    if (events.length > 0) {
      // Active analysis or SSE events exist - use SSE events
      return events
    }
    // No SSE events - use fetched progress events from database
    return statusState.progressEvents
  }, [events, statusState.progressEvents])

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
  } = useAnalysisProgress(mergedEvents)

  useSSELifecycle({
    analysisId: id,
    shouldConnect: statusState.shouldConnect,
    connect,
    disconnect,
    reset,
  })

  const { resolvedArtifactId, isResolvedComplete, isFailed, effectiveError } = useMemo(() => {
    // Issue #439: Single source of truth - artifact ID determines completion
    const resolvedArtifactId = artifactId || statusState.resolvedArtifactId || urlArtifactId
    const resolvedStatus = statusState.resolvedStatus || (isComplete ? 'completed' : undefined)

    // Issue #439: Artifact-based completion check (single source of truth)
    // No longer depends on progressStage or progressPercent which could desync
    const isTrulyComplete = checkIsTrulyComplete({
      artifactId: resolvedArtifactId,
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
    // Issue #439: Simplified dependencies - no longer depends on progress stage/percent
  }, [artifactId, urlArtifactId, statusState, isComplete, hasError, error, errorMessage])

  // Issue #452: Sync artifact ID from API to store for completed analyses
  // This ensures CompleteCardContent can display the artifact when page loads
  // for already-completed analyses (no SSE events to populate the store)
  useEffect(() => {
    // Only sync if we have artifact ID from API but not from SSE events
    if (statusState.resolvedArtifactId && !artifactId) {
      setAnalysisMetadata({
        artifactId: statusState.resolvedArtifactId,
      })
    }
  }, [statusState.resolvedArtifactId, artifactId, setAnalysisMetadata])

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
