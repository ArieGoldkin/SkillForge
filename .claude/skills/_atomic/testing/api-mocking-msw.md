---
name: api-mocking-msw
description: MSW (Mock Service Worker) for network-level API mocking
version: 1.0.0
tags: [testing, mocking, msw, api]
size: atomic
domain: testing
---

# MSW - Mock Service Worker (2025 Standard)

MSW intercepts at network level, not implementation. Your real fetch/axios code runs.

## Setup

```bash
npm install -D msw
npx msw init public/ --save
```

## Define Handlers

```typescript
// src/mocks/handlers.ts
import { http, HttpResponse } from 'msw'

export const handlers = [
  // GET request
  http.get('/api/users/:id', ({ params }) => {
    return HttpResponse.json({
      id: params.id,
      name: 'John Doe',
      email: 'john@example.com',
    })
  }),

  // POST request
  http.post('/api/users', async ({ request }) => {
    const body = await request.json()
    return HttpResponse.json({
      id: 'new-user-123',
      ...body,
    }, { status: 201 })
  }),

  // Error response
  http.get('/api/users/not-found', () => {
    return HttpResponse.json(
      { error: 'User not found' },
      { status: 404 }
    )
  }),

  // Delayed response
  http.get('/api/slow', async () => {
    await delay(2000)
    return HttpResponse.json({ data: 'slow' })
  }),
]
```

## Server Setup (Node/Vitest/Jest)

```typescript
// src/mocks/server.ts
import { setupServer } from 'msw/node'
import { handlers } from './handlers'

export const server = setupServer(...handlers)
```

```typescript
// vitest.setup.ts
import { beforeAll, afterEach, afterAll } from 'vitest'
import { server } from './src/mocks/server'

beforeAll(() => server.listen({ onUnhandledRequest: 'error' }))
afterEach(() => server.resetHandlers())
afterAll(() => server.close())
```

## Runtime Handler Overrides

```typescript
import { http, HttpResponse } from 'msw'
import { server } from '../mocks/server'

test('handles server error', async () => {
  // Override just for this test
  server.use(
    http.get('/api/users/:id', () => {
      return HttpResponse.json(
        { error: 'Server error' },
        { status: 500 }
      )
    })
  )

  render(<UserProfile id="123" />)
  expect(await screen.findByText(/server error/i)).toBeInTheDocument()
})

test('handles loading state', async () => {
  server.use(
    http.get('/api/users/:id', async () => {
      await delay(100)
      return HttpResponse.json({ id: '123', name: 'John' })
    })
  )

  render(<UserProfile id="123" />)
  expect(screen.getByTestId('skeleton')).toBeInTheDocument()
  expect(await screen.findByText('John')).toBeInTheDocument()
})
```

## Anti-Patterns

```typescript
// BAD - Mocking fetch directly
jest.spyOn(global, 'fetch').mockResolvedValue(...)

// BAD - Mocking axios
jest.mock('axios')

// BAD - Mocking your API module
jest.mock('../services/api')

// BAD - Testing implementation
expect(fetch).toHaveBeenCalledWith('/api/...')

// GOOD - Use MSW
server.use(http.get('/api/...', () => HttpResponse.json({...})))

// GOOD - Test behavior
expect(await screen.findByText('Success')).toBeInTheDocument()
```

## With React Query

```typescript
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'

function renderWithQuery(ui: React.ReactElement) {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  })
  return render(
    <QueryClientProvider client={queryClient}>{ui}</QueryClientProvider>
  )
}

test('fetches and displays user', async () => {
  renderWithQuery(<UserProfile id="123" />)
  expect(await screen.findByText('John Doe')).toBeInTheDocument()
})
```
