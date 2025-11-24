/**
 * SkillCardTags - Tag display for skill cards
 */

import * as React from 'react'

/**
 * Props for SkillCardTags component
 */
export interface SkillCardTagsProps {
  tags: string[]
  maxVisible?: number
}

/**
 * SkillCardTags component
 *
 * Displays skill tags with optional "+N more" indicator.
 * Limits visible tags to prevent overflow.
 */
export const SkillCardTags: React.FC<SkillCardTagsProps> = ({ tags, maxVisible = 3 }) => {
  const visibleTags = tags.slice(0, maxVisible)
  const hiddenTagsCount = tags.length - visibleTags.length

  return (
    <div className="flex flex-wrap gap-2">
      {visibleTags.map((tag) => (
        <span
          key={tag}
          className="text-xs bg-primary/10 text-primary px-2 py-1 rounded-md font-medium"
        >
          {tag}
        </span>
      ))}
      {hiddenTagsCount > 0 && (
        <span className="text-xs bg-muted text-muted-foreground px-2 py-1 rounded-md font-medium">
          +{hiddenTagsCount} more
        </span>
      )}
    </div>
  )
}

SkillCardTags.displayName = 'SkillCardTags'
