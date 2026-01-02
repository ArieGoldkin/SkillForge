---
name: test-frontend
description: Complete React/TypeScript frontend testing composite
version: 1.0.0
type: composite
includes:
  - testing/unit-testing-fundamentals
  - testing/unit-testing-typescript
  - testing/api-mocking-msw
  - testing/e2e-testing
trigger: "frontend/**/*.{ts,tsx}"
tags: [testing, frontend, typescript, react, composite]
---

# Frontend Testing Composite

Combines atomic skills for complete React/TypeScript testing.

## Included Skills

| Skill | Purpose |
|-------|---------|
| unit-testing-fundamentals | AAA pattern, isolation, test design |
| unit-testing-typescript | Vitest, Testing Library, hooks |
| api-mocking-msw | Network-level API mocking |
| e2e-testing | Playwright browser automation |

## Quick Start

```bash
# Install dependencies
npm install -D vitest @testing-library/react @testing-library/jest-dom
npm install -D msw @playwright/test

# Setup MSW
npx msw init public/ --save

# Run tests
npm run test              # Unit tests
npm run test:e2e          # E2E tests
npm run test:coverage     # With coverage
```

## Project Structure

```
src/
├── mocks/
│   ├── handlers.ts      # MSW request handlers
│   └── server.ts        # MSW server setup
├── components/
│   └── Button/
│       ├── Button.tsx
│       └── Button.test.tsx
└── hooks/
    └── useAuth.test.ts

e2e/
├── pages/               # Page objects
├── fixtures.ts          # Test fixtures
└── auth.spec.ts         # E2E specs
```

## Test Setup

```typescript
// vitest.setup.ts
import '@testing-library/jest-dom'
import { server } from './src/mocks/server'

beforeAll(() => server.listen({ onUnhandledRequest: 'error' }))
afterEach(() => server.resetHandlers())
afterAll(() => server.close())
```

```typescript
// src/mocks/handlers.ts
import { http, HttpResponse } from 'msw'

export const handlers = [
  http.get('/api/user', () => {
    return HttpResponse.json({ id: '1', name: 'Test User' })
  }),
]
```

## Testing Patterns

### Component Test

```typescript
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'

test('button triggers action', async () => {
  const onClick = vi.fn()
  render(<Button onClick={onClick}>Click</Button>)

  await userEvent.click(screen.getByRole('button'))

  expect(onClick).toHaveBeenCalled()
})
```

### Hook Test

```typescript
import { renderHook, act } from '@testing-library/react'

test('useCounter increments', () => {
  const { result } = renderHook(() => useCounter())

  act(() => result.current.increment())

  expect(result.current.count).toBe(1)
})
```

### MSW Override Test

```typescript
import { server } from '../mocks/server'
import { http, HttpResponse } from 'msw'

test('handles API error', async () => {
  server.use(
    http.get('/api/user', () => HttpResponse.json({}, { status: 500 }))
  )

  render(<UserProfile />)

  expect(await screen.findByText(/error/i)).toBeInTheDocument()
})
```

## Coverage Targets

- **Components**: 80%+
- **Hooks**: 90%+
- **Critical flows**: 100%
- **E2E**: 5-10 key user journeys
