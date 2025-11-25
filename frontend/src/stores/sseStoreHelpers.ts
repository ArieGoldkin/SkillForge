/**
 * SSE Store Helper Functions
 * Connection management and event handling utilities
 */

import type { SSEEvent } from '@/types/sse'
import { isCompleteEvent, isErrorEvent } from '@/types/sse'

// Connection management (shared state)
let eventSource: EventSource | null = null
let reconnectAttempts = 0
let reconnectTimeoutId: ReturnType<typeof setTimeout> | null = null

const MAX_RECONNECT_ATTEMPTS = 3
const INITIAL_RECONNECT_DELAY = 1000 // 1s
const MAX_RECONNECT_DELAY = 4000 // 4s

export interface SSEStore {
  events: SSEEvent[]
  latestEvent: SSEEvent | null
  error: Error | null
  isConnected: boolean
  isComplete: boolean
  activeAnalysisId: string | null
  connect: (analysisId: string) => void
  disconnect: () => void
  reset: () => void
}

type StoreAPI = {
  getState: () => SSEStore
  setState: (partial: Partial<SSEStore> | ((state: SSEStore) => Partial<SSEStore>)) => void
}

/**
 * Calculate exponential backoff delay
 */
function getReconnectDelay(): number {
  return Math.min(INITIAL_RECONNECT_DELAY * 2 ** reconnectAttempts, MAX_RECONNECT_DELAY)
}

/**
 * Handle connection open event
 */
function handleOpen(store: StoreAPI): () => void {
  return () => {
    reconnectAttempts = 0
    store.setState({ isConnected: true, error: null })
  }
}

/**
 * Handle progress event
 */
function handleProgressEvent(store: StoreAPI): (event: MessageEvent) => void {
  return (event: MessageEvent) => {
    try {
      const data: SSEEvent = JSON.parse(event.data)
      store.setState((state) => ({
        events: [...state.events, data],
        latestEvent: data,
      }))
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
      const data: SSEEvent = JSON.parse(event.data)
      store.setState((state) => ({
        events: [...state.events, data],
        latestEvent: data,
        isComplete: true,
      }))

      if (isCompleteEvent(data)) {
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
 */
function handleErrorEvent(store: StoreAPI): (event: MessageEvent) => void {
  return (event: MessageEvent) => {
    try {
      const data: SSEEvent = JSON.parse(event.data)
      console.error('[SSE] Server error event:', data)

      store.setState((state) => ({
        events: [...state.events, data],
        latestEvent: data,
        error: new Error(isErrorEvent(data) ? data.details.error : 'Analysis failed'),
      }))

      if (isErrorEvent(data)) {
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

    store.setState({
      isConnected: false,
      error: new Error('SSE connection failed'),
    })

    if (reconnectAttempts < MAX_RECONNECT_ATTEMPTS) {
      const delay = getReconnectDelay()
      reconnectAttempts++

      console.warn(
        `[SSE] Reconnecting in ${delay}ms (attempt ${reconnectAttempts}/${MAX_RECONNECT_ATTEMPTS})`
      )

      reconnectTimeoutId = setTimeout(() => {
        store.getState().connect(analysisId)
      }, delay)
    } else {
      console.error('[SSE] Max reconnection attempts reached')
      store.setState({
        error: new Error('Connection failed after multiple attempts'),
      })
      store.getState().disconnect()
    }
  }
}

/**
 * Setup event listeners for SSE connection
 */
function setupEventListeners(source: EventSource, analysisId: string, store: StoreAPI): void {
  source.onopen = handleOpen(store)
  source.addEventListener('progress', handleProgressEvent(store))
  source.addEventListener('complete', handleCompleteEvent(store))
  source.addEventListener('error', handleErrorEvent(store))
  source.onerror = handleConnectionError(analysisId, store)
}

/**
 * Create SSE connection
 */
export function createConnection(analysisId: string, store: StoreAPI): void {
  const currentState = store.getState()

  // Prevent duplicate connections
  if (currentState.activeAnalysisId === analysisId && currentState.isConnected) {
    console.warn(`[SSE] Already connected to analysis ${analysisId}`)
    return
  }

  // Disconnect existing connection if different analysis
  if (eventSource && currentState.activeAnalysisId !== analysisId) {
    store.getState().disconnect()
  }

  // Clear any pending reconnect
  if (reconnectTimeoutId) {
    clearTimeout(reconnectTimeoutId)
    reconnectTimeoutId = null
  }

  try {
    const apiUrl = import.meta.env.VITE_API_URL || 'http://localhost:8000'
    const url = `${apiUrl}/api/v1/analyze/${analysisId}/stream`

    eventSource = new EventSource(url)

    store.setState({
      activeAnalysisId: analysisId,
      error: null,
    })

    setupEventListeners(eventSource, analysisId, store)
  } catch (error) {
    console.error('[SSE] Failed to create connection:', error)
    store.setState({
      error: error instanceof Error ? error : new Error('Failed to create SSE connection'),
      isConnected: false,
    })
  }
}

/**
 * Close SSE connection
 */
export function closeConnection(store: StoreAPI): void {
  if (reconnectTimeoutId) {
    clearTimeout(reconnectTimeoutId)
    reconnectTimeoutId = null
  }

  if (eventSource) {
    eventSource.close()
    eventSource = null
  }

  reconnectAttempts = 0

  store.setState({
    isConnected: false,
    activeAnalysisId: null,
  })
}
