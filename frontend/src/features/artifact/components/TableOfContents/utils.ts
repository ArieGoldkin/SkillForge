/**
 * Utility functions for extracting and managing table of contents
 */

import { parseMarkdownHeadings } from '../../utils/markdownHeadingParser'

import type { TocHeading } from './types'

// Re-export slugify for backwards compatibility with any external consumers
export { slugify } from '../../utils/markdownHeadingParser'

/**
 * Extract headings from markdown content
 * Returns hierarchical structure with h3s nested under h2s
 *
 * IMPORTANT: Skips headings inside code blocks to prevent
 * extracting example headings from markdown code samples
 *
 * Uses the shared parseMarkdownHeadings utility for consistent ID generation
 * with MarkdownPreview heading renderers.
 */
export function extractHeadings(markdown: string): TocHeading[] {
  const allHeadings = parseMarkdownHeadings(markdown)
  const tocHeadings: TocHeading[] = []
  let currentH2: TocHeading | null = null

  for (const heading of allHeadings) {
    // Only include h2 and h3 in table of contents
    if (heading.level === 2) {
      const h2: TocHeading = {
        id: heading.id,
        text: heading.text,
        level: 2,
        children: [],
      }
      tocHeadings.push(h2)
      currentH2 = h2
    } else if (heading.level === 3 && currentH2) {
      const h3: TocHeading = {
        id: heading.id,
        text: heading.text,
        level: 3,
      }
      currentH2.children?.push(h3)
    }
    // Skip h1, h4, h5, h6 - not included in table of contents
  }

  return tocHeadings
}

/**
 * Get the currently active heading based on scroll position
 * Uses intersection observer to track which heading is in view
 */
export function getActiveHeading(headingIds: string[]): string | null {
  const scrollPosition = window.scrollY + 100 // Offset for sticky header

  // Find the last heading that's above the scroll position
  for (let i = headingIds.length - 1; i >= 0; i--) {
    const element = document.getElementById(headingIds[i])
    if (element && element.offsetTop <= scrollPosition) {
      return headingIds[i]
    }
  }

  return headingIds[0] || null
}
