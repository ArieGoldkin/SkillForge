/**
 * Tests for useFeedback hook - Manages feedback state and API interactions
 */

import type { SubmitFeedbackResponse, FlagForReviewResponse } from '@app-types/annotations'
import { act, renderHook, waitFor } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { annotationsAPI } from '@/api/annotations'

import { useFeedback } from '../useFeedback'

// Mock the annotations API
vi.mock('@/api/annotations', () => ({
  annotationsAPI: {
    submitFeedback: vi.fn(),
    flagForReview: vi.fn(),
  },
}))

// Mock the toast hook
vi.mock('@hooks/use-toast', () => ({
  useToast: () => ({
    toast: vi.fn(),
  }),
}))

describe('useFeedback', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  describe('Initial state', () => {
    it('starts with no feedback selected', () => {
      const { result } = renderHook(() =>
        useFeedback({ artifactId: 'artifact-123', traceId: 'trace-456' })
      )

      expect(result.current.selectedFeedback).toBeNull()
      expect(result.current.isSubmitting).toBe(false)
    })

    it('works without traceId', () => {
      const { result } = renderHook(() => useFeedback({ artifactId: 'artifact-123' }))

      expect(result.current.selectedFeedback).toBeNull()
      expect(result.current.isSubmitting).toBe(false)
    })
  })

  describe('submitFeedback', () => {
    it('updates selectedFeedback immediately (optimistic update)', async () => {
      vi.mocked(annotationsAPI.submitFeedback).mockResolvedValueOnce({
        status: 'success',
        message: 'Feedback received',
        langfuse_submitted: true,
      })

      const { result } = renderHook(() =>
        useFeedback({ artifactId: 'artifact-123', traceId: 'trace-456' })
      )

      expect(result.current.selectedFeedback).toBeNull()

      act(() => {
        result.current.submitFeedback('thumbs_up')
      })

      // Optimistic update - should update immediately
      expect(result.current.selectedFeedback).toBe('thumbs_up')
      expect(result.current.isSubmitting).toBe(true)

      await waitFor(() => {
        expect(result.current.isSubmitting).toBe(false)
      })
    })

    it('calls API with correct parameters without comment', async () => {
      const mockResponse: SubmitFeedbackResponse = {
        status: 'success',
        message: 'Feedback received',
        langfuse_submitted: true,
      }
      vi.mocked(annotationsAPI.submitFeedback).mockResolvedValueOnce(mockResponse)

      const { result } = renderHook(() =>
        useFeedback({ artifactId: 'artifact-123', traceId: 'trace-456' })
      )

      act(() => {
        result.current.submitFeedback('thumbs_up')
      })

      await waitFor(() => {
        expect(annotationsAPI.submitFeedback).toHaveBeenCalledWith({
          artifact_id: 'artifact-123',
          trace_id: 'trace-456',
          feedback: 'thumbs_up',
          comment: null,
        })
      })
    })

    it('calls API with comment when provided', async () => {
      const mockResponse: SubmitFeedbackResponse = {
        status: 'success',
        message: 'Feedback received',
        langfuse_submitted: true,
      }
      vi.mocked(annotationsAPI.submitFeedback).mockResolvedValueOnce(mockResponse)

      const { result } = renderHook(() =>
        useFeedback({ artifactId: 'artifact-123', traceId: 'trace-456' })
      )

      act(() => {
        result.current.submitFeedback('thumbs_down', 'Missing important details')
      })

      await waitFor(() => {
        expect(annotationsAPI.submitFeedback).toHaveBeenCalledWith({
          artifact_id: 'artifact-123',
          trace_id: 'trace-456',
          feedback: 'thumbs_down',
          comment: 'Missing important details',
        })
      })
    })

    it('handles null traceId correctly', async () => {
      const mockResponse: SubmitFeedbackResponse = {
        status: 'success',
        message: 'Feedback received',
        langfuse_submitted: false,
      }
      vi.mocked(annotationsAPI.submitFeedback).mockResolvedValueOnce(mockResponse)

      const { result } = renderHook(() =>
        useFeedback({ artifactId: 'artifact-123', traceId: null })
      )

      act(() => {
        result.current.submitFeedback('thumbs_up')
      })

      await waitFor(() => {
        expect(annotationsAPI.submitFeedback).toHaveBeenCalledWith({
          artifact_id: 'artifact-123',
          trace_id: null,
          feedback: 'thumbs_up',
          comment: null,
        })
      })
    })

    it('sets isSubmitting to true during API call', async () => {
      let resolvePromise: (value: SubmitFeedbackResponse) => void
      const promise = new Promise<SubmitFeedbackResponse>((resolve) => {
        resolvePromise = resolve
      })
      vi.mocked(annotationsAPI.submitFeedback).mockReturnValueOnce(promise)

      const { result } = renderHook(() =>
        useFeedback({ artifactId: 'artifact-123', traceId: 'trace-456' })
      )

      act(() => {
        result.current.submitFeedback('thumbs_up')
      })

      expect(result.current.isSubmitting).toBe(true)

      act(() => {
        resolvePromise({
          status: 'success',
          message: 'Feedback received',
          langfuse_submitted: true,
        })
      })

      await waitFor(() => {
        expect(result.current.isSubmitting).toBe(false)
      })
    })

    it('rolls back optimistic update on error', async () => {
      const { result } = renderHook(() =>
        useFeedback({ artifactId: 'artifact-123', traceId: 'trace-456' })
      )

      // First, set an initial feedback successfully
      vi.mocked(annotationsAPI.submitFeedback).mockResolvedValueOnce({
        status: 'success',
        message: 'Feedback received',
        langfuse_submitted: true,
      })

      act(() => {
        result.current.submitFeedback('thumbs_up')
      })

      await waitFor(() => {
        expect(result.current.selectedFeedback).toBe('thumbs_up')
        expect(result.current.isSubmitting).toBe(false)
      })

      // Now try to change feedback and fail
      vi.mocked(annotationsAPI.submitFeedback).mockRejectedValueOnce(new Error('Network error'))

      act(() => {
        result.current.submitFeedback('thumbs_down')
      })

      // Should optimistically update
      expect(result.current.selectedFeedback).toBe('thumbs_down')

      // Should roll back to previous value on error
      await waitFor(() => {
        expect(result.current.selectedFeedback).toBe('thumbs_up')
      })
    })

    it('rolls back to null if error occurs on first feedback', async () => {
      vi.mocked(annotationsAPI.submitFeedback).mockRejectedValueOnce(new Error('Network error'))

      const { result } = renderHook(() =>
        useFeedback({ artifactId: 'artifact-123', traceId: 'trace-456' })
      )

      act(() => {
        result.current.submitFeedback('thumbs_up')
      })

      // Should optimistically update
      expect(result.current.selectedFeedback).toBe('thumbs_up')

      // Should roll back to null on error
      await waitFor(() => {
        expect(result.current.selectedFeedback).toBeNull()
      })
    })

    it('sets isSubmitting to false after error', async () => {
      vi.mocked(annotationsAPI.submitFeedback).mockRejectedValueOnce(new Error('Network error'))

      const { result } = renderHook(() =>
        useFeedback({ artifactId: 'artifact-123', traceId: 'trace-456' })
      )

      act(() => {
        result.current.submitFeedback('thumbs_up')
      })

      expect(result.current.isSubmitting).toBe(true)

      await waitFor(() => {
        expect(result.current.isSubmitting).toBe(false)
      })
    })
  })

  describe('flagForReview', () => {
    it('calls API with correct parameters', async () => {
      const mockResponse: FlagForReviewResponse = {
        queue_id: 1,
        message: 'Flagged for review',
      }
      vi.mocked(annotationsAPI.flagForReview).mockResolvedValueOnce(mockResponse)

      const { result } = renderHook(() =>
        useFeedback({ artifactId: 'artifact-123', traceId: 'trace-456' })
      )

      act(() => {
        result.current.flagForReview('Incorrect information')
      })

      await waitFor(() => {
        expect(annotationsAPI.flagForReview).toHaveBeenCalledWith({
          artifact_id: 'artifact-123',
          reason: 'Incorrect information',
        })
      })
    })

    it('sets isSubmitting during API call', async () => {
      let resolvePromise: (value: FlagForReviewResponse) => void
      const promise = new Promise<FlagForReviewResponse>((resolve) => {
        resolvePromise = resolve
      })
      vi.mocked(annotationsAPI.flagForReview).mockReturnValueOnce(promise)

      const { result } = renderHook(() =>
        useFeedback({ artifactId: 'artifact-123', traceId: 'trace-456' })
      )

      act(() => {
        result.current.flagForReview('Incorrect information')
      })

      expect(result.current.isSubmitting).toBe(true)

      act(() => {
        resolvePromise({
          queue_id: 1,
          message: 'Flagged for review',
        })
      })

      await waitFor(() => {
        expect(result.current.isSubmitting).toBe(false)
      })
    })

    it('sets isSubmitting to false after error', async () => {
      vi.mocked(annotationsAPI.flagForReview).mockRejectedValueOnce(new Error('Network error'))

      const { result } = renderHook(() =>
        useFeedback({ artifactId: 'artifact-123', traceId: 'trace-456' })
      )

      act(() => {
        result.current.flagForReview('Incorrect information')
      })

      expect(result.current.isSubmitting).toBe(true)

      await waitFor(() => {
        expect(result.current.isSubmitting).toBe(false)
      })
    })
  })
})
