/**
 * FilterSection - Collapsible filter section with accordion behavior
 */

import * as React from 'react'

import { cn } from '@/lib/utils'

/**
 * Props for FilterSection component
 */
export interface FilterSectionProps {
  title: string
  children: React.ReactNode
  defaultOpen?: boolean
}

/**
 * FilterSection component
 *
 * Provides collapsible section wrapper for filter groups.
 * Supports keyboard navigation and screen readers.
 */
export const FilterSection: React.FC<FilterSectionProps> = ({
  title,
  children,
  defaultOpen = true,
}) => {
  const [isOpen, setIsOpen] = React.useState(defaultOpen)

  return (
    <div className="space-y-2">
      <button
        type="button"
        onClick={() => setIsOpen(!isOpen)}
        className="flex w-full items-center justify-between py-2 text-sm font-medium hover:text-primary transition-colors"
        aria-expanded={isOpen}
      >
        {title}
        <span className={cn('transition-transform', isOpen && 'rotate-180')}>▼</span>
      </button>
      {isOpen && <div className="space-y-1">{children}</div>}
    </div>
  )
}

FilterSection.displayName = 'FilterSection'
