import type { ReactNode } from 'react'

import { AnalysisHeader } from '../steps/AnalysisHeader'
import { TimeoutWarningBanner } from '../TimeoutWarningBanner'

/**
 * Props for the CommonAnalysisLayout component
 */
interface CommonAnalysisLayoutProps {
  /** Child content to render in the main content area */
  children: ReactNode
  /** Analysis metadata for the header */
  analysisMetadata?: {
    title?: string
    url?: string
    contentType?: 'article' | 'video' | 'repo'
    wordCount?: number
  }
  /** Analysis ID for fallback header text */
  analysisId?: string
  /** Whether to show the timeout warning banner */
  showTimeoutWarning?: boolean
  /** Callback when timeout warning is dismissed */
  onTimeoutWarningDismiss?: () => void
  /** Progress content to render (typically ProgressColumn) */
  progressContent?: ReactNode
}

/**
 * Common layout component that eliminates duplicate JSX across analysis routes
 *
 * This component provides:
 * - Consistent container styling
 * - AnalysisHeader (no longer duplicated)
 * - Optional timeout warning banner
 * - Optional progress content slot
 * - Main content area for route-specific content
 */
export function CommonAnalysisLayout({
  children,
  analysisMetadata,
  analysisId,
  showTimeoutWarning = false,
  onTimeoutWarningDismiss,
  progressContent,
}: CommonAnalysisLayoutProps) {
  return (
    <div className="container mx-auto px-4 py-8 max-w-7xl" data-testid="common-analysis-layout">
      <AnalysisHeader
        title={analysisMetadata?.title || 'Content Analysis'}
        url={analysisMetadata?.url || (analysisId ? `Analysis ID: ${analysisId}` : '')}
        contentType={analysisMetadata?.contentType}
        wordCount={analysisMetadata?.wordCount}
      />

      {showTimeoutWarning && onTimeoutWarningDismiss && (
        <TimeoutWarningBanner
          showTimeoutWarning={showTimeoutWarning}
          onDismiss={onTimeoutWarningDismiss}
        />
      )}

      {children}

      {progressContent}
    </div>
  )
}
