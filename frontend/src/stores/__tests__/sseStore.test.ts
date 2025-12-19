import type { SSECompleteEvent, SSEErrorEvent, SSEProgressEvent } from '@app-types/sse'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import { useSSEStore } from '../sseStore'

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

describe('SSE Store', () => {
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
