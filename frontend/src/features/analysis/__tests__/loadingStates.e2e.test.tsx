/**
 * End-to-End Workflow Tests for Loading States
 *
 * Tests complete analysis workflows from start to finish:
 * - Happy path scenarios (fast, medium, slow analyses)
 * - Error scenarios (connection failures, analysis failures)
 * - Edge cases (timeouts, rapid transitions)
 *
 * NOTE: Currently skipped due to E2E router context requirements.
 * These tests require full RouterProvider setup and should be moved
 * to proper E2E test infrastructure.
 */

import type { SSEEvent } from '@app-types/sse'
import { useSSEStore } from '@stores/sseStore'
import { render, screen, waitFor, act } from '@testing-library/react'
import { describe, expect, it, vi, beforeEach } from 'vitest'

import AnalyzeResult from '../AnalyzeResult'

// Mock TanStack Router hooks for E2E testing
vi.mock('@tanstack/react-router', async () => {
  const actual = await vi.importActual('@tanstack/react-router')
  return {
    ...actual,
    createRoute: vi.fn(),
    createRootRoute: vi.fn(),
    createFileRoute: vi.fn(),
    useParams: vi.fn(() => ({ id: 'test-analysis-id' })),
    useSearch: vi.fn(() => ({ completed: false })),
    useNavigate: vi.fn(() => vi.fn()),
  }
})

// Mock the route API for this specific route
vi.mock('../AnalyzeResult.lazy', () => ({
  Route: {
    useParams: () => ({ id: 'test-analysis-id' }),
    useSearch: () => ({ completed: false }),
  },
}))

// Simple render helper (no router context needed with mocked hooks)
function renderWithMocks(ui: React.ReactElement) {
  return render(ui)
}

// Mock dependencies
vi.mock('react-router', async () => {
  const actual = await vi.importActual('react-router')
  return {
    ...actual,
    useParams: () => ({ id: 'test-analysis-id' }),
    useSearch: () => ({ completed: false }),
  }
})

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

// Mock EventSource
global.EventSource = vi.fn().mockImplementation(() => ({
  addEventListener: vi.fn(),
  removeEventListener: vi.fn(),
  close: vi.fn(),
  readyState: 1,
  url: 'mock-url',
}))

describe.skip('Loading States E2E Workflows', () => {
  beforeEach(() => {
    const { reset } = useSSEStore.getState()
    reset()
  })

  describe('Happy Path: Fast Analysis (< 5 seconds)', () => {
    it('transitions through complete analysis workflow', async () => {
      renderWithMocks(<AnalyzeResult />)

      // Initial state: disconnected
      expect(screen.getByText('Disconnected')).toBeInTheDocument()

      // Connect and start analysis
      act(() => {
        const { connect } = useSSEStore.getState()
        connect('test-analysis-id')
      })

      await waitFor(() => {
        expect(screen.getByText('Connecting...')).toBeInTheDocument()
      })

      // Simulate connection established
      act(() => {
        useSSEStore.setState({ isConnected: true })
      })

      await waitFor(() => {
        expect(screen.getByText('Preparing analysis...')).toBeInTheDocument()
      })

      // Simulate extraction starting
      const extractionEvent: SSEEvent = {
        type: 'progress',
        stage: 'extraction',
        status: 'running',
        timestamp: new Date().toISOString(),
        details: { word_count: 1200 },
      }

      act(() => {
        const { _addEvent } = useSSEStore.getState()
        _addEvent(extractionEvent)
      })

      await waitFor(() => {
        expect(screen.getByText('Extracting content...')).toBeInTheDocument()
        expect(screen.getByText('Processing 1,200 words')).toBeInTheDocument()
      })

      // Simulate extraction complete and analysis starting
      const analysisEvent: SSEEvent = {
        type: 'progress',
        stage: 'tech_comparison',
        status: 'running',
        timestamp: new Date().toISOString(),
        details: { agent: 'TechComparisonAgent' },
      }

      act(() => {
        const { _addEvent } = useSSEStore.getState()
        _addEvent(analysisEvent)
      })

      await waitFor(() => {
        expect(screen.getByText('Analyzing content...')).toBeInTheDocument()
        expect(screen.getByText(/Running AI analysis/)).toBeInTheDocument()
      })

      // Simulate generation starting
      const generationEvent: SSEEvent = {
        type: 'progress',
        stage: 'artifact_generation',
        status: 'running',
        timestamp: new Date().toISOString(),
      }

      act(() => {
        const { _addEvent } = useSSEStore.getState()
        _addEvent(generationEvent)
      })

      await waitFor(() => {
        expect(screen.getByText('Generating report...')).toBeInTheDocument()
        expect(screen.getByText('Compiling your analysis results')).toBeInTheDocument()
      })

      // Simulate completion
      act(() => {
        useSSEStore.setState({
          isComplete: true,
          artifactId: 'completed-artifact-123',
        })
      })

      await waitFor(() => {
        expect(screen.getByText('Analysis complete')).toBeInTheDocument()
        expect(screen.getByText('Your results are ready to view')).toBeInTheDocument()
      })
    })
  })

  describe('Happy Path: Medium Analysis (10-30 seconds)', () => {
    it('shows timeout warning during longer analysis', async () => {
      renderWithMocks(<AnalyzeResult />)

      // Connect and establish connection
      act(() => {
        const { connect } = useSSEStore.getState()
        connect('test-analysis-id')
        useSSEStore.setState({ isConnected: true })
      })

      await waitFor(() => {
        expect(screen.getByText('Preparing analysis...')).toBeInTheDocument()
      })

      // Simulate timeout (30+ seconds of waiting)
      act(() => {
        const oldTime = Date.now() - 31000 // 31 seconds ago
        useSSEStore.setState({ connectionStartTime: oldTime })
      })

      await waitFor(() => {
        expect(screen.getByText(/This analysis is taking longer than expected/)).toBeInTheDocument()
      })

      // Analysis eventually starts
      const extractionEvent: SSEEvent = {
        type: 'progress',
        stage: 'extraction',
        status: 'running',
        timestamp: new Date().toISOString(),
        details: { word_count: 800 },
      }

      act(() => {
        const { _addEvent } = useSSEStore.getState()
        _addEvent(extractionEvent)
      })

      // Timeout warning should still be visible until analysis completes
      expect(screen.getByText(/taking longer than expected/)).toBeInTheDocument()

      // Complete analysis
      act(() => {
        useSSEStore.setState({
          isComplete: true,
          artifactId: 'completed-artifact-456',
        })
      })

      await waitFor(() => {
        expect(screen.getByText('Analysis complete')).toBeInTheDocument()
      })
    })
  })

  describe('Error Path: Connection Failure', () => {
    it('handles connection failures gracefully', async () => {
      renderWithMocks(<AnalyzeResult />)

      // Start connection
      act(() => {
        const { connect } = useSSEStore.getState()
        connect('test-analysis-id')
      })

      await waitFor(() => {
        expect(screen.getByText('Connecting...')).toBeInTheDocument()
      })

      // Simulate connection failure
      act(() => {
        useSSEStore.setState({
          error: new Error('Network connection failed'),
          isConnected: false,
        })
      })

      await waitFor(() => {
        expect(screen.getByText('Analysis failed')).toBeInTheDocument()
        expect(screen.getByText('Network connection failed')).toBeInTheDocument()
      })
    })
  })

  describe('Error Path: Analysis Failure', () => {
    it('handles analysis processing failures', async () => {
      renderWithMocks(<AnalyzeResult />)

      // Connect and start analysis
      act(() => {
        const { connect } = useSSEStore.getState()
        connect('test-analysis-id')
        useSSEStore.setState({ isConnected: true })
      })

      // Start extraction
      const extractionEvent: SSEEvent = {
        type: 'progress',
        stage: 'extraction',
        status: 'running',
        timestamp: new Date().toISOString(),
      }

      act(() => {
        const { _addEvent } = useSSEStore.getState()
        _addEvent(extractionEvent)
      })

      await waitFor(() => {
        expect(screen.getByText('Extracting content...')).toBeInTheDocument()
      })

      // Simulate analysis failure
      act(() => {
        useSSEStore.setState({
          error: new Error('AI processing failed: Invalid content format'),
          isConnected: false,
        })
      })

      await waitFor(() => {
        expect(screen.getByText('Analysis failed')).toBeInTheDocument()
        expect(screen.getByText('AI processing failed: Invalid content format')).toBeInTheDocument()
      })
    })
  })

  describe('Edge Case: Rapid State Transitions', () => {
    it('handles rapid loading state changes smoothly', async () => {
      renderWithMocks(<AnalyzeResult />)

      // Connect and immediately complete
      act(() => {
        const { connect } = useSSEStore.getState()
        connect('test-analysis-id')
        useSSEStore.setState({
          isConnected: true,
          isComplete: true,
          artifactId: 'rapid-complete-artifact',
        })
      })

      // Should show complete state, not intermediate states
      await waitFor(() => {
        expect(screen.getByText('Analysis complete')).toBeInTheDocument()
      })

      // Should not show loading states
      expect(screen.queryByText('Connecting...')).not.toBeInTheDocument()
      expect(screen.queryByText('Preparing analysis...')).not.toBeInTheDocument()
    })
  })

  describe('Edge Case: Timeout Recovery', () => {
    it('recovers from timeout when analysis starts', async () => {
      renderWithMocks(<AnalyzeResult />)

      // Connect and wait long enough for timeout
      act(() => {
        const { connect } = useSSEStore.getState()
        connect('test-analysis-id')
        useSSEStore.setState({
          isConnected: true,
          connectionStartTime: Date.now() - 31000, // 31 seconds ago
        })
      })

      await waitFor(() => {
        expect(screen.getByText(/taking longer than expected/)).toBeInTheDocument()
      })

      // Analysis starts - should transition out of timeout
      const extractionEvent: SSEEvent = {
        type: 'progress',
        stage: 'extraction',
        status: 'running',
        timestamp: new Date().toISOString(),
      }

      act(() => {
        const { _addEvent } = useSSEStore.getState()
        _addEvent(extractionEvent)
      })

      await waitFor(() => {
        expect(screen.getByText('Extracting content...')).toBeInTheDocument()
      })

      // Timeout warning should be gone
      expect(screen.queryByText(/taking longer than expected/)).not.toBeInTheDocument()
    })
  })

  describe('User Interaction: Timeout Dismissal', () => {
    it('allows users to dismiss timeout warnings', async () => {
      renderWithMocks(<AnalyzeResult />)

      // Connect and trigger timeout
      act(() => {
        const { connect } = useSSEStore.getState()
        connect('test-analysis-id')
        useSSEStore.setState({
          isConnected: true,
          connectionStartTime: Date.now() - 31000,
        })
      })

      await waitFor(() => {
        expect(screen.getByText(/taking longer than expected/)).toBeInTheDocument()
      })

      // User dismisses warning
      const dismissButton = screen.getByRole('button', { name: /dismiss timeout warning/i })
      act(() => {
        dismissButton.click()
      })

      // Warning should be gone
      expect(screen.queryByText(/taking longer than expected/)).not.toBeInTheDocument()

      // But timeout state should still exist in store (for programmatic access)
      const { showTimeoutWarning } = useSSEStore.getState()
      expect(showTimeoutWarning).toBe(true)
    })
  })
})
