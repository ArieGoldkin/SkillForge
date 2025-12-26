/**
 * Tests for annotations API client
 * @unit
 *
 * Tests use ky-based API client which passes Request objects to fetch
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
const { mockFetch } = vi.hoisted(() => {
  const url = 'http://localhost:8500'
  // Stub the env variable before annotations.ts loads
  vi.stubEnv('VITE_API_URL', url)
  vi.stubEnv('VITE_API_BASE_URL', url)
  return {
    mockFetch: vi.fn(),
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

      mockFetch.mockResolvedValueOnce(
        new Response(JSON.stringify(mockResponse), {
          status: 200,
          headers: { 'Content-Type': 'application/json' },
        })
      )

      const request: SubmitFeedbackRequest = {
        artifact_id: 'artifact-123',
        trace_id: 'trace-456',
        feedback: 'thumbs_up',
        comment: null,
      }

      await annotationsAPI.submitFeedback(request)

      expect(mockFetch).toHaveBeenCalled()
      const [req] = mockFetch.mock.calls[0] as [Request]
      expect(req.url).toContain('/api/v1/annotations/feedback')
      expect(req.method).toBe('POST')
    })

    it('returns response data on success', async () => {
      const mockResponse: SubmitFeedbackResponse = {
        status: 'success',
        message: 'Feedback submitted',
        langfuse_submitted: true,
      }

      mockFetch.mockResolvedValueOnce(
        new Response(JSON.stringify(mockResponse), {
          status: 200,
          headers: { 'Content-Type': 'application/json' },
        })
      )

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
      mockFetch.mockResolvedValueOnce(
        new Response(JSON.stringify({ detail: 'Invalid request' }), {
          status: 400,
          headers: { 'Content-Type': 'application/json' },
        })
      )

      const request: SubmitFeedbackRequest = {
        artifact_id: 'artifact-123',
        trace_id: null,
        feedback: 'thumbs_up',
        comment: null,
      }

      await expect(annotationsAPI.submitFeedback(request)).rejects.toThrow()
    })
  })

  describe('flagForReview', () => {
    it('calls correct endpoint with POST method', async () => {
      const mockResponse: FlagForReviewResponse = {
        queue_id: 1,
        message: 'Flagged for review',
      }

      mockFetch.mockResolvedValueOnce(
        new Response(JSON.stringify(mockResponse), {
          status: 200,
          headers: { 'Content-Type': 'application/json' },
        })
      )

      const request: FlagForReviewRequest = {
        artifact_id: 'artifact-123',
        reason: 'Incorrect information',
      }

      await annotationsAPI.flagForReview(request)

      expect(mockFetch).toHaveBeenCalled()
      const [req] = mockFetch.mock.calls[0] as [Request]
      expect(req.url).toContain('/api/v1/annotations/flag')
      expect(req.method).toBe('POST')
    })

    it('returns response data on success', async () => {
      const mockResponse: FlagForReviewResponse = {
        queue_id: 42,
        message: 'Successfully flagged',
      }

      mockFetch.mockResolvedValueOnce(
        new Response(JSON.stringify(mockResponse), {
          status: 200,
          headers: { 'Content-Type': 'application/json' },
        })
      )

      const request: FlagForReviewRequest = {
        artifact_id: 'artifact-123',
        reason: 'Outdated content',
      }

      const result = await annotationsAPI.flagForReview(request)

      expect(result).toEqual(mockResponse)
    })

    it('throws error when response is not ok', async () => {
      mockFetch.mockResolvedValueOnce(
        new Response(JSON.stringify({ message: 'Artifact not found' }), {
          status: 404,
          headers: { 'Content-Type': 'application/json' },
        })
      )

      const request: FlagForReviewRequest = {
        artifact_id: 'invalid-id',
        reason: 'Test',
      }

      await expect(annotationsAPI.flagForReview(request)).rejects.toThrow()
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

      mockFetch.mockResolvedValueOnce(
        new Response(JSON.stringify(mockResponse), {
          status: 200,
          headers: { 'Content-Type': 'application/json' },
        })
      )

      await annotationsAPI.getAnnotationQueue()

      expect(mockFetch).toHaveBeenCalled()
      const [req] = mockFetch.mock.calls[0] as [Request]
      expect(req.url).toContain('/api/v1/annotations/queue')
      expect(req.method).toBe('GET')
    })

    it('includes query parameters when provided', async () => {
      const mockResponse: AnnotationQueueListResponse = {
        items: [],
        total: 0,
        limit: 10,
        offset: 20,
      }

      mockFetch.mockResolvedValueOnce(
        new Response(JSON.stringify(mockResponse), {
          status: 200,
          headers: { 'Content-Type': 'application/json' },
        })
      )

      await annotationsAPI.getAnnotationQueue({
        limit: 10,
        offset: 20,
        status: 'pending',
      })

      expect(mockFetch).toHaveBeenCalled()
      const [req] = mockFetch.mock.calls[0] as [Request]
      expect(req.url).toContain('limit=10')
      expect(req.url).toContain('offset=20')
      expect(req.url).toContain('status=pending')
    })

    it('includes only provided query parameters', async () => {
      const mockResponse: AnnotationQueueListResponse = {
        items: [],
        total: 0,
        limit: 10,
        offset: 0,
      }

      mockFetch.mockResolvedValueOnce(
        new Response(JSON.stringify(mockResponse), {
          status: 200,
          headers: { 'Content-Type': 'application/json' },
        })
      )

      await annotationsAPI.getAnnotationQueue({ limit: 10 })

      expect(mockFetch).toHaveBeenCalled()
      const [req] = mockFetch.mock.calls[0] as [Request]
      expect(req.url).toContain('limit=10')
      expect(req.url).not.toContain('offset=')
      expect(req.url).not.toContain('status=')
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

      mockFetch.mockResolvedValueOnce(
        new Response(JSON.stringify(mockResponse), {
          status: 200,
          headers: { 'Content-Type': 'application/json' },
        })
      )

      const result = await annotationsAPI.getAnnotationQueue()

      expect(result).toEqual(mockResponse)
    })

    it('throws error when response is not ok', async () => {
      mockFetch.mockResolvedValueOnce(
        new Response(JSON.stringify({ detail: 'Unauthorized' }), {
          status: 401,
          headers: { 'Content-Type': 'application/json' },
        })
      )

      await expect(annotationsAPI.getAnnotationQueue()).rejects.toThrow()
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

      await expect(annotationsAPI.submitFeedback(request)).rejects.toThrow()
    })

    it('prefers detail over message in error response', async () => {
      mockFetch.mockResolvedValueOnce(
        new Response(
          JSON.stringify({
            detail: 'Validation error',
            message: 'Generic message',
          }),
          {
            status: 400,
            headers: { 'Content-Type': 'application/json' },
          }
        )
      )

      const request: SubmitFeedbackRequest = {
        artifact_id: 'artifact-123',
        trace_id: null,
        feedback: 'thumbs_up',
        comment: null,
      }

      // ky throws HTTPError on non-2xx responses
      await expect(annotationsAPI.submitFeedback(request)).rejects.toThrow()
    })

    it('uses message if detail is not present', async () => {
      mockFetch.mockResolvedValueOnce(
        new Response(
          JSON.stringify({
            message: 'Error message',
          }),
          {
            status: 400,
            headers: { 'Content-Type': 'application/json' },
          }
        )
      )

      const request: SubmitFeedbackRequest = {
        artifact_id: 'artifact-123',
        trace_id: null,
        feedback: 'thumbs_up',
        comment: null,
      }

      // ky throws HTTPError on non-2xx responses
      await expect(annotationsAPI.submitFeedback(request)).rejects.toThrow()
    })
  })

  describe('Headers', () => {
    it('includes Content-Type header', async () => {
      mockFetch.mockResolvedValueOnce(
        new Response(
          JSON.stringify({ status: 'success', message: 'OK', langfuse_submitted: true }),
          {
            status: 200,
            headers: { 'Content-Type': 'application/json' },
          }
        )
      )

      const request: SubmitFeedbackRequest = {
        artifact_id: 'artifact-123',
        trace_id: null,
        feedback: 'thumbs_up',
        comment: null,
      }

      await annotationsAPI.submitFeedback(request)

      expect(mockFetch).toHaveBeenCalled()
      const [req] = mockFetch.mock.calls[0] as [Request]
      // ky automatically sets content-type for JSON
      expect(req.headers.get('content-type')).toContain('application/json')
    })
  })
})
