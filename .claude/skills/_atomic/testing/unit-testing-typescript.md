---
name: unit-testing-typescript
description: Vitest/Jest patterns, mocking, Testing Library
version: 1.0.0
tags: [testing, typescript, vitest, jest]
size: atomic
domain: testing
---

# TypeScript Unit Testing with Vitest

## Setup

```bash
npm install -D vitest @testing-library/react @testing-library/jest-dom
```

```typescript
// vitest.config.ts
import { defineConfig } from 'vitest/config'

export default defineConfig({
  test: {
    globals: true,
    environment: 'jsdom',
    setupFiles: ['./vitest.setup.ts'],
  },
})
```

## Basic Tests

```typescript
import { describe, test, expect, vi } from 'vitest'
import { calculateTotal, formatCurrency } from './utils'

describe('calculateTotal', () => {
  test('sums items correctly', () => {
    const items = [{ price: 10 }, { price: 20 }]
    expect(calculateTotal(items)).toBe(30)
  })

  test('returns 0 for empty array', () => {
    expect(calculateTotal([])).toBe(0)
  })

  test('throws for negative prices', () => {
    const items = [{ price: -10 }]
    expect(() => calculateTotal(items)).toThrow('Invalid price')
  })
})
```

## Mocking

```typescript
import { vi, Mock } from 'vitest'

// Mock a module
vi.mock('./api', () => ({
  fetchUser: vi.fn(),
}))

// Mock implementation
const mockFetch = vi.fn()
mockFetch.mockResolvedValue({ id: 1, name: 'Test' })

// Spy on method
const spy = vi.spyOn(console, 'log')
doSomething()
expect(spy).toHaveBeenCalledWith('expected message')

// Mock timers
vi.useFakeTimers()
setTimeout(() => callback(), 1000)
vi.advanceTimersByTime(1000)
expect(callback).toHaveBeenCalled()
vi.useRealTimers()
```

## Testing React Components

```typescript
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { Button } from './Button'

test('calls onClick when clicked', async () => {
  const handleClick = vi.fn()
  const user = userEvent.setup()

  render(<Button onClick={handleClick}>Click me</Button>)

  await user.click(screen.getByRole('button', { name: /click me/i }))

  expect(handleClick).toHaveBeenCalledTimes(1)
})

test('shows loading state', async () => {
  render(<AsyncButton />)

  await userEvent.click(screen.getByRole('button'))

  expect(screen.getByText('Loading...')).toBeInTheDocument()

  await waitFor(() => {
    expect(screen.queryByText('Loading...')).not.toBeInTheDocument()
  })
})
```

## Testing Hooks

```typescript
import { renderHook, act } from '@testing-library/react'
import { useCounter } from './useCounter'

test('increments counter', () => {
  const { result } = renderHook(() => useCounter())

  expect(result.current.count).toBe(0)

  act(() => {
    result.current.increment()
  })

  expect(result.current.count).toBe(1)
})
```

## Async Testing

```typescript
test('fetches and displays data', async () => {
  render(<DataComponent />)

  // Wait for async operation
  expect(await screen.findByText('Loaded data')).toBeInTheDocument()
})

test('handles async errors', async () => {
  mockApi.mockRejectedValueOnce(new Error('Network error'))

  render(<DataComponent />)

  expect(await screen.findByText('Error: Network error')).toBeInTheDocument()
})
```

## Running Tests

```bash
vitest                  # Watch mode
vitest run              # Single run
vitest --coverage       # With coverage
vitest -t "pattern"     # Filter by name
vitest --ui             # Visual UI
```
