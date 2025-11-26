import { useEffect } from 'react'

import { useSSEStore } from '@stores/sseStore'

/**
 * useSSE - Convenience hook for SSE connection with lifecycle management
 *
 * Automatically connects to SSE endpoint when mounted and disconnects when unmounted.
 * Uses the global Zustand store so multiple components can share the same connection.
 *
 * @param analysisId - The analysis ID to connect to
 * @returns SSE state and disconnect function
 */
export function useSSE(analysisId: string) {
  const {
    events,
    latestEvent,
    error,
    isConnected,
    isComplete,
    activeAnalysisId,
    connect,
    disconnect,
  } = useSSEStore()

  useEffect(() => {
    // Only connect if not already connected to this analysis
    if (activeAnalysisId !== analysisId) {
      connect(analysisId)
    }

    // Note: We don't disconnect on unmount by default because other components
    // might still be using the connection. Call disconnect() explicitly when needed.
  }, [analysisId, activeAnalysisId, connect])

  return {
    events,
    latestEvent,
    error,
    isConnected,
    isComplete,
    disconnect,
  }
}
