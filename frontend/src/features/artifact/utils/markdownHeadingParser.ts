/**
 * Shared utility for parsing markdown headings
 *
 * This module contains the core heading extraction logic used by both:
 * - HeadingIdContext: For pre-computing heading IDs for React rendering
 * - TableOfContents: For extracting hierarchical heading structure
 *
 * Keeping this logic centralized ensures consistent heading ID generation
 * across the entire application.
 */

/**
 * Convert text to URL-friendly slug
 *
 * Used for generating consistent heading IDs from heading text.
 * Removes special characters, converts to lowercase, and uses hyphens.
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
 * Generate a unique ID using line number for duplicates
 *
 * This ensures deterministic IDs that don't change between renders.
 * The first occurrence of a heading gets the base ID (e.g., "details"),
 * subsequent duplicates get line-number suffixes (e.g., "details-l15").
 *
 * @param baseId - The slugified heading text
 * @param lineNumber - The 0-indexed line number in the markdown
 * @param seenIds - Map tracking how many times each ID has been seen
 * @returns Unique heading ID
 */
export function makeUniqueHeadingId(
  baseId: string,
  lineNumber: number,
  seenIds: Map<string, number>
): string {
  const count = seenIds.get(baseId) ?? 0
  seenIds.set(baseId, count + 1)
  // First occurrence: clean ID. Subsequent: use line number suffix
  return count === 0 ? baseId : `${baseId}-l${lineNumber}`
}

/**
 * Heading data extracted from markdown
 */
export interface HeadingData {
  /** Unique identifier for the heading */
  id: string
  /** Text content of the heading */
  text: string
  /** Heading level (1-6) */
  level: number
  /** 0-indexed line number in the markdown */
  lineNumber: number
}

/**
 * Parse markdown headings from content
 *
 * Extracts all headings (h1-h6) from markdown, skipping headings that appear
 * inside code blocks (``` or ~~~). Returns a flat list of headings with
 * unique IDs, text, level, and line numbers.
 *
 * This function uses position-based ID generation to ensure consistent IDs
 * across renders, even with React 18's StrictMode double-render behavior.
 *
 * @param markdown - The markdown content to parse
 * @returns Array of heading data in document order
 *
 * @example
 * ```ts
 * const markdown = `## Introduction
 * Some text.
 * ### Getting Started
 * More text.`
 *
 * const headings = parseMarkdownHeadings(markdown)
 * // [
 * //   { id: 'introduction', text: 'Introduction', level: 2, lineNumber: 0 },
 * //   { id: 'getting-started', text: 'Getting Started', level: 3, lineNumber: 2 }
 * // ]
 * ```
 */
export function parseMarkdownHeadings(markdown: string): HeadingData[] {
  const lines = markdown.split('\n')
  const headings: HeadingData[] = []
  const seenIds = new Map<string, number>()
  let inCodeBlock = false

  for (let lineNumber = 0; lineNumber < lines.length; lineNumber++) {
    const line = lines[lineNumber]

    // Track code block state (``` or ~~~)
    if (line.trim().startsWith('```') || line.trim().startsWith('~~~')) {
      inCodeBlock = !inCodeBlock
      continue
    }

    // Skip heading extraction if inside code block
    if (inCodeBlock) continue

    // Match any heading (h1-h6): /^(#{1,6})\s+(.+)$/
    const match = line.match(/^(#{1,6})\s+(.+)$/)
    if (match) {
      const level = match[1].length
      const text = match[2].trim()
      const baseId = slugify(text)
      const id = makeUniqueHeadingId(baseId, lineNumber, seenIds)

      headings.push({
        id,
        text,
        level,
        lineNumber,
      })
    }
  }

  return headings
}
