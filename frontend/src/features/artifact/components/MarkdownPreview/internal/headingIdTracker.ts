/**
 * Heading ID tracker for deduplication
 * Ensures heading IDs are unique across a markdown document
 * This prevents React key collisions in TOC and DOM ID conflicts
 */

const headingIdCounts = new Map<string, number>()

/**
 * Reset heading ID counters - call this before each MarkdownPreview render
 */
export function resetHeadingIds(): void {
  headingIdCounts.clear()
}

/**
 * Generate a unique heading ID by adding a suffix for duplicates
 * First occurrence uses base ID, subsequent ones get -2, -3, etc.
 */
export function makeUniqueHeadingId(baseId: string): string {
  const count = headingIdCounts.get(baseId) ?? 0
  headingIdCounts.set(baseId, count + 1)
  return count === 0 ? baseId : `${baseId}-${count + 1}`
}
