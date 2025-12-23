/**
 * Unit tests for SSE Store Helper Functions
 * Tests bug fixes for:
 * 1. JSON parse error on connection failure (event.data undefined guard)
 * 2. Infinite reconnection loop (permanentlyFailed flag)
 */

import type { SSEErrorEvent, SSEProgressEvent } from '@app-types/sse'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import type { SSEStore } from '../sseStore'
import { closeConnection, createConnection, type ListenerRefs } from '../sseStoreHelpers'

// Valid UUIDs for testing
const TEST_ANALYSIS_ID = '123e4567-e89b-12d3-a456-426614174000'

/**
 * Mock EventSource - Class-based mock for browser EventSource API
 */
let mockInstance: MockEventSource | null = null
let shouldAutoConnect = true

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

    // Simulate async connection open (can be controlled in tests)
    // Use two setTimeouts to ensure event listeners are attached first
    if (shouldAutoConnect) {
      setTimeout(() => {
        setTimeout(() => {
          if (this.readyState === 0 && this.onopen) {
            this.readyState = 1
            this.onopen()
          }
        }, 0)
      }, 0)
    }
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

  simulateErrorEventWithoutData(type: string) {
    const listener = this.listeners.get(type)
    if (listener) {
      // Simulate connection error - no data property
      listener(new MessageEvent(type))
    }
  }

  simulateConnectionError() {
    if (this.onerror) {
      this.onerror(new Event('error'))
    }
  }

  simulateOpen() {
    this.readyState = 1
    if (this.onopen) {
      this.onopen()
    }
  }
}

function setAutoConnect(value: boolean) {
  shouldAutoConnect = value
}

function getMockEventSource(): MockEventSource | null {
  return mockInstance
}

/**
 * Create a mock StoreAPI for testing
 *
 * The mock includes all internal state fields that were moved from module-level
 * to the Zustand store for proper memory management.
 */
function createMockStore(): {
  store: {
    getState: () => SSEStore
    setState: (partial: Partial<SSEStore> | ((state: SSEStore) => Partial<SSEStore>)) => void
  }
  state: SSEStore
} {
  const state: SSEStore = {
    // Public state
    events: [],
    latestEvent: null,
    error: null,
    isConnected: false,
    isComplete: false,
    activeAnalysisId: null,

    // Internal state (moved from module-level for memory safety)
    _eventSource: null,
    _reconnectAttempts: 0,
    _reconnectTimeoutId: null,
    _permanentlyFailed: false,
    _listenerRefs: null as ListenerRefs | null,

    // Actions
    connect: vi.fn(),
    disconnect: vi.fn(),
    reset: vi.fn(),
    startPolling: vi.fn(),
    stopPolling: vi.fn(),
    _addEvent: vi.fn(),
    _setInternalState: vi.fn(),
  }

  const store = {
    getState: () => state,
    setState: (partial: Partial<SSEStore> | ((state: SSEStore) => Partial<SSEStore>)) => {
      if (typeof partial === 'function') {
        Object.assign(state, partial(state))
      } else {
        Object.assign(state, partial)
      }
    },
  }

  // Wire up _addEvent to actually add events (for tests that check events array)
  state._addEvent = vi.fn((event) => {
    state.events = [...state.events, event]
    state.latestEvent = event
  })

  return { store, state }
}

describe('SSE Store Helpers - Bug Fixes', () => {
  beforeEach(() => {
    mockInstance = null
    shouldAutoConnect = true
    vi.stubGlobal('EventSource', MockEventSource)
    vi.stubEnv('VITE_API_BASE_URL', 'http://localhost:8500')
    vi.useFakeTimers()
  })

  afterEach(() => {
    vi.unstubAllGlobals()
    vi.unstubAllEnvs()
    vi.useRealTimers()
    vi.restoreAllMocks()
  })

  describe('Bug Fix 1: JSON parse error on connection failure', () => {
    it('should return early when error event has undefined data', async () => {
      const { store } = createMockStore()
      const consoleWarnSpy = vi.spyOn(console, 'warn').mockImplementation(() => {})
      const consoleErrorSpy = vi.spyOn(console, 'error').mockImplementation(() => {})

      createConnection(TEST_ANALYSIS_ID, store)
      await vi.runAllTimersAsync()

      // Simulate connection error event with no data (undefined)
      getMockEventSource()?.simulateErrorEventWithoutData('error')

      // Should log warning but not throw or set error
      expect(consoleWarnSpy).toHaveBeenCalledWith(
        '[WARN] Received error event with no data - likely connection error',
        expect.objectContaining({
          eventType: 'error',
        })
      )
      expect(consoleErrorSpy).not.toHaveBeenCalled()

      // Should not add event to store or set error
      expect(store.getState().events).toEqual([])
      expect(store.getState().latestEvent).toBeNull()

      consoleWarnSpy.mockRestore()
      consoleErrorSpy.mockRestore()
    })

    it('should return early when error event has null data', async () => {
      const { store } = createMockStore()
      const consoleWarnSpy = vi.spyOn(console, 'warn').mockImplementation(() => {})

      createConnection(TEST_ANALYSIS_ID, store)
      await vi.runAllTimersAsync()

      // Manually create MessageEvent with null data
      const listener = getMockEventSource()?.listeners.get('error')
      if (listener) {
        listener(new MessageEvent('error', { data: null }))
      }

      expect(consoleWarnSpy).toHaveBeenCalledWith(
        '[WARN] Received error event with no data - likely connection error',
        expect.objectContaining({
          eventType: 'error',
        })
      )
      expect(store.getState().events).toEqual([])

      consoleWarnSpy.mockRestore()
    })

    it('should parse and handle valid JSON error events normally', async () => {
      const { store } = createMockStore()
      const consoleErrorSpy = vi.spyOn(console, 'error').mockImplementation(() => {})

      createConnection(TEST_ANALYSIS_ID, store)
      await vi.runAllTimersAsync()

      const errorEvent: SSEErrorEvent = {
        type: 'error',
        analysis_id: TEST_ANALYSIS_ID,
        stage: 'extraction',
        status: 'failed',
        timestamp: new Date().toISOString(),
        error: 'Extraction failed',
        details: { error: 'Failed to extract content', error_code: 'EXTRACTION_ERROR' },
      }

      getMockEventSource()?.simulateEvent('error', errorEvent)

      // Should handle error event properly
      expect(consoleErrorSpy).toHaveBeenCalledWith(
        '[ERROR] Server sent error event',
        expect.objectContaining({
          validatedData: errorEvent,
        })
      )
      expect(store.getState().events).toHaveLength(1)
      expect(store.getState().latestEvent).toEqual(errorEvent)
      expect(store.getState().error?.message).toBe('Extraction failed')

      consoleErrorSpy.mockRestore()
    })

    it('should handle error event with error in details field', async () => {
      const { store } = createMockStore()
      const consoleErrorSpy = vi.spyOn(console, 'error').mockImplementation(() => {})

      createConnection(TEST_ANALYSIS_ID, store)
      await vi.runAllTimersAsync()

      const errorEvent: SSEErrorEvent = {
        type: 'error',
        analysis_id: TEST_ANALYSIS_ID,
        stage: 'embedding',
        status: 'failed',
        timestamp: new Date().toISOString(),
        details: { error: 'Embedding failed', error_code: 'EMBEDDING_ERROR' },
      }

      getMockEventSource()?.simulateEvent('error', errorEvent)

      expect(store.getState().error?.message).toBe('Embedding failed')

      consoleErrorSpy.mockRestore()
    })

    it('should use fallback error message when no error field provided', async () => {
      const { store } = createMockStore()
      const consoleErrorSpy = vi.spyOn(console, 'error').mockImplementation(() => {})

      createConnection(TEST_ANALYSIS_ID, store)
      await vi.runAllTimersAsync()

      const errorEvent: SSEErrorEvent = {
        type: 'error',
        analysis_id: TEST_ANALYSIS_ID,
        stage: 'unknown',
        status: 'failed',
        timestamp: new Date().toISOString(),
      }

      getMockEventSource()?.simulateEvent('error', errorEvent)

      expect(store.getState().error?.message).toBe('Analysis failed')

      consoleErrorSpy.mockRestore()
    })
  })

  describe('Bug Fix 2: Infinite reconnection loop', () => {
    it('should start polling fallback after max reconnection attempts', async () => {
      const { store, state } = createMockStore()
      const consoleErrorSpy = vi.spyOn(console, 'error').mockImplementation(() => {})

      // Mock startPolling to track calls
      const startPollingMock = vi.fn()
      state.startPolling = startPollingMock

      // Disable auto-connect to fully control connection lifecycle
      setAutoConnect(false)

      // First connection attempt
      createConnection(TEST_ANALYSIS_ID, store)
      await vi.runAllTimersAsync()

      // Simulate immediate connection failures for all 3 attempts
      // Each failure triggers a new connection attempt
      for (let i = 0; i < 4; i++) {
        // 4 times: initial + 3 reconnects
        getMockEventSource()?.simulateConnectionError()
        await vi.runAllTimersAsync()
      }

      // Should reach max reconnection attempts and start polling fallback
      expect(consoleErrorSpy).toHaveBeenCalledWith(
        '[ERROR] SSE max reconnection attempts reached, starting polling fallback',
        expect.objectContaining({
          reason: 'persistent_connection_failure',
        })
      )
      expect(store.getState().error?.message).toBe(
        'SSE connection failed. Using polling fallback to continue receiving updates.'
      )

      // Should have called startPolling as fallback
      expect(startPollingMock).toHaveBeenCalledWith(TEST_ANALYSIS_ID)

      consoleErrorSpy.mockRestore()
    })

    it('should allow new connection when switching to different analysis', async () => {
      const { store } = createMockStore()
      const consoleErrorSpy = vi.spyOn(console, 'error').mockImplementation(() => {})

      // Disable auto-connect to fully control connection lifecycle
      setAutoConnect(false)

      // First connection attempt
      createConnection(TEST_ANALYSIS_ID, store)
      await vi.runAllTimersAsync()

      // Simulate connection failures to reach max attempts
      for (let i = 0; i < 4; i++) {
        // 4 times: initial + 3 reconnects
        getMockEventSource()?.simulateConnectionError()
        await vi.runAllTimersAsync()
      }

      expect(store.getState().error?.message).toContain(
        'SSE connection failed. Using polling fallback'
      )

      // Re-enable auto-connect for new analysis
      setAutoConnect(true)

      // Connect to DIFFERENT analysis - should allow new connection
      createConnection('test-456', store)
      await vi.runAllTimersAsync()

      // Should successfully connect to new analysis
      expect(store.getState().activeAnalysisId).toBe('test-456')
      expect(store.getState().isConnected).toBe(true)
      expect(getMockEventSource()?.url).toContain('test-456')

      consoleErrorSpy.mockRestore()
    })

    it('should use exponential backoff and start polling after max attempts', async () => {
      const { store, state } = createMockStore()
      const consoleErrorSpy = vi.spyOn(console, 'error').mockImplementation(() => {})
      const consoleWarnSpy = vi.spyOn(console, 'warn').mockImplementation(() => {})

      // Mock startPolling to track calls
      const startPollingMock = vi.fn()
      state.startPolling = startPollingMock

      // Disable auto-connect to fully control connection lifecycle
      setAutoConnect(false)

      // First connection attempt
      createConnection(TEST_ANALYSIS_ID, store)
      await vi.runAllTimersAsync()

      // Trigger connection error - should schedule reconnect attempt 1
      getMockEventSource()?.simulateConnectionError()
      await vi.runAllTimersAsync()

      expect(consoleWarnSpy).toHaveBeenNthCalledWith(
        1,
        '[WARN] SSE reconnection scheduled',
        expect.objectContaining({
          delay: 1000,
          attempt: 1,
          maxAttempts: 3,
        })
      )

      // Trigger connection error - should schedule reconnect attempt 2
      getMockEventSource()?.simulateConnectionError()
      await vi.runAllTimersAsync()

      expect(consoleWarnSpy).toHaveBeenNthCalledWith(
        2,
        '[WARN] SSE reconnection scheduled',
        expect.objectContaining({
          delay: 2000,
          attempt: 2,
          maxAttempts: 3,
        })
      )

      // Trigger connection error - should schedule reconnect attempt 3
      getMockEventSource()?.simulateConnectionError()
      await vi.runAllTimersAsync()

      expect(consoleWarnSpy).toHaveBeenNthCalledWith(
        3,
        '[WARN] SSE reconnection scheduled',
        expect.objectContaining({
          delay: 4000,
          attempt: 3,
          maxAttempts: 3,
        })
      )

      // Trigger final connection error - should start polling fallback
      getMockEventSource()?.simulateConnectionError()
      await vi.runAllTimersAsync()

      // After 3rd attempt, should start polling fallback
      expect(consoleErrorSpy).toHaveBeenCalledWith(
        '[ERROR] SSE max reconnection attempts reached, starting polling fallback',
        expect.objectContaining({
          reason: 'persistent_connection_failure',
        })
      )

      // Should have called startPolling
      expect(startPollingMock).toHaveBeenCalledWith(TEST_ANALYSIS_ID)

      consoleErrorSpy.mockRestore()
      consoleWarnSpy.mockRestore()
    })

    it('should use exponential backoff for reconnection attempts', async () => {
      const { store } = createMockStore()
      const consoleWarnSpy = vi.spyOn(console, 'warn').mockImplementation(() => {})
      const consoleErrorSpy = vi.spyOn(console, 'error').mockImplementation(() => {})

      createConnection(TEST_ANALYSIS_ID, store)
      await vi.runAllTimersAsync()

      // First failure - should wait 1000ms (1s)
      getMockEventSource()?.simulateConnectionError()
      expect(consoleWarnSpy).toHaveBeenCalledWith(
        '[WARN] SSE reconnection scheduled',
        expect.objectContaining({
          delay: 1000,
          attempt: 1,
          maxAttempts: 3,
        })
      )

      await vi.advanceTimersByTimeAsync(1000)

      // Second failure - should wait 2000ms (2s)
      getMockEventSource()?.simulateConnectionError()
      expect(consoleWarnSpy).toHaveBeenCalledWith(
        '[WARN] SSE reconnection scheduled',
        expect.objectContaining({
          delay: 2000,
          attempt: 2,
          maxAttempts: 3,
        })
      )

      await vi.advanceTimersByTimeAsync(2000)

      // Third failure - should wait 4000ms (4s - max)
      getMockEventSource()?.simulateConnectionError()
      expect(consoleWarnSpy).toHaveBeenCalledWith(
        '[WARN] SSE reconnection scheduled',
        expect.objectContaining({
          delay: 4000,
          attempt: 3,
          maxAttempts: 3,
        })
      )

      consoleWarnSpy.mockRestore()
      consoleErrorSpy.mockRestore()
    })

    it('should reset reconnect attempts on successful connection', async () => {
      const { store } = createMockStore()
      const consoleWarnSpy = vi.spyOn(console, 'warn').mockImplementation(() => {})
      const consoleErrorSpy = vi.spyOn(console, 'error').mockImplementation(() => {})

      // First connection succeeds (auto-connect enabled by default)
      createConnection(TEST_ANALYSIS_ID, store)
      await vi.runAllTimersAsync()
      expect(store.getState().isConnected).toBe(true)

      // Trigger first failure
      getMockEventSource()?.simulateConnectionError()

      expect(consoleWarnSpy).toHaveBeenCalledWith(
        '[WARN] SSE reconnection scheduled',
        expect.objectContaining({
          delay: 1000,
          attempt: 1,
        })
      )

      consoleWarnSpy.mockClear()

      // Let the reconnection happen
      await vi.runAllTimersAsync()

      // Now manually open the connection to simulate successful reconnect
      getMockEventSource()?.simulateOpen()

      // Trigger second failure - should start from attempt 1 if reset worked
      getMockEventSource()?.simulateConnectionError()

      // If reconnectAttempts was reset by onopen, this should show attempt 1/3
      // If it wasn't reset, this will show attempt 2/3
      const warnCalls = consoleWarnSpy.mock.calls
      const hasAttempt1 = warnCalls.some((call) => call[1]?.attempt === 1)

      // Note: This test verifies the behavior exists in the code
      // The actual reset happens in handleOpen (line 48 of sseStoreHelpers.ts)
      expect(hasAttempt1).toBe(true)

      consoleWarnSpy.mockRestore()
      consoleErrorSpy.mockRestore()
    })
  })

  describe('createConnection', () => {
    it('should create EventSource with correct URL', async () => {
      const { store } = createMockStore()

      createConnection('analysis-456', store)
      await vi.runAllTimersAsync()

      expect(getMockEventSource()?.url).toBe(
        'http://localhost:8500/api/v1/analyze/analysis-456/stream'
      )
      expect(store.getState().activeAnalysisId).toBe('analysis-456')
    })

    it('should prevent duplicate connections to same analysis', async () => {
      const { store } = createMockStore()
      const consoleWarnSpy = vi.spyOn(console, 'warn').mockImplementation(() => {})

      // Set up initial state as already connected
      store.setState({
        activeAnalysisId: TEST_ANALYSIS_ID,
        isConnected: true,
      })

      // Try to connect again with same ID
      createConnection(TEST_ANALYSIS_ID, store)

      expect(consoleWarnSpy).toHaveBeenCalledWith(
        '[WARN] SSE connection attempt for already connected analysis',
        expect.objectContaining({
          isConnected: true,
        })
      )

      consoleWarnSpy.mockRestore()
    })

    it('should disconnect existing connection when switching analysis', async () => {
      const { store } = createMockStore()

      // Mock disconnect function
      const disconnectMock = vi.fn()
      store.setState({ disconnect: disconnectMock })

      // First connection
      createConnection(TEST_ANALYSIS_ID, store)
      await vi.runAllTimersAsync()

      store.setState({
        activeAnalysisId: TEST_ANALYSIS_ID,
        isConnected: true,
      })

      // Connect to different analysis
      createConnection('test-456', store)

      // Should call disconnect
      expect(disconnectMock).toHaveBeenCalled()
    })

    it('should handle progress events correctly', async () => {
      const { store } = createMockStore()

      createConnection(TEST_ANALYSIS_ID, store)
      await vi.runAllTimersAsync()

      const progressEvent: SSEProgressEvent = {
        type: 'progress',
        analysis_id: TEST_ANALYSIS_ID,
        stage: 'extraction',
        status: 'running',
        timestamp: new Date().toISOString(),
        details: { word_count: 1500 },
      }

      getMockEventSource()?.simulateEvent('progress', progressEvent)

      expect(store.getState().events).toHaveLength(1)
      expect(store.getState().latestEvent).toEqual(progressEvent)
    })

    it('should clear pending reconnect timeout on new connection', async () => {
      const { store } = createMockStore()
      const consoleWarnSpy = vi.spyOn(console, 'warn').mockImplementation(() => {})
      const consoleErrorSpy = vi.spyOn(console, 'error').mockImplementation(() => {})

      // First connection
      createConnection(TEST_ANALYSIS_ID, store)
      await vi.runAllTimersAsync()

      // Trigger connection error to start reconnect
      getMockEventSource()?.simulateConnectionError()

      // Should have pending reconnect timeout
      expect(consoleWarnSpy).toHaveBeenCalledWith(
        '[WARN] SSE reconnection scheduled',
        expect.any(Object)
      )

      // Create new connection before timeout fires
      createConnection('test-456', store)
      await vi.runAllTimersAsync()

      // Should successfully connect to new analysis
      expect(store.getState().activeAnalysisId).toBe('test-456')

      consoleWarnSpy.mockRestore()
      consoleErrorSpy.mockRestore()
    })
  })

  describe('closeConnection', () => {
    it('should close EventSource and reset state', async () => {
      const { store } = createMockStore()

      createConnection(TEST_ANALYSIS_ID, store)
      await vi.runAllTimersAsync()

      store.setState({
        isConnected: true,
        activeAnalysisId: TEST_ANALYSIS_ID,
      })

      closeConnection(store)

      expect(store.getState().isConnected).toBe(false)
      expect(store.getState().activeAnalysisId).toBe(null)
      expect(getMockEventSource()?.readyState).toBe(2) // CLOSED
    })

    it('should clear pending reconnect timeout', async () => {
      const { store } = createMockStore()
      const consoleWarnSpy = vi.spyOn(console, 'warn').mockImplementation(() => {})
      const consoleErrorSpy = vi.spyOn(console, 'error').mockImplementation(() => {})

      createConnection(TEST_ANALYSIS_ID, store)
      await vi.runAllTimersAsync()

      // Trigger connection error to start reconnect
      getMockEventSource()?.simulateConnectionError()

      // Close connection before timeout fires
      closeConnection(store)

      // Advance timers - reconnect should not happen
      await vi.runAllTimersAsync()

      expect(store.getState().activeAnalysisId).toBe(null)
      expect(store.getState().isConnected).toBe(false)

      consoleWarnSpy.mockRestore()
      consoleErrorSpy.mockRestore()
    })

    it('should reset reconnect attempts counter', async () => {
      const { store } = createMockStore()
      const consoleWarnSpy = vi.spyOn(console, 'warn').mockImplementation(() => {})
      const consoleErrorSpy = vi.spyOn(console, 'error').mockImplementation(() => {})

      createConnection(TEST_ANALYSIS_ID, store)
      await vi.runAllTimersAsync()

      // Trigger some connection errors
      getMockEventSource()?.simulateConnectionError()
      await vi.runAllTimersAsync()

      getMockEventSource()?.simulateConnectionError()
      await vi.runAllTimersAsync()

      expect(consoleWarnSpy).toHaveBeenCalledWith(
        '[WARN] SSE reconnection scheduled',
        expect.objectContaining({
          attempt: 2,
          maxAttempts: 3,
          reason: 'connection_lost',
        })
      )

      // Close connection
      closeConnection(store)

      // New connection should start from attempt 1
      consoleWarnSpy.mockClear()
      createConnection(TEST_ANALYSIS_ID, store)
      await vi.runAllTimersAsync()

      getMockEventSource()?.simulateConnectionError()
      await vi.runAllTimersAsync()

      expect(consoleWarnSpy).toHaveBeenCalledWith(
        '[WARN] SSE reconnection scheduled',
        expect.objectContaining({
          attempt: 1,
          maxAttempts: 3,
        })
      )

      consoleWarnSpy.mockRestore()
      consoleErrorSpy.mockRestore()
    })

    it('should handle closing when no connection exists', () => {
      const { store } = createMockStore()

      // Should not throw
      expect(() => closeConnection(store)).not.toThrow()

      expect(store.getState().isConnected).toBe(false)
      expect(store.getState().activeAnalysisId).toBe(null)
    })
  })
})
