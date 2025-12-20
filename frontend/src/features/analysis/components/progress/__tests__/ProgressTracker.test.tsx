import type { SSEProgressEvent, SSEErrorEvent } from '@app-types/sse'
import { useSSEStore, useShouldShowProgress, useLoadingState } from '@stores/sseStore'
import { render, screen, waitFor } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import { ProgressTracker, WORKING_STAGES } from '../'
import { normalizeSSEEvent, getMappedStageName, getMappedStatus } from '../sseNormalizer'

// Valid UUIDs for testing
const TEST_ANALYSIS_ID = '123e4567-e89b-12d3-a456-426614174000'
const TEST_ARTIFACT_ID = '987fcdeb-51a2-43d7-8f9e-123456789abc'

// Mock the hooks
vi.mock('@stores/sseStore', () => ({
  useSSEStore: vi.fn(),
  useShouldShowProgress: vi.fn(),
  useLoadingState: vi.fn(),
}))

const mockUseSSEStore = vi.mocked(useSSEStore)
const mockUseShouldShowProgress = vi.mocked(useShouldShowProgress)
const mockUseLoadingState = vi.mocked(useLoadingState)

/**
 * Mock EventSource - Class-based mock for browser EventSource API
 */
let mockInstance: MockEventSource | null = null

class MockEventSource {
  url: string
  onopen: (() => void) | null = null
  onerror: ((err: Event) => void) | null = null
  listeners: Map<string, (event: MessageEvent) => void> = new Map()
  readyState = 0

  constructor(url: string) {
    this.url = url
    // eslint-disable-next-line @typescript-eslint/no-this-alias -- Required for mock instance tracking
    mockInstance = this

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

  simulateEvent(type: string, data: object) {
    const listener = this.listeners.get(type)
    if (listener) {
      listener(new MessageEvent(type, { data: JSON.stringify(data) }))
    }
  }
}

function getMockEventSource(): MockEventSource | null {
  return mockInstance
}

describe('ProgressTracker Component', () => {
  beforeEach(() => {
    mockInstance = null
    vi.stubGlobal('EventSource', MockEventSource)
    vi.stubEnv('VITE_API_URL', 'http://localhost:8000')

    // Mock the hooks
    mockUseShouldShowProgress.mockReturnValue(true)
    mockUseLoadingState.mockReturnValue({ type: 'disconnected' } as LoadingState)
    mockUseSSEStore.mockReturnValue({
      events: [],
      error: null,
      isComplete: false,
    })
  })

  afterEach(() => {
    vi.unstubAllGlobals()
    vi.unstubAllEnvs()
  })

  describe('Initial Rendering', () => {
    it('renders with all stages by default', () => {
      render(<ProgressTracker analysisId={TEST_ANALYSIS_ID} />)

      expect(screen.getByText('Analysis Progress')).toBeInTheDocument()
      expect(screen.getByText('Content Extraction')).toBeInTheDocument()
      expect(screen.getByText('Routing to Agents')).toBeInTheDocument()
      expect(screen.getByText('Tech Comparison')).toBeInTheDocument()
    })

    it('renders with only WORKING_STAGES when specified', () => {
      render(<ProgressTracker analysisId={TEST_ANALYSIS_ID} stages={WORKING_STAGES} />)

      expect(screen.getByText('Content Extraction')).toBeInTheDocument()
      expect(screen.getByText('Routing to Agents')).toBeInTheDocument()
      expect(screen.queryByText('Tech Comparison')).not.toBeInTheDocument()
    })

    it('shows all stages as pending initially', () => {
      render(<ProgressTracker analysisId={TEST_ANALYSIS_ID} stages={WORKING_STAGES} />)

      const pendingBadges = screen.getAllByText('Pending')
      expect(pendingBadges.length).toBe(WORKING_STAGES.length)
    })

    it('displays connection status indicator', () => {
      render(<ProgressTracker analysisId={TEST_ANALYSIS_ID} />)

      // Initially disconnected until connection opens
      expect(screen.getByText('Disconnected')).toBeInTheDocument()
    })
  })

  describe('SSE Connection', () => {
    it.skip('connects to SSE endpoint on mount', async () => {
      // TODO: Move to AnalyzeResult integration tests
      // ProgressTracker no longer manages SSE connections
      render(<ProgressTracker analysisId={TEST_ANALYSIS_ID} />)

      await waitFor(() => {
        expect(getMockEventSource()?.url).toContain(TEST_ANALYSIS_ID)
      })
    })

    it('shows connected status when connection opens', () => {
      mockUseShouldShowProgress.mockReturnValue(false) // Connection status should show even when not showing progress
      mockUseLoadingState.mockReturnValue({ type: 'connected' } as LoadingState)
      mockUseSSEStore.mockReturnValue({
        events: [],
        error: null,
        isComplete: false,
      })

      render(<ProgressTracker analysisId={TEST_ANALYSIS_ID} />)

      expect(screen.getByText('Connected')).toBeInTheDocument()
    })
  })

  describe('Event Processing', () => {
    it('updates stage status on progress event', () => {
      const event: SSEProgressEvent = {
        type: 'progress',
        analysis_id: TEST_ANALYSIS_ID,
        stage: 'extraction',
        status: 'running',
        timestamp: new Date().toISOString(),
      }

      mockUseShouldShowProgress.mockReturnValue(true)
      mockUseSSEStore.mockReturnValue({
        events: [event],
        error: null,
        isComplete: false,
      })

      render(<ProgressTracker analysisId={TEST_ANALYSIS_ID} stages={WORKING_STAGES} />)

      expect(screen.getByText('Running')).toBeInTheDocument()
    })

    it('shows complete status when stage completes', () => {
      const event: SSEProgressEvent = {
        type: 'progress',
        analysis_id: TEST_ANALYSIS_ID,
        stage: 'extraction',
        status: 'complete',
        timestamp: new Date().toISOString(),
      }

      mockUseShouldShowProgress.mockReturnValue(true)
      mockUseSSEStore.mockReturnValue({
        events: [event],
        error: null,
        isComplete: false,
      })

      render(<ProgressTracker analysisId={TEST_ANALYSIS_ID} stages={WORKING_STAGES} />)

      expect(screen.getByText('Complete')).toBeInTheDocument()
    })
  })

  describe('Completion', () => {
    it('shows completion message when analysis completes', () => {
      mockUseSSEStore.mockReturnValue({
        events: [],
        error: null,
        isComplete: true,
      })

      render(<ProgressTracker analysisId={TEST_ANALYSIS_ID} />)

      expect(screen.getByText('Analysis Complete')).toBeInTheDocument()
    })

    it('calls onComplete callback with artifact ID', () => {
      const onComplete = vi.fn()

      // Mock events that would trigger onComplete
      const mockEvents = [
        {
          type: 'complete',
          analysis_id: TEST_ANALYSIS_ID,
          stage: 'artifact_generation',
          status: 'complete',
          timestamp: new Date().toISOString(),
          artifact_id: TEST_ARTIFACT_ID,
        },
      ]

      mockUseShouldShowProgress.mockReturnValue(true)
      mockUseLoadingState.mockReturnValue({
        type: 'complete',
        artifactId: TEST_ARTIFACT_ID,
      } as LoadingState)
      mockUseSSEStore.mockReturnValue({
        events: mockEvents,
        error: null,
        isComplete: true,
      })

      render(<ProgressTracker analysisId={TEST_ANALYSIS_ID} onComplete={onComplete} />)

      expect(onComplete).toHaveBeenCalledWith(TEST_ARTIFACT_ID)
    })
  })

  describe('Error Handling', () => {
    it('displays error message on stage failure', () => {
      const errorEvent: SSEErrorEvent = {
        type: 'error',
        analysis_id: TEST_ANALYSIS_ID,
        stage: 'extraction',
        status: 'failed',
        timestamp: new Date().toISOString(),
        details: { error: 'Failed to extract content' },
      }

      mockUseShouldShowProgress.mockReturnValue(true)
      mockUseLoadingState.mockReturnValue({
        type: 'analyzing',
        progress: 50,
      } as LoadingState)
      mockUseSSEStore.mockReturnValue({
        events: [errorEvent],
        error: null, // No global error for stage validation errors
        isComplete: false,
      })

      render(<ProgressTracker analysisId={TEST_ANALYSIS_ID} stages={WORKING_STAGES} />)

      // Should show stage-specific error, not global error
      expect(screen.getByText(/Failed to extract content/)).toBeInTheDocument()
    })

    it('calls onError callback', () => {
      const onError = vi.fn()

      const errorEvent: SSEErrorEvent = {
        type: 'error',
        analysis_id: TEST_ANALYSIS_ID,
        stage: 'extraction',
        status: 'failed',
        timestamp: new Date().toISOString(),
        details: { error: 'Test error' },
      }

      mockUseSSEStore.mockReturnValue({
        events: [errorEvent],
        error: new Error('Test error'),
        isComplete: false,
      })

      render(<ProgressTracker analysisId={TEST_ANALYSIS_ID} onError={onError} />)

      expect(onError).toHaveBeenCalledWith('Test error')
    })
  })
})

describe('SSE Event Normalizer', () => {
  describe('Stage Name Mapping', () => {
    it('maps supervisor to supervisor_routing', () => {
      expect(getMappedStageName('supervisor')).toBe('supervisor_routing')
    })

    it('returns valid stage names unchanged', () => {
      expect(getMappedStageName('extraction')).toBe('extraction')
      expect(getMappedStageName('aggregation')).toBe('aggregation')
    })

    it('returns null for unknown stages', () => {
      expect(getMappedStageName('unknown_stage')).toBeNull()
    })
  })

  describe('Status Mapping', () => {
    it('maps streaming to running', () => {
      expect(getMappedStatus('streaming')).toBe('running')
    })

    it('returns valid statuses unchanged', () => {
      expect(getMappedStatus('pending')).toBe('pending')
      expect(getMappedStatus('running')).toBe('running')
      expect(getMappedStatus('complete')).toBe('complete')
      expect(getMappedStatus('failed')).toBe('failed')
    })
  })

  describe('Event Normalization', () => {
    it('normalizes progress event with backend stage name', () => {
      const rawEvent = {
        type: 'progress',
        analysis_id: TEST_ANALYSIS_ID,
        stage: 'supervisor',
        status: 'running',
        timestamp: '2025-01-01T00:00:00Z',
      }

      const normalized = normalizeSSEEvent(rawEvent)

      expect(normalized).not.toBeNull()
      expect(normalized?.type).toBe('progress')
      if (normalized?.type === 'progress') {
        expect(normalized.stage).toBe('supervisor_routing')
        expect(normalized.status).toBe('running')
      }
    })

    it('normalizes event with streaming status', () => {
      const rawEvent = {
        type: 'progress',
        analysis_id: TEST_ANALYSIS_ID,
        stage: 'supervisor',
        status: 'streaming',
        timestamp: '2025-01-01T00:00:00Z',
      }

      const normalized = normalizeSSEEvent(rawEvent)

      expect(normalized).not.toBeNull()
      if (normalized?.type === 'progress') {
        expect(normalized.status).toBe('running')
      }
    })

    it('extracts top-level details fields', () => {
      const rawEvent = {
        type: 'progress',
        analysis_id: TEST_ANALYSIS_ID,
        stage: 'extraction',
        status: 'complete',
        timestamp: '2025-01-01T00:00:00Z',
        word_count: 1500,
        agent: 'content_extractor',
      }

      const normalized = normalizeSSEEvent(rawEvent)

      expect(normalized).not.toBeNull()
      if (normalized?.type === 'progress') {
        expect(normalized.details?.word_count).toBe(1500)
        expect(normalized.details?.agent).toBe('content_extractor')
      }
    })

    it('handles error events with top-level error fields', () => {
      const rawEvent = {
        type: 'error',
        analysis_id: TEST_ANALYSIS_ID,
        stage: 'extraction',
        status: 'failed',
        timestamp: '2025-01-01T00:00:00Z',
        error: 'Connection timeout',
        error_code: 'EXTRACTION_FAILED',
      }

      const normalized = normalizeSSEEvent(rawEvent)

      expect(normalized).not.toBeNull()
      if (normalized?.type === 'error') {
        expect(normalized.details?.error).toBe('Connection timeout')
        expect(normalized.details?.error_code).toBe('EXTRACTION_FAILED')
      }
    })

    it('returns null for invalid events', () => {
      expect(normalizeSSEEvent(null)).toBeNull()
      expect(normalizeSSEEvent(undefined)).toBeNull()
      expect(normalizeSSEEvent({})).toBeNull()
      expect(normalizeSSEEvent({ type: 'progress' })).toBeNull()
    })
  })
})
