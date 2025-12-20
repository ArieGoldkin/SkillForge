/**
 * Type definitions for TableOfContents component
 */

export interface TocHeading {
  /** Unique identifier for the heading */
  id: string
  /** Text content of the heading */
  text: string
  /** Heading level (2 or 3) */
  level: number
  /** Child headings (h3 under h2) */
  children?: TocHeading[]
}

export interface TableOfContentsProps {
  /** The markdown content to extract headings from */
  content: string
  /** Additional CSS classes */
  className?: string
}
