/**
 * AnalyzeResult Fatal Error State Tests
 *
 * Tests for the fatal error detection and UI rendering behavior.
 * Bug fix: Fatal error state now properly hides progress UI when:
 * - There's an error (from SSE, status, or prop)
 * - No events have been received (events.length === 0)
 * - SSE is disconnected (!isConnected)
 *
 * Previously, the error alert was shown but progress UI was still visible below it.
 */

import type { SSEEvent, SSEProgressEvent } from '@app-types/sse'
import { useSSEStore } from '@stores/sseStore'
import {
  RouterProvider,
  createMemoryHistory,
  createRootRoute,
  createRoute,
  createRouter,
} from '@tanstack/react-router'
import { render, screen, waitFor } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import AnalyzeResult from '../AnalyzeResult'
import * as useAnalysisStatusModule from '../hooks/useAnalysisStatus'

// Valid UUID for testing
const TEST_ANALYSIS_ID = '123e4567-e89b-12d3-a456-426614174000'

/**
 * Mock EventSource for SSE tests
 */
class MockEventSource {
  url: string
  onopen: (() => void) | null = null
  onerror: ((err: Event) => void) | null = null
  listeners: Map<string, (event: MessageEvent) => void> = new Map()
  readyState = 0

  constructor(url: string) {
    this.url = url
    setTimeout(() => {
      this.readyState = 1
      this.onopen?.()
    }, 0)
  }

  addEventListener(type: string, listener: (event: MessageEvent) => void) {
    this.listeners.set(type, listener)
  }

  removeEventListener(type: string) {
    this.listeners.delete(type)
  }

  close() {
    this.readyState = 2
    this.listeners.clear()
  }
}

/**
 * Mock modules
 */
vi.mock('../hooks/useAnalysisStatus')
vi.mock('@services/api.service', () => ({
  analyzeAPI: {
    getAnalysisStatus: vi.fn(),
  },
}))

// Mock child components to isolate fatal error logic
vi.mock('../components', () => ({
  AnalysisHeader: ({ title, url }: { title: string; url: string }) => (
    <div data-testid="analysis-header">
      {title} - {url}
    </div>
  ),
  ErrorAlert: ({ message }: { message: string }) => (
    <div data-testid="error-alert" role="alert">
      {message}
    </div>
  ),
  LoadingState: () => <div data-testid="loading-state">Loading...</div>,
  ProgressColumn: () => <div data-testid="progress-column">Progress Column</div>,
  ActivityColumn: () => <div data-testid="activity-column">Activity Column</div>,
  AnalysisCompleteCard: () => <div data-testid="complete-card">Complete Card</div>,
}))

vi.mock('../components/states/CompletedAnalysisView', () => ({
  CompletedAnalysisView: () => <div data-testid="completed-view">Completed Analysis View</div>,
}))

/**
 * Router setup for testing
 */
const rootRoute = createRootRoute()
const analyzeRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: '/analyze/$id',
  component: AnalyzeResult,
})

const routeTree = rootRoute.addChildren([analyzeRoute])

function createTestRouter(initialPath: string, search?: Record<string, unknown>) {
  // Build search params string
  const searchString = search
    ? '?' +
      new URLSearchParams(Object.entries(search).map(([key, val]) => [key, String(val)])).toString()
    : ''

  const memoryHistory = createMemoryHistory({
    initialEntries: [initialPath + searchString],
  })
  return createRouter({
    routeTree,
    history: memoryHistory,
  })
}

function renderWithRouter(router: ReturnType<typeof createTestRouter>) {
  return render(<RouterProvider router={router} />)
}

/**
 * Helper to setup useAnalysisStatus mock
 */
function mockAnalysisStatus(
  overrides?: Partial<ReturnType<typeof useAnalysisStatusModule.useAnalysisStatus>>
) {
  const defaultReturn: ReturnType<typeof useAnalysisStatusModule.useAnalysisStatus> = {
    resolvedStatus: undefined,
    resolvedArtifactId: undefined,
    shouldConnect: true,
    loading: false,
    statusError: undefined,
    refetch: vi.fn().mockResolvedValue(undefined),
  }

  vi.mocked(useAnalysisStatusModule.useAnalysisStatus).mockReturnValue({
    ...defaultReturn,
    ...overrides,
  })
}

describe('AnalyzeResult - Fatal Error State', () => {
  beforeEach(() => {
    // Setup EventSource mock
    vi.stubGlobal('EventSource', MockEventSource)
    vi.stubEnv('VITE_API_URL', 'http://localhost:8000')

    // Reset SSE store before each test
    useSSEStore.getState().reset()
    vi.clearAllMocks()
  })

  afterEach(() => {
    vi.unstubAllGlobals()
    vi.unstubAllEnvs()
    vi.clearAllMocks()
  })

  describe('Fatal Error Detection', () => {
    it('shows fatal error when SSE error occurs with no events and disconnected', async () => {
      // Setup: SSE error, no events, disconnected
      useSSEStore.setState({
        error: new Error('Connection failed'),
        events: [],
        isConnected: false,
        isComplete: false,
        latestEvent: null,
        activeAnalysisId: TEST_ANALYSIS_ID,
      })

      mockAnalysisStatus({
        shouldConnect: false,
      })

      const router = createTestRouter('/analyze/test-123')
      renderWithRouter(router)

      // Should show error alert
      await waitFor(() => {
        expect(screen.getByTestId('error-alert')).toBeInTheDocument()
        expect(screen.getByText(/Connection failed/)).toBeInTheDocument()
      })

      // Should NOT show progress UI
      expect(screen.queryByTestId('progress-column')).not.toBeInTheDocument()
      expect(screen.queryByTestId('activity-column')).not.toBeInTheDocument()
    })

    it('shows fatal error when status error occurs with no events and disconnected', async () => {
      // Setup: status error, no events, disconnected
      // Need to have a resolved status to avoid "waiting for first event" state
      mockAnalysisStatus({
        statusError: 'Analysis not found',
        shouldConnect: false,
        resolvedStatus: 'failed', // Important: must have status to exit waiting state
      })

      // Pre-set disconnected state
      useSSEStore.setState({
        error: null,
        events: [],
        isConnected: false,
        isComplete: false,
        latestEvent: null,
        activeAnalysisId: null,
      })

      const router = createTestRouter('/analyze/test-123')
      renderWithRouter(router)

      // Should show error alert with status error
      await waitFor(() => {
        expect(screen.getByTestId('error-alert')).toBeInTheDocument()
        expect(screen.getByText('Analysis not found')).toBeInTheDocument()
      })

      // Should NOT show progress UI
      expect(screen.queryByTestId('progress-column')).not.toBeInTheDocument()
      expect(screen.queryByTestId('activity-column')).not.toBeInTheDocument()
    })

    it('shows fatal error when status is failed with no events and disconnected', async () => {
      // Setup: failed status, no events, disconnected
      useSSEStore.setState({
        error: null,
        events: [],
        isConnected: false,
        isComplete: false,
        latestEvent: null,
        activeAnalysisId: TEST_ANALYSIS_ID,
      })

      mockAnalysisStatus({
        resolvedStatus: 'failed',
        shouldConnect: false,
      })

      const router = createTestRouter('/analyze/test-123')
      renderWithRouter(router)

      // Should show error alert
      await waitFor(() => {
        expect(screen.getByTestId('error-alert')).toBeInTheDocument()
      })

      // Should NOT show progress UI
      expect(screen.queryByTestId('progress-column')).not.toBeInTheDocument()
      expect(screen.queryByTestId('activity-column')).not.toBeInTheDocument()
    })
  })

  describe('Non-Fatal Error States (Recoverable)', () => {
    it('shows progress UI when error exists but events have been received', async () => {
      // Setup: error, but has events (partial progress before error)
      const events: SSEEvent[] = [
        {
          type: 'progress',
          analysis_id: TEST_ANALYSIS_ID,
          stage: 'extraction',
          status: 'complete',
          timestamp: new Date().toISOString(),
        } as SSEProgressEvent,
      ]

      useSSEStore.setState({
        error: new Error('Downstream error'),
        events,
        isConnected: false,
        isComplete: false,
        latestEvent: events[0],
        activeAnalysisId: TEST_ANALYSIS_ID,
      })

      mockAnalysisStatus({
        shouldConnect: false,
      })

      const router = createTestRouter('/analyze/test-123')
      renderWithRouter(router)

      // Should show error alert
      await waitFor(() => {
        expect(screen.getByTestId('error-alert')).toBeInTheDocument()
      })

      // Should STILL show progress UI (non-fatal error)
      expect(screen.getByTestId('progress-column')).toBeInTheDocument()
      expect(screen.getByTestId('activity-column')).toBeInTheDocument()
    })

    it('shows progress UI when error exists but still connected (recoverable)', async () => {
      // Setup: error but connection is still active
      mockAnalysisStatus({
        shouldConnect: true,
      })

      const router = createTestRouter('/analyze/test-123')
      renderWithRouter(router)

      // Wait for connection to establish
      await waitFor(() => {
        expect(useSSEStore.getState().isConnected).toBe(true)
      })

      // Manually set error in store while connected
      useSSEStore.setState({
        error: new Error('Temporary error'),
        events: [],
        isConnected: true, // Still connected - can recover
      })

      // Should show error alert
      await waitFor(() => {
        expect(screen.getByTestId('error-alert')).toBeInTheDocument()
      })

      // Should STILL show progress UI (recoverable error)
      expect(screen.getByTestId('progress-column')).toBeInTheDocument()
      expect(screen.getByTestId('activity-column')).toBeInTheDocument()
    })

    it('shows progress UI when no events but connected and no error', async () => {
      // Setup: no events yet, but connected and no error (normal waiting state)
      mockAnalysisStatus({
        shouldConnect: true,
        loading: false,
        resolvedStatus: 'processing' as const,
      })

      const router = createTestRouter('/analyze/test-123')
      renderWithRouter(router)

      // Wait for connection to establish
      await waitFor(() => {
        expect(useSSEStore.getState().isConnected).toBe(true)
      })

      // Should show progress UI (waiting for first event)
      await waitFor(() => {
        expect(screen.getByTestId('progress-column')).toBeInTheDocument()
        expect(screen.getByTestId('activity-column')).toBeInTheDocument()
      })

      // Should NOT show error alert
      expect(screen.queryByTestId('error-alert')).not.toBeInTheDocument()
    })
  })

  describe('Normal Success States', () => {
    it('shows progress UI during normal processing', async () => {
      // Setup: normal processing with events
      const events: SSEEvent[] = [
        {
          type: 'progress',
          analysis_id: TEST_ANALYSIS_ID,
          stage: 'extraction',
          status: 'running',
          timestamp: new Date().toISOString(),
        } as SSEProgressEvent,
      ]

      mockAnalysisStatus({
        shouldConnect: true,
      })

      const router = createTestRouter('/analyze/test-123')
      renderWithRouter(router)

      // Wait for connection and set events
      await waitFor(() => {
        expect(useSSEStore.getState().isConnected).toBe(true)
      })

      useSSEStore.setState({
        events,
        latestEvent: events[0],
      })

      // Should show progress UI
      await waitFor(() => {
        expect(screen.getByTestId('progress-column')).toBeInTheDocument()
        expect(screen.getByTestId('activity-column')).toBeInTheDocument()
      })

      // Should NOT show error alert
      expect(screen.queryByTestId('error-alert')).not.toBeInTheDocument()
    })

    it('shows complete card when analysis completes', async () => {
      // Setup: completed analysis with events and artifactId
      const events: SSEEvent[] = [
        {
          type: 'complete',
          analysis_id: TEST_ANALYSIS_ID,
          stage: 'artifact_generation',
          status: 'complete',
          timestamp: new Date().toISOString(),
        },
      ]

      mockAnalysisStatus({
        shouldConnect: false,
        resolvedStatus: 'processing' as const, // Not yet "completed" to avoid redirect
        resolvedArtifactId: 'artifact-456', // Artifact is now ready
      })

      // Pre-set completed state with artifact
      useSSEStore.setState({
        error: null,
        events,
        isConnected: false,
        isComplete: true, // SSE says complete
        latestEvent: events[0],
        activeAnalysisId: TEST_ANALYSIS_ID,
      })

      const router = createTestRouter('/analyze/test-123')
      renderWithRouter(router)

      // Should show progress column with complete card
      await waitFor(() => {
        expect(screen.getByTestId('progress-column')).toBeInTheDocument()
        expect(screen.getByTestId('complete-card')).toBeInTheDocument()
      })

      // Should NOT show error alert
      expect(screen.queryByTestId('error-alert')).not.toBeInTheDocument()
    })
  })

  describe('Error Alert Rendering', () => {
    it('prioritizes statusError over other error messages', async () => {
      // Setup: both SSE error and status error
      useSSEStore.setState({
        error: new Error('SSE error'),
        events: [],
        isConnected: false,
        isComplete: false,
        latestEvent: null,
        activeAnalysisId: TEST_ANALYSIS_ID,
      })

      mockAnalysisStatus({
        statusError: 'Status API error',
        shouldConnect: false,
      })

      const router = createTestRouter('/analyze/test-123')
      renderWithRouter(router)

      // Should show status error (higher priority)
      await waitFor(() => {
        expect(screen.getByTestId('error-alert')).toBeInTheDocument()
        expect(screen.getByText('Status API error')).toBeInTheDocument()
      })
    })

    it('shows error from useAnalysisProgress when no status error', async () => {
      // Setup: error from progress hook (hasError + errorMessage)
      const events: SSEEvent[] = [
        {
          type: 'error',
          analysis_id: TEST_ANALYSIS_ID,
          stage: 'extraction',
          status: 'failed',
          timestamp: new Date().toISOString(),
          error: 'Extraction failed: Invalid URL',
        },
      ]

      useSSEStore.setState({
        error: null,
        events,
        isConnected: false,
        isComplete: false,
        latestEvent: events[0],
        activeAnalysisId: TEST_ANALYSIS_ID,
      })

      mockAnalysisStatus({
        shouldConnect: false,
      })

      const router = createTestRouter('/analyze/test-123')
      renderWithRouter(router)

      // Should show error from event
      await waitFor(() => {
        expect(screen.getByTestId('error-alert')).toBeInTheDocument()
        expect(screen.getByText(/Extraction failed: Invalid URL/)).toBeInTheDocument()
      })
    })

    it('falls back to generic error message when no specific error available', async () => {
      // Setup: failed status but no error message
      useSSEStore.setState({
        error: null,
        events: [],
        isConnected: false,
        isComplete: false,
        latestEvent: null,
        activeAnalysisId: TEST_ANALYSIS_ID,
      })

      mockAnalysisStatus({
        resolvedStatus: 'failed',
        shouldConnect: false,
      })

      const router = createTestRouter('/analyze/test-123')
      renderWithRouter(router)

      // Should show generic error message
      await waitFor(() => {
        expect(screen.getByTestId('error-alert')).toBeInTheDocument()
        expect(screen.getByText('An error occurred during analysis')).toBeInTheDocument()
      })
    })
  })

  describe('Edge Cases', () => {
    it('handles completed param with urlArtifactId correctly', async () => {
      // Setup: completed via URL params
      useSSEStore.setState({
        error: null,
        events: [],
        isConnected: false,
        isComplete: false,
        latestEvent: null,
        activeAnalysisId: null,
      })

      mockAnalysisStatus({
        shouldConnect: false,
      })

      const router = createTestRouter('/analyze/test-123', {
        completed: true,
        artifactId: 'artifact-789',
      })
      renderWithRouter(router)

      // Should show completed view directly
      await waitFor(() => {
        expect(screen.getByTestId('completed-view')).toBeInTheDocument()
      })

      // Should NOT show progress or error UI
      expect(screen.queryByTestId('progress-column')).not.toBeInTheDocument()
      expect(screen.queryByTestId('error-alert')).not.toBeInTheDocument()
    })

    it('shows loading state when waiting for first event', async () => {
      // Setup: waiting for first event (no resolved status yet)
      mockAnalysisStatus({
        shouldConnect: true,
        loading: true,
        resolvedStatus: undefined,
      })

      // Pre-set disconnected state before render
      useSSEStore.setState({
        error: null,
        events: [],
        isConnected: false,
        isComplete: false,
        latestEvent: null,
        activeAnalysisId: null,
      })

      const router = createTestRouter('/analyze/test-123')
      renderWithRouter(router)

      // Should show loading state (waiting for first event)
      await waitFor(() => {
        expect(screen.getByTestId('loading-state')).toBeInTheDocument()
      })

      // Should NOT show progress or error UI
      expect(screen.queryByTestId('progress-column')).not.toBeInTheDocument()
      expect(screen.queryByTestId('error-alert')).not.toBeInTheDocument()
    })
  })

  describe('Fatal Error Flag Logic', () => {
    it('correctly calculates isFatalError = true', async () => {
      // All three conditions met: error + no events + disconnected
      useSSEStore.setState({
        error: new Error('Fatal'),
        events: [],
        isConnected: false,
        isComplete: false,
        latestEvent: null,
        activeAnalysisId: TEST_ANALYSIS_ID,
      })

      mockAnalysisStatus({
        shouldConnect: false,
      })

      const router = createTestRouter('/analyze/test-123')
      renderWithRouter(router)

      await waitFor(() => {
        expect(screen.getByTestId('error-alert')).toBeInTheDocument()
      })

      // Fatal error - no progress UI
      expect(screen.queryByTestId('progress-column')).not.toBeInTheDocument()
    })

    it('correctly calculates isFatalError = false when connected', async () => {
      // Has error and no events, but IS connected (not fatal)
      mockAnalysisStatus({
        shouldConnect: true,
      })

      const router = createTestRouter('/analyze/test-123')
      renderWithRouter(router)

      // Wait for connection
      await waitFor(() => {
        expect(useSSEStore.getState().isConnected).toBe(true)
      })

      // Set error while connected
      useSSEStore.setState({
        error: new Error('Recoverable'),
        events: [],
        isConnected: true, // Connected - can still recover
      })

      await waitFor(() => {
        expect(screen.getByTestId('error-alert')).toBeInTheDocument()
      })

      // Not fatal - show progress UI
      expect(screen.getByTestId('progress-column')).toBeInTheDocument()
    })

    it('correctly calculates isFatalError = false when has events', async () => {
      // Has error and disconnected, but HAS events (not fatal)
      const events: SSEEvent[] = [
        {
          type: 'progress',
          analysis_id: TEST_ANALYSIS_ID,
          stage: 'extraction',
          status: 'complete',
          timestamp: new Date().toISOString(),
        } as SSEProgressEvent,
      ]

      useSSEStore.setState({
        error: new Error('Partial failure'),
        events,
        isConnected: false,
        isComplete: false,
        latestEvent: events[0],
        activeAnalysisId: TEST_ANALYSIS_ID,
      })

      mockAnalysisStatus({
        shouldConnect: false,
      })

      const router = createTestRouter('/analyze/test-123')
      renderWithRouter(router)

      await waitFor(() => {
        expect(screen.getByTestId('error-alert')).toBeInTheDocument()
      })

      // Not fatal - show progress UI
      expect(screen.getByTestId('progress-column')).toBeInTheDocument()
    })
  })
})
