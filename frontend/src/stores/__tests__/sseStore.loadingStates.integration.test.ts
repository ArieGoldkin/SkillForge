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

import { useSSEStore } from '../sseStore'

// Mock EventSource to prevent real connections
global.EventSource = vi.fn().mockImplementation(() => ({
  addEventListener: vi.fn(),
  removeEventListener: vi.fn(),
  close: vi.fn(),
  readyState: 1,
  url: 'mock-url',
}))

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
      const { loadingState } = useSSEStore.getState()
      expect(loadingState.type).toBe('disconnected')
    })

    it('transitions to connecting when connect is called', () => {
      const { connect } = useSSEStore.getState()
      connect('test-analysis-id')

      const { loadingState, connectionStartTime } = useSSEStore.getState()
      expect(loadingState.type).toBe('connecting')
      expect(loadingState.startTime).toBe(connectionStartTime)
    })

    it('transitions to waiting_for_events when connected but no events', () => {
      const { connect } = useSSEStore.getState()
      connect('test-analysis-id')

      // Simulate connection established (normally done by event handlers)
      useSSEStore.setState({
        isConnected: true,
        connectionStartTime: Date.now(),
      })

      const { loadingState } = useSSEStore.getState()
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

      const { loadingState } = useSSEStore.getState()
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

      const { loadingState } = useSSEStore.getState()
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

      const { loadingState } = useSSEStore.getState()
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

      const { loadingState } = useSSEStore.getState()
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

      const { loadingState } = useSSEStore.getState()
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

      const { loadingState } = useSSEStore.getState()
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

      const { loadingState: newLoadingState, connectionMessage: newConnectionMessage } =
        useSSEStore.getState()
      expect(newLoadingState.type).toBe('waiting_for_events')
      expect(newConnectionMessage).toBe('Preparing analysis...')
    })

    it('recomputes when events array changes', () => {
      const { connect, _addEvent } = useSSEStore.getState()
      connect('test-analysis-id')
      useSSEStore.setState({ isConnected: true })

      const { loadingState } = useSSEStore.getState()
      expect(loadingState.type).toBe('waiting_for_events')

      // Add an event
      const event: SSEEvent = {
        type: 'progress',
        stage: 'extraction',
        status: 'running',
        timestamp: new Date().toISOString(),
      }

      _addEvent(event)

      const { loadingState: newLoadingState } = useSSEStore.getState()
      expect(newLoadingState.type).toBe('extracting')
    })

    it('recomputes when connection timing changes', () => {
      const { connect } = useSSEStore.getState()
      connect('test-analysis-id')
      useSSEStore.setState({ isConnected: true })

      const { loadingState } = useSSEStore.getState()
      expect(loadingState.type).toBe('waiting_for_events')

      // Simulate timeout
      const oldTime = Date.now() - 31000
      useSSEStore.setState({ connectionStartTime: oldTime })

      const { loadingState: newLoadingState } = useSSEStore.getState()
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

      const { loadingState } = useSSEStore.getState()
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

      const {
        connectionStartTime: newConnectionStartTime,
        lastActivityTime: newLastActivityTime,
        loadingState,
      } = useSSEStore.getState()
      expect(newConnectionStartTime).toBeNull()
      expect(newLastActivityTime).toBeNull()
      expect(loadingState.type).toBe('disconnected')
    })
  })
})
