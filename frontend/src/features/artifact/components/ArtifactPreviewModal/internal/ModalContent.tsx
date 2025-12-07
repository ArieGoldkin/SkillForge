/**
 * Content area for the preview modal
 */

import { MarkdownPreview } from '../../MarkdownPreview'

import { ModalErrorState } from './ModalErrorState'
import { ModalLoadingState } from './ModalLoadingState'

interface ModalContentProps {
  content: string | null
  isLoading: boolean
  error: Error | null
}

export function ModalContent({ content, isLoading, error }: ModalContentProps) {
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
      </div>
    )
  }

  return null
}

ModalContent.displayName = 'ModalContent'
