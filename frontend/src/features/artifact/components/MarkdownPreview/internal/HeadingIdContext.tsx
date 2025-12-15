/**
 * HeadingIdContext - React Context for heading ID generation
 *
 * Problem:
 * React 18's StrictMode renders components twice. Any stateful counter that
 * tracks "which occurrence of this text" gets incremented twice, causing
 * heading IDs to mismatch between TOC and actual headings.
 *
 * Solution:
 * Use POSITION-BASED lookup instead of text-based tracking:
 * 1. Pre-compute an ORDERED LIST of heading IDs from markdown
 * 2. Use a SINGLE position counter (not per-text counters)
 * 3. Each heading gets the ID at list[position++]
 *
 * This works because ReactMarkdown renders headings in document order.
 * The position counter resets on each render via a generation number,
 * ensuring StrictMode double-renders both start from position 0.
 */

import { createContext, useContext, useMemo, type ReactNode } from 'react'

import { parseMarkdownHeadings, slugify } from '../../../utils/markdownHeadingParser'

/**
 * Pre-computed heading data
 */
interface HeadingEntry {
  text: string
  id: string
  level: number
}

/**
 * Heading ID list - stores IDs in document order
 */
export class HeadingIdList {
  private headings: HeadingEntry[] = []
  private position = 0

  constructor(markdown: string) {
    this.precompute(markdown)
  }

  /**
   * Pre-compute all heading IDs from markdown in document order.
   * Uses the shared parseMarkdownHeadings utility for consistency.
   */
  private precompute(markdown: string): void {
    const headingData = parseMarkdownHeadings(markdown)
    this.headings = headingData.map(({ id, text, level }) => ({ id, text, level }))
  }

  /**
   * Reset position to start of list.
   * Called at the start of each render to handle StrictMode double-render.
   */
  resetPosition(): void {
    this.position = 0
  }

  /**
   * Get the ID for the next heading in document order.
   * Called by heading renderers as they render top-to-bottom.
   */
  getNextId(): string {
    if (this.position < this.headings.length) {
      const entry = this.headings[this.position]
      this.position++
      return entry.id
    }
    // Fallback: shouldn't happen if precompute matches render
    return `heading-${this.position++}`
  }

  /**
   * Get the ID for a heading by matching text.
   * Used as fallback when position-based lookup might fail.
   * Returns the FIRST matching ID for this text that hasn't been used.
   */
  getIdByText(text: string): string {
    // Find next unused heading with matching text
    for (let i = this.position; i < this.headings.length; i++) {
      if (this.headings[i].text === text) {
        // Skip to this position
        this.position = i + 1
        return this.headings[i].id
      }
    }
    // Not found in remaining headings - generate fallback
    return slugify(text)
  }

  /**
   * Get total count of headings
   */
  get count(): number {
    return this.headings.length
  }
}

/**
 * Context provides the ID list directly
 */
const HeadingIdContext = createContext<HeadingIdList | null>(null)

/**
 * Hook to get ID for the current heading.
 * Uses text matching to find the correct ID.
 */
// eslint-disable-next-line react-refresh/only-export-components
export function useHeadingId(text: string): string {
  const idList = useContext(HeadingIdContext)
  if (!idList) {
    // Fallback: no context (shouldn't happen)
    return slugify(text)
  }

  // Use text matching to handle any potential order mismatches
  return idList.getIdByText(text)
}

/**
 * Provider component that pre-computes heading IDs
 */
interface HeadingIdProviderProps {
  content: string
  children: ReactNode
}

export function HeadingIdProvider({ content, children }: HeadingIdProviderProps) {
  // Create ID list once per content
  const idList = useMemo(() => new HeadingIdList(content), [content])

  // Reset position at start of each render to handle StrictMode double-render
  // This ensures both render passes start from position 0
  idList.resetPosition()

  return <HeadingIdContext.Provider value={idList}>{children}</HeadingIdContext.Provider>
}
