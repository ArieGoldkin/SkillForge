/**
 * Type definitions for MarkdownPreview component
 */

/**
 * Metadata about the markdown content
 */
export interface ContentMetadata {
  /** Array of topic tags */
  topics?: string[]
  /** Content complexity level */
  complexity?: 'simple' | 'intermediate' | 'advanced'
  /** Total word count */
  word_count?: number
  /** Number of agents that contributed */
  agent_count?: number
  /** Average confidence score across agents */
  avg_confidence?: number
}

export interface MarkdownPreviewProps {
  /** The markdown content to render */
  content: string
  /** Optional metadata about the content */
  metadata?: ContentMetadata
  /** Additional CSS classes */
  className?: string
  /** Whether to show the metadata header */
  showMetadata?: boolean
}

export interface CodeBlockComponentProps {
  /** The code content */
  code: string
  /** Programming language */
  language: string
  /** Additional CSS classes */
  className?: string
}

export interface CopyButtonProps {
  /** The text to copy */
  text: string
  /** Additional CSS classes */
  className?: string
}

export interface MetadataHeaderProps {
  /** Metadata object */
  metadata: ContentMetadata
  /** Additional CSS classes */
  className?: string
}
