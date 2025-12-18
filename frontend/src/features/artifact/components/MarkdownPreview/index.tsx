import type * as React from 'react'

import ReactMarkdown from 'react-markdown'
import rehypeRaw from 'rehype-raw'
import remarkGfm from 'remark-gfm'

import { cn } from '@lib/utils'

import { HeadingIdProvider, MetadataHeader } from './internal'
import { markdownRenderers } from './markdown-config'
import type { MarkdownPreviewProps } from './types'

import '@/design-system/markdown-preview.css'

// Re-export types for external usage
export type { MarkdownPreviewProps } from './types'

/**
 * Empty state component for when no content is available
 */
const EmptyState: React.FC<{ className?: string }> = ({ className }) => (
  <div className={cn('text-center py-8 text-muted-foreground', className)}>
    <p>No content available</p>
  </div>
)

/**
 * MarkdownPreview - Render markdown content with syntax highlighting
 *
 * Features:
 * - GFM support (tables, task lists, strikethrough)
 * - Syntax-highlighted code blocks via Prism.js
 * - Optional metadata header
 * - Responsive design with light/dark theme support
 *
 * Heading ID Coordination:
 * - TableOfContents uses LOCAL counters to predict IDs from markdown
 * - HeadingIdProvider wraps ReactMarkdown with a fresh ID tracker per content
 * - Both use the same slugify() and duplicate-handling logic, ensuring IDs match
 */
export const MarkdownPreview: React.FC<MarkdownPreviewProps> = ({
  content,
  metadata,
  className,
  showMetadata = true,
}) => {
  if (!content || content.trim().length === 0) {
    return <EmptyState className={className} />
  }

  return (
    <div className={cn('markdown-preview-wrapper', className)}>
      {/* Metadata header in bordered card */}
      {showMetadata && metadata && (
        <div className="markdown-metadata-card">
          <MetadataHeader
            metadata={metadata}
            className="mb-0 rounded-none bg-transparent px-0 py-0"
          />
        </div>
      )}

      {/* Content area with proper padding */}
      <div className="markdown-content-area">
        <div className="markdown-preview" data-testid="markdown-preview">
          {/* HeadingIdProvider pre-computes IDs from content */}
          <HeadingIdProvider content={content}>
            <ReactMarkdown
              remarkPlugins={[remarkGfm]}
              rehypePlugins={[rehypeRaw]}
              components={markdownRenderers}
            >
              {content}
            </ReactMarkdown>
          </HeadingIdProvider>
        </div>
      </div>
    </div>
  )
}

MarkdownPreview.displayName = 'MarkdownPreview'
