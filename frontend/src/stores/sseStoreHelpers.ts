/* eslint-disable max-lines -- SSE Helpers contain comprehensive event lifecycle management: retention policies, memory monitoring, cleanup logic, and connection management. File length reflects necessary complexity for robust SSE handling. */

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

import { LIMIT_CONSTANTS, EVENT_RETENTION_POLICIES, MEMORY_CONSTANTS } from '@/lib/constants'
import { logger } from '@/lib/logger'
import { parseSSEEvent, type SSEEvent } from '@/schemas/sse'

import type { SSEStore, SSEStoreState } from './sseStore'

// Configuration constants (imported from shared constants)
const MAX_RECONNECT_ATTEMPTS = LIMIT_CONSTANTS.SSE_RECONNECT_ATTEMPTS
const INITIAL_RECONNECT_DELAY = LIMIT_CONSTANTS.SSE_RECONNECT_DELAY_INITIAL
const MAX_RECONNECT_DELAY = LIMIT_CONSTANTS.SSE_RECONNECT_DELAY_MAX

/** Maximum events to keep in memory (prevents unbounded growth) */
export const MAX_EVENTS = LIMIT_CONSTANTS.MAX_EVENTS

// Event retention policies imported from shared constants

// Re-export for backward compatibility
export { MEMORY_CONSTANTS as MEMORY_THRESHOLDS }

/**
 * Generate a deduplication key for an SSE event
 * Used to identify duplicate events that should be merged or ignored
 */
function getEventDeduplicationKey(event: SSEEvent): string {
  const { type, analysis_id, stage, status } = event

  switch (type) {
    case 'progress':
      // Progress events are deduplicated by analysis + stage + status
      // Same stage with same status = duplicate (e.g., multiple "running" events for extraction)
      return `${analysis_id}:${stage}:${status}`

    case 'complete':
      // Complete events are deduplicated by analysis + type
      // Only one completion event per analysis
      return `${analysis_id}:${type}`

    case 'error':
      // Error events are deduplicated by analysis + stage
      // Only one error per stage (subsequent errors for same stage are ignored)
      return `${analysis_id}:${stage}:error`

    default:
      // Unknown event types are not deduplicated
      return `${analysis_id}:${type}:${stage}:${status}:${Date.now()}`
  }
}

/**
 * Check if two events are duplicates based on their content
 * For duplicate events, keep the more recent one (higher timestamp)
 */
function isDuplicateEvent(existing: SSEEvent, incoming: SSEEvent): boolean {
  if (existing.type !== incoming.type) return false
  if (existing.analysis_id !== incoming.analysis_id) return false

  switch (existing.type) {
    case 'progress':
      // Same analysis, stage, and status = duplicate
      return existing.stage === incoming.stage && existing.status === incoming.status

    case 'complete':
      // Any complete event for same analysis = duplicate
      return true

    case 'error':
      // Same analysis and stage error = duplicate
      return existing.stage === incoming.stage

    default:
      return false
  }
}

/**
 * Deduplicate SSE events, keeping the most recent version of each unique event
 * Prevents event array bloat from duplicate status updates
 */
export function deduplicateEvents(events: SSEEvent[]): SSEEvent[] {
  const eventMap = new Map<string, SSEEvent>()

  for (const event of events) {
    const key = getEventDeduplicationKey(event)
    const existing = eventMap.get(key)

    if (!existing) {
      // First occurrence of this event type
      eventMap.set(key, event)
    } else if (isDuplicateEvent(existing, event)) {
      // Duplicate - keep the more recent one based on timestamp
      const existingTime = new Date(existing.timestamp).getTime()
      const incomingTime = new Date(event.timestamp).getTime()

      if (incomingTime > existingTime) {
        eventMap.set(key, event)
      }
      // If timestamps are equal or incoming is older, keep existing
    } else {
      // Not a duplicate (different content), keep both
      eventMap.set(`${key}:${Date.now()}`, event)
    }
  }

  return Array.from(eventMap.values()).sort(
    (a, b) => new Date(a.timestamp).getTime() - new Date(b.timestamp).getTime()
  )
}

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
 * Event lifecycle management - determines if event should be retained
 */
export function shouldRetainEvent(event: SSEEvent, now: number = Date.now()): boolean {
  const eventTime =
    typeof event.timestamp === 'string' ? new Date(event.timestamp).getTime() : event.timestamp
  const eventAge = now - eventTime

  // Always keep critical events
  if (event.type === 'error' || event.type === 'complete') {
    return true
  }

  // Apply retention policies based on event type
  if (event.type === 'progress') {
    return eventAge < EVENT_RETENTION_POLICIES.progress
  }

  // Default: keep recent events (5 minutes)
  return eventAge < EVENT_RETENTION_POLICIES.activity
}

/**
 * Clean up old events based on retention policies
 */
export function cleanupOldEvents(events: SSEEvent[]): SSEEvent[] {
  const now = Date.now()
  return events.filter((event) => shouldRetainEvent(event, now))
}

/**
 * Get memory usage statistics for monitoring
 */
export function getEventMemoryStats(events: SSEEvent[]) {
  const now = Date.now()
  const totalEvents = events.length
  const memoryUsage = totalEvents / MAX_EVENTS

  // Count events by type and age
  const stats = {
    total: totalEvents,
    memoryUsage,
    byType: {
      progress: 0,
      error: 0,
      complete: 0,
      activity: 0,
    },
    byAge: {
      recent: 0, // < 1 minute
      medium: 0, // 1-5 minutes
      old: 0, // > 5 minutes
    },
    alerts: [] as string[],
  }

  events.forEach((event) => {
    const eventTime =
      typeof event.timestamp === 'string' ? new Date(event.timestamp).getTime() : event.timestamp
    const age = now - eventTime
    const ageMinutes = age / (60 * 1000)

    // Count by type
    if (event.type === 'progress') stats.byType.progress++
    else if (event.type === 'error') stats.byType.error++
    else if (event.type === 'complete') stats.byType.complete++
    else stats.byType.activity++

    // Count by age
    if (ageMinutes < 1) stats.byAge.recent++
    else if (ageMinutes < 5) stats.byAge.medium++
    else stats.byAge.old++
  })

  // Generate alerts based on thresholds
  if (memoryUsage >= MEMORY_CONSTANTS.EMERGENCY_THRESHOLD) {
    stats.alerts.push('EMERGENCY: Event buffer near capacity - forcing cleanup')
  } else if (memoryUsage >= MEMORY_CONSTANTS.CRITICAL_THRESHOLD) {
    stats.alerts.push('CRITICAL: Event buffer over 90% capacity')
  } else if (memoryUsage >= MEMORY_CONSTANTS.WARNING_THRESHOLD) {
    stats.alerts.push('WARNING: Event buffer over 70% capacity')
  }

  return stats
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
        logger.error('Progress event validation failed', {
          rawData: typeof rawData === 'string' ? rawData.substring(0, 200) : rawData,
          eventType: 'progress',
        })
        store.setState({
          error: new Error('Received invalid progress event from server'),
        })
        return
      }

      // Use _addEvent for memory-safe event storage
      store.getState()._addEvent(validatedData)
    } catch (error) {
      logger.error('Failed to parse progress event', {
        rawData: event.data?.substring(0, 200),
        error: error instanceof Error ? error.message : String(error),
        stack: error instanceof Error ? error.stack : undefined,
      })
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
        logger.error('Complete event validation failed', {
          rawData: typeof rawData === 'string' ? rawData.substring(0, 200) : rawData,
          eventType: 'complete',
        })
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
      logger.error('Failed to parse complete event', {
        rawData: event.data?.substring(0, 200),
        error: error instanceof Error ? error.message : String(error),
        stack: error instanceof Error ? error.stack : undefined,
      })
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
      logger.warn('Received error event with no data - likely connection error', {
        eventType: event.type,
        eventTarget: event.target?.toString(),
        analysisId: store.getState().activeAnalysisId,
      })
      return
    }

    try {
      const rawData = JSON.parse(event.data)
      const validatedData = parseSSEEvent(rawData)

      if (!validatedData) {
        logger.error('Error event validation failed', {
          rawData: typeof rawData === 'string' ? rawData.substring(0, 200) : rawData,
          eventType: 'error',
        })
        store.setState({
          error: new Error('Received invalid error event from server'),
        })
        return
      }

      logger.error('Server sent error event', {
        validatedData,
        analysisId: validatedData.analysis_id,
        stage: validatedData.stage,
        error: validatedData.details?.error,
      })

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
      logger.error('Failed to parse error event', {
        rawData: event.data?.substring(0, 200),
        error: error instanceof Error ? error.message : String(error),
        stack: error instanceof Error ? error.stack : undefined,
      })
    }
  }
}

/**
 * Handle connection error with reconnection logic
 */
function handleConnectionError(analysisId: string, store: StoreAPI): (error: Event) => void {
  return (error: Event) => {
    logger.error('SSE connection error occurred', {
      error: error instanceof Error ? error.message : String(error),
      analysisId: store.getState().activeAnalysisId,
      connectionState: store.getState().connectionState,
      attempts: store.getState()._reconnectAttempts,
    })

    const state = store.getState()
    const attempts = state._reconnectAttempts

    store.setState({
      isConnected: false,
      error: new Error('SSE connection failed'),
    })

    if (attempts < MAX_RECONNECT_ATTEMPTS) {
      const delay = getReconnectDelay(attempts)
      const newAttempts = attempts + 1

      logger.warn('SSE reconnection scheduled', {
        delay,
        attempt: newAttempts,
        maxAttempts: MAX_RECONNECT_ATTEMPTS,
        analysisId,
        reason: 'connection_lost',
      })

      const timeoutId = setTimeout(() => {
        store.getState().connect(analysisId)
      }, delay)

      store.setState({
        _reconnectAttempts: newAttempts,
        _reconnectTimeoutId: timeoutId,
      })
    } else {
      logger.error('SSE max reconnection attempts reached', {
        analysisId,
        maxAttempts: MAX_RECONNECT_ATTEMPTS,
        totalAttempts: attempts + 1,
        reason: 'persistent_connection_failure',
      })
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
 * Network recovery handler for SSE connections
 * Automatically clears network errors when connection is restored
 */
function setupNetworkRecovery(_analysisId: string, store: StoreAPI): () => void {
  const handleOnline = () => {
    // Only retry if we have a network-related error
    const error = store.getState().error
    if (
      error &&
      (error.message.includes('network') ||
        error.message.includes('fetch') ||
        error.message.includes('connection lost'))
    ) {
      logger.info('Network recovered, clearing error state', { service: 'sse' })
      store.setState({ error: null })
      // The UI will handle reconnection automatically
    }
  }

  const handleOffline = () => {
    store.setState({
      error: new Error('Network connection lost. Will retry when connection is restored.'),
    })
  }

  window.addEventListener('online', handleOnline)
  window.addEventListener('offline', handleOffline)

  return () => {
    window.removeEventListener('online', handleOnline)
    window.removeEventListener('offline', handleOffline)
  }
}

/**
 * Create SSE connection
 * All state managed through Zustand store (no module-level variables)
 */
export function createConnection(analysisId: string, store: StoreAPI): void {
  // eslint-disable-line max-lines-per-function
  const state = store.getState()

  // Prevent duplicate connections
  if (state.activeAnalysisId === analysisId && state.isConnected) {
    logger.warn('SSE connection attempt for already connected analysis', {
      analysisId,
      connectionState: state.connectionState,
      isConnected: state.isConnected,
    })
    return
  }

  // Prevent reconnection after permanent failure (for same analysis)
  if (state._permanentlyFailed && state.activeAnalysisId === analysisId) {
    logger.warn('SSE reconnection blocked due to permanent failure', {
      analysisId,
      permanentlyFailed: state._permanentlyFailed,
      activeAnalysisId: state.activeAnalysisId,
      maxAttempts: MAX_RECONNECT_ATTEMPTS,
      suggestion: 'user_refresh_required',
    })
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

    // Set up network recovery for automatic reconnection
    const cleanupNetworkRecovery = setupNetworkRecovery(analysisId, store)
    store.setState({ _cleanupNetworkRecovery: cleanupNetworkRecovery })
  } catch (error) {
    logger.error('Failed to create SSE connection', {
      analysisId,
      error: error instanceof Error ? error.message : String(error),
      stack: error instanceof Error ? error.stack : undefined,
      userAgent: navigator?.userAgent,
    })
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

  // Clean up network recovery listeners
  if (state._cleanupNetworkRecovery) {
    state._cleanupNetworkRecovery()
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
