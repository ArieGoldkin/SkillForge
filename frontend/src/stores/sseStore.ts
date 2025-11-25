import { create } from 'zustand'

import type { SSEStore } from './sseStoreHelpers'
import { closeConnection, createConnection } from './sseStoreHelpers'

/**
 * SSE Store
 *
 * Manages Server-Sent Events connection for analysis workflow progress.
 * Features:
 * - Single global connection per analysis
 * - Auto-reconnect with exponential backoff (1s → 2s → 4s, max 3 attempts)
 * - Auto-close on complete event
 * - Prevents duplicate connections
 *
 * Reconnection Strategy:
 * - Initial delay: 1000ms
 * - Max delay: 4000ms
 * - Max attempts: 3
 * - Reset on successful connection
 */
export const useSSEStore = create<SSEStore>((set, get) => ({
  events: [],
  latestEvent: null,
  error: null,
  isConnected: false,
  isComplete: false,
  activeAnalysisId: null,

  connect: (analysisId: string) => {
    createConnection(analysisId, { getState: get, setState: set })
  },

  disconnect: () => {
    closeConnection({ getState: get, setState: set })
  },

  reset: () => {
    get().disconnect()
    set({
      events: [],
      latestEvent: null,
      error: null,
      isConnected: false,
      isComplete: false,
      activeAnalysisId: null,
    })
  },
}))
