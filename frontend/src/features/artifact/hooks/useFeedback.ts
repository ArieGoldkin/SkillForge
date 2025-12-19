/**
 * Custom hook for managing artifact feedback state and API interactions.
 * Provides optimistic UI updates and error handling.
 */

import { useState } from 'react'

import type { FeedbackType } from '@app-types/annotations'
import { useToast } from '@hooks/use-toast'

import { annotationsAPI } from '@/api/annotations'

interface UseFeedbackOptions {
  artifactId: string
  traceId?: string | null
}

// eslint-disable-next-line max-lines-per-function
export function useFeedback({ artifactId, traceId }: UseFeedbackOptions) {
  const [selectedFeedback, setSelectedFeedback] = useState<FeedbackType | null>(null)
  const [isSubmitting, setIsSubmitting] = useState(false)
  const { toast } = useToast()

  const submitFeedback = async (feedback: FeedbackType, comment?: string) => {
    const previousFeedback = selectedFeedback
    setSelectedFeedback(feedback)
    setIsSubmitting(true)

    try {
      const response = await annotationsAPI.submitFeedback({
        artifact_id: artifactId,
        trace_id: traceId || null,
        feedback,
        comment: comment || null,
      })

      toast({
        title: 'Feedback submitted',
        description: response.message,
        variant: 'success',
      })
    } catch (error) {
      setSelectedFeedback(previousFeedback)
      toast({
        title: 'Failed to submit feedback',
        description: error instanceof Error ? error.message : 'An error occurred',
        variant: 'destructive',
      })
    } finally {
      setIsSubmitting(false)
    }
  }

  const flagForReview = async (reason: string) => {
    setIsSubmitting(true)

    try {
      const response = await annotationsAPI.flagForReview({
        artifact_id: artifactId,
        reason,
      })

      toast({
        title: 'Flagged for review',
        description: response.message,
        variant: 'success',
      })
    } catch (error) {
      toast({
        title: 'Failed to flag for review',
        description: error instanceof Error ? error.message : 'An error occurred',
        variant: 'destructive',
      })
    } finally {
      setIsSubmitting(false)
    }
  }

  return { selectedFeedback, isSubmitting, submitFeedback, flagForReview }
}
