/**
 * FeedbackButtons - User feedback component for artifact quality.
 * Provides thumbs up/down buttons with optional comment dialog.
 *
 * Features:
 * - Optimistic UI updates
 * - Accessible with ARIA labels
 * - Loading states
 * - Optional comment dialog on thumbs down
 */

import { useState } from 'react'

import type { FeedbackType } from '@app-types/annotations'
import { ThumbsUp, ThumbsDown, MessageSquare } from 'lucide-react'

import { Button } from '@shared/components/ui/button'

import { useFeedback } from '../hooks/useFeedback'

import { CommentDialog } from './CommentDialog'

interface FeedbackButtonsProps {
  artifactId: string
  traceId?: string | null
  className?: string
}

// eslint-disable-next-line max-lines-per-function
export function FeedbackButtons({ artifactId, traceId, className }: FeedbackButtonsProps) {
  const { selectedFeedback, isSubmitting, submitFeedback } = useFeedback({
    artifactId,
    traceId,
  })
  const [showCommentDialog, setShowCommentDialog] = useState(false)
  const [pendingFeedback, setPendingFeedback] = useState<FeedbackType | null>(null)

  const handleFeedbackClick = (feedback: FeedbackType) => {
    if (feedback === 'thumbs_down') {
      setPendingFeedback(feedback)
      setShowCommentDialog(true)
    } else {
      submitFeedback(feedback)
    }
  }

  const handleCommentSubmit = (comment: string) => {
    if (pendingFeedback) {
      submitFeedback(pendingFeedback, comment)
      setPendingFeedback(null)
    }
    setShowCommentDialog(false)
  }

  const handleCommentCancel = () => {
    if (pendingFeedback) {
      submitFeedback(pendingFeedback)
      setPendingFeedback(null)
    }
    setShowCommentDialog(false)
  }

  return (
    <>
      <div className={className}>
        <div className="flex items-center gap-2">
          <span className="text-sm text-muted-foreground">Was this helpful?</span>
          <div className="flex gap-1">
            <Button
              variant={selectedFeedback === 'thumbs_up' ? 'default' : 'outline'}
              size="sm"
              onClick={() => handleFeedbackClick('thumbs_up')}
              disabled={isSubmitting}
              aria-label="This was helpful"
              aria-pressed={selectedFeedback === 'thumbs_up'}
            >
              <ThumbsUp className="h-4 w-4" />
              <span className="sr-only">Thumbs up</span>
            </Button>
            <Button
              variant={selectedFeedback === 'thumbs_down' ? 'destructive' : 'outline'}
              size="sm"
              onClick={() => handleFeedbackClick('thumbs_down')}
              disabled={isSubmitting}
              aria-label="This was not helpful"
              aria-pressed={selectedFeedback === 'thumbs_down'}
            >
              <ThumbsDown className="h-4 w-4" />
              <span className="sr-only">Thumbs down</span>
            </Button>
            <Button
              variant="ghost"
              size="sm"
              onClick={() => {
                setPendingFeedback('thumbs_down')
                setShowCommentDialog(true)
              }}
              disabled={isSubmitting}
              aria-label="Add comment"
              title="Add feedback comment"
            >
              <MessageSquare className="h-4 w-4" />
              <span className="sr-only">Add comment</span>
            </Button>
          </div>
        </div>
      </div>

      <CommentDialog
        open={showCommentDialog}
        onOpenChange={setShowCommentDialog}
        onSubmit={handleCommentSubmit}
        onCancel={handleCommentCancel}
      />
    </>
  )
}
