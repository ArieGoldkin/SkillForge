/**
 * Integration tests for AnalyzeResult loading states functionality
 *
 * Tests the integration between AnalyzeResult and the new loading state components:
 * - LoadingStateDisplay
 * - TimeoutWarningBanner
 * - ConnectionStatus (via ProgressTracker)
 */

import { useSSEStore } from '@stores/sseStore'
import { render, screen } from '@testing-library/react'
import { describe, expect, it, vi, beforeEach, afterEach } from 'vitest'

import type { LoadingState } from '@types/loading'

import AnalyzeResult from '../AnalyzeResult'

// Mock React Router
vi.mock('react-router', async () => {
  const actual = await vi.importActual('react-router')
  return {
    ...actual,
    useParams: () => ({ id: 'test-analysis-id' }),
    useSearch: () => ({ completed: false }),
  }
})

// Mock analysis hooks
vi.mock('../hooks/useAnalysisProgress', () => ({
  useAnalysisProgress: () => ({
    overallProgress: null,
    steps: [],
    hasFailedStages: false,
    failedStagesCount: 0,
    analysisMetadata: { title: 'Test Analysis', url: 'https://example.com' },
  }),
}))

vi.mock('../hooks/useAnalysisStatus', () => ({
  useAnalysisStatus: () => ({
    shouldConnect: false,
    statusLoading: false,
    resolvedStatus: 'completed',
  }),
}))

// Mock the SSE store
const mockUseSSEStore = vi.mocked(useSSEStore)

// Mock React Router
vi.mock('react-router', async () => {
  const actual = await vi.importActual('react-router')
  return {
    ...actual,
    useParams: () => ({ id: 'test-analysis-id' }),
    useSearch: () => ({ completed: false }),
  }
})

// Mock analysis hooks to prevent complex setup
vi.mock('../hooks/useAnalysisProgress', () => ({
  useAnalysisProgress: () => ({
    overallProgress: null,
    steps: [],
    hasFailedStages: false,
    failedStagesCount: 0,
    analysisMetadata: { title: 'Test Analysis', url: 'https://example.com' },
  }),
}))

vi.mock('../hooks/useAnalysisStatus', () => ({
  useAnalysisStatus: () => ({
    shouldConnect: false,
    statusLoading: false,
    resolvedStatus: 'completed',
  }),
}))

describe('AnalyzeResult Loading States Integration', () => {
  let mockStoreState: Record<string, unknown>

  beforeEach(() => {
    mockStoreState = {
      events: [],
      latestEvent: null,
      error: null,
      isConnected: false,
      isComplete: false,
      activeAnalysisId: null,
      connectionStartTime: null,
      lastActivityTime: null,
      loadingState: { type: 'disconnected' } as LoadingState,
      connectionMessage: 'Disconnected',
      showTimeoutWarning: false,
      analysisPhase: null,
      shouldShowProgress: false,
      connect: vi.fn(),
      disconnect: vi.fn(),
      reset: vi.fn(),
    }

    mockUseSSEStore.mockImplementation((selector) => {
      if (typeof selector === 'function') {
        return selector(mockStoreState)
      }
      return mockStoreState[selector as keyof typeof mockStoreState]
    })
  })

  afterEach(() => {
    vi.clearAllMocks()
  })

  describe('Waiting for Events State', () => {
    it('shows LoadingStateDisplay with contextual waiting message', () => {
      mockStoreState.loadingState = {
        type: 'waiting_for_events',
        connectedAt: Date.now(),
      } as LoadingState

      render(<AnalyzeResult />)

      expect(screen.getByText('Preparing analysis...')).toBeInTheDocument()
      expect(screen.getByText('Setting up your content analysis')).toBeInTheDocument()
    })

    it('shows TimeoutWarningBanner when timeout warning is active', () => {
      mockStoreState.loadingState = {
        type: 'waiting_for_events',
        connectedAt: Date.now(),
      } as LoadingState
      mockStoreState.showTimeoutWarning = true

      render(<AnalyzeResult />)

      expect(screen.getByText(/This analysis is taking longer than expected/)).toBeInTheDocument()
      expect(screen.getByText(/Please continue waiting/)).toBeInTheDocument()
    })

    it('does not show timeout warning when dismissed', () => {
      mockStoreState.loadingState = {
        type: 'waiting_for_events',
        connectedAt: Date.now(),
      } as LoadingState
      mockStoreState.showTimeoutWarning = true

      const { _rerender } = render(<AnalyzeResult />)

      // Click dismiss button
      const dismissButton = screen.getByRole('button', { name: /dismiss timeout warning/i })
      dismissButton.click()

      // Timeout warning should still be in state but component should not show it
      expect(screen.queryByText(/taking longer than expected/)).not.toBeInTheDocument()
    })
  })

  describe('Extracting State', () => {
    it('shows LoadingStateDisplay with word count', () => {
      mockStoreState.loadingState = {
        type: 'extracting',
        stage: 'extraction',
        status: 'running',
        wordCount: 1234,
      } as LoadingState

      render(<AnalyzeResult />)

      expect(screen.getByText('Extracting content...')).toBeInTheDocument()
      expect(screen.getByText('Processing 1,234 words')).toBeInTheDocument()
    })

    it('shows LoadingStateDisplay without word count', () => {
      mockStoreState.loadingState = {
        type: 'extracting',
        stage: 'extraction',
        status: 'running',
      } as LoadingState

      render(<AnalyzeResult />)

      expect(screen.getByText('Extracting content...')).toBeInTheDocument()
      expect(screen.getByText('Reading and analyzing your content')).toBeInTheDocument()
    })

    it('shows progress when shouldShowProgress is true', () => {
      mockStoreState.loadingState = {
        type: 'extracting',
        stage: 'extraction',
        status: 'running',
      } as LoadingState
      mockStoreState.shouldShowProgress = true

      render(<AnalyzeResult />)

      expect(screen.getByText('Analysis Progress')).toBeInTheDocument()
    })
  })

  describe('Analyzing State', () => {
    it('shows LoadingStateDisplay with progress percentage', () => {
      mockStoreState.loadingState = {
        type: 'analyzing',
        stage: 'tech_comparison',
        status: 'running',
        progress: 75,
      } as LoadingState

      render(<AnalyzeResult />)

      expect(screen.getByText('Analyzing content...')).toBeInTheDocument()
      expect(screen.getByText('Running AI analysis (75%)')).toBeInTheDocument()
    })

    it('shows progress tracker during analysis', () => {
      mockStoreState.loadingState = {
        type: 'analyzing',
        stage: 'tech_comparison',
        status: 'running',
        progress: 50,
      } as LoadingState
      mockStoreState.shouldShowProgress = true

      render(<AnalyzeResult />)

      expect(screen.getByText('Analysis Progress')).toBeInTheDocument()
    })
  })

  describe('Generating State', () => {
    it('shows LoadingStateDisplay for artifact generation', () => {
      mockStoreState.loadingState = {
        type: 'generating',
        stage: 'artifact_generation',
        status: 'running',
      } as LoadingState

      render(<AnalyzeResult />)

      expect(screen.getByText('Generating report...')).toBeInTheDocument()
      expect(screen.getByText('Compiling your analysis results')).toBeInTheDocument()
    })
  })

  describe('Complete State', () => {
    it('shows complete message', () => {
      mockStoreState.loadingState = {
        type: 'complete',
        artifactId: 'test-artifact-id',
      } as LoadingState

      render(<AnalyzeResult />)

      expect(screen.getByText('Analysis complete')).toBeInTheDocument()
      expect(screen.getByText('Your results are ready to view')).toBeInTheDocument()
    })
  })

  describe('Error State', () => {
    it('shows error message with details', () => {
      mockStoreState.loadingState = {
        type: 'error',
        error: 'Analysis failed due to network timeout',
      } as LoadingState

      render(<AnalyzeResult />)

      expect(screen.getByText('Analysis failed')).toBeInTheDocument()
      expect(screen.getByText('Analysis failed due to network timeout')).toBeInTheDocument()
    })
  })

  describe('Progress Visibility', () => {
    it('hides progress when shouldShowProgress is false', () => {
      mockStoreState.loadingState = {
        type: 'waiting_for_events',
        connectedAt: Date.now(),
      } as LoadingState
      mockStoreState.shouldShowProgress = false

      render(<AnalyzeResult />)

      expect(screen.queryByText('Analysis Progress')).not.toBeInTheDocument()
    })

    it('shows progress when shouldShowProgress is true', () => {
      mockStoreState.loadingState = {
        type: 'analyzing',
        stage: 'tech_comparison',
        status: 'running',
        progress: 50,
      } as LoadingState
      mockStoreState.shouldShowProgress = true

      render(<AnalyzeResult />)

      expect(screen.getByText('Analysis Progress')).toBeInTheDocument()
    })
  })

  describe('Component Composition', () => {
    it('renders AnalysisHeader in all loading states', () => {
      mockStoreState.loadingState = {
        type: 'waiting_for_events',
        connectedAt: Date.now(),
      } as LoadingState

      render(<AnalyzeResult />)

      expect(screen.getByText('Test Analysis')).toBeInTheDocument()
    })

    it('includes accessibility features', () => {
      mockStoreState.loadingState = {
        type: 'waiting_for_events',
        connectedAt: Date.now(),
      } as LoadingState

      render(<AnalyzeResult />)

      // Should have proper ARIA live region for screen readers
      const liveRegion = screen.getByRole('status', { hidden: true })
      expect(liveRegion).toBeInTheDocument()
    })
  })
})
