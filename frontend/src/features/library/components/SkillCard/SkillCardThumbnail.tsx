/**
 * SkillCardThumbnail - Thumbnail component for skill cards
 */

import type * as React from 'react'

/**
 * Props for SkillCardThumbnail component
 */
export interface SkillCardThumbnailProps {
  title: string
  thumbnail?: string
}

/**
 * SkillCardThumbnail component
 *
 * Displays either a provided thumbnail image or a gradient placeholder
 * with the first letter of the skill title.
 */
export function SkillCardThumbnail({ title, thumbnail }: SkillCardThumbnailProps): React.ReactNode {
  if (thumbnail) {
    return (
      <img
        src={thumbnail}
        alt={`${title} thumbnail`}
        className="w-full h-48 object-cover rounded-t-xl"
        loading="lazy"
      />
    )
  }

  return (
    <div
      className="w-full h-48 bg-linear-to-br from-primary/20 to-primary/5 rounded-t-xl flex items-center justify-center"
      role="img"
      aria-label={`${title} placeholder thumbnail`}
    >
      <div className="text-4xl font-bold text-primary/30" aria-hidden="true">
        {title.charAt(0)}
      </div>
    </div>
  )
}

SkillCardThumbnail.displayName = 'SkillCardThumbnail'
