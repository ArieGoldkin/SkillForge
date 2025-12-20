/**
 * Memory Leak Prevention Tests for SSE Store
 *
 * Issue #393: Module-level state never gets cleaned up, memory grows ~50MB per analysis
 *
 * Tests verify the four compound leak fixes:
 * 1. Events array bounded at MAX_EVENTS (500)
 * 2. Module-level state moved to Zustand store
 * 3. Proper listener cleanup with removeEventListener
 * 4. Complete reset on disconnect (permanentlyFailed flag)
 */

import type { SSEProgressEvent } from '@app-types/sse'
import { act, renderHook } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import { useSSEStore } from '../sseStore'
import { MAX_EVENTS } from '../sseStoreHelpers'

// Valid UUID for testing
const TEST_ANALYSIS_ID = '123e4567-e89b-12d3-a456-426614174000'

/**
 * Create a mock progress event for testing
 */
function createProgressEvent(index: number): SSEProgressEvent {
  return {
    type: 'progress',
    analysis_id: TEST_ANALYSIS_ID,
    stage: `stage_${index}`, // Different stage for each event to avoid deduplication
    status: 'running',
    timestamp: new Date().toISOString(),
    details: { word_count: index * 100, index },
  }
}

describe('SSE Store Memory Safety', () => {
  beforeEach(() => {
    // Reset store to clean state before each test
    const { result } = renderHook(() => useSSEStore())
    act(() => {
      result.current.reset()
    })
  })

  afterEach(() => {
    vi.restoreAllMocks()
  })

  describe('Events Array Size Limit (MAX_EVENTS)', () => {
    it('should export MAX_EVENTS constant', () => {
      expect(MAX_EVENTS).toBe(500)
    })

    it('should cap events array at MAX_EVENTS', () => {
      const { result } = renderHook(() => useSSEStore())

      // Add more than MAX_EVENTS events
      act(() => {
        for (let i = 0; i < MAX_EVENTS + 100; i++) {
          result.current._addEvent(createProgressEvent(i))
        }
      })

      // Array should be capped at MAX_EVENTS
      expect(result.current.events).toHaveLength(MAX_EVENTS)
    })

    it('should keep most recent events when capped', () => {
      const { result } = renderHook(() => useSSEStore())
      const totalEvents = MAX_EVENTS + 50

      act(() => {
        for (let i = 0; i < totalEvents; i++) {
          result.current._addEvent(createProgressEvent(i))
        }
      })

      // First event should be the oldest kept (event index 50)
      const firstEvent = result.current.events[0] as SSEProgressEvent
      expect(firstEvent.details?.index).toBe(50)

      // Last event should be the most recent (event index totalEvents - 1)
      const lastEvent = result.current.events[MAX_EVENTS - 1] as SSEProgressEvent
      expect(lastEvent.details?.index).toBe(totalEvents - 1)
    })

    it('should set latestEvent on _addEvent', () => {
      const { result } = renderHook(() => useSSEStore())
      const event = createProgressEvent(42)

      act(() => {
        result.current._addEvent(event)
      })

      expect(result.current.latestEvent).toEqual(event)
    })
  })

  describe('Store State Management', () => {
    it('should have all internal state fields in store', () => {
      const { result } = renderHook(() => useSSEStore())

      // Verify internal state exists in store (moved from module-level)
      expect(result.current).toHaveProperty('_eventSource')
      expect(result.current).toHaveProperty('_reconnectAttempts')
      expect(result.current).toHaveProperty('_reconnectTimeoutId')
      expect(result.current).toHaveProperty('_permanentlyFailed')
      expect(result.current).toHaveProperty('_listenerRefs')
    })

    it('should initialize internal state with safe defaults', () => {
      const { result } = renderHook(() => useSSEStore())

      expect(result.current._eventSource).toBeNull()
      expect(result.current._reconnectAttempts).toBe(0)
      expect(result.current._reconnectTimeoutId).toBeNull()
      expect(result.current._permanentlyFailed).toBe(false)
      expect(result.current._listenerRefs).toBeNull()
    })
  })

  describe('Reset Clears All State', () => {
    it('should clear events array on reset', () => {
      const { result } = renderHook(() => useSSEStore())

      // Add events
      act(() => {
        for (let i = 0; i < 10; i++) {
          result.current._addEvent(createProgressEvent(i))
        }
      })
      expect(result.current.events.length).toBeGreaterThan(0)

      // Reset
      act(() => {
        result.current.reset()
      })

      expect(result.current.events).toHaveLength(0)
    })

    it('should clear all public state on reset', () => {
      const { result } = renderHook(() => useSSEStore())

      // Set up state
      act(() => {
        result.current._addEvent(createProgressEvent(1))
        // Manually set other state for testing
        useSSEStore.setState({
          error: new Error('Test error'),
          isConnected: true,
          isComplete: true,
          activeAnalysisId: 'test-id',
        })
      })

      // Reset
      act(() => {
        result.current.reset()
      })

      // Verify all public state is cleared
      expect(result.current.events).toHaveLength(0)
      expect(result.current.latestEvent).toBeNull()
      expect(result.current.error).toBeNull()
      expect(result.current.isConnected).toBe(false)
      expect(result.current.isComplete).toBe(false)
      expect(result.current.activeAnalysisId).toBeNull()
    })

    it('should clear all internal state on reset', () => {
      const { result } = renderHook(() => useSSEStore())

      // Set up internal state
      act(() => {
        useSSEStore.setState({
          _reconnectAttempts: 3,
          _permanentlyFailed: true,
        })
      })

      // Reset
      act(() => {
        result.current.reset()
      })

      // Verify internal state is cleared
      expect(result.current._eventSource).toBeNull()
      expect(result.current._reconnectAttempts).toBe(0)
      expect(result.current._reconnectTimeoutId).toBeNull()
      expect(result.current._permanentlyFailed).toBe(false)
      expect(result.current._listenerRefs).toBeNull()
    })
  })

  describe('Multiple Connect/Disconnect Cycles', () => {
    it('should not accumulate state across multiple reset cycles', () => {
      const { result } = renderHook(() => useSSEStore())

      // Simulate multiple analysis sessions
      for (let cycle = 0; cycle < 5; cycle++) {
        // Add events
        act(() => {
          for (let i = 0; i < 50; i++) {
            result.current._addEvent(createProgressEvent(cycle * 100 + i))
          }
        })

        // Reset for next cycle
        act(() => {
          result.current.reset()
        })

        // Verify clean state
        expect(result.current.events).toHaveLength(0)
        expect(result.current.latestEvent).toBeNull()
        expect(result.current._reconnectAttempts).toBe(0)
        expect(result.current._permanentlyFailed).toBe(false)
      }
    })

    it('should allow reconnection after reset', () => {
      const { result } = renderHook(() => useSSEStore())

      // First session - simulate permanent failure
      act(() => {
        useSSEStore.setState({
          _permanentlyFailed: true,
          activeAnalysisId: 'session-1',
        })
      })
      expect(result.current._permanentlyFailed).toBe(true)

      // Reset
      act(() => {
        result.current.reset()
      })

      // Should be able to set new session
      act(() => {
        useSSEStore.setState({
          activeAnalysisId: 'session-2',
        })
      })

      expect(result.current._permanentlyFailed).toBe(false)
      expect(result.current.activeAnalysisId).toBe('session-2')
    })
  })

  describe('Memory Efficiency', () => {
    it('should not leak event references when capped', () => {
      const { result } = renderHook(() => useSSEStore())
      const eventRefs: SSEProgressEvent[] = []

      // Create events and keep weak references
      act(() => {
        for (let i = 0; i < MAX_EVENTS + 100; i++) {
          const event = createProgressEvent(i)
          eventRefs.push(event)
          result.current._addEvent(event)
        }
      })

      // First 100 events should not be in the store
      const firstHundredEvents = eventRefs.slice(0, 100)
      const storeEventIds = result.current.events.map((e) => (e as SSEProgressEvent).details?.index)

      firstHundredEvents.forEach((event) => {
        expect(storeEventIds).not.toContain(event.details?.index)
      })
    })

    it('should clear latestEvent reference on reset', () => {
      const { result } = renderHook(() => useSSEStore())

      act(() => {
        result.current._addEvent(createProgressEvent(1))
      })
      expect(result.current.latestEvent).not.toBeNull()

      act(() => {
        result.current.reset()
      })

      // latestEvent should be null - no lingering reference
      expect(result.current.latestEvent).toBeNull()
    })
  })
})
