/**
 * ShowcaseSection - Reusable wrapper for showcase sections
 */

import type * as React from 'react'

/**
 * Props for ShowcaseSection component
 */
export interface ShowcaseSectionProps {
  title: string
  children: React.ReactNode
  className?: string
}

/**
 * ShowcaseSection component
 *
 * Provides consistent styling for showcase sections with title.
 */
export function ShowcaseSection({
  title,
  children,
  className,
}: ShowcaseSectionProps): React.ReactNode {
  return (
    <div className={className}>
      <h3 className="text-lg font-medium mb-3">{title}</h3>
      {children}
    </div>
  )
}

ShowcaseSection.displayName = 'ShowcaseSection'
