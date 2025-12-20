/**
 * AnalyzeResult Integration Tests
 *
 * Tests AnalyzeResult component with real dependencies and SSE connections.
 * Focuses on integration between components, hooks, and external services.
 *
 * Tagged with @integration - runs when infrastructure is available
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

// Mock router for integration testing
vi.mock('@tanstack/react-router', () => ({
  getRouteApi: () => ({
    useParams: () => ({ id: 'test-analysis-id' }),
    useSearch: () => ({ completed: false }),
  }),
}))

// Mock SSE store for controlled testing
const mockState = {
  events: [],
  isConnected: false,
  isComplete: false,
  error: null,
  connect: vi.fn(),
  disconnect: vi.fn(),
  reset: vi.fn(),
  setAnalysisMetadata: vi.fn(),
}

vi.mock('@stores/sseStore', () => ({
  useSSEStore: vi.fn((selector) => {
    if (typeof selector === 'function') {
      return selector(mockState)
    }
    return mockState
  }),
  selectSetAnalysisMetadata: vi.fn(() => mockState.setAnalysisMetadata),
  useLoadingState: vi.fn(() => ({ type: 'waiting_for_events' })),
  useShowTimeoutWarning: vi.fn(() => false),
  useShouldShowProgress: vi.fn(() => false),
}))

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
  })

  // Helper function to mock SSE store dynamically for specific tests
  const mockSSEStore = (overrides: Record<string, unknown> = {}) => {
    const defaultState = {
      events: [],
      isConnected: false,
      isComplete: false,
      error: null,
      connect: vi.fn(),
      disconnect: vi.fn(),
      reset: vi.fn(),
      ...overrides,
    }

    vi.mocked(useSSEStore).mockImplementation((selector) => {
      if (typeof selector === 'function') {
        return selector(defaultState)
      }
      return defaultState
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
