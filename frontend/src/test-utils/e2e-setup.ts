/**
 * E2E Test Infrastructure & Setup
 *
 * Comprehensive setup for End-to-End testing with realistic mocking,
 * environment simulation, and test data management. Only loads when
 * E2E_READY=true to avoid impacting unit test performance.
 */

import type React from 'react'

import { vi } from 'vitest'

import { TestEnvironment } from './environment'
import { testDataFactory } from './test-helpers'

// ============================================================================
// E2E TEST INFRASTRUCTURE
// ============================================================================

/**
 * Mock Server for API Simulation
 * Provides realistic API responses for E2E testing
 */
class MockServer {
  private handlers = new Map<string, (request: unknown) => unknown>()
  private delay = 100 // Simulate network latency

  /**
   * Register a mock handler for a specific endpoint
   */
  on(method: string, path: string, handler: (request: unknown) => unknown) {
    this.handlers.set(`${method} ${path}`, handler)
  }

  /**
   * Simulate API call
   */
  async call(method: string, path: string, request: Record<string, unknown> = {}) {
    const key = `${method} ${path}`
    const handler = this.handlers.get(key)

    if (!handler) {
      throw new Error(`No mock handler for ${key}`)
    }

    // Simulate network delay
    await new Promise((resolve) => setTimeout(resolve, this.delay))

    return handler(request)
  }

  /**
   * Reset all handlers
   */
  reset() {
    this.handlers.clear()
  }

  /**
   * Set network delay simulation
   */
  setDelay(delay: number) {
    this.delay = delay
  }
}

/**
 * E2E Test Context & State Management
 */
class E2ETestContext {
  private state = new Map<string, unknown>()
  mockServer = new MockServer()

  /**
   * Set test context data
   */
  set(key: string, value: unknown) {
    this.state.set(key, value)
  }

  /**
   * Get test context data
   */
  get(key: string) {
    return this.state.get(key)
  }

  /**
   * Clear all context data
   */
  clear() {
    this.state.clear()
    this.mockServer.reset()
  }

  /**
   * Initialize realistic test data
   */
  initializeRealisticData() {
    // Pre-populate with realistic test data
    this.set(
      'currentUser',
      testDataFactory.createUser({
        email: process.env.TEST_USER_EMAIL || 'test@example.com',
      })
    )

    this.set(
      'sampleAnalysis',
      testDataFactory.createAnalysis({
        url: 'https://example.com/article',
        status: 'complete',
        wordCount: 1200,
      })
    )

    // Setup mock API handlers
    this.setupMockAPI()
  }

  /**
   * Setup mock API handlers for common endpoints
   */
  private setupMockAPI() {
    // Analysis endpoints
    this.mockServer.on('POST', '/api/v1/analyze', (request) => ({
      id: `test-analysis-${Date.now()}`,
      status: 'queued',
      url: request.url,
      createdAt: new Date().toISOString(),
    }))

    this.mockServer.on('GET', '/api/v1/analyses/:id', (request) => {
      const analysis = this.get('sampleAnalysis')
      return testDataFactory.createApiResponse({
        ...analysis,
        id: request.params.id,
        status: 'complete',
        progress: 100,
      })
    })

    // User endpoints
    this.mockServer.on('GET', '/api/v1/user/profile', () => {
      return testDataFactory.createApiResponse(this.get('currentUser'))
    })

    // Artifact endpoints
    this.mockServer.on('GET', '/api/v1/artifacts/:id', (request) => {
      return testDataFactory.createApiResponse({
        id: request.params.id,
        content: '# Test Artifact\n\nThis is generated content.',
        format: 'markdown',
        createdAt: new Date().toISOString(),
      })
    })
  }
}

/**
 * Global E2E test context
 */
const e2eContext = new E2ETestContext()

/**
 * E2E Test Setup Utilities
 */
export const e2eSetup = {
  /**
   * Initialize E2E test environment
   */
  setup: () => {
    // Mock TanStack Router hooks for E2E tests
    vi.mock('@tanstack/react-router', () => ({
      useRouter: () => ({
        navigate: vi.fn(),
        invalidate: vi.fn(),
      }),
      useParams: () => ({ id: 'test-analysis-id' }),
      useSearch: () => ({ completed: false }),
      useMatch: () => ({ pathname: '/analyze/test-analysis-id' }),
      createRouter: vi.fn(() => ({
        routesByPath: {},
        routeTree: {},
      })),
      RouterProvider: ({ children }: { children: React.ReactNode }) => children,
      getRouteApi: () => ({
        useParams: () => ({ id: 'test-analysis-id' }),
        useSearch: () => ({ completed: false }),
      }),
    }))

    // Mock EventSource for SSE connections
    class MockEventSource {
      url: string
      readyState: number = 1 // OPEN
      CONNECTING = 0
      OPEN = 1
      CLOSING = 2
      CLOSED = 3

      constructor(url: string) {
        this.url = url
      }

      addEventListener = vi.fn()
      removeEventListener = vi.fn()
      dispatchEvent = vi.fn()
      close = vi.fn()
    }

    global.EventSource = MockEventSource as typeof EventSource

    // Note: Store and hook mocks are handled at the test level
    // to avoid path resolution issues in the global setup

    // Mock global fetch for API calls
    global.fetch = vi.fn(async (url: string, options: RequestInit = {}) => {
      const method = options.method || 'GET'
      const path = url.replace(process.env.VITE_API_BASE_URL || 'http://localhost:8500', '')

      try {
        const response = await e2eContext.mockServer.call(method, path, {
          body: options.body ? JSON.parse(options.body) : undefined,
          headers: options.headers,
        })

        return {
          ok: true,
          status: 200,
          json: () => Promise.resolve(response),
          text: () => Promise.resolve(JSON.stringify(response)),
        }
      } catch (error) {
        return {
          ok: false,
          status: 500,
          json: () => Promise.resolve({ error: error.message }),
          text: () => Promise.resolve(JSON.stringify({ error: error.message })),
        }
      }
    })

    // Mock WebSocket for real-time updates
    global.WebSocket = vi.fn().mockImplementation(() => ({
      send: vi.fn(),
      close: vi.fn(),
      addEventListener: vi.fn(),
      removeEventListener: vi.fn(),
      readyState: 1, // OPEN
      CONNECTING: 0,
      OPEN: 1,
      CLOSING: 2,
      CLOSED: 3,
    }))

    // Initialize test data
    e2eContext.initializeRealisticData()

    console.log('🧪 E2E test environment initialized')
  },

  /**
   * Clean up E2E test environment
   */
  teardown: () => {
    e2eContext.clear()
    vi.restoreAllMocks()
    console.log('🧪 E2E test environment cleaned up')
  },

  /**
   * Get mock server instance for custom handlers
   */
  get mockServer() {
    return e2eContext.mockServer
  },

  /**
   * Get test data factory
   */
  get testData() {
    return testDataFactory
  },

  /**
   * Get current test context
   */
  get context() {
    return e2eContext
  },

  /**
   * Simulate network conditions
   */
  simulateNetwork: {
    fast: () => e2eContext.mockServer.setDelay(50),
    slow: () => e2eContext.mockServer.setDelay(1000),
    offline: () => {
      global.fetch = vi.fn().mockRejectedValue(new Error('Network offline'))
    },
    online: () => e2eSetup.setup(), // Reinitialize
  },

  /**
   * User session management
   */
  user: {
    login: (userData: Record<string, unknown>) => {
      e2eContext.set('currentUser', userData)
      // Update mock handlers with user data
    },

    logout: () => {
      e2eContext.set('currentUser', null)
    },

    getCurrent: () => e2eContext.get('currentUser'),
  },

  /**
   * Analysis workflow simulation
   */
  analysis: {
    start: (url: string) => {
      const analysis = testDataFactory.createAnalysis({
        url,
        status: 'processing',
        progress: 0,
      })
      e2eContext.set('currentAnalysis', analysis)
      return analysis
    },

    progress: (progress: number) => {
      const analysis = e2eContext.get('currentAnalysis')
      if (analysis) {
        analysis.progress = progress
        analysis.status = progress === 100 ? 'complete' : 'processing'
        e2eContext.set('currentAnalysis', analysis)
      }
    },

    complete: () => {
      const analysis = e2eContext.get('currentAnalysis')
      if (analysis) {
        analysis.status = 'complete'
        analysis.progress = 100
        analysis.completedAt = new Date().toISOString()
        e2eContext.set('currentAnalysis', analysis)
      }
    },

    fail: (error: string) => {
      const analysis = e2eContext.get('currentAnalysis')
      if (analysis) {
        analysis.status = 'failed'
        analysis.error = error
        e2eContext.set('currentAnalysis', analysis)
      }
    },
  },
}

/**
 * Vitest Global Setup for E2E Tests
 */
export const e2eGlobalSetup = () => {
  if (TestEnvironment.isE2EReady) {
    e2eSetup.setup()

    // Cleanup after all tests
    return () => {
      e2eSetup.teardown()
    }
  }
}

export default e2eSetup
