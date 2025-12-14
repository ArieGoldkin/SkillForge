/**
 * Types for TopicSelectModal component
 * Issue #114: Topic Selection Modal
 */

import type { TutoringTopic } from '@app-types/api'

export interface TopicSelectModalProps {
  isOpen: boolean
  onClose: () => void
  onSelect: (topicId: string) => void
  topics: TutoringTopic[]
  isLoading?: boolean
  analysisTitle?: string
}

export type { TutoringTopic }
