/**
 * Analysis Flow E2E Tests
 *
 * Comprehensive end-to-end tests for the complete analysis workflow.
 * Tests the full user journey from URL submission to results display.
 *
 * Tagged with @e2e - only runs when E2E_READY=true
 */

import React from 'react'

import { screen, waitFor, fireEvent } from '@testing-library/react'
import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest'

import { e2eSetup } from '@/test-utils/e2e-setup'
import { renderWithProviders } from '@/test-utils/test-helpers'

import AnalyzeResult from '../AnalyzeResult'

// Mock TanStack Router for E2E tests
vi.mock('@tanstack/react-router', () => ({
  useRouter: () => ({
    navigate: vi.fn(),
    invalidate: vi.fn(),
  }),
  useParams: () => ({ id: 'test-analysis-id' }),
  useSearch: () => ({ completed: false }),
  useMatch: () => ({ pathname: '/analyze/test-analysis-id' }),
  createRouter: vi.fn(() => ({
    routesByPath: {},
    routeTree: {},
  })),
  RouterProvider: ({ children }: { children: React.ReactNode }) => children,
  getRouteApi: () => ({
    useParams: () => ({ id: 'test-analysis-id' }),
    useSearch: () => ({ completed: false }),
  }),
}))

// Mock Zustand stores
vi.mock('@stores/sseStore', () => ({
  useSSEStore: vi.fn(() => ({
    events: [],
    isConnected: false,
    isComplete: false,
    error: null,
    connect: vi.fn(),
    disconnect: vi.fn(),
    reset: vi.fn(),
  })),
  useLoadingState: vi.fn(() => 'waiting_for_events'),
  useShowTimeoutWarning: vi.fn(() => false),
  useShouldShowProgress: vi.fn(() => false),
}))

// Mock analysis hooks
vi.mock('../hooks/useAnalysisProgress', () => ({
  useAnalysisProgress: vi.fn(() => ({
    overallProgress: { stage: 'waiting', progress: 0 },
    steps: [],
    activities: [],
    hasError: false,
    errorMessage: null,
    artifactId: null,
    hasFailedStages: false,
    failedStagesCount: 0,
    analysisMetadata: { title: 'Test Analysis', url: 'https://example.com' },
  })),
}))

vi.mock('../hooks/useAnalysisStatus', () => ({
  useAnalysisStatus: vi.fn(() => ({
    resolvedStatus: undefined,
    resolvedArtifactId: undefined,
    shouldConnect: false,
    loading: false,
    statusError: null,
    refetch: vi.fn(),
  })),
}))

// Only load and run when E2E_READY=true
const conditionalDescribe = process.env.E2E_READY === 'true' ? describe : describe.skip

conditionalDescribe('Analysis Flow Component @component-e2e @critical', () => {
  beforeEach(() => {
    e2eSetup.setup()
  })

  afterEach(() => {
    e2eSetup.teardown()
  })

  describe('Happy Path: Complete Analysis Workflow', () => {
    it('completes full analysis from URL submission to results', async () => {
      // Given: User navigates to analysis page
      renderWithProviders(<AnalyzeResult />)

      // When: User enters a URL and submits
      const urlInput = screen.getByLabelText(/url/i)
      const submitButton = screen.getByRole('button', { name: /analyze/i })

      fireEvent.change(urlInput, {
        target: { value: 'https://example.com/article' },
      })
      fireEvent.click(submitButton)

      // Then: Loading states are displayed
      await waitFor(() => {
        expect(screen.getByText(/connecting/i)).toBeInTheDocument()
      })

      // Simulate analysis starting
      e2eSetup.analysis.start('https://example.com/article')

      await waitFor(() => {
        expect(screen.getByText(/preparing analysis/i)).toBeInTheDocument()
      })

      // Simulate progress through stages
      e2eSetup.analysis.progress(25)
      await waitFor(() => {
        expect(screen.getByText(/extracting content/i)).toBeInTheDocument()
      })

      e2eSetup.analysis.progress(50)
      await waitFor(() => {
        expect(screen.getByText(/analyzing content/i)).toBeInTheDocument()
      })

      e2eSetup.analysis.progress(75)
      await waitFor(() => {
        expect(screen.getByText(/generating report/i)).toBeInTheDocument()
      })

      // Complete the analysis
      e2eSetup.analysis.complete()

      // Then: Results are displayed
      await waitFor(() => {
        expect(screen.getByText(/analysis complete/i)).toBeInTheDocument()
        expect(screen.getByText(/your results are ready/i)).toBeInTheDocument()
      })

      // And: User can view detailed results
      const resultsButton = screen.getByRole('button', { name: /view results/i })
      expect(resultsButton).toBeInTheDocument()
    })

    it('handles analysis timeout gracefully', async () => {
      // Given: Slow analysis that times out
      renderWithProviders(<AnalyzeResult />)

      // When: User submits URL
      const urlInput = screen.getByLabelText(/url/i)
      const submitButton = screen.getByRole('button', { name: /analyze/i })

      fireEvent.change(urlInput, {
        target: { value: 'https://example.com/slow-article' },
      })
      fireEvent.click(submitButton)

      // And: Analysis takes longer than timeout threshold
      e2eSetup.analysis.start('https://example.com/slow-article')

      // Fast-forward time to trigger timeout warning
      vi.useFakeTimers()
      vi.advanceTimersByTime(35 * 1000) // 35 seconds

      // Then: Timeout warning is displayed
      await waitFor(() => {
        expect(screen.getByText(/taking longer than expected/i)).toBeInTheDocument()
      })

      // And: User can dismiss the warning
      const dismissButton = screen.getByRole('button', { name: /dismiss/i })
      fireEvent.click(dismissButton)

      // Then: Warning is hidden
      expect(screen.queryByText(/taking longer than expected/i)).not.toBeInTheDocument()

      vi.useRealTimers()
    })
  })

  describe('Error Scenarios', () => {
    it('handles network connectivity issues', async () => {
      // Given: Network issues
      e2eSetup.simulateNetwork.offline()

      renderWithProviders(<AnalyzeResult />)

      // When: User attempts to submit URL
      const urlInput = screen.getByLabelText(/url/i)
      const submitButton = screen.getByRole('button', { name: /analyze/i })

      fireEvent.change(urlInput, {
        target: { value: 'https://example.com/article' },
      })
      fireEvent.click(submitButton)

      // Then: Network error is displayed
      await waitFor(() => {
        expect(screen.getByText(/network offline/i)).toBeInTheDocument()
        expect(screen.getByText(/analysis failed/i)).toBeInTheDocument()
      })
    })

    it('handles invalid URLs gracefully', async () => {
      renderWithProviders(<AnalyzeResult />)

      // When: User submits invalid URL
      const urlInput = screen.getByLabelText(/url/i)
      const submitButton = screen.getByRole('button', { name: /analyze/i })

      fireEvent.change(urlInput, {
        target: { value: 'not-a-valid-url' },
      })
      fireEvent.click(submitButton)

      // Then: Validation error is shown
      await waitFor(() => {
        expect(screen.getByText(/invalid url/i)).toBeInTheDocument()
      })

      // And: Submit button is disabled
      expect(submitButton).toBeDisabled()
    })

    it('handles analysis processing failures', async () => {
      renderWithProviders(<AnalyzeResult />)

      // When: Analysis starts but fails
      const urlInput = screen.getByLabelText(/url/i)
      const submitButton = screen.getByRole('button', { name: /analyze/i })

      fireEvent.change(urlInput, {
        target: { value: 'https://example.com/failing-article' },
      })
      fireEvent.click(submitButton)

      e2eSetup.analysis.start('https://example.com/failing-article')
      e2eSetup.analysis.fail('Content analysis failed: Unable to process document')

      // Then: Error state is displayed
      await waitFor(() => {
        expect(screen.getByText(/analysis failed/i)).toBeInTheDocument()
        expect(screen.getByText(/unable to process document/i)).toBeInTheDocument()
      })

      // And: Retry option is available
      const retryButton = screen.getByRole('button', { name: /retry/i })
      expect(retryButton).toBeInTheDocument()
    })
  })

  describe('User Experience Enhancements', () => {
    it('provides real-time progress updates', async () => {
      renderWithProviders(<AnalyzeResult />)

      // Given: User submits URL
      const urlInput = screen.getByLabelText(/url/i)
      const submitButton = screen.getByRole('button', { name: /analyze/i })

      fireEvent.change(urlInput, {
        target: { value: 'https://example.com/article' },
      })
      fireEvent.click(submitButton)

      e2eSetup.analysis.start('https://example.com/article')

      // When: Analysis progresses
      e2eSetup.analysis.progress(10)
      await waitFor(() => {
        expect(screen.getByText(/10%/i)).toBeInTheDocument()
      })

      e2eSetup.analysis.progress(50)
      await waitFor(() => {
        expect(screen.getByText(/50%/i)).toBeInTheDocument()
      })

      // Then: Progress is accurately reflected
      const progressBar = screen.getByRole('progressbar')
      expect(progressBar).toHaveAttribute('aria-valuenow', '50')
    })

    it('maintains accessibility throughout workflow', async () => {
      renderWithProviders(<AnalyzeResult />)

      // Given: User submits URL
      const urlInput = screen.getByLabelText(/url/i)
      const submitButton = screen.getByRole('button', { name: /analyze/i })

      // Then: All elements are properly labeled
      expect(urlInput).toHaveAccessibleName()
      expect(submitButton).toHaveAccessibleName()

      fireEvent.change(urlInput, {
        target: { value: 'https://example.com/article' },
      })
      fireEvent.click(submitButton)

      // And: Status announcements are provided
      await waitFor(() => {
        const statusRegion = screen.getByRole('status')
        expect(statusRegion).toHaveTextContent(/connecting/i)
      })
    })

    it('supports keyboard navigation', async () => {
      renderWithProviders(<AnalyzeResult />)

      // Given: User navigates with keyboard
      const urlInput = screen.getByLabelText(/url/i)

      // When: User tabs through interface
      urlInput.focus()
      expect(document.activeElement).toBe(urlInput)

      // And: Presses Tab to next element
      fireEvent.keyDown(urlInput, { key: 'Tab' })

      // Then: Focus moves appropriately
      const submitButton = screen.getByRole('button', { name: /analyze/i })
      expect(document.activeElement).toBe(submitButton)
    })
  })

  describe('Performance & Reliability', () => {
    it('completes analysis within performance budget @slow', async () => {
      const startTime = performance.now()

      renderWithProviders(<AnalyzeResult />)

      // Complete analysis workflow
      const urlInput = screen.getByLabelText(/url/i)
      const submitButton = screen.getByRole('button', { name: /analyze/i })

      fireEvent.change(urlInput, {
        target: { value: 'https://example.com/article' },
      })
      fireEvent.click(submitButton)

      e2eSetup.analysis.start('https://example.com/article')
      e2eSetup.analysis.progress(100)
      e2eSetup.analysis.complete()

      await waitFor(() => {
        expect(screen.getByText(/analysis complete/i)).toBeInTheDocument()
      })

      const endTime = performance.now()
      const duration = endTime - startTime

      // Assert performance budget (30 seconds for E2E)
      expect(duration).toBeLessThan(30000)
    })

    it('handles concurrent analysis requests', async () => {
      // Test multiple simultaneous analyses
      const analyses = ['url1', 'url2', 'url3'].map((url) => e2eSetup.analysis.start(url))

      // Verify all analyses are tracked independently
      expect(analyses).toHaveLength(3)
      analyses.forEach((analysis) => {
        expect(analysis.id).toBeDefined()
        expect(analysis.status).toBe('processing')
      })
    })
  })
})
