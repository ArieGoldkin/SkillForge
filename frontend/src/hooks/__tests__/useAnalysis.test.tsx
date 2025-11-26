import type { ReactNode } from 'react'

import type { Analysis } from '@app-types/api'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { renderHook, waitFor } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'

import { useAnalysis } from '../useAnalysis'

function createWrapper() {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  })
  return function Wrapper({ children }: { children: ReactNode }) {
    return <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
  }
}

describe('useAnalysis Hook', () => {
  const mockAnalysis: Analysis = {
    id: 'test-123',
    url: 'https://example.com/article',
    content_type: 'article',
    title: 'Test Article',
    status: 'complete',
    created_at: '2025-01-01T00:00:00Z',
    artifact_id: 'artifact-123',
  }

  afterEach(() => {
    vi.restoreAllMocks()
  })

  it('fetches analysis data successfully', async () => {
    globalThis.fetch = vi.fn(() =>
      Promise.resolve({
        ok: true,
        json: () => Promise.resolve(mockAnalysis),
      } as Response)
    )

    const { result } = renderHook(() => useAnalysis('test-123'), {
      wrapper: createWrapper(),
    })

    expect(result.current.isLoading).toBe(true)

    await waitFor(() => expect(result.current.isSuccess).toBe(true))

    expect(result.current.data).toEqual(mockAnalysis)
    // Check that fetch was called with the correct path (port may vary based on env)
    expect(globalThis.fetch).toHaveBeenCalledWith(
      expect.stringMatching(/http:\/\/localhost:\d+\/api\/v1\/analyze\/test-123/)
    )
  })

  it('handles fetch errors', async () => {
    globalThis.fetch = vi.fn(() =>
      Promise.resolve({
        ok: false,
        status: 404,
      } as Response)
    )

    const { result } = renderHook(() => useAnalysis('test-123'), {
      wrapper: createWrapper(),
    })

    await waitFor(() => expect(result.current.isError).toBe(true))

    expect(result.current.error?.message).toContain('404')
  })

  it('respects enabled option', async () => {
    globalThis.fetch = vi.fn(() =>
      Promise.resolve({
        ok: true,
        json: () => Promise.resolve(mockAnalysis),
      } as Response)
    )

    const { result } = renderHook(() => useAnalysis('test-123', { enabled: false }), {
      wrapper: createWrapper(),
    })

    await new Promise((resolve) => setTimeout(resolve, 50))

    expect(result.current.isLoading).toBe(false)
    expect(globalThis.fetch).not.toHaveBeenCalled()
  })
})
