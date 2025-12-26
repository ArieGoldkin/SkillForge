import type * as React from 'react'

import { Badge } from '@shared/components/ui/badge'

interface TopicBadgesProps {
  topics: string[]
}

/**
 * TopicBadges - Render a list of topic badges
 */
export function TopicBadges({ topics }: TopicBadgesProps): React.ReactNode {
  if (topics.length === 0) {
    return null
  }

  return (
    <div className="flex flex-wrap gap-2">
      {topics.map((topic) => (
        <Badge key={topic} variant="default" className="text-xs rounded-full px-3 py-0.5">
          {topic}
        </Badge>
      ))}
    </div>
  )
}

TopicBadges.displayName = 'TopicBadges'
