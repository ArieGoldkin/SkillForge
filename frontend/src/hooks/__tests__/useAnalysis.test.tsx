/**
 * @unit
 * Tests for useAnalysis hook with ky-based API client
 *
 * Uses vi.hoisted() to stub env variables BEFORE module imports,
 * ensuring ky's prefixUrl is configured correctly.
 */

import type { ReactNode } from 'react'

import type { Analysis } from '@app-types/api'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { renderHook, waitFor } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'

// Set up env BEFORE the module imports (hoisted to top of file)
const { mockFetch } = vi.hoisted(() => {
  const url = 'http://localhost:8500'
  // Stub the env variable before api-client.ts loads
  vi.stubEnv('VITE_API_URL', url)
  vi.stubEnv('VITE_API_BASE_URL', url)
  return {
    mockFetch: vi.fn(),
  }
})

// eslint-disable-next-line import/first -- Module must import AFTER vi.hoisted stubs the env
import { useAnalysis } from '../useAnalysis'

// Set up fetch mock globally
vi.stubGlobal('fetch', mockFetch)

function createWrapper() {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  })
  return function Wrapper({ children }: { children: ReactNode }) {
    return <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
  }
}

describe('useAnalysis Hook', () => {
  // IDs must be valid UUIDs to pass Zod validation
  const testAnalysisId = '123e4567-e89b-12d3-a456-426614174000'
  const testArtifactId = '123e4567-e89b-12d3-a456-426614174001'

  const mockAnalysis: Analysis = {
    id: testAnalysisId,
    url: 'https://example.com/article',
    content_type: 'article',
    title: 'Test Article',
    status: 'complete',
    created_at: '2025-01-01T00:00:00Z',
    artifact_id: testArtifactId,
  }

  afterEach(() => {
    vi.clearAllMocks()
  })

  it('fetches analysis data successfully', async () => {
    // ky uses proper Response objects
    mockFetch.mockResolvedValueOnce(
      new Response(JSON.stringify(mockAnalysis), {
        status: 200,
        headers: { 'Content-Type': 'application/json' },
      })
    )

    const { result } = renderHook(() => useAnalysis(testAnalysisId), {
      wrapper: createWrapper(),
    })

    expect(result.current.isLoading).toBe(true)

    await waitFor(() => expect(result.current.isSuccess).toBe(true))

    expect(result.current.data).toEqual(mockAnalysis)
    // ky passes Request objects to fetch
    expect(mockFetch).toHaveBeenCalled()
    const [req] = mockFetch.mock.calls[0] as [Request]
    expect(req.url).toContain(`/api/v1/analyze/${testAnalysisId}`)
  })

  it('handles fetch errors', async () => {
    // ky expects proper Response objects for errors too
    mockFetch.mockResolvedValueOnce(
      new Response(JSON.stringify({ detail: 'Not found' }), {
        status: 404,
        headers: { 'Content-Type': 'application/json' },
      })
    )

    const { result } = renderHook(() => useAnalysis(testAnalysisId), {
      wrapper: createWrapper(),
    })

    await waitFor(() => expect(result.current.isError).toBe(true))

    expect(result.current.error).toBeDefined()
  })

  it('respects enabled option', async () => {
    mockFetch.mockResolvedValueOnce(
      new Response(JSON.stringify(mockAnalysis), {
        status: 200,
        headers: { 'Content-Type': 'application/json' },
      })
    )

    const { result } = renderHook(() => useAnalysis(testAnalysisId, { enabled: false }), {
      wrapper: createWrapper(),
    })

    await new Promise((resolve) => setTimeout(resolve, 50))

    expect(result.current.isLoading).toBe(false)
    expect(mockFetch).not.toHaveBeenCalled()
  })
})
