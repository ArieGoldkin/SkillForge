import { useEffect } from 'react'

/**
 * Hook to manage SSE connection lifecycle
 */
export const useSSELifecycle = ({
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
