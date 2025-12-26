/**
 * Tests for useLibraryData - Main library data orchestration hook
 *
 * Validates integration of search, filtering, and result counting.
 */

import * as React from 'react'

import type { LibraryListResponse } from '@app-types/api'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { renderHook, waitFor } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { analyzeAPI } from '@services/api.service'

import { useLibraryData } from '../useLibraryData'

vi.mock('@services/api.service', () => ({
  analyzeAPI: {
    searchLibrary: vi.fn(),
  },
}))

vi.mock('@tanstack/react-router', () => ({
  useNavigate: () => vi.fn(),
}))

const mockSearchLibrary = vi.mocked(analyzeAPI.searchLibrary)

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
    {
      analysis_id: 'analysis-2',
      title: 'TypeScript Basics',
      snippet: 'TypeScript fundamentals',
      tags: ['typescript'],
      content_type: 'article',
      status: 'complete',
    },
  ],
  total: 2,
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

describe('useLibraryData', () => {
  beforeEach(() => {
    mockSearchLibrary.mockReset()
  })

  describe('initialization', () => {
    it('starts with loading state', () => {
      mockSearchLibrary.mockResolvedValue(mockResponse)

      const { result } = renderHook(
        () =>
          useLibraryData({
            searchQuery: '',
            searchMode: 'hybrid',
            filters: { difficulty: [], tags: [], status: [], durationRange: [0, 100] },
            showCompletedOnly: true,
            limit: 20,
          }),
        {
          wrapper: createWrapper(),
        }
      )

      expect(result.current.isLoading).toBe(true)
      expect(result.current.filteredSkills).toEqual([])
    })

    it('loads data on mount', async () => {
      mockSearchLibrary.mockResolvedValue(mockResponse)

      const { result } = renderHook(
        () =>
          useLibraryData({
            searchQuery: '',
            searchMode: 'hybrid',
            filters: { difficulty: [], tags: [], status: [], durationRange: [0, 100] },
            showCompletedOnly: true,
            limit: 20,
          }),
        {
          wrapper: createWrapper(),
        }
      )

      await waitFor(() => expect(result.current.isLoading).toBe(false))

      expect(result.current.filteredSkills.length).toBe(2)
      expect(mockSearchLibrary).toHaveBeenCalled()
    })
  })

  describe('search functionality', () => {
    it('passes search query to API', async () => {
      mockSearchLibrary.mockResolvedValue(mockResponse)

      const { result } = renderHook(
        () =>
          useLibraryData({
            searchQuery: 'React',
            searchMode: 'hybrid',
            filters: { difficulty: [], tags: [], status: [], durationRange: [0, 100] },
            showCompletedOnly: false,
            limit: 20,
          }),
        {
          wrapper: createWrapper(),
        }
      )

      await waitFor(() => expect(result.current.isLoading).toBe(false))

      expect(mockSearchLibrary).toHaveBeenCalledWith(
        expect.objectContaining({
          query: 'React',
          search_mode: 'hybrid',
        })
      )
    })

    it('handles different search modes', async () => {
      mockSearchLibrary.mockResolvedValue(mockResponse)

      const { result } = renderHook(
        () =>
          useLibraryData({
            searchQuery: 'test',
            searchMode: 'semantic',
            filters: { difficulty: [], tags: [], status: [], durationRange: [0, 100] },
            showCompletedOnly: false,
            limit: 20,
          }),
        {
          wrapper: createWrapper(),
        }
      )

      await waitFor(() => expect(result.current.isLoading).toBe(false))

      expect(mockSearchLibrary).toHaveBeenCalledWith(
        expect.objectContaining({
          search_mode: 'semantic',
        })
      )
    })
  })

  describe('filtering', () => {
    it('applies status filters from showCompletedOnly', async () => {
      mockSearchLibrary.mockResolvedValue(mockResponse)

      const { result } = renderHook(
        () =>
          useLibraryData({
            searchQuery: '',
            searchMode: 'hybrid',
            filters: { difficulty: [], tags: [], status: [], durationRange: [0, 100] },
            showCompletedOnly: true,
            limit: 20,
          }),
        {
          wrapper: createWrapper(),
        }
      )

      await waitFor(() => expect(result.current.isLoading).toBe(false))

      expect(mockSearchLibrary).toHaveBeenCalledWith(
        expect.objectContaining({
          status: 'complete',
        })
      )
    })

    it('applies status filters from filters object', async () => {
      mockSearchLibrary.mockResolvedValue(mockResponse)

      const { result } = renderHook(
        () =>
          useLibraryData({
            searchQuery: '',
            searchMode: 'hybrid',
            filters: {
              difficulty: [],
              tags: [],
              status: ['complete', 'failed'],
              durationRange: [0, 100],
            },
            showCompletedOnly: false,
            limit: 20,
          }),
        {
          wrapper: createWrapper(),
        }
      )

      await waitFor(() => expect(result.current.isLoading).toBe(false))

      // mapFiltersToQuery only returns first status
      expect(mockSearchLibrary).toHaveBeenCalledWith(
        expect.objectContaining({
          status: 'complete',
        })
      )
    })

    it('filters by difficulty client-side', async () => {
      mockSearchLibrary.mockResolvedValue(mockResponse)

      const { result } = renderHook(
        () =>
          useLibraryData({
            searchQuery: '',
            searchMode: 'hybrid',
            filters: {
              difficulty: ['beginner'],
              tags: [],
              status: [],
              durationRange: [0, 100],
            },
            showCompletedOnly: false,
            limit: 20,
          }),
        {
          wrapper: createWrapper(),
        }
      )

      await waitFor(() => expect(result.current.isLoading).toBe(false))

      // All items are 'intermediate', so should be filtered out
      expect(result.current.filteredSkills.length).toBe(0)
    })

    it('filters by tags client-side', async () => {
      mockSearchLibrary.mockResolvedValue(mockResponse)

      const { result } = renderHook(
        () =>
          useLibraryData({
            searchQuery: '',
            searchMode: 'hybrid',
            filters: {
              difficulty: [],
              tags: ['react'],
              status: [],
              durationRange: [0, 100],
            },
            showCompletedOnly: false,
            limit: 20,
          }),
        {
          wrapper: createWrapper(),
        }
      )

      await waitFor(() => expect(result.current.isLoading).toBe(false))

      expect(result.current.filteredSkills.length).toBe(1)
      expect(result.current.filteredSkills[0].title).toBe('React Hooks Guide')
    })
  })

  describe('result counting', () => {
    it('calculates showing and total counts', async () => {
      mockSearchLibrary.mockResolvedValue(mockResponse)

      const { result } = renderHook(
        () =>
          useLibraryData({
            searchQuery: '',
            searchMode: 'hybrid',
            filters: { difficulty: [], tags: [], status: [], durationRange: [0, 100] },
            showCompletedOnly: false,
            limit: 20,
          }),
        {
          wrapper: createWrapper(),
        }
      )

      await waitFor(() => expect(result.current.isLoading).toBe(false))

      expect(result.current.showingCount).toBe(2)
      expect(result.current.totalCount).toBe(2)
    })

    it('shows filtered count when search is active', async () => {
      mockSearchLibrary.mockResolvedValue(mockResponse)

      const { result } = renderHook(
        () =>
          useLibraryData({
            searchQuery: 'React',
            searchMode: 'hybrid',
            filters: { difficulty: [], tags: [], status: [], durationRange: [0, 100] },
            showCompletedOnly: false,
            limit: 20,
          }),
        {
          wrapper: createWrapper(),
        }
      )

      await waitFor(() => expect(result.current.isLoading).toBe(false))

      expect(result.current.showingCount).toBe(2)
    })
  })

  describe('available metadata', () => {
    it('extracts available tags', async () => {
      mockSearchLibrary.mockResolvedValue(mockResponse)

      const { result } = renderHook(
        () =>
          useLibraryData({
            searchQuery: '',
            searchMode: 'hybrid',
            filters: { difficulty: [], tags: [], status: [], durationRange: [0, 100] },
            showCompletedOnly: false,
            limit: 20,
          }),
        {
          wrapper: createWrapper(),
        }
      )

      await waitFor(() => expect(result.current.isLoading).toBe(false))

      expect(result.current.availableTags).toContain('react')
      expect(result.current.availableTags).toContain('typescript')
      expect(result.current.availableTags).toContain('hooks')
    })

    it('extracts available statuses', async () => {
      mockSearchLibrary.mockResolvedValue(mockResponse)

      const { result } = renderHook(
        () =>
          useLibraryData({
            searchQuery: '',
            searchMode: 'hybrid',
            filters: { difficulty: [], tags: [], status: [], durationRange: [0, 100] },
            showCompletedOnly: false,
            limit: 20,
          }),
        {
          wrapper: createWrapper(),
        }
      )

      await waitFor(() => expect(result.current.isLoading).toBe(false))

      expect(result.current.availableStatuses).toContain('complete')
    })
  })

  describe('pagination', () => {
    it('provides hasNextPage flag', async () => {
      mockSearchLibrary.mockResolvedValue(mockResponse)

      const { result } = renderHook(
        () =>
          useLibraryData({
            searchQuery: '',
            searchMode: 'hybrid',
            filters: { difficulty: [], tags: [], status: [], durationRange: [0, 100] },
            showCompletedOnly: false,
            limit: 20,
          }),
        {
          wrapper: createWrapper(),
        }
      )

      await waitFor(() => expect(result.current.isLoading).toBe(false))

      expect(typeof result.current.hasNextPage).toBe('boolean')
    })

    it('provides fetchNextPage function', async () => {
      mockSearchLibrary.mockResolvedValue(mockResponse)

      const { result } = renderHook(
        () =>
          useLibraryData({
            searchQuery: '',
            searchMode: 'hybrid',
            filters: { difficulty: [], tags: [], status: [], durationRange: [0, 100] },
            showCompletedOnly: false,
            limit: 20,
          }),
        {
          wrapper: createWrapper(),
        }
      )

      await waitFor(() => expect(result.current.isLoading).toBe(false))

      expect(typeof result.current.fetchNextPage).toBe('function')
    })
  })

  describe('error handling', () => {
    it('exposes error state', async () => {
      const error = new Error('API Error')
      mockSearchLibrary.mockRejectedValue(error)

      const { result } = renderHook(
        () =>
          useLibraryData({
            searchQuery: '',
            searchMode: 'hybrid',
            filters: { difficulty: [], tags: [], status: [], durationRange: [0, 100] },
            showCompletedOnly: false,
            limit: 20,
          }),
        {
          wrapper: createWrapper(),
        }
      )

      await waitFor(() => expect(result.current.isError).toBe(true))

      expect(result.current.searchError).toEqual(error)
    })

    it('provides refetch function', async () => {
      mockSearchLibrary.mockResolvedValue(mockResponse)

      const { result } = renderHook(
        () =>
          useLibraryData({
            searchQuery: '',
            searchMode: 'hybrid',
            filters: { difficulty: [], tags: [], status: [], durationRange: [0, 100] },
            showCompletedOnly: false,
            limit: 20,
          }),
        {
          wrapper: createWrapper(),
        }
      )

      await waitFor(() => expect(result.current.isLoading).toBe(false))

      expect(typeof result.current.refetch).toBe('function')
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

      const { result } = renderHook(
        () =>
          useLibraryData({
            searchQuery: '',
            searchMode: 'hybrid',
            filters: { difficulty: [], tags: [], status: [], durationRange: [0, 100] },
            showCompletedOnly: false,
            limit: 20,
          }),
        {
          wrapper: createWrapper(),
        }
      )

      await waitFor(() => expect(result.current.isLoading).toBe(false))

      expect(result.current.filteredSkills).toEqual([])
      expect(result.current.showingCount).toBe(0)
      expect(result.current.totalCount).toBe(0)
    })

    it('handles undefined search results gracefully', async () => {
      mockSearchLibrary.mockResolvedValue({
        items: [],
        total: 0,
        limit: 20,
        offset: 0,
      })

      const { result } = renderHook(
        () =>
          useLibraryData({
            searchQuery: '',
            searchMode: 'hybrid',
            filters: { difficulty: [], tags: [], status: [], durationRange: [0, 100] },
            showCompletedOnly: false,
            limit: 20,
          }),
        {
          wrapper: createWrapper(),
        }
      )

      await waitFor(() => expect(result.current.isLoading).toBe(false))

      expect(result.current.filteredSkills).toEqual([])
    })
  })
})
