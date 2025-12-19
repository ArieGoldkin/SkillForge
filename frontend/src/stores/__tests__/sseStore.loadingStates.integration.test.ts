/**
 * Store Integration Tests for Loading States
 *
 * Tests the integration between SSE store and zustand-computed middleware:
 * - Event processing triggers correct loadingState changes
 * - Connection lifecycle tracking works
 * - Timeout logic triggers at correct times
 * - Computed properties update efficiently
 */

import type { SSEEvent } from '@app-types/sse'
import { describe, expect, it, vi, beforeEach } from 'vitest'

import { deriveLoadingState, getConnectionMessage } from '../computed/loadingStates'
import { useSSEStore } from '../sseStore'

// Helper function for testing loading state computation
function getLoadingState() {
  const state = useSSEStore.getState()
  return deriveLoadingState(state as any) // Cast to match SSEStore type
}

// Mock EventSource for realistic SSE simulation
class MockEventSource {
  url: string
  readyState: number = 0
  onopen?: (event: Event) => void
  onmessage?: (event: MessageEvent) => void
  onerror?: (event: Event) => void
  private listeners = new Map<string, Function>()
  private intervalId?: NodeJS.Timeout

  constructor(url: string) {
    this.url = url

    // Simulate connection establishment
    setTimeout(() => {
      this.readyState = 1
      this.onopen?.(new Event('open'))
    }, 10)

    // Simulate periodic SSE messages
    this.intervalId = setInterval(() => {
      const event = new MessageEvent('message', {
        data: JSON.stringify({
          type: 'progress',
          stage: 'extraction',
          status: 'running',
          timestamp: new Date().toISOString(),
        }),
      })
      this.onmessage?.(event)
    }, 100)
  }

  addEventListener(type: string, listener: Function) {
    this.listeners.set(type, listener)
  }

  removeEventListener(type: string) {
    this.listeners.delete(type)
  }

  close() {
    if (this.intervalId) {
      clearInterval(this.intervalId)
    }
    this.readyState = 2
  }
}

global.EventSource = MockEventSource as any

describe('SSE Store Loading States Integration', () => {
  beforeEach(() => {
    // Reset store state before each test by calling the reset action
    const { reset } = useSSEStore.getState()
    reset()
  })

  describe('Connection Lifecycle Tracking', () => {
    it('sets connectionStartTime when connect is called', () => {
      const beforeConnect = Date.now()
      const { connect } = useSSEStore.getState()
      connect('test-analysis-id')
      const afterConnect = Date.now()

      const { connectionStartTime } = useSSEStore.getState()
      expect(connectionStartTime).toBeGreaterThanOrEqual(beforeConnect)
      expect(connectionStartTime).toBeLessThanOrEqual(afterConnect)
    })

    it('tracks lastActivityTime when events are processed', () => {
      // Simulate connecting first
      const { connect } = useSSEStore.getState()
      connect('test-analysis-id')

      const beforeEvent = Date.now()

      // Simulate receiving an event (this would normally happen via EventSource)
      const mockEvent: SSEEvent = {
        type: 'progress',
        stage: 'extraction',
        status: 'running',
        timestamp: new Date().toISOString(),
        details: { word_count: 1000 },
      }

      // Directly call _addEvent to simulate event processing
      const { _addEvent } = useSSEStore.getState()
      _addEvent(mockEvent)

      const afterEvent = Date.now()
      const { lastActivityTime } = useSSEStore.getState()

      expect(lastActivityTime).toBeGreaterThanOrEqual(beforeEvent)
      expect(lastActivityTime).toBeLessThanOrEqual(afterEvent)
    })
  })

  describe('Loading State Transitions', () => {
    it('starts in disconnected state', () => {
      const state = useSSEStore.getState()
      const loadingState = deriveLoadingState(
        state.isConnected,
        state.connectionStartTime,
        state.lastActivityTime,
        state.latestEvent,
        state.error,
        state.isComplete,
        state._reconnectAttempts
      )
      expect(loadingState.type).toBe('disconnected')
    })

    it('transitions to connecting when connect is called', () => {
      const { connect } = useSSEStore.getState()
      connect('test-analysis-id')

      const state = useSSEStore.getState()
      const loadingState = getLoadingState()

      expect(loadingState.type).toBe('connecting')
      expect(loadingState.startTime).toBe(state.connectionStartTime)
    })

    it('transitions to waiting_for_events when connected but no events', () => {
      const { connect } = useSSEStore.getState()
      connect('test-analysis-id')

      // Simulate connection established (normally done by event handlers)
      useSSEStore.setState({
        isConnected: true,
        connectionStartTime: Date.now(),
      })

      const loadingState = getLoadingState()
      expect(loadingState.type).toBe('waiting_for_events')
    })

    it('transitions to timeout_warning after 30 seconds of waiting', () => {
      const { connect } = useSSEStore.getState()
      connect('test-analysis-id')

      const connectionTime = Date.now() - 31000 // 31 seconds ago
      useSSEStore.setState({
        isConnected: true,
        connectionStartTime: connectionTime,
      })

      const loadingState = getLoadingState()
      expect(loadingState.type).toBe('timeout_warning')
      expect(loadingState.connectedAt).toBe(connectionTime)
    })

    it('transitions to extracting when extraction event received', () => {
      const { connect, _addEvent } = useSSEStore.getState()
      connect('test-analysis-id')
      useSSEStore.setState({ isConnected: true })

      const extractionEvent: SSEEvent = {
        type: 'progress',
        stage: 'extraction',
        status: 'running',
        timestamp: new Date().toISOString(),
        details: { word_count: 1500 },
      }

      _addEvent(extractionEvent)

      const loadingState = getLoadingState()
      expect(loadingState.type).toBe('extracting')
      expect(loadingState.stage).toBe('extraction')
      expect(loadingState.wordCount).toBe(1500)
    })

    it('transitions to analyzing when agent stage event received', () => {
      const { connect, _addEvent } = useSSEStore.getState()
      connect('test-analysis-id')
      useSSEStore.setState({ isConnected: true })

      const analysisEvent: SSEEvent = {
        type: 'progress',
        stage: 'tech_comparison',
        status: 'running',
        timestamp: new Date().toISOString(),
        details: { agent: 'TechComparisonAgent' },
      }

      _addEvent(analysisEvent)

      const loadingState = getLoadingState()
      expect(loadingState.type).toBe('analyzing')
      expect(loadingState.stage).toBe('tech_comparison')
      expect(loadingState.progress).toBe(0) // No progress calculation yet
    })

    it('transitions to generating when artifact generation starts', () => {
      const { connect, _addEvent } = useSSEStore.getState()
      connect('test-analysis-id')
      useSSEStore.setState({ isConnected: true })

      const generationEvent: SSEEvent = {
        type: 'progress',
        stage: 'artifact_generation',
        status: 'running',
        timestamp: new Date().toISOString(),
      }

      _addEvent(generationEvent)

      const loadingState = getLoadingState()
      expect(loadingState.type).toBe('generating')
      expect(loadingState.stage).toBe('artifact_generation')
    })

    it('transitions to complete when analysis finishes', () => {
      const { connect } = useSSEStore.getState()
      connect('test-analysis-id')
      useSSEStore.setState({
        isConnected: true,
        isComplete: true,
        artifactId: 'test-artifact-123',
      })

      const loadingState = getLoadingState()
      expect(loadingState.type).toBe('complete')
      expect(loadingState.artifactId).toBe('test-artifact-123')
    })

    it('transitions to error when error occurs', () => {
      const { connect } = useSSEStore.getState()
      connect('test-analysis-id')
      useSSEStore.setState({
        isConnected: true,
        error: new Error('Network timeout'),
      })

      const loadingState = getLoadingState()
      expect(loadingState.type).toBe('error')
      expect(loadingState.error).toBe('Network timeout')
    })
  })

  describe('Computed Property Efficiency', () => {
    it('only recomputes when relevant state changes', () => {
      const { connect } = useSSEStore.getState()
      connect('test-analysis-id')

      // Get initial computed values
      const { loadingState: initialLoadingState, connectionMessage: initialConnectionMessage } =
        useSSEStore.getState()

      // Change irrelevant state - should not trigger recomputation
      useSSEStore.setState({ activeAnalysisId: 'different-id' })

      // Computed values should be the same (zustand-computed caches them)
      const { loadingState, connectionMessage } = useSSEStore.getState()
      expect(loadingState).toBe(initialLoadingState)
      expect(connectionMessage).toBe(initialConnectionMessage)

      // Change relevant state - should trigger recomputation
      useSSEStore.setState({ isConnected: true })

      const newLoadingState = getLoadingState()
      expect(newLoadingState.type).toBe('waiting_for_events')
      expect(getConnectionMessage(useSSEStore.getState())).toBe('Preparing analysis...')
    })

    it('recomputes when events array changes', () => {
      const { connect, _addEvent } = useSSEStore.getState()
      connect('test-analysis-id')
      useSSEStore.setState({ isConnected: true })

      const loadingState = getLoadingState()
      expect(loadingState.type).toBe('waiting_for_events')

      // Add an event
      const event: SSEEvent = {
        type: 'progress',
        stage: 'extraction',
        status: 'running',
        timestamp: new Date().toISOString(),
      }

      _addEvent(event)

      const newLoadingState = getLoadingState()
      expect(newLoadingState.type).toBe('extracting')
    })

    it('recomputes when connection timing changes', () => {
      const { connect } = useSSEStore.getState()
      connect('test-analysis-id')
      useSSEStore.setState({ isConnected: true })

      const loadingState = getLoadingState()
      expect(loadingState.type).toBe('waiting_for_events')

      // Simulate timeout
      const oldTime = Date.now() - 31000
      useSSEStore.setState({ connectionStartTime: oldTime })

      const newLoadingState = getLoadingState()
      expect(newLoadingState.type).toBe('timeout_warning')
    })
  })

  describe('Progress Calculation', () => {
    it('calculates analysis progress correctly', () => {
      const { connect, _addEvent } = useSSEStore.getState()
      connect('test-analysis-id')
      useSSEStore.setState({ isConnected: true })

      // Add some completed stages
      const completedStages = [
        {
          type: 'progress' as const,
          stage: 'extraction' as const,
          status: 'complete' as const,
          timestamp: new Date().toISOString(),
        },
        {
          type: 'progress' as const,
          stage: 'tech_comparison' as const,
          status: 'complete' as const,
          timestamp: new Date().toISOString(),
        },
      ]

      // Add events one by one
      completedStages.forEach((event) => _addEvent(event))

      // Start analyzing
      const analyzingEvent: SSEEvent = {
        type: 'progress',
        stage: 'security_audit',
        status: 'running',
        timestamp: new Date().toISOString(),
      }
      _addEvent(analyzingEvent)

      const loadingState = getLoadingState()
      expect(loadingState.type).toBe('analyzing')
      expect(loadingState.progress).toBeGreaterThan(0)
      expect(loadingState.progress).toBeLessThanOrEqual(100)
    })
  })

  describe('Reset Functionality', () => {
    it('clears connection tracking on reset', () => {
      const { connect, reset } = useSSEStore.getState()
      connect('test-analysis-id')
      useSSEStore.setState({
        isConnected: true,
        connectionStartTime: Date.now(),
        lastActivityTime: Date.now(),
      })

      const { connectionStartTime, lastActivityTime } = useSSEStore.getState()
      expect(connectionStartTime).not.toBeNull()
      expect(lastActivityTime).not.toBeNull()

      reset()

      const { connectionStartTime: newConnectionStartTime, lastActivityTime: newLastActivityTime } =
        useSSEStore.getState()
      const loadingState = getLoadingState()
      expect(newConnectionStartTime).toBeNull()
      expect(newLastActivityTime).toBeNull()
      expect(loadingState.type).toBe('disconnected')
    })
  })
})
