/**
 * TypeScript types for the feedback/annotation feature.
 * Matches backend schemas in backend/app/schemas/annotations.py
 */

export type FeedbackType = 'thumbs_up' | 'thumbs_down'

export interface SubmitFeedbackRequest {
  artifact_id: string
  trace_id?: string | null
  feedback: FeedbackType
  comment?: string | null
}

export interface SubmitFeedbackResponse {
  status: string
  message: string
  langfuse_submitted: boolean
}

export interface FlagForReviewRequest {
  artifact_id: string
  reason: string
}

export interface FlagForReviewResponse {
  queue_id: number
  message: string
}

export interface AnnotationQueueItem {
  id: number
  artifact_id: string
  trace_id: string | null
  reason: string
  status: string
  metadata: Record<string, unknown> | null
  created_at: string
  reviewed_at: string | null
}

export interface AnnotationQueueListResponse {
  items: AnnotationQueueItem[]
  total: number
  limit: number
  offset: number
}
