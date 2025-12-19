/**
 * Integration tests for ProgressTracker with loading states
 *
 * Tests the integration between ProgressTracker and the computed loading states:
 * - shouldShowProgress controls visibility
 * - ConnectionStatus shows appropriate loading state
 * - Progress updates based on analysis phase
 */

import { render, screen } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'

import { useSSEStore } from '@stores/sseStore'
import type { LoadingState } from '@types/loading'

import { ProgressTracker } from '../ProgressTracker'

// Mock the SSE store
vi.mock('@stores/sseStore', () => ({
  useSSEStore: vi.fn(),
}))

const mockUseSSEStore = vi.mocked(useSSEStore)

describe('ProgressTracker Loading States Integration', () => {
  let mockStoreState: any

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

  describe('Visibility Control', () => {
    it('renders nothing when shouldShowProgress is false', () => {
      mockStoreState.shouldShowProgress = false

      const { container } = render(<ProgressTracker analysisId="test-id" />)

      expect(container.firstChild).toBeNull()
    })

    it('renders progress tracker when shouldShowProgress is true', () => {
      mockStoreState.shouldShowProgress = true

      render(<ProgressTracker analysisId="test-id" />)

      expect(screen.getByText('Analysis Progress')).toBeInTheDocument()
    })
  })

  describe('Connection Status Integration', () => {
    it('shows connecting status', () => {
      mockStoreState.shouldShowProgress = true
      mockStoreState.loadingState = { type: 'connecting', startTime: Date.now() } as LoadingState

      render(<ProgressTracker analysisId="test-id" />)

      expect(screen.getByText('Connecting...')).toBeInTheDocument()
      // Should have spinner
      const spinner = document.querySelector('.animate-spin')
      expect(spinner).toBeInTheDocument()
    })

    it('shows connected status', () => {
      mockStoreState.shouldShowProgress = true
      mockStoreState.loadingState = { type: 'connected' } as LoadingState

      render(<ProgressTracker analysisId="test-id" />)

      expect(screen.getByText('Connected')).toBeInTheDocument()
    })

    it('shows reconnecting status with attempts', () => {
      mockStoreState.shouldShowProgress = true
      mockStoreState.loadingState = { type: 'reconnecting', attempts: 2 } as LoadingState

      render(<ProgressTracker analysisId="test-id" />)

      expect(screen.getByText('Reconnecting... (2/3)')).toBeInTheDocument()
    })

    it('shows timeout warning status', () => {
      mockStoreState.shouldShowProgress = true
      mockStoreState.loadingState = {
        type: 'timeout_warning',
        connectedAt: Date.now(),
      } as LoadingState

      render(<ProgressTracker analysisId="test-id" />)

      expect(screen.getByText('Connection timeout')).toBeInTheDocument()
      // Should have alert triangle
      const alertIcon = document.querySelector('svg')
      expect(alertIcon).toBeInTheDocument()
    })

    it('shows disconnected status', () => {
      mockStoreState.shouldShowProgress = true
      mockStoreState.loadingState = { type: 'disconnected' } as LoadingState

      render(<ProgressTracker analysisId="test-id" />)

      expect(screen.getByText('Disconnected')).toBeInTheDocument()
    })
  })

  describe('Analysis Phase Integration', () => {
    it('shows progress stages during extracting phase', () => {
      mockStoreState.shouldShowProgress = true
      mockStoreState.loadingState = {
        type: 'extracting',
        stage: 'extraction',
        status: 'running',
      } as LoadingState
      // Add some mock events for progress display
      mockStoreState.events = [
        {
          type: 'progress',
          stage: 'extraction',
          status: 'running',
          timestamp: new Date().toISOString(),
          details: { word_count: 1000 },
        },
      ]

      render(<ProgressTracker analysisId="test-id" />)

      expect(screen.getByText('Analysis Progress')).toBeInTheDocument()
      // Should show progress stages
      expect(screen.getByRole('list', { name: 'Analysis stages' })).toBeInTheDocument()
    })

    it('shows progress stages during analyzing phase', () => {
      mockStoreState.shouldShowProgress = true
      mockStoreState.loadingState = {
        type: 'analyzing',
        stage: 'tech_comparison',
        status: 'running',
        progress: 75,
      } as LoadingState

      render(<ProgressTracker analysisId="test-id" />)

      expect(screen.getByText('Analysis Progress')).toBeInTheDocument()
    })

    it('shows completion message when analysis is complete', () => {
      mockStoreState.shouldShowProgress = true
      mockStoreState.isComplete = true
      mockStoreState.loadingState = {
        type: 'complete',
        artifactId: 'test-artifact-id',
      } as LoadingState

      render(<ProgressTracker analysisId="test-id" />)

      expect(screen.getByText('Analysis Progress')).toBeInTheDocument()
      // Should show completion message
      expect(screen.getByText(/complete/i)).toBeInTheDocument()
    })
  })

  describe('Error Handling', () => {
    it('shows error alert when error exists', () => {
      mockStoreState.shouldShowProgress = true
      mockStoreState.error = new Error('Network connection failed')
      mockStoreState.loadingState = {
        type: 'error',
        error: 'Network connection failed',
      } as LoadingState

      render(<ProgressTracker analysisId="test-id" />)

      expect(screen.getByText('Network connection failed')).toBeInTheDocument()
    })
  })

  describe('Accessibility', () => {
    it('has proper ARIA labels', () => {
      mockStoreState.shouldShowProgress = true

      render(<ProgressTracker analysisId="test-id" />)

      expect(screen.getByRole('list', { name: 'Analysis stages' })).toBeInTheDocument()
    })

    it('has proper heading structure', () => {
      mockStoreState.shouldShowProgress = true

      render(<ProgressTracker analysisId="test-id" />)

      const heading = screen.getByRole('heading', { name: 'Analysis Progress' })
      expect(heading).toBeInTheDocument()
      expect(heading.tagName).toBe('H2') // CardTitle renders as h2
    })
  })
})
