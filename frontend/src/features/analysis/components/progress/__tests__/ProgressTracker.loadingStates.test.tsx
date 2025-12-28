/**
 * Integration tests for ProgressTracker with loading states
 *
 * Tests the integration between ProgressTracker and the computed loading states:
 * - shouldShowProgress controls visibility
 * - ConnectionStatus shows appropriate loading state
 * - Progress updates based on analysis phase
 */

import { useLoadingState, useShouldShowProgress, useSSEStore } from '@stores/sseStore'
import { render, screen } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'

import type { LoadingState } from '@types/loading'

import { ProgressTracker } from '../ProgressTracker'

// Mock the individual hooks that the component uses
vi.mock('@stores/sseStore', () => ({
  useLoadingState: vi.fn(),
  useShouldShowProgress: vi.fn(),
  useSSEStore: vi.fn(),
}))

const mockUseLoadingState = vi.mocked(useLoadingState)
const mockUseShouldShowProgress = vi.mocked(useShouldShowProgress)
const mockUseSSEStore = vi.mocked(useSSEStore)

describe('ProgressTracker Loading States Integration', () => {
  let mockLoadingState: LoadingState
  let mockShouldShowProgress: boolean

  beforeEach(() => {
    mockLoadingState = { type: 'disconnected' } as LoadingState
    mockShouldShowProgress = false

    // Mock the individual hooks that ProgressTracker uses
    mockUseLoadingState.mockReturnValue(mockLoadingState)
    mockUseShouldShowProgress.mockReturnValue(mockShouldShowProgress)

    // Mock the main store for other properties
    mockUseSSEStore.mockReturnValue({
      events: [],
      error: null,
      isComplete: false,
    })
  })

  afterEach(() => {
    vi.clearAllMocks()
  })

  describe('Visibility Control', () => {
    it('renders basic card structure even when shouldShowProgress is false', () => {
      mockUseShouldShowProgress.mockReturnValue(false)

      render(<ProgressTracker analysisId="test-id" />)

      // Should still render the basic card with title and connection status
      expect(screen.getByText('Analysis Progress')).toBeInTheDocument()
      expect(screen.getByText('Disconnected')).toBeInTheDocument()
    })

    it('renders progress tracker with stages when shouldShowProgress is true', () => {
      mockUseShouldShowProgress.mockReturnValue(true)

      render(<ProgressTracker analysisId="test-id" />)

      expect(screen.getByText('Analysis Progress')).toBeInTheDocument()
      // Should also show progress stages
      expect(screen.getByRole('list', { name: 'Analysis stages' })).toBeInTheDocument()
    })
  })

  describe('Connection Status Integration', () => {
    it('shows connecting status', () => {
      mockUseShouldShowProgress.mockReturnValue(true)
      mockUseLoadingState.mockReturnValue({
        type: 'connecting',
        startTime: Date.now(),
      } as LoadingState)

      render(<ProgressTracker analysisId="test-id" />)

      expect(screen.getByText('Connecting...')).toBeInTheDocument()
      // Should have spinner
      const spinner = document.querySelector('.animate-spin')
      expect(spinner).toBeInTheDocument()
    })

    it('shows connected status', () => {
      mockUseShouldShowProgress.mockReturnValue(true)
      mockUseLoadingState.mockReturnValue({ type: 'connected' } as LoadingState)

      render(<ProgressTracker analysisId="test-id" />)

      expect(screen.getByText('Connected')).toBeInTheDocument()
    })

    it('shows reconnecting status with attempts', () => {
      mockUseShouldShowProgress.mockReturnValue(true)
      mockUseLoadingState.mockReturnValue({ type: 'reconnecting', attempts: 2 } as LoadingState)

      render(<ProgressTracker analysisId="test-id" />)

      expect(screen.getByText('Reconnecting... (2/3)')).toBeInTheDocument()
    })

    it('shows timeout warning status', () => {
      mockUseShouldShowProgress.mockReturnValue(true)
      mockUseLoadingState.mockReturnValue({
        type: 'timeout_warning',
        connectedAt: Date.now(),
      } as LoadingState)

      render(<ProgressTracker analysisId="test-id" />)

      expect(screen.getByText('Connection timeout')).toBeInTheDocument()
      // Should have alert triangle
      const alertIcon = document.querySelector('svg')
      expect(alertIcon).toBeInTheDocument()
    })

    it('shows disconnected status', () => {
      mockUseShouldShowProgress.mockReturnValue(true)
      mockUseLoadingState.mockReturnValue({ type: 'disconnected' } as LoadingState)

      render(<ProgressTracker analysisId="test-id" />)

      expect(screen.getByText('Disconnected')).toBeInTheDocument()
    })
  })

  describe('Analysis Phase Integration', () => {
    it('shows progress stages during extracting phase', () => {
      mockUseShouldShowProgress.mockReturnValue(true)
      mockUseLoadingState.mockReturnValue({
        type: 'extracting',
        stage: 'extraction',
        status: 'running',
      } as LoadingState)
      // Mock events for progress display
      mockUseSSEStore.mockReturnValue({
        events: [
          {
            type: 'progress',
            stage: 'extraction',
            status: 'running',
            timestamp: new Date().toISOString(),
            details: { word_count: 1000 },
          },
        ],
        error: null,
        isComplete: false,
      })

      render(<ProgressTracker analysisId="test-id" />)

      expect(screen.getByText('Analysis Progress')).toBeInTheDocument()
      // Should show progress stages
      expect(screen.getByRole('list', { name: 'Analysis stages' })).toBeInTheDocument()
    })

    it('shows progress stages during analyzing phase', () => {
      mockUseShouldShowProgress.mockReturnValue(true)
      mockUseLoadingState.mockReturnValue({
        type: 'analyzing',
        stage: 'tech_comparison',
        status: 'running',
        progress: 75,
      } as LoadingState)
      mockUseSSEStore.mockReturnValue({
        events: [],
        error: null,
        isComplete: false,
      })

      render(<ProgressTracker analysisId="test-id" />)

      expect(screen.getByText('Analysis Progress')).toBeInTheDocument()
    })

    it('shows completion message when analysis is complete', () => {
      mockUseShouldShowProgress.mockReturnValue(true)
      mockUseLoadingState.mockReturnValue({
        type: 'complete',
        artifactId: 'test-artifact-id',
      } as LoadingState)
      mockUseSSEStore.mockReturnValue({
        events: [],
        error: null,
        isComplete: true,
      })

      render(<ProgressTracker analysisId="test-id" />)

      expect(screen.getByText('Analysis Progress')).toBeInTheDocument()
      // Should show completion message - use more specific text to avoid matching stage status
      expect(screen.getByText('Analysis Complete')).toBeInTheDocument()
    })
  })

  describe('Error Handling', () => {
    it('shows error alert when error exists', () => {
      mockUseShouldShowProgress.mockReturnValue(true)
      mockUseLoadingState.mockReturnValue({
        type: 'error',
        error: 'Network connection failed',
      } as LoadingState)
      mockUseSSEStore.mockReturnValue({
        events: [],
        error: new Error('Network connection failed'),
        isComplete: false,
      })

      render(<ProgressTracker analysisId="test-id" />)

      expect(screen.getByText('Network connection failed')).toBeInTheDocument()
    })
  })

  describe('Accessibility', () => {
    it('has proper ARIA labels', () => {
      mockUseShouldShowProgress.mockReturnValue(true)
      mockUseLoadingState.mockReturnValue({ type: 'disconnected' } as LoadingState)
      mockUseSSEStore.mockReturnValue({
        events: [],
        error: null,
        isComplete: false,
      })

      render(<ProgressTracker analysisId="test-id" />)

      expect(screen.getByRole('list', { name: 'Analysis stages' })).toBeInTheDocument()
    })

    it('has proper heading structure', () => {
      mockUseShouldShowProgress.mockReturnValue(true)
      mockUseLoadingState.mockReturnValue({ type: 'disconnected' } as LoadingState)
      mockUseSSEStore.mockReturnValue({
        events: [],
        error: null,
        isComplete: false,
      })

      render(<ProgressTracker analysisId="test-id" />)

      const heading = screen.getByText('Analysis Progress')
      expect(heading).toBeInTheDocument()
      expect(heading.tagName).toBe('DIV') // CardTitle renders as styled div
    })
  })
})
