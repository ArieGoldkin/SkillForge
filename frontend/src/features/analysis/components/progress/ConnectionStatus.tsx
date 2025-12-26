import type * as React from 'react'

import { Wifi, WifiOff, AlertTriangle, Loader2 } from 'lucide-react'

import { UI_CONSTANTS } from '@/lib/constants'
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
export function ConnectionStatus({ loadingState }: ConnectionStatusProps): React.ReactNode {
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
          icon: (
            <Wifi className={`${UI_CONSTANTS.HEIGHT_XS_MEDIUM} ${UI_CONSTANTS.WIDTH_XS_MEDIUM}`} />
          ),
          text: 'Connected',
          className: 'text-status-success',
        }

      case 'reconnecting':
        return {
          icon: <Loader2 className="h-3.5 w-3.5 animate-spin" />,
          text: `Reconnecting... (${loadingState.attempts}/3)`,
          className: 'text-yellow-600',
        }

      case 'timeout_warning':
        return {
          icon: (
            <AlertTriangle
              className={`${UI_CONSTANTS.HEIGHT_XS_MEDIUM} ${UI_CONSTANTS.WIDTH_XS_MEDIUM}`}
            />
          ),
          text: 'Connection timeout',
          className: 'text-orange-600',
        }

      case 'disconnected':
        return {
          icon: (
            <WifiOff
              className={`${UI_CONSTANTS.HEIGHT_XS_MEDIUM} ${UI_CONSTANTS.WIDTH_XS_MEDIUM}`}
            />
          ),
          text: 'Disconnected',
          className: 'text-muted-foreground',
        }

      default:
        return {
          icon: (
            <WifiOff
              className={`${UI_CONSTANTS.HEIGHT_XS_MEDIUM} ${UI_CONSTANTS.WIDTH_XS_MEDIUM}`}
            />
          ),
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
