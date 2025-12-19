/**
 * API client for feedback and annotation endpoints.
 * Connects to FastAPI backend at /api/v1/annotations
 */

import type {
  AnnotationQueueListResponse,
  FlagForReviewRequest,
  FlagForReviewResponse,
  SubmitFeedbackRequest,
  SubmitFeedbackResponse,
} from '@app-types/annotations'

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8500'

/**
 * Generic fetch wrapper with error handling
 */
async function apiFetch<T>(endpoint: string, options: RequestInit = {}): Promise<T> {
  const url = `${API_BASE_URL}${endpoint}`

  const response = await fetch(url, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      ...options.headers,
    },
  })

  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}))
    throw new Error(errorData.detail || errorData.message || `API error: ${response.status}`)
  }

  return response.json()
}

/**
 * Annotation API client
 */
export const annotationsAPI = {
  /**
   * Submit user feedback (thumbs up/down)
   * POST /api/v1/annotations/feedback
   */
  submitFeedback: async (request: SubmitFeedbackRequest): Promise<SubmitFeedbackResponse> => {
    return apiFetch<SubmitFeedbackResponse>('/api/v1/annotations/feedback', {
      method: 'POST',
      body: JSON.stringify(request),
    })
  },

  /**
   * Flag artifact for review
   * POST /api/v1/annotations/flag
   */
  flagForReview: async (request: FlagForReviewRequest): Promise<FlagForReviewResponse> => {
    return apiFetch<FlagForReviewResponse>('/api/v1/annotations/flag', {
      method: 'POST',
      body: JSON.stringify(request),
    })
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
    const endpoint = `/api/v1/annotations/queue${queryString ? `?${queryString}` : ''}`

    return apiFetch<AnnotationQueueListResponse>(endpoint)
  },
}

export default annotationsAPI
