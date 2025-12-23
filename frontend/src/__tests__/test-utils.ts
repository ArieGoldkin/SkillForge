/**
 * Test utilities for async testing patterns
 *
 * These utilities help with testing complex async behavior with fake timers.
 */

/**
 * Flush all pending promises in the microtask queue
 *
 * When using fake timers, vi.runAllTimersAsync() fires timers but doesn't wait
 * for async callbacks to complete. This helper flushes the promise queue AND
 * allows React to process state updates from those async operations.
 *
 * The key insight: React 18's batching and concurrent features mean state updates
 * from async operations need multiple microtask flushes to fully propagate.
 *
 * @example
 * ```typescript
 * await act(async () => {
 *   await vi.runAllTimersAsync()  // Fire setTimeout
 *   await flushPromises()          // Wait for async callback AND React updates
 * })
 * // Now result.current will reflect the state updates
 * ```
 */
export async function flushPromises(): Promise<void> {
  // Multiple rounds of microtask flushing are required because:
  // 1. First flush: Resolves the mock API promise
  // 2. Second flush: Processes setState calls from the async function
  // 3. Third+ flushes: Allows React 18's concurrent rendering to complete
  // 4. Final flushes: Process any effect cleanups or re-runs

  // Empirically, 5-6 flushes are needed for complex hooks with:
  // - Async functions
  // - Multiple useState calls
  // - useEffect dependencies
  // - Store subscriptions (like Zustand)
  for (let i = 0; i < 6; i++) {
    await new Promise((resolve) => queueMicrotask(resolve))
  }
}
