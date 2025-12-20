import type { SSECompleteEvent, SSEErrorEvent, SSEProgressEvent } from '@app-types/sse'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import { useSSEStore } from '../sseStore'

// Valid UUIDs for testing
const TEST_ANALYSIS_ID = '123e4567-e89b-12d3-a456-426614174000'
const TEST_ARTIFACT_ID = '987fcdeb-51a2-43d7-8f9e-123456789abc'

// Helper function for recent timestamps in tests
function recentTimestamp(offsetMs: number = 0): string {
  return new Date(Date.now() - offsetMs).toISOString()
}

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
    // eslint-disable-next-line @typescript-eslint/no-this-alias
    mockInstance = this

    // Simulate async connection open
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

describe('SSE Store @unit @store', () => {
  beforeEach(() => {
    mockInstance = null
    vi.stubGlobal('EventSource', MockEventSource)
    vi.stubEnv('VITE_API_BASE_URL', 'http://localhost:8000')
    useSSEStore.getState().reset()
  })

  afterEach(() => {
    vi.unstubAllGlobals()
    vi.unstubAllEnvs()
  })

  it('connects to SSE endpoint successfully', async () => {
    const analysisId = TEST_ANALYSIS_ID
    useSSEStore.getState().connect(analysisId)

    await vi.waitFor(() => {
      expect(useSSEStore.getState().isConnected).toBe(true)
    })

    expect(useSSEStore.getState().activeAnalysisId).toBe(analysisId)
    expect(getMockEventSource()?.url).toBe(
      `http://localhost:8000/api/v1/analyze/${analysisId}/stream`
    )
  })

  it('accumulates progress events', async () => {
    useSSEStore.getState().connect(TEST_ANALYSIS_ID)
    await vi.waitFor(() => expect(useSSEStore.getState().isConnected).toBe(true))

    const event: SSEProgressEvent = {
      type: 'progress',
      analysis_id: TEST_ANALYSIS_ID,
      stage: 'extraction',
      status: 'running',
      timestamp: new Date().toISOString(),
    }

    getMockEventSource()?.simulateEvent('progress', event)

    await vi.waitFor(() => expect(useSSEStore.getState().events.length).toBe(1))
    expect(useSSEStore.getState().latestEvent).toEqual(event)
  })

  it('handles complete event and disconnects', async () => {
    useSSEStore.getState().connect(TEST_ANALYSIS_ID)
    await vi.waitFor(() => expect(useSSEStore.getState().isConnected).toBe(true))

    const event: SSECompleteEvent = {
      type: 'complete',
      analysis_id: TEST_ANALYSIS_ID,
      stage: 'artifact_generation',
      status: 'complete',
      timestamp: new Date().toISOString(),
      artifact_id: TEST_ARTIFACT_ID,
    }

    getMockEventSource()?.simulateEvent('complete', event)

    await vi.waitFor(() => expect(useSSEStore.getState().isComplete).toBe(true))
    expect(useSSEStore.getState().isConnected).toBe(false)
  })

  it('handles error events', async () => {
    useSSEStore.getState().connect(TEST_ANALYSIS_ID)
    await vi.waitFor(() => expect(useSSEStore.getState().isConnected).toBe(true))

    const event: SSEErrorEvent = {
      type: 'error',
      analysis_id: TEST_ANALYSIS_ID,
      stage: 'extraction',
      status: 'failed',
      timestamp: new Date().toISOString(),
      details: { error: 'Failed to extract', error_code: 'EXTRACTION_ERROR' },
    }

    vi.spyOn(console, 'error').mockImplementation(() => {})
    getMockEventSource()?.simulateEvent('error', event)

    await vi.waitFor(() => expect(useSSEStore.getState().error).not.toBe(null))
    expect(useSSEStore.getState().error?.message).toBe('Failed to extract')
  })

  it('disconnects properly', async () => {
    useSSEStore.getState().connect(TEST_ANALYSIS_ID)
    await vi.waitFor(() => expect(useSSEStore.getState().isConnected).toBe(true))

    useSSEStore.getState().disconnect()

    expect(useSSEStore.getState().isConnected).toBe(false)
    expect(useSSEStore.getState().activeAnalysisId).toBe(null)
    expect(getMockEventSource()?.readyState).toBe(2)
  })

  it('resets state correctly', async () => {
    useSSEStore.getState().connect(TEST_ANALYSIS_ID)
    await vi.waitFor(() => expect(useSSEStore.getState().isConnected).toBe(true))

    useSSEStore.getState().reset()

    const state = useSSEStore.getState()
    expect(state.events).toEqual([])
    expect(state.isConnected).toBe(false)
    expect(state.activeAnalysisId).toBe(null)
  })
})

/**
 * Event Buffer Management Tests - Issue #404
 * Tests for event deduplication, size limits, and memory safety
 */
describe('Event Buffer Management', () => {
  beforeEach(() => {
    mockInstance = null
    vi.stubGlobal('EventSource', MockEventSource)
    vi.stubEnv('VITE_API_BASE_URL', 'http://localhost:8000')
    useSSEStore.getState().reset()
  })

  afterEach(() => {
    vi.unstubAllGlobals()
    vi.unstubAllEnvs()
  })

  describe('Event Deduplication', () => {
    it('deduplicates progress events with same stage and status', async () => {
      useSSEStore.getState().connect(TEST_ANALYSIS_ID)
      await vi.waitFor(() => expect(useSSEStore.getState().isConnected).toBe(true))

      // Add initial progress event
      const event1: SSEProgressEvent = {
        type: 'progress',
        analysis_id: TEST_ANALYSIS_ID,
        stage: 'extraction',
        status: 'running',
        timestamp: recentTimestamp(5000), // 5 seconds ago
      }
      getMockEventSource()?.simulateEvent('progress', event1)
      await vi.waitFor(() => expect(useSSEStore.getState().events.length).toBe(1))

      // Add duplicate progress event (same stage, same status)
      const event2: SSEProgressEvent = {
        type: 'progress',
        analysis_id: TEST_ANALYSIS_ID,
        stage: 'extraction',
        status: 'running',
        timestamp: recentTimestamp(3000), // 3 seconds ago (more recent)
      }
      getMockEventSource()?.simulateEvent('progress', event2)

      // Should deduplicate to keep only the more recent event
      await vi.waitFor(() => expect(useSSEStore.getState().events.length).toBe(1))
      expect(useSSEStore.getState().events[0].timestamp).toBe(event2.timestamp)
    })

    it('keeps progress events with different statuses', async () => {
      useSSEStore.getState().connect(TEST_ANALYSIS_ID)
      await vi.waitFor(() => expect(useSSEStore.getState().isConnected).toBe(true))

      const event1: SSEProgressEvent = {
        type: 'progress',
        analysis_id: TEST_ANALYSIS_ID,
        stage: 'extraction',
        status: 'running',
        timestamp: recentTimestamp(1000),
      }
      getMockEventSource()?.simulateEvent('progress', event1)
      await vi.waitFor(() => expect(useSSEStore.getState().events.length).toBe(1))

      const event2: SSEProgressEvent = {
        type: 'progress',
        analysis_id: TEST_ANALYSIS_ID,
        stage: 'extraction',
        status: 'complete',
        timestamp: recentTimestamp(1000),
      }
      getMockEventSource()?.simulateEvent('progress', event2)
      await vi.waitFor(() => expect(useSSEStore.getState().events.length).toBe(2))

      expect(useSSEStore.getState().events.map((e) => e.status)).toEqual(['running', 'complete'])
    })

    it('deduplicates complete events for same analysis', async () => {
      useSSEStore.getState().connect(TEST_ANALYSIS_ID)
      await vi.waitFor(() => expect(useSSEStore.getState().isConnected).toBe(true))

      const baseTime = Date.now()
      const event1: SSECompleteEvent = {
        type: 'complete',
        analysis_id: TEST_ANALYSIS_ID,
        stage: 'artifact_generation',
        status: 'complete',
        timestamp: new Date(baseTime - 2000).toISOString(), // Older timestamp
        artifact_id: TEST_ARTIFACT_ID,
      }
      getMockEventSource()?.simulateEvent('complete', event1)
      await vi.waitFor(() => expect(useSSEStore.getState().events.length).toBe(1))

      const event2: SSECompleteEvent = {
        type: 'complete',
        analysis_id: TEST_ANALYSIS_ID,
        stage: 'workflow',
        status: 'complete',
        timestamp: new Date(baseTime - 1000).toISOString(), // More recent
      }
      getMockEventSource()?.simulateEvent('complete', event2)
      await vi.waitFor(() => expect(useSSEStore.getState().events.length).toBe(1))

      expect(useSSEStore.getState().events[0].timestamp).toBe(event2.timestamp)
    })

    it('deduplicates error events for same stage', async () => {
      useSSEStore.getState().connect(TEST_ANALYSIS_ID)
      await vi.waitFor(() => expect(useSSEStore.getState().isConnected).toBe(true))

      const baseTime = Date.now()
      const event1: SSEErrorEvent = {
        type: 'error',
        analysis_id: TEST_ANALYSIS_ID,
        stage: 'extraction',
        status: 'failed',
        timestamp: new Date(baseTime - 2000).toISOString(),
        error: 'First error',
      }
      getMockEventSource()?.simulateEvent('error', event1)
      await vi.waitFor(() => expect(useSSEStore.getState().events.length).toBe(1))

      const event2: SSEErrorEvent = {
        type: 'error',
        analysis_id: TEST_ANALYSIS_ID,
        stage: 'extraction',
        status: 'failed',
        timestamp: new Date(baseTime - 1000).toISOString(), // More recent
        error: 'Second error',
      }
      getMockEventSource()?.simulateEvent('error', event2)
      await vi.waitFor(() => expect(useSSEStore.getState().events.length).toBe(1))

      expect(useSSEStore.getState().events[0].error).toBe('Second error')
    })
  })

  describe('Event Size Limits', () => {
    it('enforces maximum event limit', async () => {
      useSSEStore.getState().connect(TEST_ANALYSIS_ID)
      await vi.waitFor(() => expect(useSSEStore.getState().isConnected).toBe(true))

      // Add events up to the limit + some more (550 total)
      for (let i = 0; i < 550; i++) {
        const event: SSEProgressEvent = {
          type: 'progress',
          analysis_id: TEST_ANALYSIS_ID,
          stage: `stage_${i}`,
          status: 'running',
          timestamp: recentTimestamp(1000 + i * 10), // Different timestamps
        }
        getMockEventSource()?.simulateEvent('progress', event)
      }

      // Should be capped at MAX_EVENTS (500) or less
      await vi.waitFor(() => {
        const events = useSSEStore.getState().events
        expect(events.length).toBeLessThanOrEqual(500)
      })
    })

    it('prioritizes critical events (error/complete) during cleanup', async () => {
      useSSEStore.getState().connect(TEST_ANALYSIS_ID)
      await vi.waitFor(() => expect(useSSEStore.getState().isConnected).toBe(true))

      // Add regular progress events close to the limit
      for (let i = 0; i < 499; i++) {
        const event: SSEProgressEvent = {
          type: 'progress',
          analysis_id: TEST_ANALYSIS_ID,
          stage: `stage_${i}`,
          status: 'running',
          timestamp: recentTimestamp(1000 + i),
        }
        getMockEventSource()?.simulateEvent('progress', event)
      }

      // Add critical events (should be prioritized)
      const errorEvent: SSEErrorEvent = {
        type: 'error',
        analysis_id: TEST_ANALYSIS_ID,
        stage: 'critical_stage',
        status: 'failed',
        timestamp: recentTimestamp(500),
        error: 'Critical error',
      }
      getMockEventSource()?.simulateEvent('error', errorEvent)

      const completeEvent: SSECompleteEvent = {
        type: 'complete',
        analysis_id: TEST_ANALYSIS_ID,
        stage: 'artifact_generation',
        status: 'complete',
        timestamp: recentTimestamp(500),
        artifact_id: TEST_ARTIFACT_ID,
      }
      getMockEventSource()?.simulateEvent('complete', completeEvent)

      await vi.waitFor(() => {
        const events = useSSEStore.getState().events
        expect(events.length).toBeLessThanOrEqual(501) // 499 + 2 critical
      })

      // Should contain the critical events
      const state = useSSEStore.getState()
      const errorEvents = state.events.filter((e) => e.type === 'error')
      const completeEvents = state.events.filter((e) => e.type === 'complete')
      expect(errorEvents.length).toBeGreaterThan(0)
      expect(completeEvents.length).toBeGreaterThan(0)
      if (errorEvents.length > 0) {
        expect(errorEvents[0].error).toBe('Critical error')
      }
    })
  })

  describe('Disconnect Cleanup', () => {
    it('preserves events on disconnect for UI display', async () => {
      useSSEStore.getState().connect(TEST_ANALYSIS_ID)
      await vi.waitFor(() => expect(useSSEStore.getState().isConnected).toBe(true))

      // Add some events
      const event: SSEProgressEvent = {
        type: 'progress',
        analysis_id: TEST_ANALYSIS_ID,
        stage: 'extraction',
        status: 'running',
        timestamp: recentTimestamp(1000),
      }
      getMockEventSource()?.simulateEvent('progress', event)
      await vi.waitFor(() => expect(useSSEStore.getState().events.length).toBe(1))

      // Disconnect should preserve events for UI display
      useSSEStore.getState().disconnect()

      expect(useSSEStore.getState().events).toHaveLength(1)
      expect(useSSEStore.getState().events[0]).toEqual(event)
      expect(useSSEStore.getState().isConnected).toBe(false)
      expect(useSSEStore.getState().latestEvent).toEqual(event)
    })

    it('preserves analysis metadata on disconnect', async () => {
      const store = useSSEStore.getState()

      // Set some analysis metadata
      store.setAnalysisMetadata({
        artifactId: TEST_ARTIFACT_ID,
        traceId: 'trace-123',
        overallProgress: {
          stage: 'complete',
          progress: 100,
          currentStep: 'Done',
          totalSteps: 5,
          completedSteps: 5,
        },
        hasFailedStages: false,
        failedStagesCount: 0,
      })

      store.disconnect()

      // Should preserve analysis metadata
      const afterDisconnect = useSSEStore.getState()
      expect(afterDisconnect.artifactId).toBe(TEST_ARTIFACT_ID)
      expect(afterDisconnect.traceId).toBe('trace-123')
      expect(afterDisconnect.overallProgress?.stage).toBe('complete')
    })
  })

  describe('Memory Monitoring', () => {
    it('tracks memory usage statistics', () => {
      const store = useSSEStore.getState()

      // Add events to trigger memory monitoring
      for (let i = 0; i < 10; i++) {
        const event: SSEProgressEvent = {
          type: 'progress',
          analysis_id: TEST_ANALYSIS_ID,
          stage: `stage_${i}`,
          status: 'running',
          timestamp: `recentTimestamp(${String(i).padStart(2, '0')}:00Z`,
        }
        store._addEvent(event)
      }

      // Should have memory stats
      expect(store._memoryStats).toBeDefined()
      expect(typeof store._memoryStats.total).toBe('number')
      expect(typeof store._memoryStats.memoryUsage).toBe('number')
    })
  })
})
