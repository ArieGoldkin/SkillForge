import { useSSEStore } from '@stores/sseStore'
import { renderHook, waitFor } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import type { SSEProgressEvent } from '@/schemas/sse'

import { useSSE } from '../useSSE'

// Valid UUIDs for testing
const TEST_ANALYSIS_ID = '123e4567-e89b-12d3-a456-426614174000'
const _TEST_ANALYSIS_ID_2 = 'a1b2c3d4-e5f6-47a8-b9c0-d1e2f3a4b5c6'

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

describe('useSSE Hook', () => {
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

  it('connects when mounted', async () => {
    const { result } = renderHook(() => useSSE(TEST_ANALYSIS_ID))

    await waitFor(() => expect(result.current.isConnected).toBe(true))
    expect(getMockEventSource()?.url).toContain(TEST_ANALYSIS_ID)
  })

  it('returns events from store', async () => {
    const { result } = renderHook(() => useSSE(TEST_ANALYSIS_ID))
    await waitFor(() => expect(result.current.isConnected).toBe(true))

    const event: SSEProgressEvent = {
      type: 'progress',
      analysis_id: TEST_ANALYSIS_ID,
      stage: 'extraction',
      status: 'running',
      timestamp: new Date().toISOString(),
    }

    getMockEventSource()?.simulateEvent('progress', event)

    await waitFor(() => expect(result.current.events.length).toBe(1))
    expect(result.current.latestEvent).toEqual(event)
  })

  it('shares state across instances', async () => {
    const { result: result1 } = renderHook(() => useSSE(TEST_ANALYSIS_ID))
    const { result: result2 } = renderHook(() => useSSE(TEST_ANALYSIS_ID))

    await waitFor(() => {
      expect(result1.current.isConnected).toBe(true)
      expect(result2.current.isConnected).toBe(true)
    })

    const event: SSEProgressEvent = {
      type: 'progress',
      analysis_id: TEST_ANALYSIS_ID,
      stage: 'extraction',
      status: 'running',
      timestamp: new Date().toISOString(),
    }

    getMockEventSource()?.simulateEvent('progress', event)

    await waitFor(() => {
      expect(result1.current.events.length).toBe(1)
      expect(result2.current.events.length).toBe(1)
    })
  })
})
