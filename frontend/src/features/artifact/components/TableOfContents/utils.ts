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
 * Extract headings from markdown content
 * Returns hierarchical structure with h3s nested under h2s
 *
 * IMPORTANT: Skips headings inside code blocks to prevent
 * extracting example headings from markdown code samples
 */
export function extractHeadings(markdown: string): TocHeading[] {
  const lines = markdown.split('\n')
  const headings: TocHeading[] = []
  let currentH2: TocHeading | null = null
  let inCodeBlock = false

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
      const heading: TocHeading = {
        id: slugify(text),
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
      const heading: TocHeading = {
        id: slugify(text),
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
