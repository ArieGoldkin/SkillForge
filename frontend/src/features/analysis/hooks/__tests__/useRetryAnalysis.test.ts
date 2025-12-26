/**
 * Tests for useRetryAnalysis - Retry failed analysis hook
 *
 * Validates retry logic, loading states, error handling,
 * and API response data management.
 */

import type { AnalysisRetryResponse } from '@app-types/api'
import { renderHook, act, waitFor } from '@testing-library/react'
import { describe, it, expect, beforeEach, vi } from 'vitest'

import { analyzeAPI } from '@services/api.service'

import { useRetryAnalysis } from '../useRetryAnalysis'

// Mock the API service
vi.mock('@services/api.service', () => ({
  analyzeAPI: {
    retryAnalysis: vi.fn(),
  },
}))

// Mock the logger
vi.mock('@lib/logger', () => ({
  logger: {
    info: vi.fn(),
    error: vi.fn(),
  },
}))

describe('useRetryAnalysis', () => {
  const TEST_ANALYSIS_ID = '123e4567-e89b-12d3-a456-426614174000'

  beforeEach(() => {
    vi.clearAllMocks()
  })

  describe('initialization', () => {
    it('starts with default state', () => {
      const { result } = renderHook(() => useRetryAnalysis(TEST_ANALYSIS_ID))

      expect(result.current.isRetrying).toBe(false)
      expect(result.current.error).toBeNull()
      expect(result.current.data).toBeNull()
      expect(typeof result.current.retry).toBe('function')
    })
  })

  describe('successful retry', () => {
    it('calls API with correct analysis ID', async () => {
      const mockResponse: AnalysisRetryResponse = {
        id: TEST_ANALYSIS_ID,
        status: 'pending',
        retry_count: 1,
        sse_endpoint: `/api/v1/analyze/${TEST_ANALYSIS_ID}/progress`,
      }

      vi.mocked(analyzeAPI.retryAnalysis).mockResolvedValueOnce(mockResponse)

      const { result } = renderHook(() => useRetryAnalysis(TEST_ANALYSIS_ID))

      await act(async () => {
        await result.current.retry()
      })

      expect(analyzeAPI.retryAnalysis).toHaveBeenCalledWith(TEST_ANALYSIS_ID)
      expect(analyzeAPI.retryAnalysis).toHaveBeenCalledTimes(1)
    })

    it('sets isRetrying to true during API call', async () => {
      let resolvePromise: (value: AnalysisRetryResponse) => void
      const promise = new Promise<AnalysisRetryResponse>((resolve) => {
        resolvePromise = resolve
      })

      vi.mocked(analyzeAPI.retryAnalysis).mockReturnValueOnce(promise)

      const { result } = renderHook(() => useRetryAnalysis(TEST_ANALYSIS_ID))

      act(() => {
        void result.current.retry()
      })

      expect(result.current.isRetrying).toBe(true)

      await act(async () => {
        resolvePromise({
          id: TEST_ANALYSIS_ID,
          status: 'pending',
          retry_count: 1,
          sse_endpoint: `/api/v1/analyze/${TEST_ANALYSIS_ID}/progress`,
        })
      })

      await waitFor(() => {
        expect(result.current.isRetrying).toBe(false)
      })
    })

    it('sets data on successful retry', async () => {
      const mockResponse: AnalysisRetryResponse = {
        id: TEST_ANALYSIS_ID,
        status: 'pending',
        retry_count: 1,
        sse_endpoint: `/api/v1/analyze/${TEST_ANALYSIS_ID}/progress`,
      }

      vi.mocked(analyzeAPI.retryAnalysis).mockResolvedValueOnce(mockResponse)

      const { result } = renderHook(() => useRetryAnalysis(TEST_ANALYSIS_ID))

      await act(async () => {
        await result.current.retry()
      })

      expect(result.current.data).toEqual(mockResponse)
      expect(result.current.error).toBeNull()
    })

    it('returns response data from retry function', async () => {
      const mockResponse: AnalysisRetryResponse = {
        id: TEST_ANALYSIS_ID,
        status: 'pending',
        retry_count: 1,
        sse_endpoint: `/api/v1/analyze/${TEST_ANALYSIS_ID}/progress`,
      }

      vi.mocked(analyzeAPI.retryAnalysis).mockResolvedValueOnce(mockResponse)

      const { result } = renderHook(() => useRetryAnalysis(TEST_ANALYSIS_ID))

      let returnedData: AnalysisRetryResponse | null = null
      await act(async () => {
        returnedData = await result.current.retry()
      })

      expect(returnedData).toEqual(mockResponse)
    })

    it('clears previous error on successful retry', async () => {
      const mockResponse: AnalysisRetryResponse = {
        id: TEST_ANALYSIS_ID,
        status: 'pending',
        retry_count: 1,
        sse_endpoint: `/api/v1/analyze/${TEST_ANALYSIS_ID}/progress`,
      }

      vi.mocked(analyzeAPI.retryAnalysis)
        .mockRejectedValueOnce(new Error('Network error'))
        .mockResolvedValueOnce(mockResponse)

      const { result } = renderHook(() => useRetryAnalysis(TEST_ANALYSIS_ID))

      // First retry fails
      await act(async () => {
        await result.current.retry()
      })
      expect(result.current.error).toBe('Network error')

      // Second retry succeeds
      await act(async () => {
        await result.current.retry()
      })
      expect(result.current.error).toBeNull()
    })

    it('increments retry count correctly', async () => {
      const mockResponse1: AnalysisRetryResponse = {
        id: TEST_ANALYSIS_ID,
        status: 'pending',
        retry_count: 1,
        sse_endpoint: `/api/v1/analyze/${TEST_ANALYSIS_ID}/progress`,
      }

      const mockResponse2: AnalysisRetryResponse = {
        id: TEST_ANALYSIS_ID,
        status: 'pending',
        retry_count: 2,
        sse_endpoint: `/api/v1/analyze/${TEST_ANALYSIS_ID}/progress`,
      }

      vi.mocked(analyzeAPI.retryAnalysis)
        .mockResolvedValueOnce(mockResponse1)
        .mockResolvedValueOnce(mockResponse2)

      const { result } = renderHook(() => useRetryAnalysis(TEST_ANALYSIS_ID))

      await act(async () => {
        await result.current.retry()
      })
      expect(result.current.data?.retry_count).toBe(1)

      await act(async () => {
        await result.current.retry()
      })
      expect(result.current.data?.retry_count).toBe(2)
    })
  })

  describe('failed retry', () => {
    it('sets error on API failure', async () => {
      const errorMessage = 'Network error'
      vi.mocked(analyzeAPI.retryAnalysis).mockRejectedValueOnce(new Error(errorMessage))

      const { result } = renderHook(() => useRetryAnalysis(TEST_ANALYSIS_ID))

      await act(async () => {
        await result.current.retry()
      })

      expect(result.current.error).toBe(errorMessage)
      expect(result.current.data).toBeNull()
    })

    it('sets isRetrying to false after error', async () => {
      vi.mocked(analyzeAPI.retryAnalysis).mockRejectedValueOnce(new Error('Network error'))

      const { result } = renderHook(() => useRetryAnalysis(TEST_ANALYSIS_ID))

      await act(async () => {
        await result.current.retry()
      })

      expect(result.current.isRetrying).toBe(false)
    })

    it('returns null from retry function on error', async () => {
      vi.mocked(analyzeAPI.retryAnalysis).mockRejectedValueOnce(new Error('Network error'))

      const { result } = renderHook(() => useRetryAnalysis(TEST_ANALYSIS_ID))

      let returnedData: AnalysisRetryResponse | null = null
      await act(async () => {
        returnedData = await result.current.retry()
      })

      expect(returnedData).toBeNull()
    })

    it('handles non-Error exceptions', async () => {
      vi.mocked(analyzeAPI.retryAnalysis).mockRejectedValueOnce('String error')

      const { result } = renderHook(() => useRetryAnalysis(TEST_ANALYSIS_ID))

      await act(async () => {
        await result.current.retry()
      })

      expect(result.current.error).toBe('Failed to retry analysis')
    })

    it('preserves previous data on error', async () => {
      const mockResponse: AnalysisRetryResponse = {
        id: TEST_ANALYSIS_ID,
        status: 'pending',
        retry_count: 1,
        sse_endpoint: `/api/v1/analyze/${TEST_ANALYSIS_ID}/progress`,
      }

      vi.mocked(analyzeAPI.retryAnalysis)
        .mockResolvedValueOnce(mockResponse)
        .mockRejectedValueOnce(new Error('Network error'))

      const { result } = renderHook(() => useRetryAnalysis(TEST_ANALYSIS_ID))

      // First retry succeeds
      await act(async () => {
        await result.current.retry()
      })
      const previousData = result.current.data

      // Second retry fails
      await act(async () => {
        await result.current.retry()
      })

      // Data should be preserved from previous successful retry
      expect(result.current.data).toEqual(previousData)
    })
  })

  describe('multiple retries', () => {
    it('allows multiple consecutive retries', async () => {
      const mockResponse: AnalysisRetryResponse = {
        id: TEST_ANALYSIS_ID,
        status: 'pending',
        retry_count: 1,
        sse_endpoint: `/api/v1/analyze/${TEST_ANALYSIS_ID}/progress`,
      }

      vi.mocked(analyzeAPI.retryAnalysis).mockResolvedValue(mockResponse)

      const { result } = renderHook(() => useRetryAnalysis(TEST_ANALYSIS_ID))

      await act(async () => {
        await result.current.retry()
      })
      expect(analyzeAPI.retryAnalysis).toHaveBeenCalledTimes(1)

      await act(async () => {
        await result.current.retry()
      })
      expect(analyzeAPI.retryAnalysis).toHaveBeenCalledTimes(2)

      await act(async () => {
        await result.current.retry()
      })
      expect(analyzeAPI.retryAnalysis).toHaveBeenCalledTimes(3)
    })

    it('handles alternating success and failure', async () => {
      const mockResponse: AnalysisRetryResponse = {
        id: TEST_ANALYSIS_ID,
        status: 'pending',
        retry_count: 1,
        sse_endpoint: `/api/v1/analyze/${TEST_ANALYSIS_ID}/progress`,
      }

      vi.mocked(analyzeAPI.retryAnalysis)
        .mockResolvedValueOnce(mockResponse)
        .mockRejectedValueOnce(new Error('Error 1'))
        .mockResolvedValueOnce(mockResponse)
        .mockRejectedValueOnce(new Error('Error 2'))

      const { result } = renderHook(() => useRetryAnalysis(TEST_ANALYSIS_ID))

      // Success
      await act(async () => {
        await result.current.retry()
      })
      expect(result.current.error).toBeNull()
      expect(result.current.data).toEqual(mockResponse)

      // Failure
      await act(async () => {
        await result.current.retry()
      })
      expect(result.current.error).toBe('Error 1')

      // Success
      await act(async () => {
        await result.current.retry()
      })
      expect(result.current.error).toBeNull()

      // Failure
      await act(async () => {
        await result.current.retry()
      })
      expect(result.current.error).toBe('Error 2')
    })
  })

  describe('edge cases', () => {
    it('handles empty analysis ID', async () => {
      const mockResponse: AnalysisRetryResponse = {
        id: '',
        status: 'pending',
        retry_count: 1,
        sse_endpoint: '/api/v1/analyze//progress',
      }

      vi.mocked(analyzeAPI.retryAnalysis).mockResolvedValueOnce(mockResponse)

      const { result } = renderHook(() => useRetryAnalysis(''))

      await act(async () => {
        await result.current.retry()
      })

      expect(analyzeAPI.retryAnalysis).toHaveBeenCalledWith('')
    })

    it('handles different status values in response', async () => {
      const statuses: Array<'pending' | 'running' | 'complete' | 'failed'> = [
        'pending',
        'running',
        'complete',
        'failed',
      ]

      for (const status of statuses) {
        const mockResponse: AnalysisRetryResponse = {
          id: TEST_ANALYSIS_ID,
          status,
          retry_count: 1,
          sse_endpoint: `/api/v1/analyze/${TEST_ANALYSIS_ID}/progress`,
        }

        vi.mocked(analyzeAPI.retryAnalysis).mockResolvedValueOnce(mockResponse)

        const { result } = renderHook(() => useRetryAnalysis(TEST_ANALYSIS_ID))

        await act(async () => {
          await result.current.retry()
        })

        expect(result.current.data?.status).toBe(status)
      }
    })

    it('handles high retry counts', async () => {
      const mockResponse: AnalysisRetryResponse = {
        id: TEST_ANALYSIS_ID,
        status: 'pending',
        retry_count: 999,
        sse_endpoint: `/api/v1/analyze/${TEST_ANALYSIS_ID}/progress`,
      }

      vi.mocked(analyzeAPI.retryAnalysis).mockResolvedValueOnce(mockResponse)

      const { result } = renderHook(() => useRetryAnalysis(TEST_ANALYSIS_ID))

      await act(async () => {
        await result.current.retry()
      })

      expect(result.current.data?.retry_count).toBe(999)
    })
  })

  describe('loading state transitions', () => {
    it('transitions correctly through loading states', async () => {
      let resolvePromise: (value: AnalysisRetryResponse) => void
      const promise = new Promise<AnalysisRetryResponse>((resolve) => {
        resolvePromise = resolve
      })

      vi.mocked(analyzeAPI.retryAnalysis).mockReturnValueOnce(promise)

      const { result } = renderHook(() => useRetryAnalysis(TEST_ANALYSIS_ID))

      // Initial state
      expect(result.current.isRetrying).toBe(false)

      // Trigger retry
      act(() => {
        void result.current.retry()
      })

      // Loading state
      expect(result.current.isRetrying).toBe(true)

      // Resolve promise
      await act(async () => {
        resolvePromise({
          id: TEST_ANALYSIS_ID,
          status: 'pending',
          retry_count: 1,
          sse_endpoint: `/api/v1/analyze/${TEST_ANALYSIS_ID}/progress`,
        })
      })

      // Back to idle state
      await waitFor(() => {
        expect(result.current.isRetrying).toBe(false)
      })
    })

    it('allows multiple retry calls to execute', async () => {
      const mockResponse: AnalysisRetryResponse = {
        id: TEST_ANALYSIS_ID,
        status: 'pending',
        retry_count: 1,
        sse_endpoint: `/api/v1/analyze/${TEST_ANALYSIS_ID}/progress`,
      }

      vi.mocked(analyzeAPI.retryAnalysis).mockResolvedValue(mockResponse)

      const { result } = renderHook(() => useRetryAnalysis(TEST_ANALYSIS_ID))

      // Call retry twice rapidly
      await act(async () => {
        void result.current.retry()
        await result.current.retry()
      })

      // The hook allows multiple retry calls (no concurrency guard implemented)
      // This is by design - the caller is responsible for debouncing if needed
      expect(analyzeAPI.retryAnalysis).toHaveBeenCalledWith(TEST_ANALYSIS_ID)
      expect(result.current.data).toEqual(mockResponse)
    })
  })
})
