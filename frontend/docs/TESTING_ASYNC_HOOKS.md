# Testing Async React Hooks with Vitest Fake Timers

## The Problem

When testing React hooks that combine `setTimeout` with async operations (like API calls), you encounter a complex timing issue:

1. **Vitest fake timers** (`vi.useFakeTimers()`) control `setTimeout`, `setInterval`, etc.
2. **Async operations** (Promises, API calls) run in the microtask queue
3. **React state updates** from async operations require multiple render cycles
4. **Store subscriptions** (like Zustand) add another layer of async synchronization

The naive approach doesn't work:

```typescript
// ❌ WRONG - State updates won't be visible
await act(async () => {
  await vi.runAllTimersAsync()
})
expect(result.current.status).toBe('complete') // FAILS - status is null
```

## The Solution Pattern

### 1. Set External State AFTER Rendering

When testing hooks that subscribe to external stores (Zustand, Redux, etc.), set the store state AFTER the hook renders, not before:

```typescript
// ✅ CORRECT
const { result } = renderHook(() => useMyHook())

// Set state AFTER rendering to trigger effect
act(() => {
  useStore.setState({ error: new Error('test') })
})
```

**Why:** When you set state before rendering, the hook's first render might not have the subscription set up yet, so the effect won't trigger.

### 2. Use `advanceTimersByTimeAsync()` with `flushPromises()`

Combine timer advancement with promise flushing:

```typescript
// ✅ CORRECT
await act(async () => {
  await vi.advanceTimersByTimeAsync(DELAY_MS)
  await flushPromises()
})
```

**Why:**
- `advanceTimersByTimeAsync()` fires the setTimeout callback
- `flushPromises()` waits for async operations inside the callback to complete
- React 18's concurrent rendering needs multiple microtask flushes for state updates

### 3. Implement `flushPromises()` Helper

Create a utility that flushes the microtask queue multiple times:

```typescript
// frontend/src/__tests__/test-utils.ts
export async function flushPromises(): Promise<void> {
  // Multiple rounds needed for:
  // 1. Mock API promise resolution
  // 2. setState calls from async function
  // 3. React 18's concurrent rendering
  // 4. Effect cleanups and re-runs
  for (let i = 0; i < 6; i++) {
    await new Promise((resolve) => queueMicrotask(resolve))
  }
}
```

**Why 6 iterations?**
- 1st flush: Resolves the mock API promise
- 2nd flush: Processes setState calls
- 3rd-6th flushes: Allows React 18's concurrent features to propagate updates through hooks and effects

### 4. The Complete Pattern

Here's the full correct pattern for testing async hooks with fake timers:

```typescript
import { act, renderHook } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises } from '@/__tests__/test-utils'

vi.mock('@services/api.service', () => ({
  analyzeAPI: { getAnalysisStatus: vi.fn() },
}))

const mockGetAnalysisStatus = vi.mocked(analyzeAPI.getAnalysisStatus)
const DEBOUNCE_DELAY = 2000

describe('useMyAsyncHook', () => {
  beforeEach(() => {
    vi.useFakeTimers()
    mockGetAnalysisStatus.mockReset()
    useStore.getState().reset()
  })

  afterEach(() => {
    vi.useRealTimers()
  })

  it('should handle async operation after timeout', async () => {
    // Setup mock
    mockGetAnalysisStatus.mockResolvedValueOnce({
      status: 'complete',
      data: 'test-data',
    })

    // Render hook FIRST
    const { result } = renderHook(() => useMyAsyncHook({ id: '123' }))

    // Set store state AFTER rendering (triggers effect)
    act(() => {
      useStore.setState({ error: new Error('test error') })
    })

    // Advance timers AND flush promises
    await act(async () => {
      await vi.advanceTimersByTimeAsync(DEBOUNCE_DELAY + 100)
      await flushPromises()
    })

    // Now state updates are visible
    expect(result.current.status).toBe('complete')
    expect(result.current.data).toBe('test-data')
    expect(mockGetAnalysisStatus).toHaveBeenCalledWith('123')
  })
})
```

## Common Mistakes

### ❌ Setting State Before Rendering

```typescript
// WRONG - Effect won't trigger
useStore.setState({ error: new Error() })
const { result } = renderHook(() => useMyHook())
```

### ❌ Using Only `runAllTimersAsync()`

```typescript
// WRONG - Doesn't wait for async callbacks
await act(async () => {
  await vi.runAllTimersAsync()
})
```

### ❌ Not Enough Promise Flushes

```typescript
// WRONG - Single flush not enough for React 18
await new Promise((resolve) => queueMicrotask(resolve))
```

### ❌ Using `setTimeout(0)` for Flushing

```typescript
// WRONG - Conflicts with fake timers
await new Promise((resolve) => setTimeout(resolve, 0))
```

## Testing Different Scenarios

### Debounce Verification

Test that the timer delays execution:

```typescript
it('should wait for debounce before calling API', async () => {
  const { result } = renderHook(() => useMyHook())

  act(() => {
    useStore.setState({ error: new Error() })
  })

  // Before debounce completes
  await act(async () => {
    vi.advanceTimersByTime(1000)
  })
  expect(mockAPI).not.toHaveBeenCalled()

  // After debounce completes
  await act(async () => {
    await vi.advanceTimersByTimeAsync(1100)
    await flushPromises()
  })
  expect(mockAPI).toHaveBeenCalled()
})
```

### Error Handling

Test that errors don't break state:

```typescript
it('should handle API errors gracefully', async () => {
  mockAPI.mockRejectedValueOnce(new Error('Network error'))

  const { result } = renderHook(() => useMyHook())

  act(() => {
    useStore.setState({ error: new Error() })
  })

  await act(async () => {
    await vi.advanceTimersByTimeAsync(DELAY + 100)
    await flushPromises()
  })

  expect(result.current.status).toBeNull() // Unchanged
})
```

### Cleanup on Unmount

Verify timeouts are cleared:

```typescript
it('should clear timeout on unmount', async () => {
  const { unmount } = renderHook(() => useMyHook())

  act(() => {
    useStore.setState({ error: new Error() })
  })

  unmount()

  await act(async () => {
    await vi.advanceTimersByTimeAsync(DELAY + 100)
  })

  expect(mockAPI).not.toHaveBeenCalled()
})
```

## React 18 Considerations

React 18's concurrent features and automatic batching add complexity:

1. **Concurrent rendering**: State updates may not be synchronous
2. **Automatic batching**: Multiple setState calls are batched
3. **Transitions**: Low-priority updates may be deferred
4. **Suspense boundaries**: Async rendering boundaries

The `flushPromises()` helper with 6 iterations handles all of these cases.

## Debugging Tips

Add logging to understand the timing:

```typescript
console.log('After render:', result.current)
console.log('Pending timers:', vi.getTimerCount())
console.log('After timers:', result.current)
console.log('Mock calls:', mockAPI.mock.calls.length)
```

If tests fail:
1. Check `vi.getTimerCount()` - should be > 0 after effect runs
2. Check `mockAPI.mock.calls.length` - should increase after timers advance
3. If timer count is 0, the effect didn't trigger (check state setup)
4. If mock isn't called, the timer callback didn't execute (check timer advancement)
5. If state is null, add more promise flushes

## Performance Considerations

Fake timers are much faster than real timers:

- **Real timers**: 2000ms debounce = 2 seconds per test
- **Fake timers**: 2000ms debounce = ~1ms per test

This makes test suites 1000x faster for timing-based code.

## Summary

**The 4-Step Pattern for Testing Async Hooks with Fake Timers:**

1. ✅ Render hook first
2. ✅ Set external state after render (in `act()`)
3. ✅ Use `vi.advanceTimersByTimeAsync()` + `flushPromises()`
4. ✅ Verify state updates and mock calls

This pattern works for any combination of:
- setTimeout/setInterval
- Async API calls
- React state updates
- External store subscriptions
- useEffect with dependencies

---

**Created:** 2025-01-23
**Updated:** 2025-01-23
**Context:** Issue #489 - SSE Frontend Testing
