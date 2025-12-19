import type { SSEProgressEvent, SSECompleteEvent, SSEErrorEvent } from '@app-types/sse'
import { useSSEStore } from '@stores/sseStore'
import { render, screen, waitFor } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import { ProgressTracker, WORKING_STAGES } from '../'
import { normalizeSSEEvent, getMappedStageName, getMappedStatus } from '../sseNormalizer'

// Valid UUIDs for testing
const TEST_ANALYSIS_ID = '123e4567-e89b-12d3-a456-426614174000'
const TEST_ARTIFACT_ID = '987fcdeb-51a2-43d7-8f9e-123456789abc'

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
    useSSEStore.getState().reset()
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
    it('connects to SSE endpoint on mount', async () => {
      render(<ProgressTracker analysisId={TEST_ANALYSIS_ID} />)

      await waitFor(() => {
        expect(getMockEventSource()?.url).toContain(TEST_ANALYSIS_ID)
      })
    })

    it('shows connected status when connection opens', async () => {
      render(<ProgressTracker analysisId={TEST_ANALYSIS_ID} />)

      await waitFor(() => {
        expect(screen.getByText('Connected')).toBeInTheDocument()
      })
    })
  })

  describe('Event Processing', () => {
    it('updates stage status on progress event', async () => {
      render(<ProgressTracker analysisId={TEST_ANALYSIS_ID} stages={WORKING_STAGES} />)

      await waitFor(() => expect(getMockEventSource()).toBeTruthy())

      const event: SSEProgressEvent = {
        type: 'progress',
        analysis_id: TEST_ANALYSIS_ID,
        stage: 'extraction',
        status: 'running',
        timestamp: new Date().toISOString(),
      }

      getMockEventSource()?.simulateEvent('progress', event)

      await waitFor(() => {
        expect(screen.getByText('Running')).toBeInTheDocument()
      })
    })

    it('shows complete status when stage completes', async () => {
      render(<ProgressTracker analysisId={TEST_ANALYSIS_ID} stages={WORKING_STAGES} />)

      await waitFor(() => expect(getMockEventSource()).toBeTruthy())

      const event: SSEProgressEvent = {
        type: 'progress',
        analysis_id: TEST_ANALYSIS_ID,
        stage: 'extraction',
        status: 'complete',
        timestamp: new Date().toISOString(),
      }

      getMockEventSource()?.simulateEvent('progress', event)

      await waitFor(() => {
        expect(screen.getByText('Complete')).toBeInTheDocument()
      })
    })
  })

  describe('Completion', () => {
    it('shows completion message when analysis completes', async () => {
      render(<ProgressTracker analysisId={TEST_ANALYSIS_ID} />)

      await waitFor(() => expect(getMockEventSource()).toBeTruthy())

      // Simulate complete event
      const completeEvent: SSECompleteEvent = {
        type: 'complete',
        analysis_id: TEST_ANALYSIS_ID,
        stage: 'artifact_generation',
        status: 'complete',
        timestamp: new Date().toISOString(),
        artifact_id: TEST_ARTIFACT_ID,
      }

      getMockEventSource()?.simulateEvent('complete', completeEvent)

      await waitFor(() => {
        expect(screen.getByText('Analysis Complete')).toBeInTheDocument()
      })
    })

    it('calls onComplete callback with artifact ID', async () => {
      const onComplete = vi.fn()
      render(<ProgressTracker analysisId={TEST_ANALYSIS_ID} onComplete={onComplete} />)

      await waitFor(() => expect(getMockEventSource()).toBeTruthy())

      const completeEvent: SSECompleteEvent = {
        type: 'complete',
        analysis_id: TEST_ANALYSIS_ID,
        stage: 'artifact_generation',
        status: 'complete',
        timestamp: new Date().toISOString(),
        artifact_id: TEST_ARTIFACT_ID,
      }

      getMockEventSource()?.simulateEvent('complete', completeEvent)

      await waitFor(() => {
        expect(onComplete).toHaveBeenCalledWith(TEST_ARTIFACT_ID)
      })
    })
  })

  describe('Error Handling', () => {
    it('displays error message on stage failure', async () => {
      render(<ProgressTracker analysisId={TEST_ANALYSIS_ID} stages={WORKING_STAGES} />)

      await waitFor(() => expect(getMockEventSource()).toBeTruthy())

      const errorEvent: SSEErrorEvent = {
        type: 'error',
        analysis_id: TEST_ANALYSIS_ID,
        stage: 'extraction',
        status: 'failed',
        timestamp: new Date().toISOString(),
        details: { error: 'Failed to extract content' },
      }

      getMockEventSource()?.simulateEvent('error', errorEvent)

      await waitFor(() => {
        expect(screen.getByText(/Failed to extract content/)).toBeInTheDocument()
      })
    })

    it('calls onError callback', async () => {
      const onError = vi.fn()
      render(<ProgressTracker analysisId={TEST_ANALYSIS_ID} onError={onError} />)

      await waitFor(() => expect(getMockEventSource()).toBeTruthy())

      const errorEvent: SSEErrorEvent = {
        type: 'error',
        analysis_id: TEST_ANALYSIS_ID,
        stage: 'extraction',
        status: 'failed',
        timestamp: new Date().toISOString(),
        details: { error: 'Test error' },
      }

      getMockEventSource()?.simulateEvent('error', errorEvent)

      await waitFor(() => {
        expect(onError).toHaveBeenCalledWith('Test error')
      })
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
