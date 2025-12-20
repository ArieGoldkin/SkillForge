/**
 * Hook for tracking the currently active heading based on scroll position
 */

import { useEffect, useState } from 'react'

import type { TocHeading } from '../types'
import { getActiveHeading } from '../utils'

/**
 * Flatten nested headings into a single array of IDs
 */
function flattenHeadingIds(headings: TocHeading[]): string[] {
  const ids: string[] = []

  for (const heading of headings) {
    ids.push(heading.id)
    if (heading.children) {
      for (const child of heading.children) {
        ids.push(child.id)
      }
    }
  }

  return ids
}

/**
 * Track the currently active heading based on scroll position
 */
export function useActiveHeading(headings: TocHeading[]): string | null {
  const [activeId, setActiveId] = useState<string | null>(null)

  useEffect(() => {
    const headingIds = flattenHeadingIds(headings)

    if (headingIds.length === 0) {
      return
    }

    const handleScroll = () => {
      const active = getActiveHeading(headingIds)
      setActiveId(active)
    }

    // Initial check
    handleScroll()

    // Listen for scroll events
    window.addEventListener('scroll', handleScroll, { passive: true })

    return () => {
      window.removeEventListener('scroll', handleScroll)
    }
  }, [headings])

  return activeId
}
