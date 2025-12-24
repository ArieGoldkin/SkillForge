/**
 * Tests for annotations API client
 *
 * Note: Uses vi.hoisted to ensure env is set BEFORE module loads
 */

import type {
  SubmitFeedbackRequest,
  SubmitFeedbackResponse,
  FlagForReviewRequest,
  FlagForReviewResponse,
  AnnotationQueueListResponse,
} from '@app-types/annotations'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

// Set up env BEFORE the module imports (hoisted to top of file)
const { mockFetch, API_BASE_URL } = vi.hoisted(() => {
  const url = 'http://localhost:8500'
  // Stub the env variable before annotations.ts loads
  vi.stubEnv('VITE_API_BASE_URL', url)
  return {
    mockFetch: vi.fn(),
    API_BASE_URL: url,
  }
})

// eslint-disable-next-line import/first -- Module must import AFTER vi.hoisted stubs the env
import { annotationsAPI } from '../annotations'

// Set up fetch mock globally
vi.stubGlobal('fetch', mockFetch)

describe('annotationsAPI', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  afterEach(() => {
    // Don't unstub envs - they were set in hoisted block
  })

  describe('submitFeedback', () => {
    it('calls correct endpoint with POST method', async () => {
      const mockResponse: SubmitFeedbackResponse = {
        status: 'success',
        message: 'Feedback submitted',
        langfuse_submitted: true,
      }

      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => mockResponse,
      })

      const request: SubmitFeedbackRequest = {
        artifact_id: 'artifact-123',
        trace_id: 'trace-456',
        feedback: 'thumbs_up',
        comment: null,
      }

      await annotationsAPI.submitFeedback(request)

      expect(mockFetch).toHaveBeenCalledWith(
        `${API_BASE_URL}/api/v1/annotations/feedback`,
        expect.objectContaining({
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify(request),
        })
      )
    })

    it('returns response data on success', async () => {
      const mockResponse: SubmitFeedbackResponse = {
        status: 'success',
        message: 'Feedback submitted',
        langfuse_submitted: true,
      }

      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => mockResponse,
      })

      const request: SubmitFeedbackRequest = {
        artifact_id: 'artifact-123',
        trace_id: 'trace-456',
        feedback: 'thumbs_down',
        comment: 'Missing examples',
      }

      const result = await annotationsAPI.submitFeedback(request)

      expect(result).toEqual(mockResponse)
    })

    it('throws error when response is not ok', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: false,
        status: 400,
        json: async () => ({ detail: 'Invalid request' }),
      })

      const request: SubmitFeedbackRequest = {
        artifact_id: 'artifact-123',
        trace_id: null,
        feedback: 'thumbs_up',
        comment: null,
      }

      await expect(annotationsAPI.submitFeedback(request)).rejects.toThrow('Invalid request')
    })

    it('throws error with status when no detail in response', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: false,
        status: 500,
        json: async () => ({}),
      })

      const request: SubmitFeedbackRequest = {
        artifact_id: 'artifact-123',
        trace_id: null,
        feedback: 'thumbs_up',
        comment: null,
      }

      await expect(annotationsAPI.submitFeedback(request)).rejects.toThrow('API error: 500')
    })

    it('handles JSON parse error in error response', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: false,
        status: 500,
        json: async () => {
          throw new Error('Parse error')
        },
      })

      const request: SubmitFeedbackRequest = {
        artifact_id: 'artifact-123',
        trace_id: null,
        feedback: 'thumbs_up',
        comment: null,
      }

      await expect(annotationsAPI.submitFeedback(request)).rejects.toThrow('API error: 500')
    })
  })

  describe('flagForReview', () => {
    it('calls correct endpoint with POST method', async () => {
      const mockResponse: FlagForReviewResponse = {
        queue_id: 1,
        message: 'Flagged for review',
      }

      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => mockResponse,
      })

      const request: FlagForReviewRequest = {
        artifact_id: 'artifact-123',
        reason: 'Incorrect information',
      }

      await annotationsAPI.flagForReview(request)

      expect(mockFetch).toHaveBeenCalledWith(
        `${API_BASE_URL}/api/v1/annotations/flag`,
        expect.objectContaining({
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify(request),
        })
      )
    })

    it('returns response data on success', async () => {
      const mockResponse: FlagForReviewResponse = {
        queue_id: 42,
        message: 'Successfully flagged',
      }

      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => mockResponse,
      })

      const request: FlagForReviewRequest = {
        artifact_id: 'artifact-123',
        reason: 'Outdated content',
      }

      const result = await annotationsAPI.flagForReview(request)

      expect(result).toEqual(mockResponse)
    })

    it('throws error when response is not ok', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: false,
        status: 404,
        json: async () => ({ message: 'Artifact not found' }),
      })

      const request: FlagForReviewRequest = {
        artifact_id: 'invalid-id',
        reason: 'Test',
      }

      await expect(annotationsAPI.flagForReview(request)).rejects.toThrow('Artifact not found')
    })
  })

  describe('getAnnotationQueue', () => {
    it('calls correct endpoint with GET method', async () => {
      const mockResponse: AnnotationQueueListResponse = {
        items: [],
        total: 0,
        limit: 20,
        offset: 0,
      }

      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => mockResponse,
      })

      await annotationsAPI.getAnnotationQueue()

      expect(mockFetch).toHaveBeenCalledWith(
        `${API_BASE_URL}/api/v1/annotations/queue`,
        expect.objectContaining({
          headers: {
            'Content-Type': 'application/json',
          },
        })
      )
    })

    it('includes query parameters when provided', async () => {
      const mockResponse: AnnotationQueueListResponse = {
        items: [],
        total: 0,
        limit: 10,
        offset: 20,
      }

      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => mockResponse,
      })

      await annotationsAPI.getAnnotationQueue({
        limit: 10,
        offset: 20,
        status: 'pending',
      })

      expect(mockFetch).toHaveBeenCalledWith(
        `${API_BASE_URL}/api/v1/annotations/queue?limit=10&offset=20&status=pending`,
        expect.objectContaining({
          headers: {
            'Content-Type': 'application/json',
          },
        })
      )
    })

    it('includes only provided query parameters', async () => {
      const mockResponse: AnnotationQueueListResponse = {
        items: [],
        total: 0,
        limit: 10,
        offset: 0,
      }

      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => mockResponse,
      })

      await annotationsAPI.getAnnotationQueue({ limit: 10 })

      expect(mockFetch).toHaveBeenCalledWith(
        `${API_BASE_URL}/api/v1/annotations/queue?limit=10`,
        expect.objectContaining({
          headers: {
            'Content-Type': 'application/json',
          },
        })
      )
    })

    it('returns response data on success', async () => {
      const mockResponse: AnnotationQueueListResponse = {
        items: [
          {
            id: 1,
            artifact_id: 'artifact-123',
            trace_id: 'trace-456',
            reason: 'Test reason',
            status: 'pending',
            metadata: null,
            created_at: '2024-01-01T00:00:00Z',
            reviewed_at: null,
          },
        ],
        total: 1,
        limit: 20,
        offset: 0,
      }

      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => mockResponse,
      })

      const result = await annotationsAPI.getAnnotationQueue()

      expect(result).toEqual(mockResponse)
    })

    it('throws error when response is not ok', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: false,
        status: 401,
        json: async () => ({ detail: 'Unauthorized' }),
      })

      await expect(annotationsAPI.getAnnotationQueue()).rejects.toThrow('Unauthorized')
    })
  })

  describe('Error handling', () => {
    it('handles network errors', async () => {
      mockFetch.mockRejectedValueOnce(new Error('Network error'))

      const request: SubmitFeedbackRequest = {
        artifact_id: 'artifact-123',
        trace_id: null,
        feedback: 'thumbs_up',
        comment: null,
      }

      await expect(annotationsAPI.submitFeedback(request)).rejects.toThrow('Network error')
    })

    it('prefers detail over message in error response', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: false,
        status: 400,
        json: async () => ({
          detail: 'Validation error',
          message: 'Generic message',
        }),
      })

      const request: SubmitFeedbackRequest = {
        artifact_id: 'artifact-123',
        trace_id: null,
        feedback: 'thumbs_up',
        comment: null,
      }

      await expect(annotationsAPI.submitFeedback(request)).rejects.toThrow('Validation error')
    })

    it('uses message if detail is not present', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: false,
        status: 400,
        json: async () => ({
          message: 'Error message',
        }),
      })

      const request: SubmitFeedbackRequest = {
        artifact_id: 'artifact-123',
        trace_id: null,
        feedback: 'thumbs_up',
        comment: null,
      }

      await expect(annotationsAPI.submitFeedback(request)).rejects.toThrow('Error message')
    })
  })

  describe('Headers', () => {
    it('includes Content-Type header', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({ status: 'success', message: 'OK', langfuse_submitted: true }),
      })

      const request: SubmitFeedbackRequest = {
        artifact_id: 'artifact-123',
        trace_id: null,
        feedback: 'thumbs_up',
        comment: null,
      }

      await annotationsAPI.submitFeedback(request)

      const callArgs = mockFetch.mock.calls[0]
      const options = callArgs[1] as RequestInit
      expect(options.headers).toEqual({
        'Content-Type': 'application/json',
      })
    })
  })
})
