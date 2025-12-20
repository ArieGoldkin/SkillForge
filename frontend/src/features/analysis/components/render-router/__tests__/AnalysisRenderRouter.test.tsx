import { render, screen } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'

import { AnalysisRenderRouter } from '../AnalysisRenderRouter'
import type { AnalysisProps } from '../types'

// Mock child components
vi.mock('../../states/CompletedAnalysisView', () => ({
  CompletedAnalysisView: (props: any) => (
    <div data-testid="completed-analysis-view">Completed: {props.analysisId || 'unknown'}</div>
  ),
}))

vi.mock('../../LoadingStateDisplay', () => ({
  LoadingStateDisplay: ({ loadingState }: { loadingState: any }) => (
    <div data-testid="loading-state-display">{loadingState?.type || 'unknown'}</div>
  ),
}))

vi.mock('../CommonAnalysisLayout', () => ({
  CommonAnalysisLayout: ({ children, showTimeoutWarning, progressContent }: any) => (
    <div data-testid="common-analysis-layout">
      {showTimeoutWarning && <div data-testid="timeout-warning-banner">Timeout Warning</div>}
      {children}
      {progressContent}
    </div>
  ),
}))

// ActiveAnalysisView was inlined into the router - no mock needed

vi.mock('../../progress/ProgressColumn', () => ({
  ProgressColumn: (props: any) => <div data-testid="progress-column" />,
}))

describe('AnalysisRenderRouter', () => {
  // Clean up after each test to ensure isolation
  afterEach(() => {
    vi.clearAllMocks()
  })

  const baseProps: AnalysisProps = {
    id: 'test-analysis-id',
    completed: false,
    urlArtifactId: undefined,
    isResolvedComplete: false,
    resolvedArtifactId: undefined,
    isFatalError: false,
    effectiveError: '',
    loadingState: { type: 'waiting_for_events' },
    showTimeoutWarning: false,
    timeoutWarningDismissed: false,
    shouldShowProgress: false,
    handleTimeoutWarningDismiss: vi.fn(),
    overallProgress: { stage: 'waiting', progress: 0 },
    steps: [],
    activities: [],
    hasFailedStages: false,
    failedStagesCount: 0,
    analysisMetadata: { title: 'Test Analysis', url: 'https://test.com' },
    error: null,
    hasError: false,
    statusError: null,
    isFailed: false,
    isConnected: false,
    isComplete: false,
    completionRef: { current: null },
  }

  it('renders legacy completion when completed && urlArtifactId (priority 100)', () => {
    const props = {
      ...baseProps,
      completed: true,
      urlArtifactId: 'test-artifact-id',
    }

    render(<AnalysisRenderRouter {...props} />)

    // Completion routes render CompletedAnalysisView directly (includes its own layout)
    expect(screen.getByTestId('completed-analysis-view')).toBeInTheDocument()
    expect(screen.getByText('Completed: test-analysis-id')).toBeInTheDocument()
    // Should NOT have CommonAnalysisLayout wrapper
    expect(screen.queryByTestId('common-analysis-layout')).not.toBeInTheDocument()
  })

  it('renders modern completion when isResolvedComplete && resolvedArtifactId (priority 90)', () => {
    const props = {
      ...baseProps,
      isResolvedComplete: true,
      resolvedArtifactId: 'test-artifact-id',
    }

    render(<AnalysisRenderRouter {...props} />)

    // Completion routes render CompletedAnalysisView directly (includes its own layout)
    expect(screen.getByTestId('completed-analysis-view')).toBeInTheDocument()
    // Should NOT have CommonAnalysisLayout wrapper
    expect(screen.queryByTestId('common-analysis-layout')).not.toBeInTheDocument()
  })

  it('prioritizes legacy completion over modern completion', () => {
    const props = {
      ...baseProps,
      completed: true,
      urlArtifactId: 'legacy-artifact',
      isResolvedComplete: true,
      resolvedArtifactId: 'modern-artifact',
    }

    render(<AnalysisRenderRouter {...props} />)

    // Should render legacy completion (priority 100 > 90)
    expect(screen.getByText('Completed: test-analysis-id')).toBeInTheDocument()
  })

  it('renders loading states for active analysis phases (priority 80)', () => {
    const loadingStates = ['waiting_for_events', 'extracting', 'analyzing', 'generating']

    loadingStates.forEach((loadingType) => {
      const props = {
        ...baseProps,
        loadingState: { type: loadingType },
      }

      const { rerender } = render(<AnalysisRenderRouter {...props} />)

      expect(screen.getByTestId('common-analysis-layout')).toBeInTheDocument()
      expect(screen.getByTestId('loading-state-display')).toBeInTheDocument()
      expect(screen.getByText(loadingType)).toBeInTheDocument()

      rerender(<></>) // Clear for next test
    })
  })

  it('renders error state when loadingState.type === error (priority 70)', () => {
    const props = {
      ...baseProps,
      loadingState: { type: 'error', message: 'Test error' },
    }

    render(<AnalysisRenderRouter {...props} />)

    expect(screen.getByTestId('common-analysis-layout')).toBeInTheDocument()
    expect(screen.getByTestId('loading-state-display')).toBeInTheDocument()
    expect(screen.getByText('error')).toBeInTheDocument()
  })

  it('renders loading completion when loadingState.type === complete (priority 60)', () => {
    const props = {
      ...baseProps,
      loadingState: { type: 'complete' },
    }

    render(<AnalysisRenderRouter {...props} />)

    // Loading completion renders CompletedAnalysisView directly (includes its own layout)
    expect(screen.getByTestId('completed-analysis-view')).toBeInTheDocument()
    // Should NOT have CommonAnalysisLayout wrapper
    expect(screen.queryByTestId('common-analysis-layout')).not.toBeInTheDocument()
  })

  it('renders default active analysis view as fallback (priority 10)', () => {
    const props = {
      ...baseProps,
      loadingState: { type: 'unknown' }, // Doesn't match any loading conditions
      // No completion conditions match - should fall back to active view
    }

    render(<AnalysisRenderRouter {...props} />)

    // Active analysis view is inlined in the router with data-testid
    expect(screen.getByTestId('active-analysis-view')).toBeInTheDocument()
    expect(screen.getByText('Active: test-analysis-id')).toBeInTheDocument()
  })

  it('includes timeout warning and progress in loading states when enabled', () => {
    const props = {
      ...baseProps,
      loadingState: { type: 'analyzing' },
      showTimeoutWarning: true,
      timeoutWarningDismissed: false,
      shouldShowProgress: true,
    }

    render(<AnalysisRenderRouter {...props} />)

    // Loading states use CommonAnalysisLayout
    expect(screen.getByTestId('common-analysis-layout')).toBeInTheDocument()
    expect(screen.getByTestId('loading-state-display')).toBeInTheDocument()
    // Progress should be rendered when shouldShowProgress is true
    expect(screen.getByTestId('progress-column')).toBeInTheDocument()
  })

  it('always has a fallback route (priority 10)', () => {
    // The default route (priority 10) always matches with condition () => true
    // This ensures we never reach the error case
    const props = {
      ...baseProps,
      loadingState: { type: 'unknown' }, // Doesn't match any loading conditions
      // No completion conditions match - should fall back to active view
    }

    render(<AnalysisRenderRouter {...props} />)

    // Fallback route renders inlined active analysis view
    expect(screen.getByTestId('active-analysis-view')).toBeInTheDocument()
    expect(screen.getByText('Active: test-analysis-id')).toBeInTheDocument()
  })

  it('prioritizes routes correctly (100 > 90 > 80 > 70 > 60 > 10)', () => {
    // Test that higher priority routes win when multiple conditions match
    const props = {
      ...baseProps,
      completed: true,
      urlArtifactId: 'test', // Matches priority 100
      isResolvedComplete: true,
      resolvedArtifactId: 'test', // Would match priority 90 if 100 didn't exist
    }

    render(<AnalysisRenderRouter {...props} />)

    // Should render priority 100 (legacy completion), not priority 90
    expect(screen.getByTestId('completed-analysis-view')).toBeInTheDocument()
    expect(screen.getByText('Completed: test-analysis-id')).toBeInTheDocument()
  })
})
