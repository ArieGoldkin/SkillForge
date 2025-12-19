import { memo } from 'react'
import type * as React from 'react'

import { FileText, Loader2 } from 'lucide-react'

import type { LoadingState } from '@/types/loading'

import { cn } from '@lib/utils'

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
const getWaitingDisplay = (): { icon: React.ReactNode; text: string; subtitle: string } => ({
  icon: <Loader2 className="h-4 w-4 animate-spin" />,
  text: 'Preparing analysis...',
  subtitle: 'Setting up your content analysis',
})

const getExtractingDisplay = (
  wordCount?: number
): { icon: React.ReactNode; text: string; subtitle: string } => ({
  icon: <FileText className="h-4 w-4" />,
  text: 'Extracting content...',
  subtitle: wordCount
    ? `Processing ${wordCount.toLocaleString()} words`
    : 'Reading and analyzing your content',
})

const getAnalyzingDisplay = (
  progress: number
): { icon: React.ReactNode; text: string; subtitle: string } => ({
  icon: <Loader2 className="h-4 w-4 animate-spin" />,
  text: 'Analyzing content...',
  subtitle: `Running AI analysis (${progress}%)`,
})

const getGeneratingDisplay = (): { icon: React.ReactNode; text: string; subtitle: string } => ({
  icon: <Loader2 className="h-4 w-4 animate-spin" />,
  text: 'Generating report...',
  subtitle: 'Compiling your analysis results',
})

const getCompleteDisplay = (): { text: string; subtitle: string } => ({
  text: 'Analysis complete',
  subtitle: 'Your results are ready to view',
})

const getErrorDisplay = (error: string): { text: string; subtitle: string } => ({
  text: 'Analysis failed',
  subtitle: error,
})

const getDefaultDisplay = (): { icon: React.ReactNode; text: string; subtitle: string } => ({
  icon: <Loader2 className="h-4 w-4 animate-spin" />,
  text: 'Loading...',
  subtitle: 'Please wait',
})

export const LoadingStateDisplay = memo<LoadingStateDisplayProps>(function LoadingStateDisplay({
  loadingState,
}) {
  const getDisplayContent = (): { icon?: React.ReactNode; text: string; subtitle?: string } => {
    switch (loadingState.type) {
      case 'waiting_for_events':
        return getWaitingDisplay()

      case 'extracting':
        return getExtractingDisplay(loadingState.wordCount)

      case 'analyzing':
        return getAnalyzingDisplay(loadingState.progress)

      case 'generating':
        return getGeneratingDisplay()

      case 'complete':
        return getCompleteDisplay()

      case 'error':
        return getErrorDisplay(loadingState.error)

      default:
        return getDefaultDisplay()
    }
  }

  const { icon, text, subtitle } = getDisplayContent()

  // Generate screen reader announcement for loading state changes
  const getScreenReaderText = (): string => {
    switch (loadingState.type) {
      case 'waiting_for_events':
        return 'Preparing analysis. Setting up your content analysis.'
      case 'extracting':
        return `Extracting content. ${loadingState.wordCount ? `Processing ${loadingState.wordCount.toLocaleString()} words.` : 'Reading and analyzing your content.'}`
      case 'analyzing':
        return `Analyzing content. Running AI analysis at ${loadingState.progress}% completion.`
      case 'generating':
        return 'Generating report. Compiling your analysis results.'
      case 'complete':
        return 'Analysis complete. Your results are ready to view.'
      case 'error':
        return `Analysis failed. ${loadingState.error}`
      default:
        return 'Loading analysis. Please wait.'
    }
  }

  return (
    <>
      {/* Screen reader live region for dynamic content */}
      <div aria-live="polite" aria-atomic="true" className="sr-only" role="status">
        {getScreenReaderText()}
      </div>

      {/* Visual loading state display */}
      <div
        className="flex items-center gap-3 sm:gap-4 p-3 sm:p-4 bg-muted/50 rounded-lg"
        role="status"
        aria-label={`Loading state: ${text}`}
      >
        {icon && (
          <div className="flex-shrink-0" aria-hidden="true">
            {icon}
          </div>
        )}
        <div className="flex-1 min-w-0">
          <p
            className={cn(
              'text-sm sm:text-base font-medium',
              loadingState.type === 'error' && 'text-status-error',
              loadingState.type === 'complete' && 'text-status-success'
            )}
          >
            {text}
          </p>
          {subtitle && (
            <p className="text-xs sm:text-sm text-muted-foreground mt-0.5">{subtitle}</p>
          )}
        </div>
      </div>
    </>
  )
})

LoadingStateDisplay.displayName = 'LoadingStateDisplay'
