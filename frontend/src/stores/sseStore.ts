import type { SSEEvent } from '@app-types/sse'
import { create } from 'zustand'
import { useShallow } from 'zustand/react/shallow'

import {
  deriveLoadingState,
  getConnectionMessage,
  shouldShowTimeoutWarning,
  getAnalysisPhase,
  shouldShowProgress,
} from './computed/loadingStates'
import { closeConnection, createConnection, MAX_EVENTS, type ListenerRefs } from './sseStoreHelpers'

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
  // Internal actions - used by helpers
  _addEvent: (event: SSEEvent) => void
  _setInternalState: (partial: Partial<SSEStoreState>) => void
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

  connect: (analysisId: string) => {
    // Track connection start time for timeout warnings (Issue #399)
    set({ connectionStartTime: Date.now() })
    createConnection(analysisId, { getState: get, setState: set })
  },

  disconnect: () => {
    closeConnection({ getState: get, setState: set })
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
   * Add event with size limit to prevent memory leaks
   * Keeps only the last MAX_EVENTS events
   */
  _addEvent: (event: SSEEvent) => {
    set((state) => {
      const newEvents = [...state.events, event]
      // Memory safety: cap events array size
      const cappedEvents = newEvents.length > MAX_EVENTS ? newEvents.slice(-MAX_EVENTS) : newEvents
      return {
        events: cappedEvents,
        latestEvent: event,
        // Track activity for timeout logic (Issue #399)
        lastActivityTime: Date.now(),
      }
    })
  },

  /**
   * Set internal state - used by helpers for connection management
   */
  _setInternalState: (partial: Partial<SSEStoreState>) => {
    set(partial)
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

// Computed Loading State Hooks (Issue #399 - Missing Loading States)

/**
 * Hook to get the current loading state
 * Recomputes only when relevant state changes
 */
export const useLoadingState = () => useSSEStore(deriveLoadingState)

/**
 * Hook to get the connection message
 * Recomputes only when relevant state changes
 */
export const useConnectionMessage = () => useSSEStore(getConnectionMessage)

/**
 * Hook to get timeout warning state
 * Recomputes only when relevant state changes
 */
export const useShowTimeoutWarning = () => useSSEStore(shouldShowTimeoutWarning)

/**
 * Hook to get current analysis phase
 * Recomputes only when relevant state changes
 */
export const useAnalysisPhase = () => useSSEStore(getAnalysisPhase)

/**
 * Hook to get progress visibility
 * Recomputes only when relevant state changes
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
