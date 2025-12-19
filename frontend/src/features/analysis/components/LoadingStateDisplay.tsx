import type * as React from 'react'

import { FileText, Loader2 } from 'lucide-react'

import { cn } from '@lib/utils'
import type { LoadingState } from '@types/loading'

interface LoadingStateDisplayProps {
  loadingState: LoadingState
}

/**
 * Contextual loading state display for analysis phases
 *
 * Shows appropriate messages and icons based on the current loading state.
 * Provides clear feedback to users about what's happening during analysis.
 *
 * Issue #399: Replaces generic "Loading" with specific, contextual messages
 */
export const LoadingStateDisplay: React.FC<LoadingStateDisplayProps> = ({ loadingState }) => {
  const getDisplayContent = (): { icon?: React.ReactNode; text: string; subtitle?: string } => {
    switch (loadingState.type) {
      case 'waiting_for_events':
        return {
          icon: <Loader2 className="h-4 w-4 animate-spin" />,
          text: 'Preparing analysis...',
          subtitle: 'Setting up your content analysis',
        }

      case 'extracting':
        return {
          icon: <FileText className="h-4 w-4" />,
          text: 'Extracting content...',
          subtitle: loadingState.wordCount
            ? `Processing ${loadingState.wordCount.toLocaleString()} words`
            : 'Reading and analyzing your content',
        }

      case 'analyzing':
        return {
          icon: <Loader2 className="h-4 w-4 animate-spin" />,
          text: 'Analyzing content...',
          subtitle: `Running AI analysis (${loadingState.progress}%)`,
        }

      case 'generating':
        return {
          icon: <Loader2 className="h-4 w-4 animate-spin" />,
          text: 'Generating report...',
          subtitle: 'Compiling your analysis results',
        }

      case 'complete':
        return {
          text: 'Analysis complete',
          subtitle: 'Your results are ready to view',
        }

      case 'error':
        return {
          text: 'Analysis failed',
          subtitle: loadingState.error,
        }

      default:
        return {
          icon: <Loader2 className="h-4 w-4 animate-spin" />,
          text: 'Loading...',
          subtitle: 'Please wait',
        }
    }
  }

  const { icon, text, subtitle } = getDisplayContent()

  return (
    <div className="flex items-center gap-3 p-4 bg-muted/50 rounded-lg">
      {icon && <div className="flex-shrink-0">{icon}</div>}
      <div className="flex-1 min-w-0">
        <p
          className={cn(
            'text-sm font-medium',
            loadingState.type === 'error' && 'text-destructive',
            loadingState.type === 'complete' && 'text-green-700'
          )}
        >
          {text}
        </p>
        {subtitle && <p className="text-xs text-muted-foreground mt-0.5">{subtitle}</p>}
      </div>
    </div>
  )
}

LoadingStateDisplay.displayName = 'LoadingStateDisplay'
