/**
 * Custom hook for managing artifact feedback state and API interactions.
 * Provides optimistic UI updates and error handling using React 19 useOptimistic.
 */

import { useOptimistic, useState, useTransition } from 'react'

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
  const [optimisticFeedback, setOptimisticFeedback] = useOptimistic(
    selectedFeedback,
    (_currentFeedback, newFeedback: FeedbackType) => newFeedback
  )
  const [isPending, startTransition] = useTransition()
  const { toast } = useToast()

  const submitFeedback = async (feedback: FeedbackType, comment?: string) => {
    startTransition(async () => {
      setOptimisticFeedback(feedback)

      try {
        const response = await annotationsAPI.submitFeedback({
          artifact_id: artifactId,
          trace_id: traceId || null,
          feedback,
          comment: comment || null,
        })

        // Confirm the optimistic update
        setSelectedFeedback(feedback)

        toast({
          title: 'Feedback submitted',
          description: response.message,
          variant: 'success',
        })
      } catch (error) {
        // useOptimistic automatically rolls back on error
        toast({
          title: 'Failed to submit feedback',
          description: error instanceof Error ? error.message : 'An error occurred',
          variant: 'destructive',
        })
      }
    })
  }

  const flagForReview = async (reason: string) => {
    startTransition(async () => {
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
      }
    })
  }

  return {
    selectedFeedback: optimisticFeedback,
    isSubmitting: isPending,
    submitFeedback,
    flagForReview,
  }
}
