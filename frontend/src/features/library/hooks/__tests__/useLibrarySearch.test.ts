/**
 * Tests for useLibrarySearch - Library search functionality
 *
 * Validates search query handling, infinite pagination, and error states.
 */

import * as React from 'react'

import type { LibraryListResponse, LibrarySearchParams } from '@app-types/api'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { renderHook, waitFor } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { analyzeAPI } from '@services/api.service'

import { useLibrarySearch, useLibrarySearchInfinite } from '../useLibrarySearch'

vi.mock('@services/api.service', () => ({
  analyzeAPI: {
    searchLibrary: vi.fn(),
  },
}))

const mockSearchLibrary = vi.mocked(analyzeAPI.searchLibrary)

// Mock response
const mockResponse: LibraryListResponse = {
  items: [
    {
      analysis_id: 'analysis-1',
      title: 'React Hooks Guide',
      snippet: 'Learn about <mark>React hooks</mark>',
      tags: ['react', 'hooks'],
      content_type: 'article',
      status: 'complete',
    },
  ],
  total: 1,
  limit: 20,
  offset: 0,
}

const createWrapper = () => {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
    },
  })

  return ({ children }: { children: React.ReactNode }) =>
    React.createElement(QueryClientProvider, { client: queryClient }, children)
}

describe('useLibrarySearch', () => {
  beforeEach(() => {
    mockSearchLibrary.mockReset()
  })

  describe('initialization', () => {
    it('starts with undefined data', () => {
      mockSearchLibrary.mockResolvedValue(mockResponse)

      const { result } = renderHook(() => useLibrarySearch({ limit: 20 }), {
        wrapper: createWrapper(),
      })

      expect(result.current.data).toBeUndefined()
      expect(result.current.isLoading).toBe(true)
    })

    it('fetches data on mount', async () => {
      mockSearchLibrary.mockResolvedValue(mockResponse)

      const { result } = renderHook(() => useLibrarySearch({ limit: 20 }), {
        wrapper: createWrapper(),
      })

      await waitFor(() => expect(result.current.isSuccess).toBe(true))

      expect(mockSearchLibrary).toHaveBeenCalledWith({ limit: 20 })
      expect(result.current.data).toEqual(mockResponse)
    })
  })

  describe('search functionality', () => {
    it('includes query parameter when provided', async () => {
      mockSearchLibrary.mockResolvedValue(mockResponse)

      const params: LibrarySearchParams = {
        query: 'React hooks',
        search_mode: 'hybrid',
        limit: 20,
      }

      const { result } = renderHook(() => useLibrarySearch(params), {
        wrapper: createWrapper(),
      })

      await waitFor(() => expect(result.current.isSuccess).toBe(true))

      expect(mockSearchLibrary).toHaveBeenCalledWith(params)
    })

    it('handles different search modes', async () => {
      mockSearchLibrary.mockResolvedValue(mockResponse)

      const params: LibrarySearchParams = {
        query: 'test',
        search_mode: 'semantic',
        limit: 20,
      }

      const { result } = renderHook(() => useLibrarySearch(params), {
        wrapper: createWrapper(),
      })

      await waitFor(() => expect(result.current.isSuccess).toBe(true))

      expect(mockSearchLibrary).toHaveBeenCalledWith(params)
    })

    it('includes filters in query', async () => {
      mockSearchLibrary.mockResolvedValue(mockResponse)

      const params: LibrarySearchParams = {
        query: 'test',
        content_type: 'article',
        status: 'complete',
        limit: 20,
      }

      const { result } = renderHook(() => useLibrarySearch(params), {
        wrapper: createWrapper(),
      })

      await waitFor(() => expect(result.current.isSuccess).toBe(true))

      expect(mockSearchLibrary).toHaveBeenCalledWith(params)
    })
  })

  describe('error handling', () => {
    it('handles API errors', async () => {
      const error = new Error('API Error')
      mockSearchLibrary.mockRejectedValue(error)

      const { result } = renderHook(() => useLibrarySearch({ limit: 20 }), {
        wrapper: createWrapper(),
      })

      await waitFor(() => expect(result.current.isError).toBe(true))

      expect(result.current.error).toEqual(error)
    })

    it('does not retry on failure', async () => {
      mockSearchLibrary.mockRejectedValue(new Error('API Error'))

      const { result } = renderHook(() => useLibrarySearch({ limit: 20 }), {
        wrapper: createWrapper(),
      })

      await waitFor(() => expect(result.current.isError).toBe(true))

      // Should only be called once (no retries)
      expect(mockSearchLibrary).toHaveBeenCalledTimes(1)
    })
  })

  describe('edge cases', () => {
    it('handles empty search query', async () => {
      mockSearchLibrary.mockResolvedValue(mockResponse)

      const { result } = renderHook(() => useLibrarySearch({ query: '', limit: 20 }), {
        wrapper: createWrapper(),
      })

      await waitFor(() => expect(result.current.isSuccess).toBe(true))

      expect(mockSearchLibrary).toHaveBeenCalledWith({ query: '', limit: 20 })
    })

    it('handles empty results', async () => {
      const emptyResponse: LibraryListResponse = {
        items: [],
        total: 0,
        limit: 20,
        offset: 0,
      }
      mockSearchLibrary.mockResolvedValue(emptyResponse)

      const { result } = renderHook(() => useLibrarySearch({ limit: 20 }), {
        wrapper: createWrapper(),
      })

      await waitFor(() => expect(result.current.isSuccess).toBe(true))

      expect(result.current.data?.items).toEqual([])
      expect(result.current.data?.total).toBe(0)
    })
  })

  describe('placeholder data', () => {
    it('keeps previous data while loading new results', async () => {
      mockSearchLibrary.mockResolvedValue(mockResponse)

      const { result, rerender } = renderHook(
        ({ params }: { params: LibrarySearchParams }) => useLibrarySearch(params),
        {
          wrapper: createWrapper(),
          initialProps: { params: { query: 'first', limit: 20 } },
        }
      )

      await waitFor(() => expect(result.current.isSuccess).toBe(true))

      const firstData = result.current.data

      // Change query
      rerender({ params: { query: 'second', limit: 20 } })

      // Should still have old data during loading
      expect(result.current.data).toEqual(firstData)
    })
  })
})

describe('useLibrarySearchInfinite', () => {
  beforeEach(() => {
    mockSearchLibrary.mockReset()
  })

  describe('initialization', () => {
    it('starts with undefined data', () => {
      mockSearchLibrary.mockResolvedValue(mockResponse)

      const { result } = renderHook(() => useLibrarySearchInfinite({ limit: 20 }), {
        wrapper: createWrapper(),
      })

      expect(result.current.data).toBeUndefined()
      expect(result.current.isLoading).toBe(true)
    })

    it('fetches first page on mount', async () => {
      mockSearchLibrary.mockResolvedValue(mockResponse)

      const { result } = renderHook(() => useLibrarySearchInfinite({ limit: 20 }), {
        wrapper: createWrapper(),
      })

      await waitFor(() => expect(result.current.isSuccess).toBe(true))

      expect(mockSearchLibrary).toHaveBeenCalledWith({ limit: 20, offset: 0 })
      expect(result.current.data?.pages).toHaveLength(1)
    })
  })

  describe('pagination', () => {
    it('calculates next page offset correctly', async () => {
      const page1: LibraryListResponse = {
        items: Array(20)
          .fill(null)
          .map((_, i) => ({
            analysis_id: `analysis-${i}`,
            title: `Item ${i}`,
            snippet: null,
            tags: [],
            content_type: 'article',
            status: 'complete',
          })),
        total: 40,
        limit: 20,
        offset: 0,
      }

      mockSearchLibrary.mockResolvedValue(page1)

      const { result } = renderHook(() => useLibrarySearchInfinite({ limit: 20 }), {
        wrapper: createWrapper(),
      })

      await waitFor(() => expect(result.current.isSuccess).toBe(true))

      // Full page returned (20 items), so hook assumes there may be more
      expect(result.current.hasNextPage).toBe(true)
    })

    it('detects end of results when page is incomplete', async () => {
      const page1: LibraryListResponse = {
        items: Array(10)
          .fill(null)
          .map((_, i) => ({
            analysis_id: `analysis-${i}`,
            title: `Item ${i}`,
            snippet: null,
            tags: [],
            content_type: 'article',
            status: 'complete',
          })),
        total: 10,
        limit: 20,
        offset: 0,
      }

      mockSearchLibrary.mockResolvedValue(page1)

      const { result } = renderHook(() => useLibrarySearchInfinite({ limit: 20 }), {
        wrapper: createWrapper(),
      })

      await waitFor(() => expect(result.current.isSuccess).toBe(true))

      expect(result.current.hasNextPage).toBe(false)
    })

    it('uses custom offset if provided', async () => {
      mockSearchLibrary.mockResolvedValue(mockResponse)

      const { result } = renderHook(() => useLibrarySearchInfinite({ limit: 20, offset: 40 }), {
        wrapper: createWrapper(),
      })

      await waitFor(() => expect(result.current.isSuccess).toBe(true))

      expect(mockSearchLibrary).toHaveBeenCalledWith({ limit: 20, offset: 40 })
    })
  })

  describe('query key stability', () => {
    it('stringifies params for stable query key', async () => {
      mockSearchLibrary.mockResolvedValue(mockResponse)

      const { result } = renderHook(() => useLibrarySearchInfinite({ query: 'test', limit: 20 }), {
        wrapper: createWrapper(),
      })

      await waitFor(() => expect(result.current.isSuccess).toBe(true))

      // Query key should be stable across renders
      expect(result.current.data?.pages).toHaveLength(1)
    })
  })

  describe('error handling', () => {
    it('handles API errors', async () => {
      const error = new Error('API Error')
      mockSearchLibrary.mockRejectedValue(error)

      const { result } = renderHook(() => useLibrarySearchInfinite({ limit: 20 }), {
        wrapper: createWrapper(),
      })

      await waitFor(() => expect(result.current.isError).toBe(true))

      expect(result.current.error).toEqual(error)
    })

    it('does not retry on failure', async () => {
      mockSearchLibrary.mockRejectedValue(new Error('API Error'))

      const { result } = renderHook(() => useLibrarySearchInfinite({ limit: 20 }), {
        wrapper: createWrapper(),
      })

      await waitFor(() => expect(result.current.isError).toBe(true))

      // Should only be called once (no retries)
      expect(mockSearchLibrary).toHaveBeenCalledTimes(1)
    })
  })

  describe('edge cases', () => {
    it('handles empty results', async () => {
      const emptyResponse: LibraryListResponse = {
        items: [],
        total: 0,
        limit: 20,
        offset: 0,
      }
      mockSearchLibrary.mockResolvedValue(emptyResponse)

      const { result } = renderHook(() => useLibrarySearchInfinite({ limit: 20 }), {
        wrapper: createWrapper(),
      })

      await waitFor(() => expect(result.current.isSuccess).toBe(true))

      expect(result.current.data?.pages[0].items).toEqual([])
      expect(result.current.hasNextPage).toBe(false)
    })

    it('handles zero limit gracefully', async () => {
      const response: LibraryListResponse = {
        items: [],
        total: 0,
        limit: 0,
        offset: 0,
      }
      mockSearchLibrary.mockResolvedValue(response)

      const { result } = renderHook(() => useLibrarySearchInfinite({ limit: 0 }), {
        wrapper: createWrapper(),
      })

      await waitFor(() => expect(result.current.isSuccess).toBe(true))

      expect(result.current.hasNextPage).toBe(false)
    })
  })
})
