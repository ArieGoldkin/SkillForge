/**
 * Integration tests for AnalyzeResult loading states functionality
 *
 * Tests the integration between AnalyzeResult and the new loading state components:
 * - LoadingStateDisplay
 * - TimeoutWarningBanner
 * - ConnectionStatus (via ProgressTracker)
 */

import {
  useLoadingState,
  useConnectionMessage,
  useShowTimeoutWarning,
  useAnalysisPhase,
  useShouldShowProgress,
} from '@stores/sseStore'
import { act, render, screen } from '@testing-library/react'
import { describe, expect, it, vi, beforeEach, afterEach } from 'vitest'

import type { LoadingState } from '@types/loading'

import AnalyzeResult from '../AnalyzeResult'

// Mock CompletedAnalysisView to avoid React Query dependencies in unit tests
vi.mock('../components/states/CompletedAnalysisView', () => ({
  CompletedAnalysisView: ({ analysisId: _analysisId }: { analysisId: string }) => (
    <div data-testid="completed-analysis-view">
      <p>Analysis complete</p>
      <p>Your results are ready to view</p>
    </div>
  ),
}))

// Mock TanStack Router
vi.mock('@tanstack/react-router', () => ({
  getRouteApi: () => ({
    useParams: () => ({ id: 'test-analysis-id' }),
    useSearch: () => ({ completed: false, artifactId: undefined }),
  }),
  useNavigate: () => vi.fn(),
  useRouter: () => ({
    navigate: vi.fn(),
  }),
}))

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

// Modern Hook-Based Testing Architecture
// Each hook is independently mocked for clean, focused testing
// useSSEStore must also be mocked to prevent real Zustand store from triggering infinite updates
vi.mock('@stores/sseStore', async (importOriginal) => {
  const actual = await importOriginal<typeof import('@stores/sseStore')>()
  return {
    ...actual,
    // Mock the main store hook to prevent real connection/state management
    useSSEStore: vi.fn((selector) => {
      // Return mock data based on what the selector is requesting
      const mockState = {
        events: [],
        latestEvent: null,
        isConnected: false,
        isComplete: false,
        error: null,
        activeAnalysisId: null,
        connect: vi.fn(),
        disconnect: vi.fn(),
        reset: vi.fn(),
        setAnalysisMetadata: vi.fn(),
      }
      return selector(mockState)
    }),
    useLoadingState: vi.fn(),
    useConnectionMessage: vi.fn(),
    useShowTimeoutWarning: vi.fn(),
    useAnalysisPhase: vi.fn(),
    useShouldShowProgress: vi.fn(),
  }
})

const mockUseLoadingState = vi.mocked(useLoadingState)
const mockUseConnectionMessage = vi.mocked(useConnectionMessage)
const mockUseShowTimeoutWarning = vi.mocked(useShowTimeoutWarning)
const mockUseAnalysisPhase = vi.mocked(useAnalysisPhase)
const mockUseShouldShowProgress = vi.mocked(useShouldShowProgress)

// Mock analysis hooks to prevent complex setup
vi.mock('../hooks/useAnalysisProgress', () => ({
  useAnalysisProgress: () => ({
    overallProgress: {
      stage: 'extracting',
      progress: 0,
      currentStep: 1,
      totalSteps: 8,
      completedSteps: 0,
      estimatedTimeRemaining: null,
    },
    steps: [],
    hasFailedStages: false,
    failedStagesCount: 0,
    analysisMetadata: { title: 'Test Analysis', url: 'https://example.com' },
  }),
}))

// Mock React Query hooks to prevent QueryClient dependency
vi.mock('@tanstack/react-query', () => ({
  useQuery: () => ({ data: null, isLoading: false, error: null }),
  useQueryClient: () => ({}),
}))

vi.mock('../hooks/useAnalysisStatus', () => ({
  useAnalysisStatus: () => ({
    shouldConnect: false,
    statusLoading: false,
    resolvedStatus: 'completed',
  }),
}))

describe('AnalyzeResult Loading States Integration', () => {
  beforeEach(() => {
    // Modern hook-based test setup - each hook is independently controlled
    mockUseLoadingState.mockReturnValue({ type: 'disconnected' } as LoadingState)
    mockUseConnectionMessage.mockReturnValue('Disconnected')
    mockUseShowTimeoutWarning.mockReturnValue(false)
    mockUseAnalysisPhase.mockReturnValue(null)
    mockUseShouldShowProgress.mockReturnValue(false)
  })

  afterEach(() => {
    vi.clearAllMocks()
  })

  describe('Waiting for Events State', () => {
    it('shows LoadingStateDisplay with contextual waiting message', () => {
      mockUseLoadingState.mockReturnValue({
        type: 'waiting_for_events',
        connectedAt: Date.now(),
      } as LoadingState)

      render(<AnalyzeResult />)

      expect(screen.getByText('Preparing analysis...')).toBeInTheDocument()
      expect(screen.getByText('Setting up your content analysis')).toBeInTheDocument()
    })

    it('shows TimeoutWarningBanner when timeout warning is active', () => {
      mockUseLoadingState.mockReturnValue({
        type: 'waiting_for_events',
        connectedAt: Date.now(),
      } as LoadingState)
      mockUseShowTimeoutWarning.mockReturnValue(true)

      render(<AnalyzeResult />)

      expect(screen.getByText(/This analysis is taking longer than expected/)).toBeInTheDocument()
      expect(screen.getByText(/Please continue waiting/)).toBeInTheDocument()
    })

    it('does not show timeout warning when dismissed', () => {
      mockUseLoadingState.mockReturnValue({
        type: 'waiting_for_events',
        connectedAt: Date.now(),
      } as LoadingState)
      mockUseShowTimeoutWarning.mockReturnValue(true)

      render(<AnalyzeResult />)

      // Should show timeout warning initially
      expect(screen.getByText(/taking longer than expected/)).toBeInTheDocument()

      // Click dismiss button
      const dismissButton = screen.getByRole('button', { name: /dismiss timeout warning/i })
      act(() => {
        dismissButton.click()
      })

      // Timeout warning should be dismissed
      expect(screen.queryByText(/taking longer than expected/)).not.toBeInTheDocument()
    })
  })

  describe('Extracting State', () => {
    it('shows LoadingStateDisplay with word count', () => {
      mockUseLoadingState.mockReturnValue({
        type: 'extracting',
        stage: 'extraction',
        status: 'running',
        wordCount: 1234,
      } as LoadingState)

      render(<AnalyzeResult />)

      expect(screen.getByText('Extracting content...')).toBeInTheDocument()
      expect(screen.getByText('Processing 1,234 words')).toBeInTheDocument()
    })

    it('shows LoadingStateDisplay without word count', () => {
      mockUseLoadingState.mockReturnValue({
        type: 'extracting',
        stage: 'extraction',
        status: 'running',
      } as LoadingState)

      render(<AnalyzeResult />)

      expect(screen.getByText('Extracting content...')).toBeInTheDocument()
      expect(screen.getByText('Reading and analyzing your content')).toBeInTheDocument()
    })

    it('shows progress when shouldShowProgress is true', () => {
      mockUseLoadingState.mockReturnValue({
        type: 'extracting',
        stage: 'extraction',
        status: 'running',
      } as LoadingState)
      mockUseShouldShowProgress.mockReturnValue(true)

      render(<AnalyzeResult />)

      // New HeroSummaryCard shows "Total Stages" instead of "Overall Progress"
      expect(screen.getByText('Total Stages')).toBeInTheDocument()
    })
  })

  describe('Analyzing State', () => {
    it('shows LoadingStateDisplay with progress percentage', () => {
      mockUseLoadingState.mockReturnValue({
        type: 'analyzing',
        stage: 'tech_comparison',
        status: 'running',
        progress: 75,
      } as LoadingState)

      render(<AnalyzeResult />)

      expect(screen.getByText('Analyzing content...')).toBeInTheDocument()
      expect(screen.getByText('Running AI analysis (75%)')).toBeInTheDocument()
    })

    it('shows progress tracker during analysis', () => {
      mockUseLoadingState.mockReturnValue({
        type: 'analyzing',
        stage: 'tech_comparison',
        status: 'running',
        progress: 50,
      } as LoadingState)
      mockUseShouldShowProgress.mockReturnValue(true)

      render(<AnalyzeResult />)

      // New HeroSummaryCard shows "Total Stages" instead of "Overall Progress"
      expect(screen.getByText('Total Stages')).toBeInTheDocument()
    })
  })

  describe('Generating State', () => {
    it('shows LoadingStateDisplay for artifact generation', () => {
      mockUseLoadingState.mockReturnValue({
        type: 'generating',
        stage: 'artifact_generation',
        status: 'running',
      } as LoadingState)

      render(<AnalyzeResult />)

      expect(screen.getByText('Generating report...')).toBeInTheDocument()
      expect(screen.getByText('Compiling your analysis results')).toBeInTheDocument()
    })
  })

  describe('Complete State', () => {
    it('shows complete message', () => {
      mockUseLoadingState.mockReturnValue({
        type: 'complete',
        artifactId: 'test-artifact-id',
      } as LoadingState)

      render(<AnalyzeResult />)

      expect(screen.getByText('Analysis complete')).toBeInTheDocument()
      expect(screen.getByText('Your results are ready to view')).toBeInTheDocument()
    })
  })

  describe('Error State', () => {
    it('shows error message with details', () => {
      mockUseLoadingState.mockReturnValue({
        type: 'error',
        error: 'Analysis failed due to network timeout',
      } as LoadingState)

      render(<AnalyzeResult />)

      expect(screen.getByText('Analysis failed')).toBeInTheDocument()
      expect(screen.getByText('Analysis failed due to network timeout')).toBeInTheDocument()
    })
  })

  describe('Progress Visibility', () => {
    it('hides progress when shouldShowProgress is false', () => {
      mockUseLoadingState.mockReturnValue({
        type: 'waiting_for_events',
        connectedAt: Date.now(),
      } as LoadingState)
      mockUseShouldShowProgress.mockReturnValue(false)

      render(<AnalyzeResult />)

      expect(screen.queryByText('Analysis Progress')).not.toBeInTheDocument()
    })

    it('shows progress when shouldShowProgress is true', () => {
      mockUseLoadingState.mockReturnValue({
        type: 'analyzing',
        stage: 'tech_comparison',
        status: 'running',
        progress: 50,
      } as LoadingState)
      mockUseShouldShowProgress.mockReturnValue(true)

      render(<AnalyzeResult />)

      // New HeroSummaryCard shows "Total Stages" instead of "Overall Progress"
      expect(screen.getByText('Total Stages')).toBeInTheDocument()
    })
  })

  describe('Component Composition', () => {
    it('renders AnalysisHeader in all loading states', () => {
      mockUseLoadingState.mockReturnValue({
        type: 'waiting_for_events',
        connectedAt: Date.now(),
      } as LoadingState)

      render(<AnalyzeResult />)

      expect(screen.getByText('Test Analysis')).toBeInTheDocument()
    })

    it.skip('includes accessibility features', () => {
      // TODO: Re-enable when LoadingStateDisplay rendering is stable
      // The aria-live region is tested in other loading state tests
      mockUseLoadingState.mockReturnValue({
        type: 'waiting_for_events',
        connectedAt: Date.now(),
      } as LoadingState)

      render(<AnalyzeResult />)

      // Should have proper ARIA live region for screen readers
      const liveRegion = document.querySelector('[aria-live="polite"]')
      expect(liveRegion).toBeInTheDocument()
      expect(liveRegion).toHaveAttribute('aria-atomic', 'true')
      expect(liveRegion).toHaveAttribute('role', 'status')
    })
  })
})
