import type * as React from 'react'

import { Wifi, WifiOff } from 'lucide-react'

import { cn } from '@lib/utils'

interface ConnectionStatusProps {
  isConnected: boolean
}

/**
 * Connection status indicator for SSE stream
 */
export const ConnectionStatus: React.FC<ConnectionStatusProps> = ({ isConnected }) => (
  <div
    className={cn(
      'flex items-center gap-1.5 text-xs',
      isConnected ? 'text-[oklch(0.6959_0.1491_162.4796)]' : 'text-muted-foreground'
    )}
  >
    {isConnected ? <Wifi className="h-3.5 w-3.5" /> : <WifiOff className="h-3.5 w-3.5" />}
    <span>{isConnected ? 'Connected' : 'Disconnected'}</span>
  </div>
)

ConnectionStatus.displayName = 'ConnectionStatus'
