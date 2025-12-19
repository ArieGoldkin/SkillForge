import { useEffect, useMemo } from 'react'

import type { SSEStore } from '@stores/sseStore'
import { useSSEStore } from '@stores/sseStore'

/**
 * Zustand Selectors - Defined at module level for stable references
 *
 * Using individual selectors instead of whole-store subscription:
 * - Prevents re-renders when unrelated state changes
 * - Each selector only triggers re-render when its specific slice changes
 * - Critical for performance during SSE streaming (50+ events/second)
 */
const selectEvents = (state: SSEStore) => state.events
const selectLatestEvent = (state: SSEStore) => state.latestEvent
const selectError = (state: SSEStore) => state.error
const selectIsConnected = (state: SSEStore) => state.isConnected
const selectIsComplete = (state: SSEStore) => state.isComplete
const selectActiveAnalysisId = (state: SSEStore) => state.activeAnalysisId
const selectConnect = (state: SSEStore) => state.connect
const selectDisconnect = (state: SSEStore) => state.disconnect

/**
 * useSSE - Convenience hook for SSE connection with lifecycle management
 *
 * Automatically connects to SSE endpoint when mounted and disconnects when unmounted.
 * Uses the global Zustand store so multiple components can share the same connection.
 *
 * Performance Optimizations:
 * - Individual Zustand selectors prevent cascading re-renders
 * - Memoized return value avoids new object reference per render
 * - Only subscribes to state slices actually used by consumer
 *
 * @param analysisId - The analysis ID to connect to
 * @returns SSE state and disconnect function
 */
export function useSSE(analysisId: string) {
  // Individual selectors - only re-render when specific state changes
  const events = useSSEStore(selectEvents)
  const latestEvent = useSSEStore(selectLatestEvent)
  const error = useSSEStore(selectError)
  const isConnected = useSSEStore(selectIsConnected)
  const isComplete = useSSEStore(selectIsComplete)
  const activeAnalysisId = useSSEStore(selectActiveAnalysisId)
  const connect = useSSEStore(selectConnect)
  const disconnect = useSSEStore(selectDisconnect)

  useEffect(() => {
    // Only connect if not already connected to this analysis
    if (activeAnalysisId !== analysisId) {
      connect(analysisId)
    }

    // Note: We don't disconnect on unmount by default because other components
    // might still be using the connection. Call disconnect() explicitly when needed.
  }, [analysisId, activeAnalysisId, connect])

  // Memoize return object to prevent new reference on each render
  // This helps consumers avoid unnecessary re-renders when their parent re-renders
  return useMemo(
    () => ({
      events,
      latestEvent,
      error,
      isConnected,
      isComplete,
      disconnect,
    }),
    [events, latestEvent, error, isConnected, isComplete, disconnect]
  )
}
