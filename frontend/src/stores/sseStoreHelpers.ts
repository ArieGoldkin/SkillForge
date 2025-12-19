/**
 * SSE Store Helper Functions
 *
 * Connection management and event handling utilities.
 * All state now managed through Zustand store (no module-level variables).
 *
 * Memory Safety:
 * - No module-level state that could leak between analyses
 * - Events array capped at MAX_EVENTS
 * - Proper listener cleanup on disconnect
 */

import { isCompleteEvent, isErrorEvent } from '@app-types/sse'

import { parseSSEEvent } from '@/schemas/sse'

// Configuration constants
const MAX_RECONNECT_ATTEMPTS = 3
const INITIAL_RECONNECT_DELAY = 1000 // 1s
const MAX_RECONNECT_DELAY = 4000 // 4s

/** Maximum events to keep in memory (prevents unbounded growth) */
export const MAX_EVENTS = 500

/**
 * Listener references for proper cleanup
 * Storing references allows removeEventListener to work correctly
 */
export interface ListenerRefs {
  progress: (event: MessageEvent) => void
  complete: (event: MessageEvent) => void
  error: (event: MessageEvent) => void
  connectionError: (event: Event) => void
}

type StoreAPI = {
  getState: () => SSEStore
  setState: (
    partial: Partial<SSEStoreState> | ((state: SSEStoreState) => Partial<SSEStoreState>)
  ) => void
}

/**
 * Calculate exponential backoff delay
 */
function getReconnectDelay(attempts: number): number {
  return Math.min(INITIAL_RECONNECT_DELAY * 2 ** attempts, MAX_RECONNECT_DELAY)
}

/**
 * Handle connection open event
 */
function handleOpen(store: StoreAPI): () => void {
  return () => {
    store.setState({
      _reconnectAttempts: 0,
      isConnected: true,
      error: null,
    })
  }
}

/**
 * Handle progress event
 */
function handleProgressEvent(store: StoreAPI): (event: MessageEvent) => void {
  return (event: MessageEvent) => {
    try {
      const rawData = JSON.parse(event.data)
      const validatedData = parseSSEEvent(rawData)

      if (!validatedData) {
        console.error('[SSE] Progress event validation failed')
        store.setState({
          error: new Error('Received invalid progress event from server'),
        })
        return
      }

      // Use _addEvent for memory-safe event storage
      store.getState()._addEvent(validatedData)
    } catch (error) {
      console.error('[SSE] Failed to parse progress event:', error)
      store.setState({
        error: error instanceof Error ? error : new Error('Failed to parse progress event'),
      })
    }
  }
}

/**
 * Handle complete event
 */
function handleCompleteEvent(store: StoreAPI): (event: MessageEvent) => void {
  return (event: MessageEvent) => {
    try {
      const rawData = JSON.parse(event.data)
      const validatedData = parseSSEEvent(rawData)

      if (!validatedData) {
        console.error('[SSE] Complete event validation failed')
        store.setState({
          error: new Error('Received invalid complete event from server'),
        })
        return
      }

      // Use _addEvent for memory-safe event storage
      store.getState()._addEvent(validatedData)
      store.setState({ isComplete: true })

      if (isCompleteEvent(validatedData)) {
        store.getState().disconnect()
      }
    } catch (error) {
      console.error('[SSE] Failed to parse complete event:', error)
      store.setState({
        error: error instanceof Error ? error : new Error('Failed to parse complete event'),
      })
    }
  }
}

/**
 * Handle server error event
 * Note: This handles server-sent 'error' events, not connection errors (handled by onerror)
 */
function handleErrorEvent(store: StoreAPI): (event: MessageEvent) => void {
  return (event: MessageEvent) => {
    // Guard: connection errors may fire this with undefined data
    if (!event.data) {
      console.warn('[SSE] Received error event with no data (connection error)')
      return
    }

    try {
      const rawData = JSON.parse(event.data)
      const validatedData = parseSSEEvent(rawData)

      if (!validatedData) {
        console.error('[SSE] Error event validation failed')
        store.setState({
          error: new Error('Received invalid error event from server'),
        })
        return
      }

      console.error('[SSE] Server error event:', validatedData)

      // Use _addEvent for memory-safe event storage
      store.getState()._addEvent(validatedData)
      store.setState({
        error: new Error(
          isErrorEvent(validatedData)
            ? (validatedData.error ?? validatedData.details?.error ?? 'Analysis failed')
            : 'Analysis failed'
        ),
      })

      if (isErrorEvent(validatedData)) {
        store.getState().disconnect()
      }
    } catch (error) {
      console.error('[SSE] Failed to parse error event:', error)
    }
  }
}

/**
 * Handle connection error with reconnection logic
 */
function handleConnectionError(analysisId: string, store: StoreAPI): (error: Event) => void {
  return (error: Event) => {
    console.error('[SSE] Connection error:', error)

    const state = store.getState()
    const attempts = state._reconnectAttempts

    store.setState({
      isConnected: false,
      error: new Error('SSE connection failed'),
    })

    if (attempts < MAX_RECONNECT_ATTEMPTS) {
      const delay = getReconnectDelay(attempts)
      const newAttempts = attempts + 1

      console.warn(
        `[SSE] Reconnecting in ${delay}ms (attempt ${newAttempts}/${MAX_RECONNECT_ATTEMPTS})`
      )

      const timeoutId = setTimeout(() => {
        store.getState().connect(analysisId)
      }, delay)

      store.setState({
        _reconnectAttempts: newAttempts,
        _reconnectTimeoutId: timeoutId,
      })
    } else {
      console.error('[SSE] Max reconnection attempts reached - giving up')
      store.setState({
        _permanentlyFailed: true,
        error: new Error('Connection failed after multiple attempts. Please refresh to retry.'),
      })
      store.getState().disconnect()
    }
  }
}

/**
 * Setup event listeners for SSE connection
 * Returns listener references for proper cleanup
 */
function setupEventListeners(
  source: EventSource,
  analysisId: string,
  store: StoreAPI
): ListenerRefs {
  const refs: ListenerRefs = {
    progress: handleProgressEvent(store),
    complete: handleCompleteEvent(store),
    error: handleErrorEvent(store),
    connectionError: handleConnectionError(analysisId, store),
  }

  source.onopen = handleOpen(store)
  source.addEventListener('progress', refs.progress)
  source.addEventListener('complete', refs.complete)
  source.addEventListener('error', refs.error)
  source.onerror = refs.connectionError

  return refs
}

/**
 * Remove event listeners from SSE connection
 * Critical for preventing memory leaks from closure references
 */
function cleanupEventListeners(source: EventSource, refs: ListenerRefs): void {
  source.removeEventListener('progress', refs.progress)
  source.removeEventListener('complete', refs.complete)
  source.removeEventListener('error', refs.error)
  source.onopen = null
  source.onerror = null
}

/**
 * Create SSE connection
 * All state managed through Zustand store (no module-level variables)
 */
export function createConnection(analysisId: string, store: StoreAPI): void {
  const state = store.getState()

  // Prevent duplicate connections
  if (state.activeAnalysisId === analysisId && state.isConnected) {
    console.warn(`[SSE] Already connected to analysis ${analysisId}`)
    return
  }

  // Prevent reconnection after permanent failure (for same analysis)
  if (state._permanentlyFailed && state.activeAnalysisId === analysisId) {
    console.warn(`[SSE] Connection permanently failed for ${analysisId}. Refresh to retry.`)
    return
  }

  // Disconnect existing connection if different analysis
  if (state._eventSource && state.activeAnalysisId !== analysisId) {
    store.getState().disconnect()
    // Reset permanent failure flag for new analysis
    store.setState({ _permanentlyFailed: false })
  }

  // Clear any pending reconnect
  if (state._reconnectTimeoutId) {
    clearTimeout(state._reconnectTimeoutId)
    store.setState({ _reconnectTimeoutId: null })
  }

  try {
    const apiUrl = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8500'
    const url = `${apiUrl}/api/v1/analyze/${analysisId}/stream`

    const eventSource = new EventSource(url)
    const listenerRefs = setupEventListeners(eventSource, analysisId, store)

    store.setState({
      _eventSource: eventSource,
      _listenerRefs: listenerRefs,
      activeAnalysisId: analysisId,
      error: null,
    })
  } catch (error) {
    console.error('[SSE] Failed to create connection:', error)
    store.setState({
      error: error instanceof Error ? error : new Error('Failed to create SSE connection'),
      isConnected: false,
    })
  }
}

/**
 * Close SSE connection with proper cleanup
 * Removes all event listeners and clears internal state
 */
export function closeConnection(store: StoreAPI): void {
  const state = store.getState()

  // Clear any pending reconnect timeout
  if (state._reconnectTimeoutId) {
    clearTimeout(state._reconnectTimeoutId)
  }

  // Remove listeners before closing (prevents memory leaks from closures)
  if (state._eventSource && state._listenerRefs) {
    cleanupEventListeners(state._eventSource, state._listenerRefs)
  }

  // Close the EventSource connection
  if (state._eventSource) {
    state._eventSource.close()
  }

  // Reset all internal connection state
  // Note: _permanentlyFailed is reset here to allow reconnection after disconnect
  store.setState({
    _eventSource: null,
    _listenerRefs: null,
    _reconnectAttempts: 0,
    _reconnectTimeoutId: null,
    _permanentlyFailed: false, // CRITICAL: Reset to allow future connections
    isConnected: false,
    activeAnalysisId: null,
  })
}
