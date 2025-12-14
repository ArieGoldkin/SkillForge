/**
 * Utility functions for extracting and managing table of contents
 */

import type { TocHeading } from './types'

/**
 * Convert text to URL-friendly slug
 */
export function slugify(text: string): string {
  return text
    .toLowerCase()
    .trim()
    .replace(/[^\w\s-]/g, '') // Remove special characters
    .replace(/[\s_-]+/g, '-') // Replace spaces/underscores with hyphens
    .replace(/^-+|-+$/g, '') // Remove leading/trailing hyphens
}

/**
 * Generate a unique ID by adding a suffix if the base ID already exists
 * This prevents React key collisions when multiple headings have the same text
 */
function makeUniqueId(baseId: string, seenIds: Map<string, number>): string {
  const count = seenIds.get(baseId) ?? 0
  seenIds.set(baseId, count + 1)

  // First occurrence uses base ID, subsequent ones get -2, -3, etc.
  return count === 0 ? baseId : `${baseId}-${count + 1}`
}

/**
 * Extract headings from markdown content
 * Returns hierarchical structure with h3s nested under h2s
 *
 * IMPORTANT: Skips headings inside code blocks to prevent
 * extracting example headings from markdown code samples
 *
 * IDs are guaranteed unique to prevent React key collisions
 */
export function extractHeadings(markdown: string): TocHeading[] {
  const lines = markdown.split('\n')
  const headings: TocHeading[] = []
  let currentH2: TocHeading | null = null
  let inCodeBlock = false
  const seenIds = new Map<string, number>() // Track seen IDs for uniqueness

  for (const line of lines) {
    // Track code block state (``` or ~~~)
    if (line.trim().startsWith('```') || line.trim().startsWith('~~~')) {
      inCodeBlock = !inCodeBlock
      continue
    }

    // Skip heading extraction if inside code block
    if (inCodeBlock) continue

    // Match h2 (## Heading)
    const h2Match = line.match(/^##\s+(.+)$/)
    if (h2Match) {
      const text = h2Match[1].trim()
      const baseId = slugify(text)
      const heading: TocHeading = {
        id: makeUniqueId(baseId, seenIds),
        text,
        level: 2,
        children: [],
      }
      headings.push(heading)
      currentH2 = heading
      continue
    }

    // Match h3 (### Heading)
    const h3Match = line.match(/^###\s+(.+)$/)
    if (h3Match && currentH2) {
      const text = h3Match[1].trim()
      const baseId = slugify(text)
      const heading: TocHeading = {
        id: makeUniqueId(baseId, seenIds),
        text,
        level: 3,
      }
      currentH2.children?.push(heading)
    }
  }

  return headings
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
