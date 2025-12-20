import type * as React from 'react'

import { FileText, Loader2 } from 'lucide-react'

import { UI_CONSTANTS } from '@/lib/constants'

import { cn } from '../../../../lib/utils'
import type { LoadingState } from '../../../../types/loading'

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
/**
 * Get display content for waiting state
 */
const getWaitingContent = () => ({
  icon: <Loader2 className="h-4 w-4 animate-spin" />,
  text: 'Preparing analysis...',
  subtitle: 'Setting up your content analysis',
})

/**
 * Get display content for extracting state
 */
const getExtractingContent = (wordCount?: number) => ({
  icon: <FileText className={`${UI_CONSTANTS.HEIGHT_SM} ${UI_CONSTANTS.WIDTH_SM}`} />,
  text: 'Extracting content...',
  subtitle: wordCount
    ? `Processing ${wordCount.toLocaleString()} words`
    : 'Reading and analyzing your content',
})

/**
 * Get display content for analyzing state
 */
const getAnalyzingContent = (progress: number) => ({
  icon: <Loader2 className="h-4 w-4 animate-spin" />,
  text: 'Analyzing content...',
  subtitle: `Running AI analysis (${progress}%)`,
})

/**
 * Get display content for generating state
 */
const getGeneratingContent = () => ({
  icon: <Loader2 className="h-4 w-4 animate-spin" />,
  text: 'Generating report...',
  subtitle: 'Compiling your analysis results',
})

/**
 * Get display content for complete state
 */
const getCompleteContent = () => ({
  text: 'Analysis complete',
  subtitle: 'Your results are ready to view',
})

/**
 * Get display content for error state
 */
const getErrorContent = (error: string) => ({
  text: 'Analysis failed',
  subtitle: error,
})

/**
 * Get display content for default loading state
 */
const getDefaultContent = () => ({
  icon: <Loader2 className="h-4 w-4 animate-spin" />,
  text: 'Loading...',
  subtitle: 'Please wait',
})

export const LoadingStateDisplay: React.FC<LoadingStateDisplayProps> = ({ loadingState }) => {
  const getDisplayContent = (): { icon?: React.ReactNode; text: string; subtitle?: string } => {
    switch (loadingState.type) {
      case 'waiting_for_events':
        return getWaitingContent()
      case 'extracting':
        return getExtractingContent(loadingState.wordCount)
      case 'analyzing':
        return getAnalyzingContent(loadingState.progress)
      case 'generating':
        return getGeneratingContent()
      case 'complete':
        return getCompleteContent()
      case 'error':
        return getErrorContent(loadingState.error)
      default:
        return getDefaultContent()
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
