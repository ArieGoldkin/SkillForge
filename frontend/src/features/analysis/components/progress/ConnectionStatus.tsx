import type * as React from 'react'

import type { LucideIcon } from 'lucide-react'
import { Wifi, WifiOff, AlertTriangle, Loader2 } from 'lucide-react'

import { UI_CONSTANTS } from '@/lib/constants'
import { cn } from '@/lib/utils'
import type { LoadingState } from '@/types/loading'

interface ConnectionStatusProps {
  loadingState: LoadingState
}

/**
 * Connection state UI configuration
 */
interface ConnectionStateUI {
  icon: LucideIcon
  text: string | ((state: LoadingState) => string)
  className: string
  animate: boolean
}

/**
 * Enum-driven configuration for connection states
 * Replaces switch/case with declarative config object
 */
const CONNECTION_STATE_CONFIG = {
  connecting: {
    icon: Loader2,
    text: 'Connecting...',
    className: 'text-muted-foreground',
    animate: true,
  },
  connected: {
    icon: Wifi,
    text: 'Connected',
    className: 'text-status-success',
    animate: false,
  },
  reconnecting: {
    icon: Loader2,
    text: (state: LoadingState) =>
      state.type === 'reconnecting' ? `Reconnecting... (${state.attempts}/3)` : 'Reconnecting...',
    className: 'text-yellow-600',
    animate: true,
  },
  timeout_warning: {
    icon: AlertTriangle,
    text: 'Connection timeout',
    className: 'text-orange-600',
    animate: false,
  },
  disconnected: {
    icon: WifiOff,
    text: 'Disconnected',
    className: 'text-muted-foreground',
    animate: false,
  },
  waiting_for_events: {
    icon: Loader2,
    text: 'Waiting for events...',
    className: 'text-muted-foreground',
    animate: true,
  },
  extracting: {
    icon: Loader2,
    text: 'Extracting...',
    className: 'text-muted-foreground',
    animate: true,
  },
  analyzing: {
    icon: Loader2,
    text: 'Analyzing...',
    className: 'text-muted-foreground',
    animate: true,
  },
  generating: {
    icon: Loader2,
    text: 'Generating...',
    className: 'text-muted-foreground',
    animate: true,
  },
  complete: {
    icon: Wifi,
    text: 'Complete',
    className: 'text-status-success',
    animate: false,
  },
  error: {
    icon: AlertTriangle,
    text: 'Error',
    className: 'text-destructive',
    animate: false,
  },
} as const satisfies Record<LoadingState['type'], ConnectionStateUI>

/**
 * Enhanced connection status indicator for SSE stream with granular loading states
 *
 * Issue #399: Shows contextual connection messages instead of simple connected/disconnected
 * Issue #433: Refactored to use enum-driven configuration pattern (2025 best practice)
 */
export function ConnectionStatus({ loadingState }: ConnectionStatusProps): React.ReactNode {
  const config = CONNECTION_STATE_CONFIG[loadingState.type]
  const Icon = config.icon
  const text = typeof config.text === 'function' ? config.text(loadingState) : config.text

  return (
    <div className={cn('flex items-center gap-1.5 text-xs', config.className)}>
      <Icon
        className={cn(
          UI_CONSTANTS.HEIGHT_XS_MEDIUM,
          UI_CONSTANTS.WIDTH_XS_MEDIUM,
          config.animate && 'animate-spin'
        )}
      />
      <span>{text}</span>
    </div>
  )
}

ConnectionStatus.displayName = 'ConnectionStatus'
