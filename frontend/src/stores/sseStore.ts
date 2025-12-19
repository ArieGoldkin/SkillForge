import type { SSEEvent } from '@app-types/sse'
import { create } from 'zustand'

import { closeConnection, createConnection, MAX_EVENTS, type ListenerRefs } from './sseStoreHelpers'

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

  // Internal state - connection management (moved from module-level to prevent memory leaks)
  _eventSource: EventSource | null
  _reconnectAttempts: number
  _reconnectTimeoutId: ReturnType<typeof setTimeout> | null
  _permanentlyFailed: boolean
  _listenerRefs: ListenerRefs | null
}

export interface SSEStoreActions {
  connect: (analysisId: string) => void
  disconnect: () => void
  reset: () => void
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
export const useSSEStore = create<SSEStore>((set, get) => ({
  // Public state
  events: [],
  latestEvent: null,
  error: null,
  isConnected: false,
  isComplete: false,
  activeAnalysisId: null,

  // Internal state (previously module-level - now properly managed)
  _eventSource: null,
  _reconnectAttempts: 0,
  _reconnectTimeoutId: null,
  _permanentlyFailed: false,
  _listenerRefs: null,

  connect: (analysisId: string) => {
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
      // Internal state - ensure clean slate
      _eventSource: null,
      _reconnectAttempts: 0,
      _reconnectTimeoutId: null,
      _permanentlyFailed: false,
      _listenerRefs: null,
    })
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
