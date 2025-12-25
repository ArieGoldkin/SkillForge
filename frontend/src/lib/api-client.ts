/**
 * Modern HTTP Client with ky
 *
 * Issue #550: Request Interceptor Pattern with ky
 *
 * Features:
 * - Automatic retry with exponential backoff (3 retries)
 * - Configurable timeout (30s default)
 * - Request ID injection for distributed tracing
 * - Development logging
 * - Error enrichment from response body
 * - Zod validation integration for type-safe responses
 *
 * @module lib/api-client
 */

import ky, { type Options, HTTPError } from 'ky'
import type { z } from 'zod'

import { logger } from '@/lib/logger'

// API base URL - uses Vite env variable or defaults to localhost:8500
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8500'

// Request metadata for timing (using WeakMap to avoid memory leaks)
const requestStartTimes = new WeakMap<Request, number>()

/**
 * Configured ky instance with interceptors
 *
 * Interceptor Chain:
 * 1. beforeRequest: Add request ID, log request, record start time
 * 2. beforeRetry: Log retry attempts, optionally refresh auth token
 * 3. afterResponse: Log response with duration
 * 4. beforeError: Enrich error with response body message
 */
export const apiClient = ky.create({
  prefixUrl: API_BASE_URL,
  timeout: 30000,
  retry: {
    limit: 3,
    methods: ['get', 'head', 'options'],
    statusCodes: [408, 429, 500, 502, 503, 504],
    backoffLimit: 3000,
  },
  hooks: {
    beforeRequest: [
      (request) => {
        // Add request ID for distributed tracing
        const requestId = crypto.randomUUID()
        request.headers.set('X-Request-ID', requestId)

        // Record start time for duration logging
        requestStartTimes.set(request, Date.now())

        // Development logging
        if (import.meta.env.DEV) {
          logger.debug(`[API] ${request.method} ${request.url}`, {
            requestId,
            headers: Object.fromEntries(request.headers.entries()),
          })
        }
      },
    ],
    beforeRetry: [
      async ({ request, error, retryCount }) => {
        const requestId = request.headers.get('X-Request-ID')
        logger.warn(`[API] Retry ${retryCount} for ${request.url}`, {
          requestId,
          error: error instanceof Error ? error.message : String(error),
        })

        // Future: Refresh auth token on 401 before retry
        // if (error instanceof HTTPError && error.response.status === 401) {
        //   await refreshAuthToken()
        // }
      },
    ],
    afterResponse: [
      (request, _options, response) => {
        const startTime = requestStartTimes.get(request)
        const duration = startTime ? Date.now() - startTime : null
        const requestId = request.headers.get('X-Request-ID')

        // Clean up timing data
        requestStartTimes.delete(request)

        // Log response
        if (import.meta.env.DEV) {
          logger.debug(
            `[API] ${response.status} ${request.method} ${request.url}${duration ? ` (${duration}ms)` : ''}`,
            { requestId, status: response.status }
          )
        }

        // Handle rate limiting
        if (response.status === 429) {
          const retryAfter = response.headers.get('Retry-After')
          logger.warn(`[API] Rate limited, retry after ${retryAfter}s`, { requestId })
        }

        return response
      },
    ],
    beforeError: [
      async (error) => {
        // Enrich error with message from response body
        const { response } = error
        if (response) {
          try {
            const body = (await response.clone().json()) as Record<string, unknown>
            const message = body.detail || body.message || body.error
            if (typeof message === 'string') {
              error.message = message
            }
          } catch {
            // Response body not JSON, keep original error
          }
        }
        return error
      },
    ],
  },
})

/**
 * Type-safe API fetch with Zod validation
 *
 * Combines ky's HTTP client with Zod schema validation for
 * compile-time and runtime type safety.
 *
 * @param endpoint - API endpoint (without leading slash, prefixUrl handles base)
 * @param schema - Zod schema for response validation
 * @param options - ky request options
 * @returns Validated response data
 *
 * @example
 * ```typescript
 * const analysis = await api('api/v1/analyze/123', AnalysisResponseSchema)
 * // analysis is fully typed based on schema
 * ```
 */
export async function api<T>(
  endpoint: string,
  schema: z.ZodType<T>,
  options?: Options
): Promise<T> {
  const response = await apiClient(endpoint, options).json()
  return schema.parse(response)
}

/**
 * Safe API fetch that returns null on errors instead of throwing
 *
 * Useful for optional data fetching where errors should be handled gracefully.
 *
 * @param endpoint - API endpoint
 * @param schema - Zod schema for response validation
 * @param options - ky request options
 * @returns Validated response data or null on error
 */
export async function safeApi<T>(
  endpoint: string,
  schema: z.ZodType<T>,
  options?: Options
): Promise<T | null> {
  try {
    return await api(endpoint, schema, options)
  } catch (error) {
    const isHttp = error instanceof HTTPError
    logger.warn(`[API] Request failed: ${endpoint}`, {
      error: error instanceof Error ? error.message : String(error),
      status: isHttp ? error.response.status : undefined,
    })
    return null
  }
}

/**
 * Raw API fetch without Zod validation
 *
 * Use when you need the raw response or for streaming endpoints.
 *
 * @param endpoint - API endpoint
 * @param options - ky request options
 * @returns ky Response
 */
export function apiRaw(endpoint: string, options?: Options) {
  return apiClient(endpoint, options)
}

/**
 * Check if an error is an HTTP error from ky
 */
export function isHTTPError(error: unknown): error is HTTPError {
  return error instanceof HTTPError
}

/**
 * Get the API base URL (for SSE endpoints that need full URL)
 */
export function getApiBaseUrl(): string {
  return API_BASE_URL
}

export { HTTPError }
