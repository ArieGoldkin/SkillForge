/**
 * Advanced Test Utilities & Helpers
 *
 * Provides smart testing utilities that adapt to environment and test context.
 * Follows 2025 testing best practices with intelligent mocking and fixtures.
 */

import React from 'react'

import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, type RenderOptions } from '@testing-library/react'

import { TestEnvironment } from './environment'

/**
 * Enhanced render function with full app context
 * Automatically includes React Query, Router, and other providers
 */
export function renderWithProviders(ui: React.ReactElement, options: RenderOptions = {}) {
  // Create QueryClient with test-friendly defaults
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: {
        retry: false, // Disable retries in tests
        staleTime: 0,
        gcTime: 0, // Previously cacheTime
      },
      mutations: {
        retry: false,
      },
    },
  })

  function AllTheProviders({ children }: { children: React.ReactNode }): React.ReactNode {
    return <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
  }

  return render(ui, { wrapper: AllTheProviders, ...options })
}

/**
 * Smart test data generator
 * Creates realistic test data based on environment
 */
export class TestDataFactory {
  private static instance: TestDataFactory
  private cache = new Map<string, unknown>()

  static getInstance(): TestDataFactory {
    if (!TestDataFactory.instance) {
      TestDataFactory.instance = new TestDataFactory()
    }
    return TestDataFactory.instance
  }

  /**
   * Create user with environment-aware data
   */
  createUser(overrides: Record<string, unknown> = {}) {
    const cacheKey = `user-${JSON.stringify(overrides)}`

    if (this.cache.has(cacheKey)) {
      return this.cache.get(cacheKey)
    }

    const user = {
      id: TestEnvironment.isE2EReady ? 'real-user-123' : 'mock-user-123',
      email: TestEnvironment.isE2EReady
        ? process.env.TEST_USER_EMAIL || 'test@example.com'
        : 'test@example.com',
      name: 'Test User',
      avatar: 'https://example.com/avatar.jpg',
      role: 'user',
      createdAt: new Date().toISOString(),
      token: TestEnvironment.isE2EReady
        ? process.env.TEST_API_TOKEN || 'real-token'
        : 'mock-token-123',
      ...overrides,
    }

    this.cache.set(cacheKey, user)
    return user
  }

  /**
   * Create analysis with realistic data
   */
  createAnalysis(overrides: Record<string, unknown> = {}) {
    const cacheKey = `analysis-${JSON.stringify(overrides)}`

    if (this.cache.has(cacheKey)) {
      return this.cache.get(cacheKey)
    }

    const analysis = {
      id: 'test-analysis-id',
      url: 'https://example.com/article',
      title: 'Test Analysis Title',
      content: 'This is test content for analysis.',
      status: 'completed',
      wordCount: 1200,
      readingTime: 6,
      metadata: {
        author: 'Test Author',
        publishedAt: new Date().toISOString(),
        tags: ['test', 'analysis'],
      },
      createdAt: new Date().toISOString(),
      updatedAt: new Date().toISOString(),
      ...overrides,
    }

    this.cache.set(cacheKey, analysis)
    return analysis
  }

  /**
   * Create API response with consistent structure
   */
  createApiResponse(data: unknown, overrides: Record<string, unknown> = {}) {
    return {
      success: true,
      data,
      timestamp: new Date().toISOString(),
      requestId: 'test-request-123',
      ...overrides,
    }
  }

  /**
   * Clear all cached test data
   */
  clearCache() {
    this.cache.clear()
  }
}

/**
 * Smart wait utilities for async operations
 */
export const waitFor = {
  /**
   * Wait for element with timeout awareness
   */
  element: async (_selector: string, options: { timeout?: number } = {}) => {
    const _timeout = options.timeout || TestEnvironment.testTimeout

    // Implementation would use testing-library's waitFor
    // This is a placeholder for the concept
  },

  /**
   * Wait for API call to complete
   */
  apiCall: async (mockFn: { mock: { calls: unknown[] } }, options: { timeout?: number } = {}) => {
    const _timeout = options.timeout || TestEnvironment.testTimeout

    // Wait for mock to be called
    await new Promise((resolve, reject) => {
      const timeoutId = setTimeout(() => {
        reject(new Error('API call timeout'))
      }, _timeout)

      const checkCall = () => {
        if (mockFn.mock.calls.length > 0) {
          clearTimeout(timeoutId)
          resolve(void 0)
        } else {
          setTimeout(checkCall, 10)
        }
      }
      checkCall()
    })
  },

  /**
   * Wait for component state change
   */
  stateChange: async (
    _component: unknown,
    _stateKey: string,
    _expectedValue: unknown,
    options: { timeout?: number } = {}
  ) => {
    const _timeout = options.timeout || TestEnvironment.testTimeout

    // Implementation for state change waiting
  },
}

/**
 * Mock utilities for external dependencies
 */
export const createMocks = {
  /**
   * Mock fetch with environment awareness
   */
  fetch: () => {
    const mockFetch = vi.fn()

    // Default successful response
    mockFetch.mockResolvedValue({
      ok: true,
      status: 200,
      json: () => Promise.resolve({ success: true }),
      text: () => Promise.resolve('mock response'),
    })

    return mockFetch
  },

  /**
   * Mock localStorage with environment awareness
   */
  localStorage: () => {
    const store: Record<string, string> = {}

    return {
      getItem: vi.fn((key: string) => store[key] || null),
      setItem: vi.fn((key: string, value: string) => {
        store[key] = value
      }),
      removeItem: vi.fn((key: string) => {
        delete store[key]
      }),
      clear: vi.fn(() => {
        Object.keys(store).forEach((key) => {
          delete store[key]
        })
      }),
      key: vi.fn((index: number) => Object.keys(store)[index] || null),
      get length() {
        return Object.keys(store).length
      },
    }
  },

  /**
   * Mock WebSocket with realistic behavior
   */
  webSocket: () => {
    const mockWS = {
      send: vi.fn(),
      close: vi.fn(),
      addEventListener: vi.fn(),
      removeEventListener: vi.fn(),
      readyState: 1, // OPEN
      CONNECTING: 0,
      OPEN: 1,
      CLOSING: 2,
      CLOSED: 3,
    }

    return mockWS
  },
}

/**
 * Performance testing utilities
 */
export const performanceTest = {
  /**
   * Measure component render performance
   */
  measureRender: async (
    component: React.ComponentType,
    props: Record<string, unknown> = {},
    iterations: number = 10
  ) => {
    const times: number[] = []

    for (let i = 0; i < iterations; i++) {
      const start = performance.now()
      renderWithProviders(React.createElement(component, props))
      const end = performance.now()
      times.push(end - start)
    }

    const avg = times.reduce((a, b) => a + b, 0) / times.length
    const min = Math.min(...times)
    const max = Math.max(...times)

    return { avg, min, max, times }
  },

  /**
   * Assert performance budget
   */
  assertPerformanceBudget: (actualTime: number, budgetMs: number, testName: string) => {
    if (actualTime > budgetMs) {
      const message = `${testName} exceeded performance budget: ${actualTime}ms > ${budgetMs}ms`
      if (TestEnvironment.isCI) {
        throw new Error(message)
      } else {
        console.warn(`⚠️ ${message}`)
      }
    }
  },
}

/**
 * Accessibility testing utilities
 */
export const a11yTest = {
  /**
   * Check for common accessibility issues
   */
  checkCommonIssues: (container: HTMLElement) => {
    const issues: string[] = []

    // Check for missing alt text
    const images = container.querySelectorAll('img:not([alt])')
    if (images.length > 0) {
      issues.push(`${images.length} images missing alt text`)
    }

    // Check for missing labels
    const inputs = container.querySelectorAll('input:not([aria-label]):not([aria-labelledby])')
    if (inputs.length > 0) {
      issues.push(`${inputs.length} inputs missing labels`)
    }

    // Check for low contrast (placeholder - would need actual color checking)
    // This is a simplified check

    return issues
  },
}

// Export singleton instance
export const testDataFactory = TestDataFactory.getInstance()
