/**
 * API client for feedback and annotation endpoints.
 * Connects to FastAPI backend at /api/v1/annotations
 * Uses ky HTTP client with interceptors (Issue #550)
 */

import type {
  AnnotationQueueListResponse,
  FlagForReviewRequest,
  FlagForReviewResponse,
  SubmitFeedbackRequest,
  SubmitFeedbackResponse,
} from '@app-types/annotations'

import { apiClient } from '@/lib/api-client'

/**
 * Annotation API client
 */
export const annotationsAPI = {
  /**
   * Submit user feedback (thumbs up/down)
   * POST /api/v1/annotations/feedback
   */
  submitFeedback: async (request: SubmitFeedbackRequest): Promise<SubmitFeedbackResponse> => {
    return apiClient('api/v1/annotations/feedback', {
      method: 'POST',
      json: request,
    }).json<SubmitFeedbackResponse>()
  },

  /**
   * Flag artifact for review
   * POST /api/v1/annotations/flag
   */
  flagForReview: async (request: FlagForReviewRequest): Promise<FlagForReviewResponse> => {
    return apiClient('api/v1/annotations/flag', {
      method: 'POST',
      json: request,
    }).json<FlagForReviewResponse>()
  },

  /**
   * Get annotation queue items
   * GET /api/v1/annotations/queue
   */
  getAnnotationQueue: async (params?: {
    limit?: number
    offset?: number
    status?: string
  }): Promise<AnnotationQueueListResponse> => {
    const searchParams = new URLSearchParams()
    if (params?.limit) searchParams.set('limit', params.limit.toString())
    if (params?.offset) searchParams.set('offset', params.offset.toString())
    if (params?.status) searchParams.set('status', params.status)

    const queryString = searchParams.toString()
    const endpoint = `api/v1/annotations/queue${queryString ? `?${queryString}` : ''}`

    return apiClient(endpoint).json<AnnotationQueueListResponse>()
  },

  /**
   * Mark annotation queue item as reviewed
   * PATCH /api/v1/annotations/queue/{id}/reviewed
   */
  markReviewed: async (queueId: number): Promise<{ status: string; message: string }> => {
    return apiClient(`api/v1/annotations/queue/${queueId}/reviewed`, {
      method: 'PATCH',
    }).json<{ status: string; message: string }>()
  },
}

export default annotationsAPI
