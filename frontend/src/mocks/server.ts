/**
 * MSW Server Setup for Node.js (Tests)
 *
 * Issue #551: MSW for Network-Level API Mocking
 *
 * Sets up the MSW server for use in Vitest tests. Import this
 * in your test setup file to enable network-level mocking.
 *
 * @module mocks/server
 */

import { setupServer } from 'msw/node'

import { handlers } from './handlers'

/**
 * MSW server instance for tests
 *
 * Usage in test setup:
 * ```typescript
 * import { server } from '@/mocks/server'
 *
 * beforeAll(() => server.listen({ onUnhandledRequest: 'error' }))
 * afterEach(() => server.resetHandlers())
 * afterAll(() => server.close())
 * ```
 *
 * Usage in individual tests to override handlers:
 * ```typescript
 * import { server } from '@/mocks/server'
 * import { http, HttpResponse } from 'msw'
 *
 * it('handles error response', async () => {
 *   server.use(
 *     http.get('/api/v1/analyze/:id', () => {
 *       return HttpResponse.json({ detail: 'Not found' }, { status: 404 })
 *     })
 *   )
 *   // ... test code
 * })
 * ```
 */
export const server = setupServer(...handlers)

// Re-export everything for convenience
export { handlers } from './handlers'
export * from './factories'
