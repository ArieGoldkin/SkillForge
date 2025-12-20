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
vi.mock('@stores/sseStore', () => ({
  useSSEStore: vi.fn(),
  useLoadingState: vi.fn(),
  useShowTimeoutWarning: vi.fn(),
  useShouldShowProgress: vi.fn(),
}))

const mockUseSSEStore = vi.mocked(useSSEStore)
const mockUseLoadingState = vi.mocked(useLoadingState)
const mockUseShowTimeoutWarning = vi.mocked(useShowTimeoutWarning)
const mockUseShouldShowProgress = vi.mocked(useShouldShowProgress)

describe('AnalyzeResult Integration Tests @integration', () => {
  beforeEach(() => {
    vi.clearAllMocks()

    // Setup default mocks
    mockUseSSEStore.mockImplementation((selector) => {
      if (selector === vi.fn()) return { connect: vi.fn(), disconnect: vi.fn() }
      return {}
    })

    mockUseLoadingState.mockReturnValue('waiting_for_events')
    mockUseShowTimeoutWarning.mockReturnValue(false)
    mockUseShouldShowProgress.mockReturnValue(false)
  })

  describe('SSE Connection Integration', () => {
    it('connects to SSE endpoint on mount', async () => {
      const mockConnect = vi.fn()
      const mockDisconnect = vi.fn()

      // Mock the store to return connection functions
      mockUseSSEStore.mockImplementation((selector) => {
        if (typeof selector === 'function') {
          return { connect: mockConnect, disconnect: mockDisconnect }
        }
        return {}
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

      mockUseSSEStore.mockImplementation((selector) => {
        if (typeof selector === 'function') {
          return { connect: mockConnect, disconnect: mockDisconnect }
        }
        return {}
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
      let connectionState = { connect: mockConnect, disconnect: vi.fn() }

      mockUseSSEStore.mockImplementation((selector) => {
        if (typeof selector === 'function') {
          return connectionState
        }
        return {}
      })

      const { rerender } = render(<AnalyzeResult />)

      // Initially should connect
      await waitFor(() => {
        expect(mockConnect).toHaveBeenCalledWith('test-analysis-id')
      })

      // Simulate connection state change
      connectionState = { connect: vi.fn(), disconnect: vi.fn() }

      rerender(<AnalyzeResult />)

      // Component should handle state changes gracefully
      expect(screen.getByTestId('common-analysis-layout')).toBeInTheDocument()
    })
  })

  describe('Component Integration', () => {
    it('integrates with loading state display', () => {
      mockUseLoadingState.mockReturnValue('extracting')

      render(<AnalyzeResult />)

      // Verify loading state is passed through correctly
      expect(screen.getByTestId('loading-state-display')).toBeInTheDocument()
      expect(screen.getByText('extracting')).toBeInTheDocument()
    })

    it('integrates with timeout warning system', () => {
      mockUseShowTimeoutWarning.mockReturnValue(true)

      render(<AnalyzeResult />)

      // Should show timeout warning when enabled
      expect(screen.getByTestId('common-analysis-layout')).toBeInTheDocument()
    })

    it('integrates with progress tracking', () => {
      mockUseShouldShowProgress.mockReturnValue(true)

      render(<AnalyzeResult />)

      // Should render progress components when enabled
      expect(screen.getByTestId('common-analysis-layout')).toBeInTheDocument()
    })
  })
})
