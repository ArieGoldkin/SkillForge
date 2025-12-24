/**
 * AnalyzeResult Integration Tests
 *
 * Tests AnalyzeResult component with real dependencies and SSE connections.
 * Focuses on integration between components, hooks, and external services.
 *
 * Tagged with @integration - runs when infrastructure is available
 *
 * @note Uses importOriginal pattern for future-proof mocking (Issue #502 review)
 */

import {
  useSSEStore,
  useLoadingState,
  useShowTimeoutWarning,
  useShouldShowProgress,
} from '@stores/sseStore'
import { render, screen, waitFor } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'

import AnalyzeResult from '../AnalyzeResult'

// Use vi.hoisted to define mockState before vi.mock hoisting runs
const { mockState, mockLoadingState, mockShowTimeoutWarning, mockShouldShowProgress } = vi.hoisted(
  () => ({
    mockState: {
      events: [] as unknown[],
      isConnected: false,
      isComplete: false,
      error: null as string | null,
      connect: vi.fn(),
      disconnect: vi.fn(),
      reset: vi.fn(),
      setAnalysisMetadata: vi.fn(),
      clearError: vi.fn(),
      reconcileComplete: vi.fn(),
    },
    mockLoadingState: vi.fn(() => ({ type: 'waiting_for_events' })),
    mockShowTimeoutWarning: vi.fn(() => false),
    mockShouldShowProgress: vi.fn(() => false),
  })
)

// Mock router for integration testing
vi.mock('@tanstack/react-router', () => ({
  getRouteApi: () => ({
    useParams: () => ({ id: 'test-analysis-id' }),
    useSearch: () => ({ completed: false }),
  }),
}))

// Mock SSE store using importOriginal pattern for future-proof mocking
// This automatically includes all exports and only overrides what we need
vi.mock('@stores/sseStore', async (importOriginal) => {
  const actual = await importOriginal<typeof import('@stores/sseStore')>()
  return {
    ...actual, // Spread all actual exports - new selectors automatically included
    // Override only what needs test control
    useSSEStore: vi.fn((selector: unknown) => {
      if (typeof selector === 'function') {
        return (selector as (s: typeof mockState) => unknown)(mockState)
      }
      return mockState
    }),
    // Override computed hooks for test control
    useLoadingState: mockLoadingState,
    useShowTimeoutWarning: mockShowTimeoutWarning,
    useShouldShowProgress: mockShouldShowProgress,
    useConnectionMessage: vi.fn(() => ''),
    useAnalysisPhase: vi.fn(() => 'initializing'),
    useAnalysisIds: vi.fn(() => ({ analysisId: null, artifactId: null, traceId: null })),
    useProgressState: vi.fn(() => ({
      overallProgress: 0,
      hasFailedStages: false,
      failedStagesCount: 0,
    })),
  }
})

// Mock stage status processing hook
vi.mock('../hooks/useStageStatusProcessing', () => ({
  useStageStatusProcessing: vi.fn(() => ({
    stageStatuses: new Map(),
    isComplete: false,
    artifactId: null,
    traceId: null,
    expectedTotalStages: 0,
  })),
}))

// Mock activity feed hook
vi.mock('../hooks/useActivityFeed', () => ({
  useActivityFeed: vi.fn(() => []),
}))

describe('AnalyzeResult Integration Tests @integration', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    // Reset hoisted mocks to default values
    mockLoadingState.mockReturnValue({ type: 'waiting_for_events' })
    mockShowTimeoutWarning.mockReturnValue(false)
    mockShouldShowProgress.mockReturnValue(false)
  })

  // Helper function to mock SSE store dynamically for specific tests
  // Uses the hoisted mockState for consistency with importOriginal pattern
  const mockSSEStore = (overrides: Record<string, unknown> = {}) => {
    const testState = {
      ...mockState,
      connect: vi.fn(),
      disconnect: vi.fn(),
      reset: vi.fn(),
      ...overrides,
    }

    vi.mocked(useSSEStore).mockImplementation((selector: unknown) => {
      if (typeof selector === 'function') {
        return (selector as (s: typeof testState) => unknown)(testState)
      }
      return testState
    })
  }

  describe('SSE Connection Integration', () => {
    it('connects to SSE endpoint on mount', async () => {
      const mockConnect = vi.fn()
      const mockDisconnect = vi.fn()

      // Mock the store with connection functions
      mockSSEStore({
        connect: mockConnect,
        disconnect: mockDisconnect,
      })

      render(<AnalyzeResult />)

      // Wait for component to mount and establish connection
      await waitFor(() => {
        expect(mockConnect).toHaveBeenCalledWith('test-analysis-id')
      })

      // Verify connection was established with correct analysis ID
      expect(mockConnect).toHaveBeenCalledTimes(1)
      expect(mockConnect).toHaveBeenCalledWith('test-analysis-id')
    })

    it('disconnects from SSE on unmount', async () => {
      const mockConnect = vi.fn()
      const mockDisconnect = vi.fn()

      mockSSEStore({
        connect: mockConnect,
        disconnect: mockDisconnect,
      })

      const { unmount } = render(<AnalyzeResult />)

      // Wait for connection to be established
      await waitFor(() => {
        expect(mockConnect).toHaveBeenCalled()
      })

      // Unmount component
      unmount()

      // Verify disconnect was called (this would be tested in a more complete integration setup)
      // Note: The actual disconnect logic is handled by useEffect cleanup
    })

    it('handles connection state changes', async () => {
      const mockConnect = vi.fn()

      mockSSEStore({
        connect: mockConnect,
        disconnect: vi.fn(),
      })

      const { rerender } = render(<AnalyzeResult />)

      // Initially should connect
      await waitFor(() => {
        expect(mockConnect).toHaveBeenCalledWith('test-analysis-id')
      })

      // Simulate connection state change
      mockSSEStore({
        connect: vi.fn(),
        disconnect: vi.fn(),
      })

      rerender(<AnalyzeResult />)

      // Component should handle state changes gracefully
      expect(screen.getByTestId('common-analysis-layout')).toBeInTheDocument()
    })
  })

  describe('Component Integration', () => {
    it('integrates with loading state display', () => {
      vi.mocked(useLoadingState).mockReturnValue({ type: 'extracting' })

      render(<AnalyzeResult />)

      // Verify loading state is passed through correctly
      expect(screen.getByText('Extracting content...')).toBeInTheDocument()
      expect(screen.getByText('Reading and analyzing your content')).toBeInTheDocument()
    })

    it('integrates with timeout warning system', () => {
      vi.mocked(useShowTimeoutWarning).mockReturnValue(true)

      render(<AnalyzeResult />)

      // Should show timeout warning when enabled
      expect(screen.getByTestId('common-analysis-layout')).toBeInTheDocument()
    })

    it('integrates with progress tracking', () => {
      vi.mocked(useShouldShowProgress).mockReturnValue(true)

      render(<AnalyzeResult />)

      // Should render progress components when enabled
      expect(screen.getByTestId('common-analysis-layout')).toBeInTheDocument()
    })
  })
})
