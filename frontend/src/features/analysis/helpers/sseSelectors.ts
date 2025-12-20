import type { SSEStore } from '@stores/sseStore'

/**
 * Zustand Selectors - Optimized consolidated subscriptions
 * Reduces from 7 individual subscriptions to 3 consolidated ones
 */

/**
 * High-frequency events selector (keep separate to avoid unnecessary re-renders)
 */
export const selectEvents = (state: SSEStore) => state.events

/**
 * Connection state selector - consolidates connection-related state and actions
 */
export const selectConnectionState = (state: SSEStore) => ({
  isConnected: state.isConnected,
  connect: state.connect,
  disconnect: state.disconnect,
})

/**
 * Analysis state selector - consolidates analysis completion, errors, and reset
 */
export const selectAnalysisState = (state: SSEStore) => ({
  isComplete: state.isComplete,
  error: state.error,
  reset: state.reset,
})
