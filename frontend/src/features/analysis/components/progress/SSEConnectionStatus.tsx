import { memo } from 'react'

import { useSSEStore } from '@stores/sseStore'
import { Wifi, WifiOff, RefreshCw, AlertCircle } from 'lucide-react'

import { Badge } from '@shared/components/ui/badge'

import { cn } from '@lib/utils'

/**
 * Get connection status configuration based on current state
 */
function getConnectionStatus(
  isConnected: boolean,
  isPolling: boolean,
  connectionState: string,
  error: Error | null
) {
  if (error && !isConnected && !isPolling) {
    return {
      label: 'Connection Error',
      variant: 'destructive' as const,
      icon: AlertCircle,
    }
  }
  if (isPolling) {
    return {
      label: 'Polling',
      variant: 'default' as const,
      icon: RefreshCw,
    }
  }
  if (isConnected) {
    return {
      label: 'Connected',
      variant: 'success' as const,
      icon: Wifi,
    }
  }
  if (connectionState === 'reconnecting') {
    return {
      label: 'Reconnecting',
      variant: 'warning' as const,
      icon: RefreshCw,
    }
  }
  return {
    label: 'Disconnected',
    variant: 'secondary' as const,
    icon: WifiOff,
  }
}

/**
 * SSE Connection Status Component
 *
 * Displays the current connection state with visual indicators:
 * - Connected: Green badge with WiFi icon
 * - Reconnecting: Yellow badge with refresh icon
 * - Polling: Blue badge with refresh icon
 * - Disconnected: Gray badge with WiFi off icon
 * - Error: Red badge with alert icon
 */
export const SSEConnectionStatus = memo(function SSEConnectionStatus({
  className,
}: {
  className?: string
}) {
  const isConnected = useSSEStore((state) => state.isConnected)
  const isPolling = useSSEStore((state) => state.isPolling)
  const connectionState = useSSEStore((state) => state.connectionState)
  const error = useSSEStore((state) => state.error)

  const status = getConnectionStatus(isConnected, isPolling, connectionState, error)
  const StatusIcon = status.icon

  return (
    <Badge
      variant={status.variant}
      className={cn(
        'flex items-center gap-1.5 text-xs',
        status.variant === 'success' && 'bg-green-500 hover:bg-green-600',
        status.variant === 'warning' && 'bg-yellow-500 hover:bg-yellow-600',
        status.variant === 'destructive' && 'bg-red-500 hover:bg-red-600',
        className
      )}
      title={error ? error.message : undefined}
    >
      <StatusIcon
        className={cn(
          'h-3 w-3',
          (connectionState === 'reconnecting' || isPolling) && 'animate-spin'
        )}
        aria-hidden="true"
      />
      <span>{status.label}</span>
    </Badge>
  )
})
