import type * as React from 'react'

import { Wifi, WifiOff, AlertTriangle, Loader2 } from 'lucide-react'

import { cn } from '@/lib/utils'
import type { LoadingState } from '@/types/loading'

interface ConnectionStatusProps {
  loadingState: LoadingState
}

/**
 * Enhanced connection status indicator for SSE stream with granular loading states
 *
 * Issue #399: Shows contextual connection messages instead of simple connected/disconnected
 */
export const ConnectionStatus: React.FC<ConnectionStatusProps> = ({ loadingState }) => {
  const getStatusDisplay = (): { icon: React.ReactNode; text: string; className: string } => {
    switch (loadingState.type) {
      case 'connecting':
        return {
          icon: <Loader2 className="h-3.5 w-3.5 animate-spin" />,
          text: 'Connecting...',
          className: 'text-muted-foreground',
        }

      case 'connected':
        return {
          icon: <Wifi className="h-3.5 w-3.5" />,
          text: 'Connected',
          className: 'text-[oklch(0.6959_0.1491_162.4796)]',
        }

      case 'reconnecting':
        return {
          icon: <Loader2 className="h-3.5 w-3.5 animate-spin" />,
          text: `Reconnecting... (${loadingState.attempts}/3)`,
          className: 'text-yellow-600',
        }

      case 'timeout_warning':
        return {
          icon: <AlertTriangle className="h-3.5 w-3.5" />,
          text: 'Connection timeout',
          className: 'text-orange-600',
        }

      case 'disconnected':
        return {
          icon: <WifiOff className="h-3.5 w-3.5" />,
          text: 'Disconnected',
          className: 'text-muted-foreground',
        }

      default:
        return {
          icon: <WifiOff className="h-3.5 w-3.5" />,
          text: 'Disconnected',
          className: 'text-muted-foreground',
        }
    }
  }

  const { icon, text, className } = getStatusDisplay()

  return (
    <div className={cn('flex items-center gap-1.5 text-xs', className)}>
      {icon}
      <span>{text}</span>
    </div>
  )
}

ConnectionStatus.displayName = 'ConnectionStatus'
