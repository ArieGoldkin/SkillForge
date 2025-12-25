/* eslint-disable max-lines -- SSE Store orchestrates complex state management: event lifecycle, connection management, memory monitoring, and store actions. File length reflects necessary complexity for robust SSE handling. */

import { create } from 'zustand'
import { useShallow } from 'zustand/react/shallow'

import { LIMIT_CONSTANTS } from '@/lib/constants'
import { logger } from '@/lib/logger'
import type { SSEEvent } from '@/schemas/sse'

import {
  deriveLoadingState,
  getConnectionMessage,
  shouldShowTimeoutWarning,
  getAnalysisPhase,
  shouldShowProgress,
} from './computed/loadingStates'
import {
  closeConnection,
  createConnection,
  MAX_EVENTS,
  type ListenerRefs,
  cleanupOldEvents,
  getEventMemoryStats,
  deduplicateEvents,
} from './sseStoreHelpers'

/**
 * Convert API progress events to SSE format
 * Extracted to reduce complexity in startPolling
 */
function convertProgressToSSE(progressData: {
  analysis_id: string
  events: Array<{
    stage: string
    status: string
    timestamp: string
    progress_data: unknown
  }>
}): SSEEvent[] {
  return progressData.events.map((event) => {
    const progressDataObj =
      event.progress_data && typeof event.progress_data === 'object' ? event.progress_data : null

    return {
      type: 'progress' as const,
      analysis_id: progressData.analysis_id,
      stage: event.stage,
      status: event.status,
      timestamp: event.timestamp,
      details: progressDataObj || undefined,
      ...(progressDataObj &&
        'analysis_metadata' in progressDataObj && {
          analysis_metadata: progressDataObj.analysis_metadata,
        }),
      ...(progressDataObj &&
        'artifact_id' in progressDataObj && {
          artifact_id: progressDataObj.artifact_id as string,
        }),
      ...(progressDataObj &&
        'trace_id' in progressDataObj && {
          trace_id: progressDataObj.trace_id as string,
        }),
    } as SSEEvent
  })
}

// Analysis Metadata Types (Issue #396 - Eliminate Prop Drilling)

/**
 * Analysis stage type representing the current processing state
 */
export type AnalysisStage = 'extracting' | 'processing' | 'analyzing' | 'generating' | 'complete'

/**
 * Granular connection states for detailed loading status (Issue #399)
 */
export type ConnectionState =
  | 'connecting'
  | 'connected'
  | 'reconnecting'
  | 'polling'
  | 'disconnected'
  | 'timeout_warning'

/**
 * Overall progress state for UI display
 */
export interface OverallProgress {
  stage: AnalysisStage
  progress: number
  currentStep: string
  totalSteps: number
  completedSteps: number
  estimatedTimeRemaining?: string
}

/**
 * Analysis metadata extracted from SSE events
 */
export interface AnalysisMetadata {
  title?: string
  contentType?: 'article' | 'video' | 'repo'
  url?: string
  wordCount?: number
}

/**
 * SSE Store State Interface
 *
 * Public state is exposed to components.
 * Internal state (prefixed with _) manages connection lifecycle.
 */
export interface SSEStoreState {
  // Public state - consumed by components
  events: SSEEvent[]
  latestEvent: SSEEvent | null
  error: Error | null
  isConnected: boolean
  isComplete: boolean
  activeAnalysisId: string | null

  // Granular connection state (Issue #399 - Missing Loading States)
  connectionState: ConnectionState
  connectionStartTime: number | null // timestamp when connection started
  lastActivityTime: number | null // timestamp of last event/activity

  // Analysis metadata (Issue #396 - Eliminates prop drilling)
  // These are derived from SSE events in useAnalysisProgress and synced here
  // for direct access by leaf components (GuideButton, TeachMeButton, etc.)
  artifactId: string | null
  traceId: string | null
  overallProgress: OverallProgress | null
  hasFailedStages: boolean
  failedStagesCount: number
  analysisMetadata: AnalysisMetadata | null

  // Internal state - connection management (moved from module-level to prevent memory leaks)
  _eventSource: EventSource | null
  _reconnectAttempts: number
  _reconnectTimeoutId: ReturnType<typeof setTimeout> | null
  _permanentlyFailed: boolean
  _listenerRefs: ListenerRefs | null
  _cleanupNetworkRecovery: (() => void) | null
  // Polling fallback state
  isPolling: boolean
  _pollingIntervalId: ReturnType<typeof setInterval> | null
  // Telemetry - track validation failures (Issue #489)
  _validationFailures: number
}

export interface SSEStoreActions {
  connect: (analysisId: string) => void
  disconnect: () => void
  reset: () => void
  // Analysis metadata sync (Issue #396)
  setAnalysisMetadata: (meta: {
    artifactId?: string | null
    traceId?: string | null
    overallProgress?: OverallProgress | null
    hasFailedStages?: boolean
    failedStagesCount?: number
    analysisMetadata?: AnalysisMetadata | null
  }) => void
  // REST API reconciliation actions (Issue #489)
  clearError: () => void
  setComplete: (value: boolean) => void
  reconcileComplete: () => void // Atomic: clears error AND sets complete in single update
  // Internal actions - used by helpers
  _addEvent: (event: SSEEvent) => void
  _setInternalState: (partial: Partial<SSEStoreState>) => void
  // Polling actions
  startPolling: (analysisId: string) => void
  stopPolling: () => void
}

export type SSEStore = SSEStoreState & SSEStoreActions

/**
 * SSE Store
 *
 * Manages Server-Sent Events connection for analysis workflow progress.
 *
 * Features:
 * - Single global connection per analysis
 * - Auto-reconnect with exponential backoff (1s → 2s → 4s, max 3 attempts)
 * - Auto-close on complete event
 * - Prevents duplicate connections
 * - Memory-safe: Events capped at MAX_EVENTS, all state in store (no module-level leaks)
 *
 * Memory Management:
 * - Events array limited to MAX_EVENTS (prevents unbounded growth)
 * - All connection state in Zustand (cleaned up on disconnect/reset)
 * - Listener references stored for proper cleanup
 */
// eslint-disable-next-line max-lines-per-function -- Zustand store requires all state/actions in single create()
const baseStore = create<SSEStore>((set, get) => ({
  // Public state
  events: [],
  latestEvent: null,
  error: null,
  isConnected: false,
  isComplete: false,
  activeAnalysisId: null,

  // Granular connection state (Issue #399 - Missing Loading States)
  connectionState: 'disconnected' as ConnectionState,
  connectionStartTime: null,
  lastActivityTime: null,

  // Analysis metadata (Issue #396 - synced from useAnalysisProgress)
  artifactId: null,
  traceId: null,
  overallProgress: null,
  hasFailedStages: false,
  failedStagesCount: 0,
  analysisMetadata: null,

  // Internal state (previously module-level - now properly managed)
  _eventSource: null,
  _reconnectAttempts: 0,
  _reconnectTimeoutId: null,
  _permanentlyFailed: false,
  _listenerRefs: null,
  _cleanupNetworkRecovery: null,
  // Polling fallback state
  isPolling: false,
  _pollingIntervalId: null,
  // Telemetry (Issue #489)
  _validationFailures: 0,

  connect: (analysisId: string) => {
    // Track connection start time for timeout warnings (Issue #399)
    set({ connectionStartTime: Date.now() })
    createConnection(analysisId, { getState: get, setState: set })
  },

  disconnect: () => {
    // Stop polling before closing connection
    get().stopPolling()
    closeConnection({ getState: get, setState: set })

    // Keep events for UI display after disconnect - only reset() clears events
    // This allows users to see final analysis state even after connection closes
    set((_state) => ({
      // Keep events and latestEvent for UI display
      // Clear connection-specific state but preserve analysis results
      isConnected: false,
      connectionState: 'disconnected' as ConnectionState,
      lastActivityTime: null,
      // Clear internal connection tracking but preserve analysis metadata
      _eventSource: null,
      _listenerRefs: null,
      _reconnectAttempts: 0,
      _reconnectTimeoutId: null,
      _permanentlyFailed: false,
      _cleanupNetworkRecovery: undefined,
      // Stop polling on disconnect
      isPolling: false,
      _pollingIntervalId: null,
    }))
  },

  reset: () => {
    get().disconnect()
    set({
      // Public state
      events: [],
      latestEvent: null,
      error: null,
      isConnected: false,
      isComplete: false,
      activeAnalysisId: null,
      // Analysis metadata - clear on reset
      artifactId: null,
      traceId: null,
      overallProgress: null,
      hasFailedStages: false,
      failedStagesCount: 0,
      analysisMetadata: null,
      // Connection lifecycle tracking - clear on reset (Issue #399)
      connectionState: 'disconnected' as ConnectionState,
      connectionStartTime: null,
      lastActivityTime: null,
      // Internal state - ensure clean slate
      _eventSource: null,
      _reconnectAttempts: 0,
      _reconnectTimeoutId: null,
      _permanentlyFailed: false,
      _listenerRefs: null,
      _cleanupNetworkRecovery: null,
      // Clear polling state on reset
      isPolling: false,
      _pollingIntervalId: null,
      // Clear telemetry (Issue #489)
      _validationFailures: 0,
    })
  },

  /**
   * Update analysis metadata (Issue #396)
   * Called from useAnalysisProgress to sync derived data for global access
   */
  setAnalysisMetadata: (meta) => {
    set((state) => ({
      artifactId: meta.artifactId !== undefined ? meta.artifactId : state.artifactId,
      traceId: meta.traceId !== undefined ? meta.traceId : state.traceId,
      overallProgress:
        meta.overallProgress !== undefined ? meta.overallProgress : state.overallProgress,
      hasFailedStages:
        meta.hasFailedStages !== undefined ? meta.hasFailedStages : state.hasFailedStages,
      failedStagesCount:
        meta.failedStagesCount !== undefined ? meta.failedStagesCount : state.failedStagesCount,
      analysisMetadata:
        meta.analysisMetadata !== undefined ? meta.analysisMetadata : state.analysisMetadata,
    }))
  },

  /**
   * Clear error state (Issue #489 - REST API reconciliation)
   * Called when REST API confirms success but SSE showed error
   */
  clearError: () => {
    set({ error: null })
  },

  /**
   * Set completion state (Issue #489 - REST API reconciliation)
   * Called when REST API confirms completion
   */
  setComplete: (value: boolean) => {
    set({ isComplete: value })
  },

  /**
   * Atomic reconciliation action (Issue #489 - Race condition fix)
   * Clears error AND sets complete in a single store update to prevent
   * intermediate state where error is cleared but isComplete is still false.
   * This is critical because components subscribed to the store would otherwise
   * see an inconsistent state between two separate set() calls.
   */
  reconcileComplete: () => {
    set({ error: null, isComplete: true })
  },

  /**
   * Add event with size limit to prevent memory leaks
   * Keeps only the last MAX_EVENTS events
   */
  _addEvent: (event: SSEEvent) => {
    set((state) => {
      let newEvents = [...state.events]

      // Deduplicate events before adding new one
      newEvents = deduplicateEvents([...newEvents, event])

      // Apply retention policies and cleanup old events
      newEvents = cleanupOldEvents(newEvents)

      // Emergency cleanup if still over limit
      if (newEvents.length > MAX_EVENTS) {
        // Keep most recent events, prioritizing critical ones
        const criticalEvents = newEvents.filter((e) => e.type === 'error' || e.type === 'complete')
        const otherEvents = newEvents.filter((e) => e.type !== 'error' && e.type !== 'complete')
        newEvents = [...criticalEvents, ...otherEvents.slice(-(MAX_EVENTS - criticalEvents.length))]
      }

      // Get memory stats for monitoring
      const memoryStats = getEventMemoryStats(newEvents)

      // Log alerts if any
      memoryStats.alerts.forEach((alert) => {
        console.warn(`[SSE Memory] ${alert}`, {
          totalEvents: memoryStats.total,
          memoryUsage: `${(memoryStats.memoryUsage * 100).toFixed(1)}%`,
          byType: memoryStats.byType,
        })
      })

      return {
        events: newEvents,
        latestEvent: event,
        // Track activity for timeout logic (Issue #399)
        lastActivityTime: Date.now(),
        // Store memory stats for debugging/monitoring
        _memoryStats: memoryStats,
      }
    })
  },

  /**
   * Set internal state - used by helpers for connection management
   */
  _setInternalState: (partial: Partial<SSEStoreState>) => {
    set(partial)
  },

  /**
   * Start polling fallback when SSE connection fails
   */
  startPolling: (analysisId: string) => {
    const state = get()
    // Don't start polling if already polling or if SSE is connected
    if (state.isPolling || state.isConnected) {
      return
    }

    // Stop any existing polling
    if (state._pollingIntervalId) {
      clearInterval(state._pollingIntervalId)
    }

    logger.info('Starting polling fallback', {
      analysisId,
      reason: 'sse_connection_failed',
      pollingInterval: LIMIT_CONSTANTS.SSE_POLLING_INTERVAL,
    })

    // Import analyzeAPI dynamically to avoid circular dependencies
    import('@services/api.service').then(({ analyzeAPI }) => {
      const pollProgress = async () => {
        try {
          const progressData = await analyzeAPI.getAnalysisProgress(analysisId)
          // Convert and add events
          const sseEvents = convertProgressToSSE(progressData)
          sseEvents.forEach((event) => {
            get()._addEvent(event)
          })

          // Check if analysis is complete
          const statusData = await analyzeAPI.getAnalysisStatus(analysisId)
          if (
            statusData.status === 'complete' ||
            statusData.status === 'completed' ||
            statusData.status === 'failed'
          ) {
            get().stopPolling()
            set({ isComplete: true })
          }
        } catch (error) {
          logger.error('Polling failed', {
            analysisId,
            error: error instanceof Error ? error.message : String(error),
          })
        }
      }

      // Poll immediately, then at intervals
      void pollProgress()
      const intervalId = setInterval(pollProgress, LIMIT_CONSTANTS.SSE_POLLING_INTERVAL)

      set({
        isPolling: true,
        _pollingIntervalId: intervalId,
        connectionState: 'polling' as ConnectionState,
      })
    })
  },

  /**
   * Stop polling fallback
   */
  stopPolling: () => {
    const state = get()
    if (state._pollingIntervalId) {
      clearInterval(state._pollingIntervalId)
      logger.info('Stopped polling fallback', {
        analysisId: state.activeAnalysisId,
      })
    }
    set({
      isPolling: false,
      _pollingIntervalId: null,
    })
  },
}))

// Export the base store with computed properties added via selectors
export const useSSEStore = baseStore

// Selectors (Issue #396 - Granular subscriptions to prevent unnecessary re-renders)
// Module-level selectors for stable references - use these instead of inline selectors

/** Select artifact ID for navigation to artifact page */
export const selectArtifactId = (state: SSEStore) => state.artifactId
/** Select trace ID for Langfuse feedback submission */
export const selectTraceId = (state: SSEStore) => state.traceId

/** Select active analysis ID (for tutoring, etc.) */
export const selectAnalysisId = (state: SSEStore) => state.activeAnalysisId

/** Select overall progress for progress display */
export const selectOverallProgress = (state: SSEStore) => state.overallProgress

/** Select failure state for error display */
export const selectHasFailedStages = (state: SSEStore) => state.hasFailedStages

/** Select failure count for error summary */
export const selectFailedStagesCount = (state: SSEStore) => state.failedStagesCount

/** Select analysis metadata (title, contentType, url, wordCount) */
export const selectAnalysisMetadata = (state: SSEStore) => state.analysisMetadata

/** Select setAnalysisMetadata action */
export const selectSetAnalysisMetadata = (state: SSEStore) => state.setAnalysisMetadata

/** Select error state (Issue #489 - REST API reconciliation) */
export const selectError = (state: SSEStore) => state.error

/** Select clearError action (Issue #489 - REST API reconciliation) */
export const selectClearError = (state: SSEStore) => state.clearError

/** Select setComplete action (Issue #489 - REST API reconciliation) */
export const selectSetComplete = (state: SSEStore) => state.setComplete

/** Select reconcileComplete action (Issue #489 - Atomic error+complete update) */
export const selectReconcileComplete = (state: SSEStore) => state.reconcileComplete

/** Select validation failures count (Issue #489 - for telemetry) */
export const selectValidationFailures = (state: SSEStore) => state._validationFailures

// Computed Loading State Hooks (Issue #399 - Missing Loading States)
// IMPORTANT: Hooks that return objects MUST use useShallow to prevent infinite re-renders
// See issue #438 for details on the "getSnapshot should be cached" error

/**
 * Hook to get the current loading state
 * Uses useShallow because deriveLoadingState returns discriminated union objects
 */
export const useLoadingState = () => useSSEStore(useShallow(deriveLoadingState))

/**
 * Hook to get the connection message
 * Returns primitive string - no shallow comparison needed
 */
export const useConnectionMessage = () => useSSEStore(getConnectionMessage)

/**
 * Hook to get timeout warning state
 * Returns primitive boolean - no shallow comparison needed
 */
export const useShowTimeoutWarning = () => useSSEStore(shouldShowTimeoutWarning)

/**
 * Hook to get current analysis phase
 * Returns primitive string|null - no shallow comparison needed
 */
export const useAnalysisPhase = () => useSSEStore(getAnalysisPhase)

/**
 * Hook to get progress visibility
 * Returns primitive boolean - no shallow comparison needed
 */
export const useShouldShowProgress = () => useSSEStore(shouldShowProgress)

// Composite Selectors (use useShallow for object/array selections)

/**
 * Hook to get all artifact-related IDs in one call with shallow comparison
 * Use this when you need multiple IDs and want to minimize re-renders
 *
 * @example
 * const { artifactId, analysisId, traceId } = useAnalysisIds()
 */
export const useAnalysisIds = () =>
  useSSEStore(
    useShallow((state) => ({
      artifactId: state.artifactId,
      analysisId: state.activeAnalysisId,
      traceId: state.traceId,
    }))
  )

/**
 * Hook to get progress-related state with shallow comparison
 *
 * @example
 * const { overallProgress, hasFailedStages, failedStagesCount } = useProgressState()
 */
export const useProgressState = () =>
  useSSEStore(
    useShallow((state) => ({
      overallProgress: state.overallProgress,
      hasFailedStages: state.hasFailedStages,
      failedStagesCount: state.failedStagesCount,
    }))
  )
