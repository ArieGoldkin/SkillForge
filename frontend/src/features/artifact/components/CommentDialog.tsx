/**
 * CommentDialog - Dialog for collecting optional user feedback comments.
 *
 * Features:
 * - Textarea for multi-line comments
 * - Character limit validation (1000 chars)
 * - Accessible with ARIA labels
 * - Keyboard navigation (Enter to submit, Esc to cancel)
 */

import { useState, type KeyboardEvent } from 'react'

import { useFocusReturn } from '@/hooks'

import { Button } from '@shared/components/ui/button'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@shared/components/ui/dialog'

interface CommentDialogProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  onSubmit: (comment: string) => void
  onCancel: () => void
}

const MAX_COMMENT_LENGTH = 1000

// eslint-disable-next-line max-lines-per-function
export function CommentDialog({ open, onOpenChange, onSubmit, onCancel }: CommentDialogProps) {
  const [comment, setComment] = useState('')
  const [error, setError] = useState('')

  // WCAG 2.1 AA: Return focus to trigger element when modal closes
  useFocusReturn(open)

  const handleOpenChange = (newOpen: boolean) => {
    if (!newOpen) {
      setComment('')
      setError('')
    }
    onOpenChange(newOpen)
  }

  const handleSubmit = () => {
    const trimmedComment = comment.trim()

    if (trimmedComment.length > MAX_COMMENT_LENGTH) {
      setError(`Comment must be ${MAX_COMMENT_LENGTH} characters or less`)
      return
    }

    onSubmit(trimmedComment)
  }

  const handleKeyDown = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && (e.ctrlKey || e.metaKey)) {
      e.preventDefault()
      handleSubmit()
    }
  }

  const remainingChars = MAX_COMMENT_LENGTH - comment.length
  const isOverLimit = remainingChars < 0

  return (
    <Dialog open={open} onOpenChange={handleOpenChange}>
      <DialogContent className="sm:max-w-[525px]">
        <DialogHeader>
          <DialogTitle>Share your feedback</DialogTitle>
          <DialogDescription>
            Help us improve by telling us what could be better. Your feedback is optional but
            appreciated.
          </DialogDescription>
        </DialogHeader>

        <div className="grid gap-4 py-4">
          <div className="grid gap-2">
            <label htmlFor="comment" className="text-sm font-medium">
              Comment (optional)
            </label>
            <textarea
              id="comment"
              value={comment}
              onChange={(e) => setComment(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder="What could we improve?"
              className="min-h-[120px] w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50 resize-y"
              aria-describedby="comment-hint comment-error"
              aria-invalid={!!error || isOverLimit}
            />
            <div className="flex justify-between text-xs">
              <span id="comment-hint" className="text-muted-foreground">
                Press Ctrl+Enter to submit
              </span>
              <span
                className={`${isOverLimit ? 'text-destructive font-medium' : 'text-muted-foreground'}`}
              >
                {remainingChars} characters remaining
              </span>
            </div>
            {error && (
              <p id="comment-error" className="text-sm text-destructive" role="alert">
                {error}
              </p>
            )}
          </div>
        </div>

        <DialogFooter>
          <Button variant="outline" onClick={onCancel}>
            Skip
          </Button>
          <Button onClick={handleSubmit} disabled={isOverLimit}>
            Submit Feedback
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
