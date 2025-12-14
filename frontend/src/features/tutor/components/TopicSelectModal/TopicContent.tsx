/**
 * TopicContent - Content area for topic selection modal
 */

import { Loader2 } from 'lucide-react'

import { TopicList } from './TopicList'
import type { TutoringTopic } from './types'

interface TopicContentProps {
  isLoading: boolean
  topics: TutoringTopic[]
  selectedId: string | null
  onSelect: (id: string) => void
}

export function TopicContent({ isLoading, topics, selectedId, onSelect }: TopicContentProps) {
  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-8">
        <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
      </div>
    )
  }

  if (topics.length === 0) {
    return (
      <p className="text-sm text-muted-foreground text-center py-4">
        No topics available for this analysis.
      </p>
    )
  }

  return <TopicList topics={topics} selectedId={selectedId} onSelect={onSelect} />
}
