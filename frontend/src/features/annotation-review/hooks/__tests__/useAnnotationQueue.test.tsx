/**
 * Tests for useAnnotationQueue hook - Manages annotation queue state and API interactions
 */

import type { ReactNode } from 'react'

import type { AnnotationQueueListResponse } from '@app-types/annotations'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { act, renderHook, waitFor } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { annotationsAPI } from '@/api/annotations'

import { useAnnotationQueue } from '../useAnnotationQueue'

// Mock the annotations API
vi.mock('@/api/annotations', () => ({
  annotationsAPI: {
    getAnnotationQueue: vi.fn(),
    markReviewed: vi.fn(),
  },
}))

// Mock the toast hook
vi.mock('@hooks/use-toast', () => ({
  useToast: () => ({
    toast: vi.fn(),
  }),
}))

// Create a wrapper with QueryClientProvider
function createWrapper() {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: {
        retry: false,
        gcTime: 0,
      },
      mutations: {
        retry: false,
      },
    },
  })

  return function Wrapper({ children }: { children: ReactNode }) {
    return <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
  }
}

describe('useAnnotationQueue', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  describe('Initial state', () => {
    it('starts with empty items and loading state', () => {
      vi.mocked(annotationsAPI.getAnnotationQueue).mockImplementation(
        () => new Promise(() => {}) // Never resolves
      )

      const { result } = renderHook(() => useAnnotationQueue(), {
        wrapper: createWrapper(),
      })

      expect(result.current.items).toEqual([])
      expect(result.current.total).toBe(0)
      expect(result.current.isLoading).toBe(true)
      expect(result.current.error).toBeNull()
    })

    it('accepts query options', () => {
      vi.mocked(annotationsAPI.getAnnotationQueue).mockImplementation(
        () => new Promise(() => {}) // Never resolves
      )

      renderHook(() => useAnnotationQueue({ limit: 20, offset: 0, status: 'pending' }), {
        wrapper: createWrapper(),
      })

      expect(annotationsAPI.getAnnotationQueue).toHaveBeenCalledWith({
        limit: 20,
        offset: 0,
        status: 'pending',
      })
    })
  })

  describe('Successful data fetch', () => {
    it('loads and displays queue items', async () => {
      const mockResponse: AnnotationQueueListResponse = {
        items: [
          {
            id: 1,
            artifact_id: 'artifact-123',
            reason: 'Poor quality',
            status: 'pending',
            created_at: '2024-01-01T00:00:00Z',
            reviewed_at: null,
          },
          {
            id: 2,
            artifact_id: 'artifact-456',
            reason: 'Incorrect information',
            status: 'pending',
            created_at: '2024-01-02T00:00:00Z',
            reviewed_at: null,
          },
        ],
        total: 2,
        limit: 20,
        offset: 0,
      }

      vi.mocked(annotationsAPI.getAnnotationQueue).mockResolvedValueOnce(mockResponse)

      const { result } = renderHook(() => useAnnotationQueue(), {
        wrapper: createWrapper(),
      })

      await waitFor(() => {
        expect(result.current.isLoading).toBe(false)
      })

      expect(result.current.items).toHaveLength(2)
      expect(result.current.items[0].id).toBe(1)
      expect(result.current.items[1].id).toBe(2)
      expect(result.current.total).toBe(2)
      expect(result.current.error).toBeNull()
    })

    it('handles empty queue', async () => {
      const mockResponse: AnnotationQueueListResponse = {
        items: [],
        total: 0,
        limit: 20,
        offset: 0,
      }

      vi.mocked(annotationsAPI.getAnnotationQueue).mockResolvedValueOnce(mockResponse)

      const { result } = renderHook(() => useAnnotationQueue(), {
        wrapper: createWrapper(),
      })

      await waitFor(() => {
        expect(result.current.isLoading).toBe(false)
      })

      expect(result.current.items).toEqual([])
      expect(result.current.total).toBe(0)
      expect(result.current.error).toBeNull()
    })

    it('passes query parameters correctly', async () => {
      const mockResponse: AnnotationQueueListResponse = {
        items: [],
        total: 0,
        limit: 10,
        offset: 20,
      }

      vi.mocked(annotationsAPI.getAnnotationQueue).mockResolvedValueOnce(mockResponse)

      const { result } = renderHook(
        () => useAnnotationQueue({ limit: 10, offset: 20, status: 'reviewed' }),
        {
          wrapper: createWrapper(),
        }
      )

      await waitFor(() => {
        expect(result.current.isLoading).toBe(false)
      })

      expect(annotationsAPI.getAnnotationQueue).toHaveBeenCalledWith({
        limit: 10,
        offset: 20,
        status: 'reviewed',
      })
    })
  })

  describe('Error handling', () => {
    it('handles API errors', async () => {
      const mockError = new Error('Failed to fetch queue')
      vi.mocked(annotationsAPI.getAnnotationQueue).mockRejectedValueOnce(mockError)

      const { result } = renderHook(() => useAnnotationQueue(), {
        wrapper: createWrapper(),
      })

      await waitFor(() => {
        expect(result.current.isLoading).toBe(false)
      })

      expect(result.current.items).toEqual([])
      expect(result.current.total).toBe(0)
      expect(result.current.error).toBeTruthy()
    })
  })

  describe('markReviewed mutation', () => {
    it('updates item status when marking as reviewed', async () => {
      const mockInitialResponse: AnnotationQueueListResponse = {
        items: [
          {
            id: 1,
            artifact_id: 'artifact-123',
            reason: 'Poor quality',
            status: 'pending',
            created_at: '2024-01-01T00:00:00Z',
            reviewed_at: null,
          },
        ],
        total: 1,
        limit: 20,
        offset: 0,
      }

      const mockUpdatedResponse: AnnotationQueueListResponse = {
        items: [
          {
            id: 1,
            artifact_id: 'artifact-123',
            reason: 'Poor quality',
            status: 'reviewed',
            created_at: '2024-01-01T00:00:00Z',
            reviewed_at: '2024-01-01T01:00:00Z',
          },
        ],
        total: 1,
        limit: 20,
        offset: 0,
      }

      vi.mocked(annotationsAPI.getAnnotationQueue)
        .mockResolvedValueOnce(mockInitialResponse)
        .mockResolvedValueOnce(mockUpdatedResponse)

      vi.mocked(annotationsAPI.markReviewed).mockResolvedValueOnce({
        status: 'success',
        message: 'Marked as reviewed',
      })

      const { result } = renderHook(() => useAnnotationQueue(), {
        wrapper: createWrapper(),
      })

      await waitFor(() => {
        expect(result.current.isLoading).toBe(false)
      })

      expect(result.current.items[0].status).toBe('pending')
      expect(result.current.items[0].reviewed_at).toBeNull()

      // Perform mutation
      act(() => {
        result.current.markReviewed(1)
      })

      // Wait for mutation to complete and query to refetch
      await waitFor(() => {
        expect(result.current.items[0].status).toBe('reviewed')
        expect(result.current.items[0].reviewed_at).toBe('2024-01-01T01:00:00Z')
      })
    })

    it('calls API with correct queue ID', async () => {
      const mockResponse: AnnotationQueueListResponse = {
        items: [
          {
            id: 42,
            artifact_id: 'artifact-123',
            reason: 'Poor quality',
            status: 'pending',
            created_at: '2024-01-01T00:00:00Z',
            reviewed_at: null,
          },
        ],
        total: 1,
        limit: 20,
        offset: 0,
      }

      vi.mocked(annotationsAPI.getAnnotationQueue).mockResolvedValue(mockResponse)
      vi.mocked(annotationsAPI.markReviewed).mockResolvedValueOnce({
        status: 'success',
        message: 'Marked as reviewed',
      })

      const { result } = renderHook(() => useAnnotationQueue(), {
        wrapper: createWrapper(),
      })

      await waitFor(() => {
        expect(result.current.isLoading).toBe(false)
      })

      act(() => {
        result.current.markReviewed(42)
      })

      await waitFor(() => {
        expect(annotationsAPI.markReviewed).toHaveBeenCalledWith(42)
      })
    })

    it('reverts optimistic update on error', async () => {
      const mockResponse: AnnotationQueueListResponse = {
        items: [
          {
            id: 1,
            artifact_id: 'artifact-123',
            reason: 'Poor quality',
            status: 'pending',
            created_at: '2024-01-01T00:00:00Z',
            reviewed_at: null,
          },
        ],
        total: 1,
        limit: 20,
        offset: 0,
      }

      vi.mocked(annotationsAPI.getAnnotationQueue).mockResolvedValue(mockResponse)
      vi.mocked(annotationsAPI.markReviewed).mockRejectedValueOnce(
        new Error('Failed to mark as reviewed')
      )

      const { result } = renderHook(() => useAnnotationQueue(), {
        wrapper: createWrapper(),
      })

      await waitFor(() => {
        expect(result.current.isLoading).toBe(false)
      })

      expect(result.current.items[0].status).toBe('pending')

      // Perform mutation that will fail
      act(() => {
        result.current.markReviewed(1)
      })

      // Wait for error and rollback
      await waitFor(() => {
        expect(result.current.items[0].status).toBe('pending')
        expect(result.current.items[0].reviewed_at).toBeNull()
      })
    })

    it('invalidates queries after successful mutation', async () => {
      const mockResponse: AnnotationQueueListResponse = {
        items: [
          {
            id: 1,
            artifact_id: 'artifact-123',
            reason: 'Poor quality',
            status: 'pending',
            created_at: '2024-01-01T00:00:00Z',
            reviewed_at: null,
          },
        ],
        total: 1,
        limit: 20,
        offset: 0,
      }

      const mockUpdatedResponse: AnnotationQueueListResponse = {
        items: [
          {
            id: 1,
            artifact_id: 'artifact-123',
            reason: 'Poor quality',
            status: 'reviewed',
            created_at: '2024-01-01T00:00:00Z',
            reviewed_at: '2024-01-01T01:00:00Z',
          },
        ],
        total: 1,
        limit: 20,
        offset: 0,
      }

      vi.mocked(annotationsAPI.getAnnotationQueue)
        .mockResolvedValueOnce(mockResponse)
        .mockResolvedValueOnce(mockUpdatedResponse)

      vi.mocked(annotationsAPI.markReviewed).mockResolvedValueOnce({
        status: 'success',
        message: 'Marked as reviewed',
      })

      const { result } = renderHook(() => useAnnotationQueue(), {
        wrapper: createWrapper(),
      })

      await waitFor(() => {
        expect(result.current.isLoading).toBe(false)
      })

      act(() => {
        result.current.markReviewed(1)
      })

      // Wait for mutation to complete and query to be refetched
      await waitFor(() => {
        expect(result.current.items[0].status).toBe('reviewed')
        expect(result.current.items[0].reviewed_at).toBe('2024-01-01T01:00:00Z')
      })
    })

    it('tracks isMarkingReviewed state during mutation', async () => {
      const mockResponse: AnnotationQueueListResponse = {
        items: [
          {
            id: 1,
            artifact_id: 'artifact-123',
            reason: 'Poor quality',
            status: 'pending',
            created_at: '2024-01-01T00:00:00Z',
            reviewed_at: null,
          },
        ],
        total: 1,
        limit: 20,
        offset: 0,
      }

      vi.mocked(annotationsAPI.getAnnotationQueue).mockResolvedValue(mockResponse)
      vi.mocked(annotationsAPI.markReviewed).mockImplementation(
        () =>
          new Promise((resolve) => {
            setTimeout(() => resolve({ status: 'success', message: 'Marked as reviewed' }), 100)
          })
      )

      const { result } = renderHook(() => useAnnotationQueue(), {
        wrapper: createWrapper(),
      })

      await waitFor(() => {
        expect(result.current.isLoading).toBe(false)
      })

      expect(result.current.isMarkingReviewed).toBe(false)

      act(() => {
        result.current.markReviewed(1)
      })

      // Should be marking during mutation
      await waitFor(() => {
        expect(result.current.isMarkingReviewed).toBe(true)
      })

      // Should complete
      await waitFor(() => {
        expect(result.current.isMarkingReviewed).toBe(false)
      })
    })
  })

  describe('Refetch', () => {
    it('provides refetch function', async () => {
      const mockResponse: AnnotationQueueListResponse = {
        items: [],
        total: 0,
        limit: 20,
        offset: 0,
      }

      vi.mocked(annotationsAPI.getAnnotationQueue).mockResolvedValue(mockResponse)

      const { result } = renderHook(() => useAnnotationQueue(), {
        wrapper: createWrapper(),
      })

      await waitFor(() => {
        expect(result.current.isLoading).toBe(false)
      })

      expect(result.current.refetch).toBeDefined()
      expect(typeof result.current.refetch).toBe('function')

      // Call refetch
      await act(async () => {
        await result.current.refetch()
      })

      // API should be called again
      expect(annotationsAPI.getAnnotationQueue).toHaveBeenCalledTimes(2)
    })
  })
})
