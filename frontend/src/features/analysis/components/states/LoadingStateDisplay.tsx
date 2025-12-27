import type * as React from 'react'

import type { LucideIcon } from 'lucide-react'
import { FileText, Loader2, CheckCircle2, AlertCircle } from 'lucide-react'

import { UI_CONSTANTS } from '@/lib/constants'

import { cn } from '../../../../lib/utils'
import type { LoadingState } from '../../../../types/loading'

interface LoadingStateDisplayProps {
  loadingState: LoadingState
}

/**
 * Loading state UI configuration
 */
interface LoadingStateUIConfig {
  icon: LucideIcon
  text: string
  subtitle: string | ((state: LoadingState) => string)
  textClassName?: string
  animate?: boolean
}

/**
 * Enum-driven configuration for loading states
 * Replaces switch/case with declarative config object
 */
const LOADING_STATE_CONFIG = {
  disconnected: {
    icon: Loader2,
    text: 'Disconnected',
    subtitle: 'Waiting to connect...',
    animate: false,
  },
  connecting: {
    icon: Loader2,
    text: 'Connecting...',
    subtitle: 'Establishing connection',
    animate: true,
  },
  connected: {
    icon: Loader2,
    text: 'Connected',
    subtitle: 'Waiting for analysis to start',
    animate: false,
  },
  reconnecting: {
    icon: Loader2,
    text: 'Reconnecting...',
    subtitle: 'Attempting to restore connection',
    animate: true,
  },
  waiting_for_events: {
    icon: Loader2,
    text: 'Preparing analysis...',
    subtitle: 'Setting up your content analysis',
    animate: true,
  },
  timeout_warning: {
    icon: AlertCircle,
    text: 'Connection timeout',
    subtitle: 'This is taking longer than expected',
    textClassName: 'text-orange-600',
    animate: false,
  },
  extracting: {
    icon: FileText,
    text: 'Extracting content...',
    subtitle: (state: LoadingState) =>
      state.type === 'extracting' && state.wordCount
        ? `Processing ${state.wordCount.toLocaleString()} words`
        : 'Reading and analyzing your content',
    animate: false,
  },
  analyzing: {
    icon: Loader2,
    text: 'Analyzing content...',
    subtitle: (state: LoadingState) =>
      state.type === 'analyzing'
        ? `Running AI analysis (${state.progress}%)`
        : 'Running AI analysis',
    animate: true,
  },
  generating: {
    icon: Loader2,
    text: 'Generating report...',
    subtitle: 'Compiling your analysis results',
    animate: true,
  },
  complete: {
    icon: CheckCircle2,
    text: 'Analysis complete',
    subtitle: 'Your results are ready to view',
    textClassName: 'text-green-700',
    animate: false,
  },
  error: {
    icon: AlertCircle,
    text: 'Analysis failed',
    subtitle: (state: LoadingState) => (state.type === 'error' ? state.error : 'An error occurred'),
    textClassName: 'text-destructive',
    animate: false,
  },
} as const satisfies Record<LoadingState['type'], LoadingStateUIConfig>

/**
 * Contextual loading state display for analysis phases
 *
 * Shows appropriate messages and icons based on the current loading state.
 * Provides clear feedback to users about what's happening during analysis.
 *
 * Issue #399: Replaces generic "Loading" with specific, contextual messages
 * Issue #433: Refactored to use enum-driven configuration pattern (2025 best practice)
 */
export function LoadingStateDisplay({ loadingState }: LoadingStateDisplayProps): React.ReactNode {
  const config = LOADING_STATE_CONFIG[loadingState.type]
  const Icon = config.icon
  const subtitle =
    typeof config.subtitle === 'function' ? config.subtitle(loadingState) : config.subtitle

  return (
    <div className="flex items-center gap-3 p-4 bg-muted/50 rounded-lg">
      <div className="flex-shrink-0">
        <Icon
          className={cn(
            UI_CONSTANTS.HEIGHT_SM,
            UI_CONSTANTS.WIDTH_SM,
            config.animate && 'animate-spin'
          )}
        />
      </div>
      <div className="flex-1 min-w-0">
        <p className={cn('text-sm font-medium', config.textClassName)}>{config.text}</p>
        <p className="text-xs text-muted-foreground mt-0.5">{subtitle}</p>
      </div>
    </div>
  )
}

LoadingStateDisplay.displayName = 'LoadingStateDisplay'
