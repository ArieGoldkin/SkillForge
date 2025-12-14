/**
 * TableOfContents - Sticky sidebar navigation for markdown content
 *
 * Features:
 * - Extracts h2 and h3 headings from markdown
 * - Sticky positioning for always-visible navigation
 * - Active section highlighting based on scroll position
 * - Smooth scroll to section on click
 * - Collapsible on mobile devices
 * - Nested h3s displayed under h2s
 */

import type * as React from 'react'
import { useMemo } from 'react'

import { cn } from '@lib/utils'

import { useActiveHeading } from './hooks/useActiveHeading'
import { useTocCollapse } from './hooks/useTocCollapse'
import type { TableOfContentsProps, TocHeading } from './types'
import { extractHeadings } from './utils'

import '@/design-system/table-of-contents.css'

/**
 * Scroll to a heading with smooth animation
 */
function scrollToHeading(headingId: string) {
  const element = document.getElementById(headingId)
  if (element) {
    const yOffset = -80 // Offset for sticky header
    const y = element.getBoundingClientRect().top + window.pageYOffset + yOffset
    window.scrollTo({ top: y, behavior: 'smooth' })
  }
}

/**
 * Individual TOC link component
 */
interface TocLinkProps {
  heading: TocHeading
  isActive: boolean
  onClick: (id: string) => void
}

const TocLink: React.FC<TocLinkProps> = ({ heading, isActive, onClick }) => {
  const isH3 = heading.level === 3

  return (
    <button
      type="button"
      onClick={() => onClick(heading.id)}
      className={cn(
        'block w-full text-left text-sm py-1.5 px-3 rounded transition-colors duration-150',
        'hover:bg-accent hover:text-accent-foreground',
        isH3 && 'pl-6 text-xs',
        isActive
          ? 'bg-primary/10 text-primary font-medium border-l-2 border-primary'
          : 'text-muted-foreground border-l-2 border-transparent'
      )}
      aria-current={isActive ? 'location' : undefined}
    >
      <span className="line-clamp-2">{heading.text}</span>
    </button>
  )
}

/**
 * Toggle button for collapsing TOC on mobile
 */
interface TocToggleProps {
  isCollapsed: boolean
  onToggle: () => void
}

const TocToggle: React.FC<TocToggleProps> = ({ isCollapsed, onToggle }) => (
  <button
    type="button"
    onClick={onToggle}
    className="lg:hidden w-full flex items-center justify-between px-4 py-3 mb-2 bg-card border border-border rounded-lg hover:bg-accent transition-colors"
    aria-expanded={!isCollapsed}
  >
    <span className="font-semibold text-sm">Table of Contents</span>
    <svg
      className={cn('w-4 h-4 transition-transform', !isCollapsed && 'rotate-180')}
      fill="none"
      stroke="currentColor"
      viewBox="0 0 24 24"
      aria-hidden="true"
    >
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
    </svg>
  </button>
)

/**
 * TOC content with headings list
 */
interface TocContentProps {
  headings: TocHeading[]
  activeId: string | null
  isCollapsed: boolean
  onLinkClick: (id: string) => void
}

const TocContent: React.FC<TocContentProps> = ({
  headings,
  activeId,
  isCollapsed,
  onLinkClick,
}) => (
  <div
    className={cn(
      'toc-content',
      'lg:block', // Always visible on desktop
      isCollapsed && 'hidden' // Hidden when collapsed on mobile
    )}
  >
    <div className="space-y-1">
      {headings.map((heading) => (
        <div key={heading.id}>
          <TocLink heading={heading} isActive={activeId === heading.id} onClick={onLinkClick} />
          {heading.children &&
            heading.children.length > 0 &&
            heading.children.map((child) => (
              <TocLink
                key={child.id}
                heading={child}
                isActive={activeId === child.id}
                onClick={onLinkClick}
              />
            ))}
        </div>
      ))}
    </div>
  </div>
)

/**
 * Main TableOfContents component
 */
export const TableOfContents: React.FC<TableOfContentsProps> = ({ content, className }) => {
  const headings = useMemo(() => extractHeadings(content), [content])
  const activeId = useActiveHeading(headings)
  const { isCollapsed, toggleCollapse } = useTocCollapse()

  // Don't render if no headings
  if (headings.length === 0) {
    return null
  }

  const handleLinkClick = (headingId: string) => {
    scrollToHeading(headingId)
  }

  return (
    <nav
      className={cn('toc-nav', className)}
      aria-label="Table of contents"
      data-testid="table-of-contents"
    >
      <TocToggle isCollapsed={isCollapsed} onToggle={toggleCollapse} />
      <TocContent
        headings={headings}
        activeId={activeId}
        isCollapsed={isCollapsed}
        onLinkClick={handleLinkClick}
      />
    </nav>
  )
}

TableOfContents.displayName = 'TableOfContents'
