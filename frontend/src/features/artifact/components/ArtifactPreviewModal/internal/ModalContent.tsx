/**
 * Content area for the preview modal
 */

import { FeedbackButtons } from '../../FeedbackButtons'
import { MarkdownPreview } from '../../MarkdownPreview'

import { ModalErrorState } from './ModalErrorState'
import { ModalLoadingState } from './ModalLoadingState'

interface ModalContentProps {
  content: string | null
  isLoading: boolean
  error: Error | null
  artifactId?: string | null
}

export function ModalContent({ content, isLoading, error, artifactId }: ModalContentProps) {
  if (isLoading) {
    return <ModalLoadingState />
  }

  if (error) {
    return <ModalErrorState message={error.message} />
  }

  if (content) {
    return (
      <div className="p-6">
        <MarkdownPreview content={content} showMetadata={false} />
        {/* Feedback section at the bottom of the preview */}
        {artifactId && (
          <div className="mt-8 pt-6 border-t border-border">
            <FeedbackButtons artifactId={artifactId} traceId={null} />
          </div>
        )}
      </div>
    )
  }

  return null
}

ModalContent.displayName = 'ModalContent'
